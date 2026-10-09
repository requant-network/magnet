"""Bounded exact support<=3 family, including SIS1's nonprimitive vectors."""

import itertools
import math
from collections import Counter

from reference.sis import Profile, encode_case

MAX_CANDIDATES = 20000
MAX_PROOFS = 256


def validate(profile, matrix, bound, candidate_limit, proof_limit):
    if not isinstance(profile, Profile) or profile.m > 16 or profile.b2 > 12:
        raise ValueError('small-coefficient profile outside laboratory range')
    encode_case(profile, matrix, [0]*profile.m)
    for value, maximum in ((bound, 2), (candidate_limit, MAX_CANDIDATES), (proof_limit, MAX_PROOFS)):
        if type(value) is not int or not 1 <= value <= maximum:
            raise ValueError('small-coefficient bound/cap outside laboratory range')


def templates(profile, bound):
    choices = tuple(x for magnitude in range(1, bound+1) for x in (magnitude, -magnitude))
    result, work = {}, dict(template_visits=0, template_norm_terms=0)
    for weight in range(1, min(3, profile.m)+1):
        patterns = []
        for first in range(1, bound+1):
            for tail in itertools.product(choices, repeat=weight-1):
                values = (first,)+tail
                work['template_visits'] += 1
                work['template_norm_terms'] += weight
                if sum(x*x for x in values) <= profile.b2:
                    patterns.append(values)
        result[weight] = tuple(patterns)
    return result, work


def candidates(m, patterns):
    for weight, coefficients in patterns.items():
        for positions in itertools.combinations(range(m), weight):
            for values in coefficients:
                yield positions, values


def dense(m, positions, values):
    vector = [0]*m
    for i, value in zip(positions, values):
        vector[i] = value
    return tuple(vector)


def direction(vector):
    divisor = math.gcd(*vector)
    return tuple(x//divisor for x in vector)


def screen(matrix, positions, values, q):
    terms, rows = 0, 0
    for row in matrix:
        residue = sum(row[i]*value for i, value in zip(positions, values)) % q
        terms += len(values)
        rows += 1
        if residue:
            return False, terms, rows
    return True, terms, rows


def search(profile, matrix, *, bound, candidate_limit=MAX_CANDIDATES, proof_limit=MAX_PROOFS):
    validate(profile, matrix, bound, candidate_limit, proof_limit)
    patterns, work = templates(profile, bound)
    census = {str(w): dict(domain=math.comb(profile.m, w)*len(p), tested=0, accepted=0)
              for w, p in patterns.items()}
    domain = sum(x['domain'] for x in census.values())
    work.update(generated=0, screened=0, matrix_terms=0, row_reductions=0,
                returned=0, vector_entries=0, gcd_terms=0,
                primitive_returned=0, nonprimitive_returned=0,
                validation_matrix_entries=profile.n*profile.m, validation_vector_entries=profile.m)
    coefficients = {','.join(map(str, values)): dict(domain=math.comb(profile.m, w), tested=0, accepted=0)
                    for w, entries in patterns.items() for values in entries}
    proofs = []
    for positions, values in itertools.islice(candidates(profile.m, patterns), candidate_limit):
        work['generated'] += 1
        work['screened'] += 1
        group = census[str(len(values))]
        group['tested'] += 1
        coefficient = coefficients[','.join(map(str, values))]
        coefficient['tested'] += 1
        accepted, terms, rows = screen(matrix, positions, values, profile.q)
        work['matrix_terms'] += terms
        work['row_reductions'] += rows
        if accepted:
            proofs.append(dense(profile.m, positions, values))
            group['accepted'] += 1
            coefficient['accepted'] += 1
            work['returned'] += 1
            work['vector_entries'] += profile.m
            work['gcd_terms'] += len(values)
            category = 'primitive_returned' if math.gcd(*values) == 1 else 'nonprimitive_returned'
            work[category] += 1
            if len(proofs) == proof_limit:
                break
    checked = work['screened']
    reason = 'proof-limit' if len(proofs) == proof_limit else 'candidate-limit' if checked < domain else 'domain-exhausted'
    return dict(bound=bound, domain=domain, proofs=proofs, work=work, weights=census,
                coefficients=coefficients, reason=reason,
                checked_interval=[0, checked], unchecked_domain_suffix=domain-checked,
                domain_exhausted=checked == domain, proof_cap_hit=len(proofs) == proof_limit,
                candidate_cap_truncates_domain=candidate_limit < domain,
                candidate_censored=reason == 'candidate-limit',
                all_proofs_returned=checked == domain, accepted_tail_discarded=0)


def refresh(profile, matrix, previous, acquired, *, pool_limit=32):
    """Pay dense carry checks, then stably merge a separately paid acquisition."""
    validate(profile, matrix, 2, 1, 1)
    if type(pool_limit) is not int or not 1 <= pool_limit <= 32:
        raise ValueError('pool cap outside laboratory range')
    if type(previous) not in (list, tuple) or len(previous) > pool_limit:
        raise ValueError('previous pool exceeds cap')
    if type(acquired) not in (list, tuple) or len(acquired) > MAX_PROOFS:
        raise ValueError('acquisition exceeds cap')
    for pool in (previous, acquired):
        for vector in pool:
            encode_case(profile, matrix, vector)
            if (next((x for x in vector if x), 0) <= 0 or sum(x*x for x in vector) > profile.b2
                    or max(map(abs, vector)) > 2 or sum(x != 0 for x in vector) > 3):
                raise ValueError('pool vector outside family')
        if len({tuple(v) for v in pool}) != len(pool):
            raise ValueError('duplicate pool vector')
    verdicts, carried = [], []
    work = dict(carry_checks=0, matrix_terms=0, row_reductions=0, retained_entries=0,
                acquired_checks=0, acquired_matrix_terms=0, acquired_row_reductions=0,
                validation_vector_entries=(1+len(previous)+len(acquired))*profile.m,
                validation_matrix_entries=(1+len(previous)+len(acquired))*profile.n*profile.m,
                dedup_comparisons=0,
                direction_gcd_terms=0)
    for vector in previous:
        valid, terms, rows = screen(matrix, tuple(range(profile.m)), vector, profile.q)
        verdicts.append(valid)
        work['carry_checks'] += 1
        work['matrix_terms'] += terms
        work['row_reductions'] += rows
        if valid:
            carried.append(tuple(vector))
    for vector in acquired:
        valid, terms, rows = screen(matrix, tuple(range(profile.m)), vector, profile.q)
        work['acquired_checks'] += 1
        work['acquired_matrix_terms'] += terms
        work['acquired_row_reductions'] += rows
        if not valid:
            raise ValueError('invalid acquired proof')
    merged = list(carried)
    overlap = 0
    for vector in acquired:
        vector = tuple(vector)
        found = False
        for existing in merged:
            work['dedup_comparisons'] += 1
            if vector == existing:
                found = True
                break
        if found:
            overlap += 1
        else:
            merged.append(vector)
    retained = merged[:pool_limit]
    work['retained_entries'] = len(retained)*profile.m
    direction_counts = {}
    retained_multiplicities = None
    for name, pool in (('carried', carried), ('acquired', acquired), ('union', merged), ('retained', retained)):
        directions = Counter(direction(v) for v in pool)
        work['direction_gcd_terms'] += len(pool)*profile.m
        direction_counts[name] = len(directions)
        if name == 'retained':
            retained_multiplicities = [dict(direction=v, multiplicity=count) for v, count in sorted(directions.items())]
    return dict(previous=[tuple(v) for v in previous], carry_verdicts=verdicts,
                carried=carried, acquired_overlap=overlap, distinct_union=len(merged),
                distinct_overflow=len(merged)-len(retained), retained=retained,
                directions=direction_counts,
                retained_direction_multiplicities=retained_multiplicities,
                new_directions=direction_counts['union']-direction_counts['carried'], work=work)
