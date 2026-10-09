"""Owned CUDA sessions; exact fused column masks, no CPU fallback (spec/19)."""

import ctypes as C
from pathlib import Path
import time

from reference.column_search import support_at, vector_for
from reference.native_columns import validate


class Library:
    """Load only an explicitly built trusted local library. ABI is not a sandbox."""
    def __init__(self, path):
        self.path = Path(path).resolve(strict=True)
        lib = self.lib = C.CDLL(str(self.path))
        lib.mg_abi_version.argtypes = []
        lib.mg_abi_version.restype = C.c_int
        if lib.mg_abi_version() != 1:
            raise RuntimeError('unsupported fused CUDA ABI')
        lib.mg_error.argtypes = [C.c_int]
        lib.mg_error.restype = C.c_char_p
        lib.mg_open.argtypes = [C.POINTER(C.c_int64), C.c_size_t, C.c_int, C.c_int, C.c_int,
                               C.c_int, C.c_int, C.POINTER(C.c_void_p)]
        lib.mg_open.restype = C.c_int
        lib.mg_batch.argtypes = [C.c_void_p, C.c_int, C.c_int, C.POINTER(C.c_uint8), C.c_size_t]
        lib.mg_batch.restype = C.c_int
        lib.mg_audit.argtypes = [C.c_void_p, C.c_int, C.c_int, C.POINTER(C.c_int32), C.c_size_t]
        lib.mg_audit.restype = C.c_int
        lib.mg_close.argtypes = [C.c_void_p]
        lib.mg_close.restype = C.c_int
        lib.mg_runtime_version.argtypes = [C.POINTER(C.c_int)]
        lib.mg_runtime_version.restype = C.c_int
        runtime = C.c_int()
        self.check(lib.mg_runtime_version(C.byref(runtime)))
        self.runtime_version = runtime.value

    def check(self, code):
        if code:
            raise RuntimeError(f'fused CUDA error {code}: '+self.lib.mg_error(code).decode('utf-8', 'replace'))


class Session:
    def __init__(self, library, profile, matrix, width):
        validate(profile, matrix, 16384, 256, width)
        self.library, self.profile, self.width = library, profile, width
        self.domain = profile.m if profile.b2 == 1 else profile.m**2
        self.handle = C.c_void_p()
        entries = profile.n*profile.m
        data = (C.c_int64*entries)(*(a for row in matrix for a in row))
        library.check(library.lib.mg_open(data, entries, profile.n, profile.m, profile.q,
                                        int(profile.b2 == 1), width, C.byref(self.handle)))
        if not self.handle.value:
            raise RuntimeError('fused CUDA returned null session')

    def __enter__(self):
        return self

    def __exit__(self, kind, error, traceback):
        handle, self.handle = self.handle, C.c_void_p()
        try:
            self.library.check(self.library.lib.mg_close(handle))
        except RuntimeError as cleanup:
            if error is None:
                raise
            error.add_note(str(cleanup))

    def _range(self, offset, count):
        if (not self.handle.value or type(offset) is not int or type(count) is not int
                or not 0 <= offset < self.domain or not 1 <= count <= self.width
                or offset+count > self.domain):
            raise ValueError('invalid/closed fused session range')

    def mask(self, offset, count):
        self._range(offset, count)
        result = (C.c_uint8*count)()
        self.library.check(self.library.lib.mg_batch(self.handle, offset, count, result, count))
        values = bytes(result)
        if any(v not in (0, 1) for v in values):
            raise RuntimeError('nonboolean CUDA mask')
        return values

    def audit(self, offset, count):
        self._range(offset, count)
        result = (C.c_int32*(3*count))()
        self.library.check(self.library.lib.mg_audit(self.handle, offset, count, result, 3*count))
        return [tuple(result[i:i+3]) for i in range(0, 3*count, 3)]


def search(profile, matrix, *, library, candidate_limit=16384, proof_limit=256, batch_size=256):
    begin = time.perf_counter_ns()
    validate(profile, matrix, candidate_limit, proof_limit, batch_size)
    domain = profile.m if profile.b2 == 1 else profile.m**2
    starts = tuple(i*(2*profile.m-i-1)//2 for i in range(profile.m))
    proofs, checked, batches, accepted = [], 0, 0, 0
    reason = 'domain-exhausted'
    end = min(domain, candidate_limit)
    with Session(library, profile, matrix, batch_size) as session:
        for offset in range(0, end, batch_size):
            count = min(batch_size, end-offset)
            flags = session.mask(offset, count)
            accepted += sum(flags)
            ordinals = [offset+i for i, valid in enumerate(flags) if valid][:proof_limit-len(proofs)]
            proofs.extend(vector_for(profile.m, support_at(profile.m, i, starts)) for i in ordinals)
            checked += count
            batches += 1
            if len(proofs) == proof_limit:
                reason = 'proof-limit'
                break
    if reason != 'proof-limit' and checked < domain:
        reason = 'candidate-limit'
    exhausted = checked == domain
    work = dict(generated=checked, screened=checked, vector_entries=len(proofs)*profile.m,
                matrix_grid_slots=checked*profile.n*profile.m, matrix_entries=profile.n*profile.m,
                batches=batches, accepted_seen=accepted, returned=len(proofs), support_entries=3*checked,
                scheduled_column_reads=2*checked*profile.n, host_prefix_entries=profile.m,
                device_prefix_entries=0, column_table_entries=0, explicit_h2d_bytes=8*profile.n*profile.m,
                explicit_d2h_bytes=checked, kernel_launches=batches)
    return dict(backend='cuda-fused', domain=domain, reason=reason, domain_exhausted=exhausted,
                all_proofs_returned=exhausted and accepted == len(proofs), proofs=proofs, work=work,
                elapsed_ns=time.perf_counter_ns()-begin,
                logical_owned_device_bytes=8*profile.n*profile.m+batch_size)
