"""Bounded attack probes on known lab solutions; no claims about mining cost."""

import itertools
import math

from reference.sis import _check_shape, verify

MAX_DERIVED_ATTEMPTS = 4096
MAX_SPARSE_ATTEMPTS = 100_000


def canonical(vector):
    first = next((value for value in vector if value), 0)
    return tuple(-value for value in vector) if first < 0 else tuple(vector)


def derive_solutions(profile, matrix, known, coefficient_limit=3):
    """Reduce gcd, take multiples, then small combinations of at most two seeds."""
    if type(known) not in (list, tuple) or len(known) > 2:
        raise ValueError("provide at most two known solutions")
    if type(coefficient_limit) is not int or not 1 <= coefficient_limit <= 8:
        raise ValueError("coefficient limit out of range")
    _check_shape(profile, matrix, [0] * profile.m)
    if any(not verify(profile, matrix, x) for x in known):
        raise ValueError("known vectors must be valid canonical solutions")
    primitives = [tuple(value // math.gcd(*x) for value in x) for x in known]
    result = set()
    attempts = 0

    def propose(vector):
        nonlocal attempts
        attempts += 1
        if attempts > MAX_DERIVED_ATTEMPTS:
            raise ValueError("derived candidate budget exceeded")
        vector = canonical(vector)
        if verify(profile, matrix, vector):
            result.add(vector)

    for vector in primitives:
        norm = sum(value * value for value in vector)
        for factor in range(1, math.isqrt(profile.b2 // norm) + 1):
            propose(tuple(factor * value for value in vector))
    if len(primitives) == 2:
        for a, b in itertools.product(range(-coefficient_limit, coefficient_limit + 1), repeat=2):
            propose(tuple(a * u + b * v for u, v in zip(*primitives)))
    return result, attempts


def sparse_solutions(profile, matrix):
    """Try support <= 2 before consulting the exhaustive oracle; may miss solutions."""
    _check_shape(profile, matrix, [0] * profile.m)
    radius = math.isqrt(profile.b2)
    pairs = math.comb(profile.m, 2)
    upper_bound = profile.m * radius + pairs * radius * (2 * radius + 1)
    if upper_bound > MAX_SPARSE_ATTEMPTS:
        raise ValueError("sparse candidate budget exceeded")
    result = set()
    attempts = 0
    for i in range(profile.m):
        for a in range(1, radius + 1):
            vector = [0] * profile.m
            vector[i] = a
            attempts += 1
            if verify(profile, matrix, vector):
                result.add(tuple(vector))
    for i, j in itertools.combinations(range(profile.m), 2):
        for a in range(1, radius + 1):
            for b in range(-radius, radius + 1):
                if b == 0 or a * a + b * b > profile.b2:
                    continue
                vector = [0] * profile.m
                vector[i], vector[j] = a, b
                attempts += 1
                if verify(profile, matrix, vector):
                    result.add(tuple(vector))
    return result, attempts


def matrix_rank(profile, matrix):
    """Exact Gaussian elimination over the profile's prime field."""
    _check_shape(profile, matrix, [0] * profile.m)
    rows = [list(row) for row in matrix]
    rank = 0
    for column in range(profile.m):
        pivot = next((i for i in range(rank, profile.n) if rows[i][column]), None)
        if pivot is None:
            continue
        rows[rank], rows[pivot] = rows[pivot], rows[rank]
        inverse = pow(rows[rank][column], -1, profile.q)
        rows[rank] = [(value * inverse) % profile.q for value in rows[rank]]
        for i in range(rank + 1, profile.n):
            factor = rows[i][column]
            rows[i] = [(a - factor * b) % profile.q for a, b in zip(rows[i], rows[rank])]
        rank += 1
        if rank == profile.n:
            break
    return rank
