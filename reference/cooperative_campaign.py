"""Paid verification and retention transactions for cooperative local searches."""

import math

from reference.component_meter import ComponentMeter, ComponentStop
from reference.cooperative_solvers import ALGORITHMS, Acquisition
from reference.sis import Profile, _check_shape, expand_matrix

POLICIES = ('exact', 'direction')


def paid_verify(profile, matrix, vector, meter, phase):
    _check_shape(profile, matrix, vector)
    work = dict(shape_entries=profile.n*profile.m+profile.m, sign_terms=0,
                norm_terms=0, matrix_terms=0, row_reductions=0, checks=1)
    first = 0
    for x in vector:
        work['sign_terms'] += 1
        if x:
            first = x
            break
    valid = False
    if first > 0:
        work['norm_terms'] = profile.m
        valid = sum(x*x for x in vector) <= profile.b2
    if valid:
        for row in matrix:
            work['matrix_terms'] += profile.m
            work['row_reductions'] += 1
            if sum(a*x for a, x in zip(row, vector)) % profile.q:
                valid = False
                break
    meter.add(phase, **work)
    return valid


def step(profile, seed, algorithm, policy, previous, *, budget, pool_limit=8, proof_limit=64):
    if (not isinstance(profile, Profile) or profile.n > 3 or profile.m > 6 or profile.b2 > 12
            or type(seed) is not bytes or len(seed) != 32):
        raise ValueError('cooperative profile/seed outside laboratory range')
    if algorithm not in ALGORITHMS or policy not in POLICIES:
        raise ValueError('unknown cooperative algorithm/policy')
    for value, maximum in ((pool_limit, 8), (proof_limit, 64)):
        if type(value) is not int or not 1 <= value <= maximum:
            raise ValueError('cooperative output cap outside range')
    if type(previous) not in (tuple, list) or len(previous) > pool_limit:
        raise ValueError('invalid previous inventory')
    for vector in previous:
        _check_shape(profile, [[0]*profile.m for _ in range(profile.n)], vector)
        if next((x for x in vector if x), 0) <= 0 or sum(x*x for x in vector) > profile.b2:
            raise ValueError('previous vector outside canonical norm ball')
    if len({tuple(v) for v in previous}) != len(previous):
        raise ValueError('duplicate previous vector')
    meter = ComponentMeter(budget)
    matrix = expand_matrix(profile, seed)
    _check_shape(profile, matrix, [0]*profile.m)
    meter.add('matrix', expansions=1, entries=profile.n*profile.m,
              shake_output_bytes=2*(4*profile.n*profile.m+1024))
    meter.add('setup', shape_entries=profile.n*profile.m+profile.m,
              previous_shape_entries=len(previous)*(profile.n*profile.m+profile.m),
              previous_norm_terms=len(previous)*profile.m,
              previous_sign_terms=sum(next(i+1 for i, x in enumerate(v) if x) for v in previous),
              previous_key_entries=len(previous)*profile.m)
    source = Acquisition(profile, matrix, algorithm, meter)
    iterator = None
    retained, keys, acquired, emissions, carry = [], [], [], [], []
    overlaps, overflow = 0, 0
    reason = 'not-started'

    def retain(vector):
        nonlocal overlaps, overflow
        divisor = math.gcd(*vector)
        primitive = tuple(x//divisor for x in vector)
        key = tuple(vector) if policy == 'exact' else primitive
        meter.add('retention', gcd_terms=profile.m, direction_entries=profile.m, key_entries=profile.m)
        for existing in keys:
            meter.add('retention', comparisons=1)
            if existing == key:
                overlaps += 1
                return
        if len(retained) == pool_limit:
            overflow += 1
            return
        retained.append(tuple(vector))
        keys.append(key)
        meter.add('retention', inserted_entries=profile.m)

    try:
        meter.check()
        for vector in previous:
            valid = paid_verify(profile, matrix, vector, meter, 'carry')
            carry.append(dict(vector=tuple(vector), valid=valid))
            if valid:
                retain(vector)
            meter.check()
        iterator = source.solutions()
        for vector in iterator:
            emissions.append(tuple(vector))
            source.sync()
            if algorithm in ('ball', 'mitm'):
                meter.add('solver_output', vector_entries=profile.m)
            valid = paid_verify(profile, matrix, vector, meter, 'verification')
            if not valid:
                raise RuntimeError('invalid solver emission')
            acquired.append(tuple(vector))
            retain(vector)
            if len(acquired) == proof_limit:
                reason = 'proof-limit'
                break
            meter.check()
        if reason == 'not-started':
            reason = source.reason
    except ComponentStop:
        reason = 'component-budget'
    finally:
        if iterator is not None:
            iterator.close()
        source.sync()
    directions = {}
    for vector in retained:
        divisor = math.gcd(*vector)
        key = tuple(x//divisor for x in vector)
        directions[key] = directions.get(key, 0)+1
    # These reporting-only direction calculations are outside the model, like oracle audits.
    report = meter.report()
    return dict(algorithm=algorithm, policy=policy, matrix=matrix, previous=[tuple(v) for v in previous],
                pool_limit=pool_limit, proof_limit=proof_limit,
                carry=carry, unchecked_carry=len(previous)-len(carry), emissions=emissions,
                acquired=acquired, retained=retained, overlaps=overlaps, overflow=overflow,
                retained_direction_multiplicities=[dict(direction=k, count=v) for k, v in sorted(directions.items())],
                reason=reason, solver_reason=source.reason,
                domain_exhausted=source.reason == 'domain-exhausted',
                proof_cap_hit=len(acquired) == proof_limit, budget_reached=report['used'] >= budget,
                meter=report)
