"""Independent Cartesian acceptance/order oracles, complete balls and Rust checks."""

import hashlib
import itertools
import json
import math
import struct
import subprocess

from reference.ball import BallSearch
from reference.sis import Profile, encode_case, verify
from reference.small_coefficients import candidates, dense, screen, search, templates


def oracle(profile, matrix, bound):
    if profile.m > 5:
        raise ValueError('Cartesian audit dimension cap')
    vectors = []
    for vector in itertools.product(range(-bound, bound+1), repeat=profile.m):
        nonzero = tuple(x for x in vector if x)
        if not nonzero or nonzero[0] < 0 or len(nonzero) > 3 or sum(x*x for x in vector) > profile.b2:
            continue
        positions = tuple(i for i, x in enumerate(vector) if x)
        codes = tuple(2*(abs(x)-1)+(x < 0) for x in nonzero[1:])
        vectors.append(((len(nonzero), positions, nonzero[0], codes), vector))
    return [v for _, v in sorted(vectors)]


def native_verdicts(executable, packets, expected):
    if len(packets) != len(expected) or len(packets) > 20000:
        raise ValueError('native audit batch cap')
    for offset in range(0, len(packets), 256):
        batch = packets[offset:offset+256]
        wire = b''.join(struct.pack('<I', len(p))+p for p in batch)
        result = subprocess.run([str(executable)], input=wire, capture_output=True, timeout=30, check=True)
        if result.stderr or result.stdout != bytes(expected[offset:offset+256]):
            raise RuntimeError('independent native candidate verdict mismatch')


def audit_search(profile, matrix, bound, result, candidate_limit=20000, proof_limit=256):
    """Rebuild the complete capped ledger from the independent tiny box oracle."""
    vectors = oracle(profile, matrix, bound)
    weights = {str(w): dict(domain=0, tested=0, accepted=0) for w in range(1, min(3, profile.m)+1)}
    coefficients = {}
    for vector in vectors:
        values = tuple(x for x in vector if x)
        weights[str(len(values))]['domain'] += 1
        key = ','.join(map(str, values))
        coefficients.setdefault(key, dict(domain=0, tested=0, accepted=0))['domain'] += 1
    proofs, checked, terms, rows = [], 0, 0, 0
    for vector in vectors[:candidate_limit]:
        values = tuple(x for x in vector if x)
        checked += 1
        valid = True
        for row in matrix:
            rows += 1
            terms += len(values)
            if sum(a*x for a, x in zip(row, vector)) % profile.q:
                valid = False
                break
        for census in (weights[str(len(values))], coefficients[','.join(map(str, values))]):
            census['tested'] += 1
            census['accepted'] += int(valid)
        if valid:
            proofs.append(vector)
            if len(proofs) == proof_limit:
                break
    domain = len(vectors)
    template_visits = sum(bound*(2*bound)**(w-1) for w in range(1, min(3, profile.m)+1))
    template_norm_terms = sum(w*bound*(2*bound)**(w-1) for w in range(1, min(3, profile.m)+1))
    primitive = sum(math.gcd(*v) == 1 for v in proofs)
    reason = 'proof-limit' if len(proofs) == proof_limit else 'candidate-limit' if checked < domain else 'domain-exhausted'
    expected = dict(bound=bound, domain=domain, proofs=proofs, weights=weights, coefficients=coefficients,
        reason=reason, checked_interval=[0, checked], unchecked_domain_suffix=domain-checked,
        domain_exhausted=checked == domain, proof_cap_hit=len(proofs) == proof_limit,
        candidate_cap_truncates_domain=candidate_limit < domain, candidate_censored=reason == 'candidate-limit',
        all_proofs_returned=checked == domain, accepted_tail_discarded=0,
        work=dict(template_visits=template_visits, template_norm_terms=template_norm_terms,
                  generated=checked, screened=checked, matrix_terms=terms, row_reductions=rows,
                  returned=len(proofs), vector_entries=len(proofs)*profile.m,
                  gcd_terms=sum(sum(x != 0 for x in v) for v in proofs), primitive_returned=primitive,
                  nonprimitive_returned=len(proofs)-primitive,
                  validation_matrix_entries=profile.n*profile.m, validation_vector_entries=profile.m))
    if result != expected:
        different = [key for key in expected if result.get(key) != expected[key]]
        raise RuntimeError('independent search ledger mismatch: '+','.join(different))


def tiny_audits(executable):
    summaries, verdict_count = [], 0
    for m in range(1, 6):
        for b2 in (1, 2, 3, 4, 5, 8, 9, 12):
            p = Profile(17, 2, m, b2)
            matrix = tuple(tuple((7*i+3*j+1) % 17 for j in range(m)) for i in range(2))
            for bound in (1, 2):
                expected = oracle(p, matrix, bound)
                patterns, _ = templates(p, bound)
                actual = [dense(m, pos, values) for pos, values in candidates(m, patterns)]
                if actual != expected:
                    raise RuntimeError('complete Cartesian candidate-order mismatch')
                flags = [int(verify(p, matrix, v)) for v in expected]
                native_verdicts(executable, [encode_case(p, matrix, v) for v in actual], flags)
                verdict_count += len(flags)
                full = search(p, matrix, bound=bound, proof_limit=256)
                audit_search(p, matrix, bound, full)
                valid = [v for v, hit in zip(expected, flags) if hit]
                if not full['domain_exhausted'] or full['proofs'] != valid:
                    raise RuntimeError('complete small-family search mismatch')
                for cap, proofs in ((1, 1), (7, 2), (20000, 256)):
                    bounded = search(p, matrix, bound=bound, candidate_limit=cap, proof_limit=proofs)
                    audit_search(p, matrix, bound, bounded, cap, proofs)
                    prefix = []
                    checked = 0
                    for v, hit in zip(expected[:cap], flags[:cap]):
                        checked += 1
                        if hit:
                            prefix.append(v)
                            if len(prefix) == proofs:
                                break
                    if bounded['proofs'] != prefix or bounded['work']['screened'] != checked:
                        raise RuntimeError('independent capped prefix mismatch')
                summaries.append(dict(m=m, b2=b2, bound=bound, candidates=len(expected), accepted=len(valid),
                                      ordered_sha256=hashlib.sha256(json.dumps(expected).encode()).hexdigest()))
    balls = []
    for b2 in (5, 8, 12):
        p, matrix = Profile(7, 1, 4, b2), ((1, 2, 3, 4),)
        engine = BallSearch(p, matrix)
        valid = set(engine.solutions())
        if engine.reason != 'domain-exhausted':
            raise RuntimeError('full ball oracle censored')
        for bound in (1, 2):
            eligible = {v for v in valid if max(map(abs, v)) <= bound and sum(x != 0 for x in v) <= 3}
            result = search(p, matrix, bound=bound)
            audit_search(p, matrix, bound, result)
            if not result['domain_exhausted'] or set(result['proofs']) != eligible:
                raise RuntimeError('exhausted ball filtered-family mismatch')
            balls.append(dict(b2=b2, bound=bound, ball_accepted=len(valid), family_accepted=len(eligible),
                              omitted_ball_solutions=len(valid-eligible), prefix_nodes=engine.work.prefix_nodes))
    return dict(cartesian=summaries, native_candidate_verdicts=verdict_count, complete_balls=balls)


def max_shape_audits(executable):
    p = Profile(65521, 64, 16, 12)
    # Late columns enforce 2*(q-1)+2*(q-1)+2*2=0 mod q at the maximum norm.
    matrix = tuple(tuple(1 if j < 13 else (65520, 65520, 2)[j-13] for j in range(16)) for _ in range(64))
    patterns, _ = templates(p, 2)
    vectors = [dense(16, pos, values) for pos, values in candidates(16, patterns)]
    flags = [int(verify(p, matrix, v)) for v in vectors]
    sparse_flags = [int(screen(matrix, pos, values, p.q)[0]) for pos, values in candidates(16, patterns)]
    if sparse_flags != flags:
        raise RuntimeError('maximum-shape sparse/dense acceptance mismatch')
    native_verdicts(executable, [encode_case(p, matrix, v) for v in vectors], flags)
    witness = (0,)*13+(2, 2, 2)
    ordinal = vectors.index(witness)
    if not flags[ordinal] or len(vectors) != 18912:
        raise RuntimeError('maximum-shape constructed witness missing')
    return dict(candidates=len(vectors), native_candidate_verdicts=len(vectors),
                late_witness_ordinal=ordinal, witness=witness,
                accepted=sum(flags), accepted_mask_sha256=hashlib.sha256(bytes(flags)).hexdigest())
