"""Matched CPU/CUDA chunks over spec21; independent host unranking and ledgers."""

import ctypes as C
import itertools
import math
from pathlib import Path
import time

from reference.small_coefficients import dense, candidates, screen, templates, validate

BACKENDS = {'native-cpu': 0, 'fused-gpu': 1}


def validate_settings(profile, matrix, bound, candidate_limit, proof_limit, batch_size):
    validate(profile, matrix, bound, candidate_limit, proof_limit)
    if type(batch_size) is not int or not 1 <= batch_size <= 4096:
        raise ValueError('coefficient chunk outside range')


class Domain:
    def __init__(self, profile, bound):
        self.m = profile.m
        self.patterns, self.template_work = templates(profile, bound)
        self.sizes = {w: math.comb(profile.m, w)*len(v) for w, v in self.patterns.items()}
        self.size = sum(self.sizes.values())
        self.pattern_count = sum(map(len, self.patterns.values()))

    def at(self, ordinal):
        if type(ordinal) is not int or not 0 <= ordinal < self.size:
            raise ValueError('coefficient ordinal outside domain')
        for w, patterns in self.patterns.items():
            if ordinal < self.sizes[w]:
                rank, pattern = divmod(ordinal, len(patterns))
                positions, minimum = [], 0
                for left in range(w, 0, -1):
                    for position in range(minimum, self.m-left+1):
                        block = math.comb(self.m-position-1, left-1)
                        if rank < block:
                            positions.append(position)
                            minimum = position+1
                            break
                        rank -= block
                return tuple(positions), patterns[pattern]
            ordinal -= self.sizes[w]
        raise RuntimeError('unreachable coefficient ordinal')


class MaskValidationFailure(RuntimeError):
    def __init__(self, count):
        super().__init__('nonboolean coefficient mask after successful completion')
        self.completed_mask_count = count


class Library:
    def __init__(self, path):
        self.path = Path(path).resolve(strict=True)
        lib = self.lib = C.CDLL(str(self.path))
        signatures = {
            'cc_abi_version': ([], C.c_int), 'cc_error': ([C.c_int], C.c_char_p),
            'cc_runtime': ([C.POINTER(C.c_int)], C.c_int), 'cc_sync': ([], C.c_int),
            'cc_open': ([C.c_int, C.POINTER(C.c_int64), C.c_size_t, C.c_int, C.c_int, C.c_int,
                         C.c_uint64, C.c_int, C.c_int, C.POINTER(C.c_void_p)], C.c_int),
            'cc_batch': ([C.c_void_p, C.c_int, C.c_int, C.POINTER(C.c_uint8), C.c_size_t], C.c_int),
            'cc_audit': ([C.c_void_p, C.c_int, C.c_int, C.POINTER(C.c_int32), C.c_size_t], C.c_int),
            'cc_close': ([C.c_void_p], C.c_int)}
        for name, (args, result) in signatures.items():
            function = getattr(lib, name)
            function.argtypes, function.restype = args, result
        if lib.cc_abi_version() != 1:
            raise RuntimeError('unsupported coefficient ABI')
        runtime = C.c_int()
        self.check(lib.cc_runtime(C.byref(runtime)))
        self.runtime_version = runtime.value

    def check(self, code):
        if code:
            raise RuntimeError(f'coefficient FFI error {code}: '+self.lib.cc_error(code).decode('utf-8', 'replace'))


class Session:
    def __init__(self, library, profile, matrix, backend, bound, width):
        validate_settings(profile, matrix, bound, 20000, 256, width)
        if type(backend) is not str or backend not in BACKENDS:
            raise ValueError('unknown coefficient backend')
        self.library, self.width = library, width
        self.domain = Domain(profile, bound).size
        self.handle = C.c_void_p()
        entries = profile.n*profile.m
        matrix_buffer = (C.c_int64*entries)(*(a for row in matrix for a in row))
        library.check(library.lib.cc_open(BACKENDS[backend], matrix_buffer, entries, profile.n, profile.m,
                                        profile.q, profile.b2, bound, width, C.byref(self.handle)))
        if not self.handle.value:
            raise RuntimeError('null coefficient session')

    def __enter__(self):
        return self

    def __exit__(self, kind, error, traceback):
        handle, self.handle = self.handle, C.c_void_p()
        try:
            self.library.check(self.library.lib.cc_close(handle))
        except RuntimeError as cleanup:
            if error is None:
                raise
            error.add_note(str(cleanup))

    def _range(self, offset, count):
        if (not self.handle.value or type(offset) is not int or type(count) is not int
                or not 0 <= offset < self.domain or not 1 <= count <= self.width
                or count > self.domain-offset):
            raise ValueError('invalid or closed coefficient range')

    def mask(self, offset, count):
        self._range(offset, count)
        out = (C.c_uint8*count)()
        self.library.check(self.library.lib.cc_batch(self.handle, offset, count, out, count))
        try:
            flags = bytes(out)
            if any(x not in (0, 1) for x in flags):
                raise MaskValidationFailure(count)
            return flags
        except Exception as error:
            # FFI has completed even if Python cannot allocate/validate the bytes.
            error.completed_mask_count = count
            raise

    def audit(self, offset, count):
        self._range(offset, count)
        out = (C.c_int32*(6*count))()
        self.library.check(self.library.lib.cc_audit(self.handle, offset, count, out, 6*count))
        return [tuple(out[i:i+6]) for i in range(0, 6*count, 6)]


def ledger(domain, checked, hits, emitted):
    weights, coefficients, base = {}, {}, 0
    for w, patterns in domain.patterns.items():
        tested = min(max(checked-base, 0), domain.sizes[w])
        weights[str(w)] = dict(domain=domain.sizes[w], tested=tested, accepted=0, returned=0, discarded=0)
        for index, values in enumerate(patterns):
            coefficients[','.join(map(str, values))] = dict(domain=math.comb(domain.m, w),
                tested=(tested+len(patterns)-1-index)//len(patterns), accepted=0, returned=0, discarded=0)
        base += domain.sizes[w]
    emitted = set(emitted)
    for ordinal in hits:
        positions, values = domain.at(ordinal)
        for group in (weights[str(len(positions))], coefficients[','.join(map(str, values))]):
            group['accepted'] += 1
            group['returned' if ordinal in emitted else 'discarded'] += 1
    return weights, coefficients


def result_for(profile, domain, bound, cap, proof_cap, width, checked, batches, hits, emitted, proofs):
    weights, coefficients = ledger(domain, checked, hits, emitted)
    exhausted = checked == domain.size
    reason = 'proof-limit' if len(proofs) == proof_cap else 'candidate-limit' if not exhausted else 'domain-exhausted'
    return dict(bound=bound, domain=domain.size, proofs=proofs, weights=weights, coefficients=coefficients,
        reason=reason, domain_exhausted=exhausted, all_proofs_returned=exhausted and len(hits) == len(proofs),
        checked_interval=[0, checked], unchecked_domain_suffix=domain.size-checked,
        proof_cap_hit=len(proofs) == proof_cap, candidate_cap_truncates_domain=cap < domain.size,
        candidate_censored=reason == 'candidate-limit', accepted_tail_discarded=len(hits)-len(proofs),
        work=dict(**domain.template_work, generated=checked, screened=checked, batches=batches,
            accepted_seen=len(hits), returned=len(proofs), vector_entries=len(proofs)*profile.m,
            matrix_entries=profile.n*profile.m, pattern_entries=domain.pattern_count,
            scheduled_row_slots=checked*profile.n,
            scheduled_coefficient_terms=sum(int(w)*g['tested']*profile.n for w, g in weights.items()),
            primitive_returned=sum(math.gcd(*v) == 1 for v in proofs),
            nonprimitive_returned=sum(math.gcd(*v) > 1 for v in proofs)), chunk_width=width)


class SearchFailure(RuntimeError):
    def __init__(self, diagnostic):
        super().__init__('coefficient search failed: '+diagnostic['stage'])
        self.diagnostic = diagnostic


def search(profile, matrix, *, library, backend, bound, candidate_limit=20000, proof_limit=256, batch_size=256):
    begin = time.perf_counter_ns()
    stage, checked, batches, hits, accepted = 'validation', 0, 0, [], 0
    try:
        validate_settings(profile, matrix, bound, candidate_limit, proof_limit, batch_size)
        if type(backend) is not str or backend not in BACKENDS:
            raise ValueError('unknown coefficient backend')
        domain = Domain(profile, bound)
        proofs, emitted = [], []
        stage = 'session-open'
        with Session(library, profile, matrix, backend, bound, batch_size) as session:
            for offset in range(0, min(domain.size, candidate_limit), batch_size):
                stage = 'mask-completion'
                count = min(batch_size, min(domain.size, candidate_limit)-offset)
                flags = session.mask(offset, count)
                checked += count
                batches += 1
                stage = 'mask-accounting'
                accepted += sum(flags)
                stage = 'output-decode'
                current_hits = [offset+i for i, flag in enumerate(flags) if flag]
                hits.extend(current_hits)
                selected = current_hits[:proof_limit-len(proofs)]
                for ordinal in selected:
                    proofs.append(dense(profile.m, *domain.at(ordinal)))
                emitted.extend(selected)
                if len(proofs) == proof_limit:
                    break
            stage = 'session-close'
        stage = 'result-ledger'
        result = result_for(profile, domain, bound, candidate_limit, proof_limit, batch_size,
                            checked, batches, hits, emitted, proofs)
        gpu = backend == 'fused-gpu'
        payload = 8*profile.n*profile.m+16*domain.pattern_count
        result.update(backend=backend, logical_host_matrix_bytes=8*profile.n*profile.m,
                      logical_host_pattern_bytes=42*16,
                      logical_device_bytes=payload+batch_size if gpu else 0)
        result['work'].update(host_matrix_copy_bytes=8*profile.n*profile.m,
                              explicit_h2d_bytes=payload if gpu else 0,
                              explicit_d2h_bytes=checked if gpu else 0)
        result['elapsed_ns'] = time.perf_counter_ns()-begin
        return result
    except Exception as error:
        if stage == 'validation':
            raise
        corrupt = getattr(error, 'completed_mask_count', 0)
        raise SearchFailure(dict(backend=backend, stage='mask-validation' if corrupt else stage,
            completed_screened=checked+corrupt, completed_batches=batches+int(bool(corrupt)),
            completed_accepted=None if corrupt or stage == 'mask-accounting' else accepted, validated_screened=checked,
            validated_batches=batches, validated_accepted=None if stage == 'mask-accounting' else accepted,
            in_flight_work_unknown=stage == 'mask-completion' and not corrupt,
            elapsed_ns=time.perf_counter_ns()-begin, detail=str(error),
            cleanup_notes=getattr(error, '__notes__', []))) from error


def reference_search(profile, matrix, *, bound, candidate_limit=20000, proof_limit=256, batch_size=256):
    validate_settings(profile, matrix, bound, candidate_limit, proof_limit, batch_size)
    domain = Domain(profile, bound)
    iterator = candidates(profile.m, domain.patterns)
    hits, emitted, proofs, checked, batches = [], [], [], 0, 0
    for offset in range(0, min(domain.size, candidate_limit), batch_size):
        count = min(batch_size, min(domain.size, candidate_limit)-offset)
        current = []
        for index, (positions, values) in enumerate(itertools.islice(iterator, count)):
            if screen(matrix, positions, values, profile.q)[0]:
                current.append(offset+index)
        hits.extend(current)
        selected = current[:proof_limit-len(proofs)]
        emitted.extend(selected)
        proofs.extend(dense(profile.m, *domain.at(i)) for i in selected)
        checked += count
        batches += 1
        if len(proofs) == proof_limit:
            break
    return result_for(profile, domain, bound, candidate_limit, proof_limit, batch_size,
                      checked, batches, hits, emitted, proofs)


def reconcile(expected, actual):
    for key, value in expected.items():
        if key == 'work':
            for counter, amount in value.items():
                if actual['work'].get(counter) != amount:
                    raise RuntimeError('matched coefficient counter mismatch: '+counter)
        elif actual.get(key) != value:
            raise RuntimeError('matched coefficient result mismatch: '+key)
