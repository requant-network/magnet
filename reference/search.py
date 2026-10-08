"""Exhaustive oracle for tiny lab cases only; not a production SIS solver."""

import itertools
import math

from reference.sis import Profile, _check_shape

MAX_CANDIDATES = 1_000_000


def exhaustive_solutions(profile: Profile, matrix):
    """Enumerate all canonical solutions, with a hard bound on the search box."""
    _check_shape(profile, matrix, [0] * profile.m)
    radius = math.isqrt(profile.b2)
    if (2 * radius + 1) ** profile.m > MAX_CANDIDATES:
        raise ValueError("exhaustive search exceeds laboratory budget")
    for candidate in itertools.product(range(-radius, radius + 1), repeat=profile.m):
        # Independent of verify(): enumerate by norm, sign, then incremental residues.
        if not 0 < sum(v**2 for v in candidate) <= profile.b2:
            continue
        if next(v for v in candidate if v) < 0:
            continue
        residues = [0] * profile.n
        for column, coordinate in enumerate(candidate):
            for row in range(profile.n):
                residues[row] = (residues[row] + matrix[row][column] * coordinate) % profile.q
        if residues == [0] * profile.n:
            yield candidate
