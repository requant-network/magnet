"""Independent acquisition/FFI/full-domain audits outside matched search timing."""

import ctypes as C
import hashlib
import itertools
import math
import struct

from reference.matched_sparse import Session
from reference.sis import Profile
from reference.sparse_domain import supports, vector_for

COMMON = ('domain', 'reason', 'domain_exhausted', 'all_proofs_returned', 'proofs', 'weights',
          'checked_interval', 'proof_cap_hit', 'candidate_cap_truncates_domain', 'candidate_censored',
          'unchecked_domain_suffix', 'accepted_tail_discarded')


def reconcile(expected, actual):
    for key in COMMON:
        if expected[key] != actual[key]:
            raise RuntimeError('matched acquisition differs: '+key)
    for key, value in expected['work'].items():
        if actual['work'][key] != value:
            raise RuntimeError('matched common work differs: '+key)


def audit_ledger(p, settings, result):
    w, weights = result['work'], result['weights']
    domain_weights = (p.m, p.m*(p.m-1) if min(p.b2, settings['max_weight']) >= 2 else 0,
                      4*math.comb(p.m, 3) if min(p.b2, settings['max_weight']) >= 3 else 0)
    checked, returned = w['screened'], len(result['proofs'])
    start, coefficients = 0, 0
    for weight, domain in enumerate(domain_weights, 1):
        data = weights[str(weight)]
        tested = max(0, min(checked-start, domain))
        if (data['domain'] != domain or data['tested'] != tested or not 0 <= data['emitted'] <= data['accepted'] <= tested
                or data['discarded'] != data['accepted']-data['emitted']):
            raise RuntimeError('matched weight census mismatch')
        coefficients += weight*tested
        start += domain
    accepted = sum(v['accepted'] for v in weights.values())
    if (sum(v['emitted'] for v in weights.values()) != returned or result['domain'] != start
            or result['checked_interval'] != [0, checked] or w['accepted_seen'] != accepted
            or returned != min(settings['proof_limit'], accepted)):
        raise RuntimeError('matched outcome census mismatch')
    end = min(start, settings['candidate_limit'])
    if checked != min(w['batches']*settings['batch_size'], end):
        raise RuntimeError('matched paid chunk mismatch')
    gpu = result['backend'] == 'fused-gpu'
    expected = dict(generated=checked, returned=returned, vector_entries=returned*p.m,
                    support_slots=6*checked, scheduled_column_reads=p.n*coefficients, matrix_entries=p.n*p.m,
                    host_matrix_copy_bytes=8*p.n*p.m, explicit_h2d_bytes=8*p.n*p.m if gpu else 0,
                    explicit_d2h_bytes=checked if gpu else 0)
    if any(w[key] != value for key, value in expected.items()):
        raise RuntimeError('matched transfer/materialization mismatch')
    if (result['logical_host_matrix_bytes'] != 8*p.n*p.m or
            result['logical_device_bytes'] != (8*p.n*p.m+settings['batch_size'] if gpu else 0)):
        raise RuntimeError('matched logical ownership mismatch')


def audit_domains(library):
    records = []
    # Full large domain at m128, plus awkward widths/family boundaries at m1..32.
    for m, b2, width in ((1, 1, 1), (2, 3, 3), (3, 3, 7), (8, 3, 13),
                          (16, 3, 64), (32, 3, 4096), (128, 3, 4096)):
        p = Profile(65521, 1, m, b2)
        for maximum in (2, 3):
            hashes = []
            for backend in ('native-cpu', 'fused-gpu'):
                digest, oracle = hashlib.sha256(), supports(p, maximum)
                with Session(library, p, [[0]*m], backend, maximum, width) as session:
                    for offset in range(0, session.domain, width):
                        count = min(width, session.domain-offset)
                        actual = session.audit(offset, count)
                        if actual != list(itertools.islice(oracle, count)):
                            raise RuntimeError('matched full support order disagreement')
                        for support in actual:
                            digest.update(struct.pack('<6i', *support))
                    domain = session.domain
                hashes.append(digest.hexdigest())
            if hashes[0] != hashes[1]:
                raise RuntimeError('matched domain hashes differ')
            records.append(dict(m=m, b2=b2, max_weight=maximum, batch_size=width,
                                candidates_per_backend=domain, ordered_supports_sha256=hashes[0]))
    return records


def audit_boundaries(library):
    rejects = 0
    data, handle = (C.c_int64*1)(0), C.c_void_p()
    invalid = [(0, 0, 1, 7, 3, 3, 1, 1), (0, 65, 1, 7, 3, 3, 1, 1),
               (0, 1, 129, 7, 3, 3, 1, 1), (2, 1, 1, 7, 3, 3, 1, 1),
               (0, 1, 1, 4, 3, 3, 1, 1), (0, 1, 1, 7, 49, 3, 1, 1),
               (0, 1, 1, 7, 0, 3, 1, 1), (0, 1, 1, 7, 3, 4, 1, 1),
               (0, 1, 1, 7, 3, 3, 4097, 1), (0, 1, 1, 7, 3, 3, 1, 2)]
    for backend, n, m, q, b2, weight, width, entries in invalid:
        handle.value = 123
        if library.lib.sp_open(backend, data, entries, n, m, q, b2, weight, width, C.byref(handle)) != -1 or handle.value:
            raise RuntimeError('matched invalid C open accepted')
        rejects += 1
    for backend in (0, 1):
        for residue in (-1, 7):
            data[0] = residue
            if library.lib.sp_open(backend, data, 1, 1, 1, 7, 3, 3, 1, C.byref(handle)) != -1 or handle.value:
                raise RuntimeError('matched invalid C matrix accepted')
            rejects += 1
    probes = []
    for q in (2, 3):
        for b2 in (1, 2, 3):
            for row in itertools.product(range(q), repeat=3):
                probes.append((Profile(q, 1, 3, b2), [row], 2))
    p = Profile(65521, 64, 128, 65521**2-1)
    maximum_matrix = [[(i % 8)*9360 % p.q for i in range(p.m)] for _ in range(p.n)]
    for row in maximum_matrix:
        row[:3] = [p.q-1, p.q-1, 2]  # (+++) wraps to 2*q.
        row[-3:] = [p.q-1, 2, 1]  # Last triple (+,+,-) wraps to q.
    # Full mask domain for max dimensions at weight2; bounded labelled triple
    # regions exercise transitions and last-domain ordinal without huge host proof audits.
    probes.append((p, maximum_matrix, 4096))
    masks, tested = 0, 0
    for p, matrix, width in probes:
        maximum = 2 if p.m == 128 else 3
        for backend in ('native-cpu', 'fused-gpu'):
            oracle = supports(p, maximum)
            with Session(library, p, matrix, backend, maximum, width) as session:
                for offset in range(0, session.domain, width):
                    count = min(width, session.domain-offset)
                    chunk = list(itertools.islice(oracle, count))
                    wanted = bytes(int(all(sum(row[i]*a for i, a in zip(s[:3], s[3:]) if a) % p.q == 0
                                          for row in matrix)) for s in chunk)
                    if session.mask(offset, count) != wanted:
                        raise RuntimeError('matched full mask disagreement')
                    masks += 1
                    tested += count
                out = (C.c_uint8*2)()
                for offset, count, length in ((-1, 1, 1), (session.domain, 1, 1), (0, 1, 2)):
                    if library.lib.sp_batch(session.handle, offset, count, out, length) != -1:
                        raise RuntimeError('matched invalid C batch accepted')
                    rejects += 1
    regions = []
    p = Profile(65521, 64, 128, 65521**2-1)
    matrix = maximum_matrix
    for offset, count in ((127, 3), (16383, 4), (65530, 13), (1381888-7, 7)):
        wanted = bytes(int(all(sum(row[i]*a for i, a in zip(s[:3], s[3:]) if a) % p.q == 0
                              for row in matrix))
                       for s in itertools.islice(supports(p, 3), offset, offset+count))
        for backend in ('native-cpu', 'fused-gpu'):
            with Session(library, p, matrix, backend, 3, 4096) as session:
                if session.mask(offset, count) != wanted:
                    raise RuntimeError('matched triple boundary-region disagreement')
        regions.append(dict(offset=offset, count=count, accepted=sum(wanted)))
    return dict(ffi_rejections=rejects, full_mask_cases=len(probes), full_mask_backend_chunks=masks,
                full_mask_backend_ordinals=tested, maximum_shape_triple_regions=regions)
