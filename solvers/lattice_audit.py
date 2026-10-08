"""Independent certificates: integer determinants and Gram-matrix LDL, not solver GSO."""
from fractions import Fraction

from reference.reuse import matrix_rank
from reference.sis import Profile, _check_shape


def determinant(matrix):
    """Bareiss elimination with exact divisibility and row pivoting."""
    rows = [list(row) for row in matrix]
    size, sign, previous = len(rows), 1, 1
    if not size or any(len(row) != size for row in rows):
        raise ValueError("expected nonempty square matrix")
    for k in range(size-1):
        pivot = next((i for i in range(k, size) if rows[i][k]), None)
        if pivot is None:
            return 0
        if pivot != k:
            rows[k], rows[pivot] = rows[pivot], rows[k]
            sign = -sign
        value = rows[k][k]
        for i in range(k+1, size):
            for j in range(k+1, size):
                numerator = rows[i][j]*value - rows[i][k]*rows[k][j]
                quotient, remainder = divmod(numerator, previous)
                if remainder:
                    raise ValueError("nonintegral Bareiss division")
                rows[i][j] = quotient
            rows[i][k] = 0
        previous = value
    return sign*rows[-1][-1]


def reduced_inequalities(basis):
    """Recover GS coefficients from integer Gram entries via exact LDL recurrence."""
    size = len(basis)
    gram = [[sum(a*b for a, b in zip(left, right)) for right in basis] for left in basis]
    norms, mu = [], []
    for i in range(size):
        coefficients = []
        for j in range(i):
            dot = Fraction(gram[i][j]) - sum((coefficients[k]*mu[j][k]*norms[k]
                                             for k in range(j)), Fraction(0))
            coefficients.append(dot/norms[j])
        norm = Fraction(gram[i][i]) - sum((x*x*d for x, d in zip(coefficients, norms)), Fraction(0))
        if norm <= 0:
            return False
        norms.append(norm)
        mu.append(coefficients)
    return (all(abs(x) <= Fraction(1, 2) for row in mu for x in row)
            and all(norms[i] >= (Fraction(3, 4)-mu[i][i-1]**2)*norms[i-1]
                    for i in range(1, size)))


def audit_certificate(profile, matrix, reduction):
    if not isinstance(profile, Profile):
        raise ValueError("expected Profile")
    _check_shape(profile, matrix, [0] * profile.m)
    if profile.m > 16:
        raise ValueError("certificate dimension exceeds audit budget")
    if not all(hasattr(reduction, field) for field in ("initial_basis", "basis", "transform", "rank", "reason")):
        raise ValueError("expected reduction certificate")
    matrices = (reduction.initial_basis, reduction.basis, reduction.transform)
    for square in matrices:
        if (type(square) not in (list, tuple) or len(square) != profile.m
                or any(type(row) not in (list, tuple) or len(row) != profile.m for row in square)
                or any(type(value) is not int or abs(value).bit_length() > 4096
                       for row in square for value in row)):
            raise ValueError("invalid certificate matrix")
    rank = matrix_rank(profile, matrix)
    if type(reduction.rank) is not int or reduction.rank != rank:
        raise ValueError("incorrect kernel rank")
    if abs(determinant(reduction.initial_basis)) != profile.q**rank:
        raise ValueError("initial basis has incorrect lattice index")
    if abs(determinant(reduction.transform)) != 1:
        raise ValueError("transformation is not unimodular")
    expected = tuple(tuple(sum(reduction.transform[i][k]*reduction.initial_basis[k][j]
                               for k in range(profile.m)) for j in range(profile.m))
                     for i in range(profile.m))
    if expected != tuple(map(tuple, reduction.basis)):
        raise ValueError("transformation does not match final basis")
    if any(sum(a*x for a, x in zip(row, vector)) % profile.q
           for vector in reduction.initial_basis for row in matrix):
        raise ValueError("initial basis is outside modular kernel")
    if reduction.reason not in ("lll-reduced", "step-limit", "reduction-limit", "arithmetic-limit"):
        raise ValueError("unknown reduction status")
    if reduction.reason == "lll-reduced" and not reduced_inequalities(reduction.basis):
        raise ValueError("completed basis is not LLL-reduced")
    return {"rank": rank, "lattice_index": profile.q**rank,
            "unimodular": True, "lll_reduced": reduction.reason == "lll-reduced"}
