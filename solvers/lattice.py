"""Bounded exact-rational LLL on the full integer modular-kernel lattice."""
from dataclasses import dataclass
from fractions import Fraction
from itertools import combinations, product

from reference.reuse import canonical
from reference.sis import Profile, _check_shape, verify

MAX_DIMENSION = 16
MAX_STEPS = 10_000
MAX_REDUCTIONS = 10_000
MAX_BITS = 4096
DELTA = Fraction(3, 4)


@dataclass
class LatticeWork:
    pivots: int = 0
    elimination_terms: int = 0
    gso_calls: int = 0
    dot_terms: int = 0
    steps: int = 0
    size_reductions: int = 0
    swaps: int = 0
    max_integer_bits: int = 0
    max_fraction_bits: int = 0


@dataclass
class Reduction:
    initial_basis: tuple
    basis: tuple
    transform: tuple
    rank: int
    reason: str
    work: LatticeWork


def kernel_basis(profile, matrix, work=None):
    """RREF pivots give q*e_pivot rows and centered modular free-column lifts."""
    if not isinstance(profile, Profile):
        raise ValueError("expected Profile")
    _check_shape(profile, matrix, [0] * profile.m)
    if profile.m > MAX_DIMENSION:
        raise ValueError("lattice dimension exceeds reference budget")
    work = LatticeWork() if work is None else work
    rows = [list(row) for row in matrix]
    pivots = []
    for column in range(profile.m):
        rank = len(pivots)
        pivot = next((i for i in range(rank, profile.n) if rows[i][column]), None)
        if pivot is None:
            continue
        rows[rank], rows[pivot] = rows[pivot], rows[rank]
        inverse = pow(rows[rank][column], -1, profile.q)
        rows[rank] = [(value * inverse) % profile.q for value in rows[rank]]
        work.elimination_terms += profile.m
        for i in range(profile.n):
            if i == rank or not rows[i][column]:
                continue
            factor = rows[i][column]
            rows[i] = [(a - factor*b) % profile.q for a, b in zip(rows[i], rows[rank])]
            work.elimination_terms += profile.m
        pivots.append(column)
        work.pivots += 1
        if len(pivots) == profile.n:
            break
    basis = []
    for column in pivots:
        row = [0] * profile.m
        row[column] = profile.q
        basis.append(row)
    for column in range(profile.m):
        if column in pivots:
            continue
        row = [0] * profile.m
        row[column] = 1
        for i, pivot in enumerate(pivots):
            value = -rows[i][column] % profile.q
            row[pivot] = value if 2*value <= profile.q else value - profile.q
        basis.append(row)
    return tuple(map(tuple, basis)), len(pivots)


class _ArithmeticLimit(Exception):
    pass


class _Guard:
    def __init__(self, work, bit_limit):
        self.work, self.bit_limit = work, bit_limit

    def integer(self, value):
        bits = abs(value).bit_length()
        self.work.max_integer_bits = max(self.work.max_integer_bits, bits)
        if bits > self.bit_limit:
            raise _ArithmeticLimit
        return value

    def fraction(self, value):
        bits = max(abs(value.numerator).bit_length(), value.denominator.bit_length())
        self.work.max_fraction_bits = max(self.work.max_fraction_bits, bits)
        if bits > self.bit_limit:
            raise _ArithmeticLimit
        return value

    def dot(self, left, right):
        self.work.dot_terms += len(left)
        return self.fraction(sum((a*b for a, b in zip(left, right)), Fraction(0)))


def _gram_schmidt(basis, guard):
    guard.work.gso_calls += 1
    orthogonal, norms, mu = [], [], []
    for row in basis:
        original = tuple(map(Fraction, row))
        residual = list(original)
        coefficients = []
        for j, star in enumerate(orthogonal):
            coefficient = guard.fraction(guard.dot(original, star) / norms[j])
            coefficients.append(coefficient)
            residual = [guard.fraction(a - coefficient*b) for a, b in zip(residual, star)]
        norm = guard.dot(residual, residual)
        if norm <= 0:
            raise ValueError("dependent basis in exact Gram-Schmidt")
        orthogonal.append(residual)
        norms.append(norm)
        mu.append(coefficients)
    return mu, norms


def reduce_kernel(profile, matrix, *, step_limit=MAX_STEPS,
                  reduction_limit=MAX_REDUCTIONS, bit_limit=MAX_BITS):
    for value, maximum in ((step_limit, MAX_STEPS), (reduction_limit, MAX_REDUCTIONS),
                           (bit_limit, MAX_BITS)):
        if type(value) is not int or not 1 <= value <= maximum:
            raise ValueError("invalid lattice reference budget")
    work = LatticeWork()
    initial, rank = kernel_basis(profile, matrix, work)
    basis = [list(row) for row in initial]
    transform = [[int(i == j) for j in range(profile.m)] for i in range(profile.m)]
    guard = _Guard(work, bit_limit)
    reason = "lll-reduced"
    try:
        for row in basis:
            for value in row:
                guard.integer(value)
        mu, norms = _gram_schmidt(basis, guard)
        k = 1
        while k < profile.m:
            if work.steps == step_limit:
                reason = "step-limit"
                break
            work.steps += 1
            for j in range(k-1, -1, -1):
                if abs(mu[k][j]) <= Fraction(1, 2):
                    continue
                if work.size_reductions == reduction_limit:
                    reason = "reduction-limit"
                    break
                value = mu[k][j]
                # Nearest integer, ties towards +infinity; exact fractions only.
                coefficient = (2*value.numerator + value.denominator) // (2*value.denominator)
                next_row = [guard.integer(a-coefficient*b) for a, b in zip(basis[k], basis[j])]
                next_transform = [guard.integer(a-coefficient*b)
                                  for a, b in zip(transform[k], transform[j])]
                basis[k], transform[k] = next_row, next_transform
                work.size_reductions += 1
                mu, norms = _gram_schmidt(basis, guard)
            if reason != "lll-reduced":
                break
            if norms[k] >= (DELTA - mu[k][k-1]**2)*norms[k-1]:
                k += 1
            else:
                basis[k], basis[k-1] = basis[k-1], basis[k]
                transform[k], transform[k-1] = transform[k-1], transform[k]
                work.swaps += 1
                mu, norms = _gram_schmidt(basis, guard)
                k = max(1, k-1)
    except _ArithmeticLimit:
        reason = "arithmetic-limit"
    return Reduction(initial, tuple(map(tuple, basis)), tuple(map(tuple, transform)), rank, reason, work)


def probe_basis(profile, matrix, reduction, *, proposal_limit=4096):
    """Inspect rows, then small two-row combinations. Not exhaustive SVP/SIS."""
    if not isinstance(profile, Profile):
        raise ValueError("expected Profile")
    _check_shape(profile, matrix, [0] * profile.m)
    if type(proposal_limit) is not int or not 1 <= proposal_limit <= 4096:
        raise ValueError("invalid lattice candidate budget")
    if (not isinstance(reduction, Reduction) or type(reduction.basis) not in (list, tuple)
            or len(reduction.basis) != profile.m or profile.m > MAX_DIMENSION
            or any(type(row) not in (list, tuple) or len(row) != profile.m for row in reduction.basis)
            or any(type(x) is not int or abs(x).bit_length() > MAX_BITS
                   for row in reduction.basis for x in row)):
        raise ValueError("invalid bounded lattice basis")
    proofs, basis_proofs = set(), set()
    proposed, shortest = 0, None

    def proposals():
        for row in reduction.basis:
            yield row, True
        for left, right in combinations(reduction.basis, 2):
            for a, b in product((1, 2), (-2, -1, 1, 2)):
                yield tuple(a*x+b*y for x, y in zip(left, right)), False

    for vector, from_basis in proposals():
        if proposed == proposal_limit:
            return {"reason": "proposal-limit", "proposals": proposed,
                    "proofs": sorted(proofs), "basis_proofs": sorted(basis_proofs), "min_norm2": shortest}
        proposed += 1
        vector = canonical(vector)
        norm = sum(x*x for x in vector)
        if norm:
            shortest = norm if shortest is None else min(shortest, norm)
        if norm <= profile.b2 and verify(profile, matrix, vector):
            proofs.add(vector)
            if from_basis:
                basis_proofs.add(vector)
    return {"reason": "probe-exhausted", "proposals": proposed,
            "proofs": sorted(proofs), "basis_proofs": sorted(basis_proofs), "min_norm2": shortest}
