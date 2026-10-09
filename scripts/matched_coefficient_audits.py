"""Complete independent support/mask and chunk-ledger audits outside timers."""

import ctypes as C
import hashlib
import itertools
import math
import struct

from reference.matched_coefficients import BACKENDS, Domain, Session
from reference.sis import Profile, encode_case, verify
from reference.small_coefficients import candidates, dense, templates
from scripts.native_coefficient_checks import independent_vectors, late_fixture
from scripts.small_coefficient_audits import native_verdicts, oracle


def support(positions, values):
    return positions+(0,)*(3-len(positions))+values+(0,)*(3-len(values))


def audit_ledger(p, matrix, settings, result):
    patterns, template_work = templates(p, settings['bound'])
    family = list(candidates(p.m, patterns))
    checked = result['work']['screened']
    if not 1 <= checked <= min(len(family), settings['candidate_limit']):
        raise RuntimeError('coefficient checked prefix outside limits')
    weights = {str(w): dict(domain=math.comb(p.m, w)*len(values), tested=0, accepted=0, returned=0, discarded=0)
               for w, values in patterns.items()}
    coefficients = {','.join(map(str, v)): dict(domain=math.comb(p.m, w), tested=0, accepted=0, returned=0, discarded=0)
                    for w, values in patterns.items() for v in values}
    accepted, proofs = 0, []
    for positions, values in family[:checked]:
        vector = dense(p.m, positions, values)
        valid = verify(p, matrix, vector)
        emitted = valid and len(proofs) < settings['proof_limit']
        if emitted:
            proofs.append(vector)
        accepted += int(valid)
        for group in (weights[str(len(positions))], coefficients[','.join(map(str, values))]):
            group['tested'] += 1
            group['accepted'] += int(valid)
            group['returned'] += int(emitted)
            group['discarded'] += int(valid and not emitted)
    width = settings['batch_size']
    if checked % width and checked != min(len(family), settings['candidate_limit']):
        raise RuntimeError('partial coefficient chunk without input/domain boundary')
    if checked < min(len(family), settings['candidate_limit']) and accepted < settings['proof_limit']:
        raise RuntimeError('coefficient search stopped without cap')
    previous_boundary = ((checked-1)//width)*width
    earlier = sum(verify(p, matrix, dense(p.m, pos, v)) for pos, v in family[:previous_boundary])
    if earlier >= settings['proof_limit']:
        raise RuntimeError('coefficient search did not stop on first cap chunk')
    reason = 'proof-limit' if len(proofs) == settings['proof_limit'] else 'candidate-limit' if checked < len(family) else 'domain-exhausted'
    expected = dict(domain=len(family), proofs=proofs, weights=weights, coefficients=coefficients,
        reason=reason, domain_exhausted=checked == len(family),
        all_proofs_returned=checked == len(family) and accepted == len(proofs),
        checked_interval=[0, checked], unchecked_domain_suffix=len(family)-checked,
        accepted_tail_discarded=accepted-len(proofs), proof_cap_hit=len(proofs) == settings['proof_limit'],
        candidate_cap_truncates_domain=settings['candidate_limit'] < len(family), candidate_censored=reason == 'candidate-limit')
    if any(result[k] != v for k, v in expected.items()):
        raise RuntimeError('independent coefficient prefix ledger mismatch')
    gpu = result['backend'] == 'fused-gpu'
    pattern_count = sum(map(len, patterns.values()))
    payload = 8*p.n*p.m+16*pattern_count
    work = dict(**template_work, generated=checked, batches=math.ceil(checked/width), accepted_seen=accepted,
        returned=len(proofs), vector_entries=len(proofs)*p.m, matrix_entries=p.n*p.m, pattern_entries=pattern_count,
        scheduled_row_slots=checked*p.n,
        scheduled_coefficient_terms=sum(int(w)*g['tested']*p.n for w, g in weights.items()),
        primitive_returned=sum(math.gcd(*v) == 1 for v in proofs),
        nonprimitive_returned=sum(math.gcd(*v) > 1 for v in proofs), host_matrix_copy_bytes=8*p.n*p.m,
        explicit_h2d_bytes=payload if gpu else 0, explicit_d2h_bytes=checked if gpu else 0)
    if any(result['work'][k] != v for k, v in work.items()):
        raise RuntimeError('independent coefficient work mismatch')
    if (result['logical_host_matrix_bytes'] != 8*p.n*p.m or result['logical_host_pattern_bytes'] != 672
            or result['logical_device_bytes'] != (payload+width if gpu else 0)):
        raise RuntimeError('coefficient ownership mismatch')


def audit_domains(library):
    records, total = [], 0
    for m in range(1, 17):
        for b2 in (1, 2, 3, 4, 5, 8, 9, 12):
            p = Profile(17, 1, m, b2)
            for bound in (1, 2):
                patterns, _ = templates(p, bound)
                expected = [support(pos, v) for pos, v in candidates(m, patterns)]
                if m <= 4:
                    vectors = [dense(m, pos, v) for pos, v in candidates(m, patterns)]
                    if vectors != oracle(p, [[0]*m], bound):
                        raise RuntimeError('complete independent Cartesian order mismatch')
                hashes = []
                for backend in BACKENDS:
                    digest = hashlib.sha256()
                    with Session(library, p, [[0]*m], backend, bound, 257) as session:
                        for offset in range(0, session.domain, 257):
                            count = min(257, session.domain-offset)
                            decoded = session.audit(offset, count)
                            if decoded != expected[offset:offset+count]:
                                raise RuntimeError('complete native coefficient support order mismatch')
                            for item in decoded:
                                digest.update(struct.pack('<6i', *item))
                        total += session.domain
                    hashes.append(digest.hexdigest())
                if hashes[0] != hashes[1]:
                    raise RuntimeError('CPU/GPU coefficient domain digest differs')
                records.append(dict(m=m, b2=b2, bound=bound, domain=len(expected), support_sha256=hashes[0]))
    return dict(cases=len(records), audited_ordinals_both_backends=total, records=records)


def audit_masks(library, verifier, fixtures):
    cases = []
    for q in (2, 3):
        for b2 in (1, 3):
            for row in itertools.product(range(q), repeat=3):
                for bound in (1, 2):
                    cases.append((Profile(q, 1, 3, b2), [row], bound))
    cases.extend((p, matrix, bound) for _, p, matrix in fixtures for bound in (1, 2))
    checks, native_checks, chunks = 0, 0, 0
    for p, matrix, bound in cases:
        family = list(candidates(p.m, templates(p, bound)[0]))
        wanted = bytes(int(verify(p, matrix, dense(p.m, pos, v))) for pos, v in family)
        packets = [encode_case(p, matrix, dense(p.m, pos, v)) for pos, v in family]
        native_verdicts(verifier, packets, list(wanted))
        native_checks += len(packets)
        if p.m <= 4 and {dense(p.m, pos, v) for (pos, v), valid in zip(family, wanted) if valid} != independent_vectors(p, matrix, bound):
            raise RuntimeError('complete mask independent Cartesian set mismatch')
        for backend in BACKENDS:
            with Session(library, p, matrix, backend, bound, 257) as session:
                for offset in range(0, session.domain, 257):
                    count = min(257, session.domain-offset)
                    if session.mask(offset, count) != wanted[offset:offset+count]:
                        raise RuntimeError('complete coefficient mask mismatch')
                    checks += count
                    chunks += 1
        if p == late_fixture()[0] and bound == 2:
            witness = (0,)*13+(2, 2, 2)
            vectors = [dense(p.m, pos, v) for pos, v in family]
            if len(family) != 18912 or sum(wanted) != 6 or not wanted[vectors.index(witness)]:
                raise RuntimeError('late native coefficient witness missing')
    return dict(cases=len(cases), candidate_checks_both_backends=checks, backend_chunks=chunks,
                native_candidate_verdicts=native_checks)


def audit_boundaries(library):
    data = (C.c_int64*1)(0)
    handle = C.c_void_p()
    rejections = 0
    invalid = [(2, 1, 1, 17, 1, 1, 1, 1), (0, 0, 1, 17, 1, 1, 1, 1),
               (0, 65, 1, 17, 1, 1, 1, 1), (0, 1, 17, 17, 1, 1, 1, 1),
               (0, 1, 1, 15, 1, 1, 1, 1), (0, 1, 1, 2, 4, 1, 1, 1),
               (0, 1, 1, 17, 13, 1, 1, 1), (0, 1, 1, 17, 1, 3, 1, 1),
               (0, 1, 1, 17, 1, 1, 4097, 1), (0, 1, 1, 17, 1, 1, 1, 2)]
    for backend, n, m, q, b2, bound, width, entries in invalid:
        handle.value = 123
        if library.lib.cc_open(backend, data, entries, n, m, q, b2, bound, width, C.byref(handle)) != -1 or handle.value:
            raise RuntimeError('invalid coefficient open accepted')
        rejections += 1
    for backend in BACKENDS.values():
        for residue in (-1, 17):
            data[0] = residue
            if library.lib.cc_open(backend, data, 1, 1, 1, 17, 1, 1, 1, C.byref(handle)) != -1 or handle.value:
                raise RuntimeError('invalid coefficient residue accepted')
            rejections += 1
    for backend in BACKENDS:
        p = Profile(17, 1, 3, 5)
        with Session(library, p, [[0]*3], backend, 2, 7) as session:
            output, audit = (C.c_uint8*7)(), (C.c_int32*42)()
            for offset, count, length in ((-1, 1, 1), (session.domain, 1, 1), (0, 8, 7),
                                          (session.domain-1, 2, 2), (0, 1, 2), (0, 0, 0)):
                if library.lib.cc_batch(session.handle, offset, count, output, length) != -1:
                    raise RuntimeError('invalid coefficient batch accepted')
                rejections += 1
            if library.lib.cc_audit(session.handle, 0, 1, audit, 5) != -1:
                raise RuntimeError('invalid coefficient audit accepted')
            rejections += 1
    if library.lib.cc_close(None) != -1:
        raise RuntimeError('null coefficient close accepted')
    return dict(ffi_rejections=rejections+1)
