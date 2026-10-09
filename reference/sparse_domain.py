"""Independent canonical weight<=3 unit domain, bounds and paid-mask census."""

import itertools
import math

from reference.sis import Profile, encode_case

MAX_CANDIDATES, MAX_PROOFS, MAX_BATCH = 65536, 256, 4096


def validate(profile, matrix, max_weight, candidate_limit, proof_limit, batch_size):
    if not isinstance(profile, Profile):
        raise ValueError('expected Profile')
    encode_case(profile, matrix, [1]+[0]*(profile.m-1))
    if type(max_weight) is not int or max_weight not in (2, 3):
        raise ValueError('maximum weight must be 2 or 3')
    for value, maximum in ((candidate_limit, MAX_CANDIDATES), (proof_limit, MAX_PROOFS), (batch_size, MAX_BATCH)):
        if type(value) is not int or not 1 <= value <= maximum:
            raise ValueError('matched search cap outside laboratory range')


def weight_domains(profile, max_weight):
    weight = min(profile.b2, max_weight)
    return {1: profile.m, 2: profile.m*(profile.m-1) if weight >= 2 else 0,
            3: 4*math.comb(profile.m, 3) if weight >= 3 else 0}


def supports(profile, max_weight):
    for i in range(profile.m):
        yield (i, i, i, 1, 0, 0)
    if min(profile.b2, max_weight) >= 2:
        for i, j in itertools.combinations(range(profile.m), 2):
            for sign in (1, -1):
                yield (i, j, j, 1, sign, 0)
    if min(profile.b2, max_weight) >= 3:
        for i, j, k in itertools.combinations(range(profile.m), 3):
            for second in (1, -1):
                for third in (1, -1):
                    yield (i, j, k, 1, second, third)


def support_at(m, ordinal):
    """Host output decoder; independent nested-combination iterator is the oracle."""
    if (type(m) is not int or not 1 <= m <= 128 or type(ordinal) is not int
            or not 0 <= ordinal < m*m+4*math.comb(m, 3)):
        raise ValueError('support ordinal outside domain')
    if ordinal < m:
        return ordinal, ordinal, ordinal, 1, 0, 0
    if ordinal < m*m:
        rank, parity = divmod(ordinal-m, 2)
        i = 0
        while rank >= m-i-1:
            rank -= m-i-1
            i += 1
        j = i+1+rank
        return i, j, j, 1, 1-2*parity, 0
    rank, signs = divmod(ordinal-m*m, 4)
    i = 0
    while rank >= math.comb(m-i-1, 2):
        rank -= math.comb(m-i-1, 2)
        i += 1
    j = i+1
    while rank >= m-j-1:
        rank -= m-j-1
        j += 1
    return i, j, j+1+rank, 1, 1-2*(signs//2), 1-2*(signs % 2)


def vector_for(m, support):
    vector = [0]*m
    for index, coefficient in zip(support[:3], support[3:]):
        if coefficient:
            vector[index] = coefficient
    return tuple(vector)


def new_weights(profile, max_weight):
    return {str(w): dict(domain=d, tested=0, accepted=0, emitted=0, discarded=0)
            for w, d in weight_domains(profile, max_weight).items()}


def charge_mask(weights, offset, flags, emitted):
    """Census every paid mask byte, including accepted tail discarded by cap."""
    end = offset+len(flags)
    begin = 0
    for data in weights.values():
        boundary = begin+data['domain']
        low, high = max(offset, begin), min(end, boundary)
        if low < high:
            data['tested'] += high-low
            data['accepted'] += sum(flags[low-offset:high-offset])
        data['emitted'] += sum(begin <= ordinal < boundary for ordinal in emitted)
        data['discarded'] = data['accepted']-data['emitted']
        begin = boundary


def result_for(profile, max_weight, candidate_limit, proof_limit, batch_size, proofs, weights, batches):
    checked = sum(w['tested'] for w in weights.values())
    domain = sum(w['domain'] for w in weights.values())
    accepted = sum(w['accepted'] for w in weights.values())
    reason = 'proof-limit' if len(proofs) == proof_limit else 'candidate-limit' if checked < domain else 'domain-exhausted'
    coefficients = sum(int(k)*v['tested'] for k, v in weights.items())
    return dict(domain=domain, reason=reason, domain_exhausted=checked == domain,
                all_proofs_returned=checked == domain and accepted == len(proofs), proofs=proofs,
                weights=weights, checked_interval=[0, checked], proof_cap_hit=len(proofs) == proof_limit,
                candidate_cap_truncates_domain=candidate_limit < domain,
                candidate_censored=reason == 'candidate-limit',
                unchecked_domain_suffix=domain-checked, accepted_tail_discarded=accepted-len(proofs),
                work=dict(generated=checked, screened=checked, batches=batches, accepted_seen=accepted,
                          returned=len(proofs), vector_entries=len(proofs)*profile.m, support_slots=6*checked,
                          scheduled_column_reads=profile.n*coefficients, matrix_entries=profile.n*profile.m))


def reference_search(profile, matrix, *, max_weight, candidate_limit=65536, proof_limit=256, batch_size=256):
    validate(profile, matrix, max_weight, candidate_limit, proof_limit, batch_size)
    weights, proofs, batches = new_weights(profile, max_weight), [], 0
    domain = sum(w['domain'] for w in weights.values())
    iterator = supports(profile, max_weight)
    for offset in range(0, min(domain, candidate_limit), batch_size):
        count = min(batch_size, min(domain, candidate_limit)-offset)
        chunk = list(itertools.islice(iterator, count))
        flags = bytes(int(all(sum(row[i]*a for i, a in zip(s[:3], s[3:]) if a) % profile.q == 0
                              for row in matrix)) for s in chunk)
        emitted = [offset+i for i, valid in enumerate(flags) if valid][:proof_limit-len(proofs)]
        proofs.extend(vector_for(profile.m, chunk[i-offset]) for i in emitted)
        charge_mask(weights, offset, flags, emitted)
        batches += 1
        if len(proofs) == proof_limit:
            break
    return result_for(profile, max_weight, candidate_limit, proof_limit, batch_size, proofs, weights, batches)
