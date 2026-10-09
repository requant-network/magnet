"""Independent tiny-box and late-witness audits for the SCP1 search engine."""

import itertools
import random
import struct

from reference.native_coefficients import MAX_REQUEST, encode_request, exchange, search_many
from reference.sis import Profile, verify
from scripts.small_coefficient_audits import audit_search


def late_fixture():
    p = Profile(65521, 64, 16, 12)
    matrix = [[int(row == column) for column in range(16)] for row in range(13)]
    matrix.append([0]*13+[65520, 65520, 2])
    matrix.extend([[0]*16 for _ in range(50)])
    return p, matrix


def independent_vectors(profile, matrix, bound):
    # Full box order is intentionally unrelated to the support/template engine.
    return {v for v in itertools.product(range(-bound, bound+1), repeat=profile.m)
            if next((x for x in v if x), 0) > 0 and sum(x != 0 for x in v) <= 3
            and sum(x*x for x in v) <= profile.b2 and verify(profile, matrix, v)}


def differential_coefficients(executable):
    rng = random.Random(2026100922)
    cases = []
    for i in range(96):
        q = rng.choice((3, 7, 17, 257, 65521))
        p = Profile(q, rng.randint(1, 5), rng.randint(1, 16), rng.randint(1, min(12, q*q-1)))
        matrix = [[rng.randrange(q) for _ in range(p.m)] for _ in range(p.n)]
        if i % 6 == 0:
            matrix = [[0]*p.m for _ in range(p.n)]
        elif i % 6 == 1 and p.m > 1:
            for row in matrix:
                row[-1] = row[0]
        for bound in (1, 2):
            for cap, proofs in ((1, 1), (31, 3), (4096, 32), (20000, 256)):
                cases.append((p, matrix, dict(bound=bound, candidate_limit=cap, proof_limit=proofs)))
    outputs, _ = search_many(executable, cases)
    proof_checks = 0
    for (p, matrix, _), output in zip(cases, outputs):
        for v in output['result']['proofs']:
            if not verify(p, matrix, v):
                raise RuntimeError('native returned invalid SIS proof')
            proof_checks += 1
    tiny_cases, tiny_candidates = 0, 0
    for q in (3, 7, 17):
        for m in (1, 2, 3, 4):
            p = Profile(q, 2, m, min(12, q*q-1))
            for zero in (False, True):
                matrix = [[0 if zero else rng.randrange(q) for _ in range(m)] for _ in range(2)]
                for bound in (1, 2):
                    result = search_many(executable, [(p, matrix, dict(bound=bound))])[0][0]['result']
                    expected = independent_vectors(p, matrix, bound)
                    if not result['domain_exhausted'] or set(result['proofs']) != expected:
                        raise RuntimeError('independent tiny box disagreement')
                    audit_search(p, matrix, bound, result, 20000, 256)
                    tiny_candidates += result['domain']
                    tiny_cases += 1
    p, matrix = late_fixture()
    late = search_many(executable, [(p, matrix, dict(bound=2))])[0][0]['result']
    late_expected = {(0,)*13+v for v in independent_vectors(Profile(65521, 1, 3, 12), [[65520, 65520, 2]], 2)}
    if (late['work']['screened'] != 18912 or not late['domain_exhausted']
            or (0,)*13+(2, 2, 2) not in late['proofs'] or set(late['proofs']) != late_expected):
        raise RuntimeError('maximum-shape late witness missing or censored')
    packet = encode_request(Profile(17, 1, 2, 5), [[1, 2]], bound=2)
    malformed = [b'\x01', struct.pack('<I', MAX_REQUEST+1), struct.pack('<I', 32)+b'abc',
                 struct.pack('<I', 0)]
    mutations = ((0, b'BAD!'), (4, struct.pack('<I', 15)), (8, struct.pack('<H', 0)),
                 (10, struct.pack('<H', 17)), (12, struct.pack('<Q', 289)), (20, b'\x03'),
                 (21, b'\x01'), (24, struct.pack('<I', 0)), (28, struct.pack('<I', 257)),
                 (32, struct.pack('<I', 17)))
    for offset, replacement in mutations:
        bad = packet[:offset]+replacement+packet[offset+len(replacement):]
        malformed.append(struct.pack('<I', len(bad))+bad)
    malformed.append(struct.pack('<I', len(packet)-1)+packet[:-1])
    valid_frame = struct.pack('<I', len(packet))+packet
    # Even when a valid response precedes an invalid request, the batch is unusable.
    malformed.append(valid_frame+struct.pack('<I', 0))
    for wire in malformed:
        try:
            exchange(executable, wire, 2*17768, timeout=5)
        except RuntimeError:
            continue
        raise RuntimeError('native malformed request accepted')
    if search_many(executable, [])[0] != []:
        raise RuntimeError('empty stream mismatch')
    return dict(seed=2026100922, comparisons=len(cases), proof_checks=proof_checks,
                tiny_box_cases=tiny_cases, tiny_candidates=tiny_candidates,
                malformed_rejections=len(malformed), empty_stream_checks=1,
                late_witness=dict(profile=(65521, 64, 16, 12), screened=18912,
                                  proofs=len(late['proofs']), full_domain=True), mismatches=0)
