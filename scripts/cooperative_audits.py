"""Independent norm-ball oracle, paid verification ledger and meter reconciliation."""

import itertools
import math

from reference.sis import verify
from reference.component_meter import ZERO_WEIGHT


def oracle(profile, matrix, algorithm):
    radius = math.isqrt(profile.b2)
    if (2*radius+1)**profile.m > 200000:
        raise ValueError('independent box oracle cap')
    valid = set()
    for vector in itertools.product(range(-radius, radius+1), repeat=profile.m):
        values = [x for x in vector if x]
        if not values or values[0] <= 0 or sum(x*x for x in vector) > profile.b2:
            continue
        if algorithm.startswith('sparse') and (len(values) > 3 or max(map(abs, values)) > int(algorithm[-1])):
            continue
        if verify(profile, matrix, vector):
            valid.add(vector)
    return valid


def verification_work(profile, matrix, vectors):
    work = dict(shape_entries=0, sign_terms=0, norm_terms=0, matrix_terms=0, row_reductions=0, checks=0)
    verdicts = []
    for vector in vectors:
        work['shape_entries'] += profile.n*profile.m+profile.m
        work['checks'] += 1
        first = next((i for i, x in enumerate(vector) if x), None)
        work['sign_terms'] += profile.m if first is None else first+1
        valid = first is not None and vector[first] > 0
        if valid:
            work['norm_terms'] += profile.m
            valid = sum(x*x for x in vector) <= profile.b2
        if valid:
            residues = [sum(a*x for a, x in zip(row, vector)) % profile.q for row in matrix]
            visited = next((i+1 for i, x in enumerate(residues) if x), profile.n)
            work['matrix_terms'] += visited*profile.m
            work['row_reductions'] += visited
            valid = not any(residues)
        verdicts.append(valid)
    return work, verdicts


def audit_record(profile, record):
    meter = record['meter']
    phases = meter['phases']
    if set(phases)-{'matrix', 'setup', 'solver_setup', 'solver', 'solver_output', 'carry', 'verification', 'retention'}:
        raise RuntimeError('unknown component phase')
    if any(type(v) is not int or v < 0 for counts in phases.values() for v in counts.values()):
        raise RuntimeError('invalid component count')
    if phases['matrix'] != dict(expansions=1, entries=profile.n*profile.m,
                               shake_output_bytes=2*(4*profile.n*profile.m+1024)):
        raise RuntimeError('matrix preparation mismatch')
    previous = record['previous']
    setup = dict(shape_entries=profile.n*profile.m+profile.m,
                 previous_shape_entries=len(previous)*(profile.n*profile.m+profile.m),
                 previous_norm_terms=len(previous)*profile.m,
                 previous_sign_terms=sum(next(i+1 for i, x in enumerate(v) if x) for v in previous),
                 previous_key_entries=len(previous)*profile.m)
    if phases.get('setup') != setup:
        raise RuntimeError('common preparation mismatch')
    if record['solver_reason'] == 'not-started':
        if 'solver_setup' in phases or phases.get('solver') != {}:
            raise RuntimeError('unstarted solver has paid search work')
    else:
        if record['algorithm'].startswith('sparse'):
            bound = int(record['algorithm'][-1])
            expected_setup = dict(template_visits=sum(bound*(2*bound)**(w-1) for w in range(1, min(3, profile.m)+1)),
                template_norm_terms=sum(w*bound*(2*bound)**(w-1) for w in range(1, min(3, profile.m)+1)))
        else:
            expected_setup = dict(shape_entries=profile.n*profile.m+profile.m)
        if phases.get('solver_setup') != expected_setup:
            raise RuntimeError('solver preparation mismatch')
    emitted = len(record['emissions'])
    if record['algorithm'] in ('ball', 'mitm') and emitted:
        if phases.get('solver_output') != dict(vector_entries=emitted*profile.m):
            raise RuntimeError('legacy output materialization mismatch')
    elif 'solver_output' in phases:
        raise RuntimeError('unexpected separate output materialization')
    if [tuple(x['vector']) for x in record['carry']] != [tuple(v) for v in record['previous'][:len(record['carry'])]]:
        raise RuntimeError('carry prefix mismatch')
    used = sum(value for phase, counts in phases.items() for key, value in counts.items()
               if phase+'.'+key not in ZERO_WEIGHT)
    if used != meter['used'] or meter['overshoot'] != max(0, used-meter['limit']):
        raise RuntimeError('component total/overshoot mismatch')
    first = meter['first_boundary']
    if (first is None) != (used < meter['limit']):
        raise RuntimeError('component boundary mismatch')
    if first is not None and (type(first.get('used')) is not int or not meter['limit'] <= first['used'] <= used
                              or first.get('phase') not in phases):
        raise RuntimeError('impossible first component boundary')
    if meter['post_boundary_units'] != (0 if first is None else used-first['used']):
        raise RuntimeError('post-boundary accounting mismatch')
    for phase, vectors in (('carry', [x['vector'] for x in record['carry']]), ('verification', record['emissions'])):
        expected, verdicts = verification_work(profile, record['matrix'], vectors)
        if vectors and phases.get(phase) != expected:
            raise RuntimeError('paid verification ledger mismatch')
        if not vectors and phase in phases:
            raise RuntimeError('unexpected verification phase')
        if phase == 'carry' and verdicts != [x['valid'] for x in record['carry']]:
            raise RuntimeError('carry validity mismatch')
        if phase == 'verification' and (not all(verdicts) or record['emissions'] != record['acquired']):
            raise RuntimeError('emission/verified acquisition mismatch')
    eligible = [tuple(x['vector']) for x in record['carry'] if x['valid']]+[tuple(v) for v in record['acquired']]
    keys, retained, overlap, overflow, comparisons = [], [], 0, 0, 0
    for vector in eligible:
        divisor = math.gcd(*vector)
        primitive = tuple(x//divisor for x in vector)
        key = vector if record['policy'] == 'exact' else primitive
        found = False
        for existing in keys:
            comparisons += 1
            if existing == key:
                found = True
                break
        if found:
            overlap += 1
        elif len(retained) == record['pool_limit']:
            overflow += 1
        else:
            retained.append(vector)
            keys.append(key)
    expected = dict(gcd_terms=len(eligible)*profile.m, direction_entries=len(eligible)*profile.m,
                    key_entries=len(eligible)*profile.m)
    if comparisons:
        expected['comparisons'] = comparisons
    if retained:
        expected['inserted_entries'] = len(retained)*profile.m
    if eligible and phases.get('retention') != expected:
        raise RuntimeError('retention work mismatch')
    if not eligible and 'retention' in phases:
        raise RuntimeError('unexpected retention phase')
    if (retained != [tuple(v) for v in record['retained']] or overlap != record['overlaps']
            or overflow != record['overflow'] or record['unchecked_carry'] != len(record['previous'])-len(record['carry'])):
        raise RuntimeError('retention transition mismatch')
    histogram = {}
    for v in retained:
        divisor = math.gcd(*v)
        key = tuple(x//divisor for x in v)
        histogram[key] = histogram.get(key, 0)+1
    expected_histogram = [dict(direction=k, count=v) for k, v in sorted(histogram.items())]
    if record['retained_direction_multiplicities'] != expected_histogram:
        raise RuntimeError('retained direction histogram mismatch')
    if (record['budget_reached'] != (used >= meter['limit'])
            or record['proof_cap_hit'] != (len(record['acquired']) == record['proof_limit'])):
        raise RuntimeError('independent stop flag mismatch')
    if record['domain_exhausted'] != (record['solver_reason'] == 'domain-exhausted'):
        raise RuntimeError('solver exhaustion flag mismatch')
    reason, solver_reason = record['reason'], record['solver_reason']
    if solver_reason not in ('not-started', 'interrupted', 'domain-exhausted', 'node-limit', 'table-limit', 'pair-limit'):
        raise RuntimeError('unknown solver stop reason')
    if record['proof_cap_hit'] != (reason == 'proof-limit'):
        raise RuntimeError('proof-limit reason mismatch')
    if reason == 'component-budget':
        if not record['budget_reached']:
            raise RuntimeError('budget-stop reason without reached budget')
    elif reason != 'proof-limit' and reason != solver_reason:
        raise RuntimeError('solver/run stop reason mismatch')
    if reason in ('not-started', 'interrupted'):
        raise RuntimeError('unfinished run lacks a stopping cause')
