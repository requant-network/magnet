"""Identical in-process wrappers for native CPU/GPU acquisition (spec/20)."""

import ctypes as C
from pathlib import Path
import time

from reference.sparse_domain import (charge_mask, new_weights, result_for, support_at,
                                     validate, vector_for, weight_domains)

BACKENDS = {'native-cpu': 0, 'fused-gpu': 1}


class MaskValidationFailure(RuntimeError):
    def __init__(self, count):
        super().__init__('nonboolean matched mask after successful FFI completion')
        self.completed_mask_count = count


class Library:
    def __init__(self, path):
        self.path = Path(path).resolve(strict=True)
        lib = self.lib = C.CDLL(str(self.path))
        signatures = {
            'sp_abi_version': ([], C.c_int), 'sp_error': ([C.c_int], C.c_char_p),
            'sp_runtime': ([C.POINTER(C.c_int)], C.c_int), 'sp_sync': ([], C.c_int),
            'sp_open': ([C.c_int, C.POINTER(C.c_int64), C.c_size_t, C.c_int, C.c_int, C.c_int,
                         C.c_uint64, C.c_int, C.c_int, C.POINTER(C.c_void_p)], C.c_int),
            'sp_batch': ([C.c_void_p, C.c_int, C.c_int, C.POINTER(C.c_uint8), C.c_size_t], C.c_int),
            'sp_audit': ([C.c_void_p, C.c_int, C.c_int, C.POINTER(C.c_int32), C.c_size_t], C.c_int),
            'sp_close': ([C.c_void_p], C.c_int)}
        for name, (arguments, output) in signatures.items():
            function = getattr(lib, name)
            function.argtypes, function.restype = arguments, output
        if lib.sp_abi_version() != 1:
            raise RuntimeError('unsupported matched sparse ABI')
        runtime = C.c_int()
        self.check(lib.sp_runtime(C.byref(runtime)))
        self.runtime_version = runtime.value

    def check(self, code):
        if code:
            raise RuntimeError(f'matched sparse error {code}: '+self.lib.sp_error(code).decode('utf-8', 'replace'))


class Session:
    def __init__(self, library, profile, matrix, backend, max_weight, width):
        validate(profile, matrix, max_weight, 65536, 256, width)
        if type(backend) is not str or backend not in BACKENDS:
            raise ValueError('unknown matched backend')
        self.library, self.width = library, width
        self.domain = sum(weight_domains(profile, max_weight).values())
        self.handle = C.c_void_p()
        entries = profile.n*profile.m
        data = (C.c_int64*entries)(*(a for row in matrix for a in row))
        library.check(library.lib.sp_open(BACKENDS[backend], data, entries, profile.n, profile.m, profile.q,
                                        profile.b2, max_weight, width, C.byref(self.handle)))
        if not self.handle.value:
            raise RuntimeError('null matched sparse session')

    def __enter__(self):
        return self

    def __exit__(self, kind, error, traceback):
        handle, self.handle = self.handle, C.c_void_p()
        try:
            self.library.check(self.library.lib.sp_close(handle))
        except RuntimeError as cleanup:
            if error is None:
                raise
            error.add_note(str(cleanup))

    def _range(self, offset, count):
        if (not self.handle.value or type(offset) is not int or type(count) is not int
                or not 0 <= offset < self.domain or not 1 <= count <= self.width or offset+count > self.domain):
            raise ValueError('invalid/closed matched range')

    def mask(self, offset, count):
        self._range(offset, count)
        result = (C.c_uint8*count)()
        self.library.check(self.library.lib.sp_batch(self.handle, offset, count, result, count))
        flags = bytes(result)
        if any(v not in (0, 1) for v in flags):
            raise MaskValidationFailure(count)
        return flags

    def audit(self, offset, count):
        self._range(offset, count)
        result = (C.c_int32*(6*count))()
        self.library.check(self.library.lib.sp_audit(self.handle, offset, count, result, 6*count))
        return [tuple(result[i:i+6]) for i in range(0, 6*count, 6)]


class SearchFailure(RuntimeError):
    def __init__(self, diagnostic):
        super().__init__('matched search failed at '+diagnostic['stage'])
        self.diagnostic = diagnostic


def search(profile, matrix, *, library, backend, max_weight, candidate_limit=65536, proof_limit=256, batch_size=256):
    begin = time.perf_counter_ns()
    stage, checked, batches, accepted = 'validation', 0, 0, 0
    try:
        validate(profile, matrix, max_weight, candidate_limit, proof_limit, batch_size)
        if type(backend) is not str or backend not in BACKENDS:
            raise ValueError('unknown matched backend')
        weights, proofs = new_weights(profile, max_weight), []
        end = min(sum(w['domain'] for w in weights.values()), candidate_limit)
        stage = 'session-open'
        with Session(library, profile, matrix, backend, max_weight, batch_size) as session:
            for offset in range(0, end, batch_size):
                stage = 'mask-completion'
                count = min(batch_size, end-offset)
                flags = session.mask(offset, count)
                # Completed masks remain charged if later host decoding fails.
                checked += count
                batches += 1
                accepted += sum(flags)
                stage = 'output-decode'
                emitted = [offset+i for i, valid in enumerate(flags) if valid][:proof_limit-len(proofs)]
                proofs.extend(vector_for(profile.m, support_at(profile.m, i)) for i in emitted)
                charge_mask(weights, offset, flags, emitted)
                if len(proofs) == proof_limit:
                    break
            stage = 'session-close'
        stage = 'result-ledger'
        result = result_for(profile, max_weight, candidate_limit, proof_limit, batch_size, proofs, weights, batches)
        result['backend'] = backend
        result['work'].update(host_matrix_copy_bytes=8*profile.n*profile.m,
                              explicit_h2d_bytes=8*profile.n*profile.m if backend == 'fused-gpu' else 0,
                              explicit_d2h_bytes=checked if backend == 'fused-gpu' else 0)
        result['logical_host_matrix_bytes'] = 8*profile.n*profile.m
        result['logical_device_bytes'] = 8*profile.n*profile.m+batch_size if backend == 'fused-gpu' else 0
        result['elapsed_ns'] = time.perf_counter_ns()-begin
        return result
    except Exception as error:
        if stage == 'validation':
            raise
        completed_mask = getattr(error, 'completed_mask_count', 0)
        raise SearchFailure(dict(backend=backend, stage='mask-validation' if completed_mask else stage,
                                 elapsed_ns=time.perf_counter_ns()-begin,
                                 completed_screened=checked+completed_mask,
                                 completed_batches=batches+int(bool(completed_mask)),
                                 completed_accepted=None if completed_mask else accepted,
                                 validated_screened=checked, validated_batches=batches,
                                 validated_accepted=accepted, detail=str(error),
                                 cleanup_notes=getattr(error, '__notes__', []))) from error
