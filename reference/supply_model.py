"""Exact precommitted-pool laws under an iid-uniform prime-field matrix model."""

from dataclasses import dataclass
from fractions import Fraction
from itertools import combinations
from math import comb, lcm

from reference.sis import Profile

MAX_POOL = 6
MAX_ARITHMETIC = 250_000
MAX_LAW_BITS = 6144


def validate_pool(profile, pool):
    """Validate vector eligibility independently of whether any particular A accepts."""
    if not isinstance(profile, Profile) or type(pool) not in (list, tuple) or not 1 <= len(pool) <= MAX_POOL:
        raise ValueError("profile/pool bound")
    result = []
    for vector in pool:
        if type(vector) not in (list, tuple) or len(vector) != profile.m or any(
                type(x) is not int or not -(2**31) <= x < 2**31 for x in vector):
            raise ValueError("vector shape/type")
        if next((x for x in vector if x), 0) <= 0 or sum(x*x for x in vector) > profile.b2:
            raise ValueError("vector sign/norm")
        result.append(tuple(vector))
    if len(set(result)) != len(result):
        raise ValueError("duplicate proof inputs")
    return tuple(result)


class _Budget:
    def __init__(self, limit):
        if type(limit) is not int or not 1 <= limit <= MAX_ARITHMETIC:
            raise ValueError("arithmetic budget")
        self.limit, self.used = limit, 0

    def spend(self, amount):
        if amount > self.limit - self.used:
            raise ValueError("rank arithmetic cap")
        self.used += amount


def _rank(vectors, q, budget):
    rows = [[x % q for x in vector] for vector in vectors]
    rank, width = 0, len(rows[0])
    for column in range(width):
        pivot = next((i for i in range(rank, len(rows)) if rows[i][column]), None)
        if pivot is None:
            continue
        rows[rank], rows[pivot] = rows[pivot], rows[rank]
        inverse = pow(rows[rank][column], -1, q)
        budget.spend(width-column)
        rows[rank][column:] = [(x*inverse) % q for x in rows[rank][column:]]
        for i in range(rank+1, len(rows)):
            factor = rows[i][column]
            if factor:
                budget.spend(2*(width-column))
                rows[i][column:] = [(x-factor*y) % q for x, y in zip(
                    rows[i][column:], rows[rank][column:])]
        rank += 1
        if rank == len(rows):
            break
    return rank


@dataclass(frozen=True)
class PoolLaw:
    histogram: tuple
    subset_ranks: tuple
    rank_arithmetic_units: int

    @property
    def any_valid(self):
        return 1-self.histogram[0]

    @property
    def mean_valid(self):
        return sum(k*p for k, p in enumerate(self.histogram))


def pool_law(profile, pool, *, arithmetic_budget=MAX_ARITHMETIC):
    """Exact law of K valid vectors; the pool must be fixed independently of fresh A.

    This is a model, not an assertion about deterministic SHAKE headers or miners.
    Profile caps bound exponents by n*MAX_POOL <= 384. At q<=65521, powers
    use at most 6144 bits. Denominators in the probability law divide q**384.
    """
    vectors = validate_pool(profile, pool)
    budget = _Budget(arithmetic_budget)
    count = len(vectors)
    moments = [Fraction(1)] + [Fraction(0)]*count
    ranks = []
    for size in range(1, count+1):
        for indices in combinations(range(count), size):
            rank = _rank(tuple(vectors[i] for i in indices), profile.q, budget)
            mask = sum(1 << i for i in indices)
            ranks.append((mask, rank))
            moments[size] += Fraction(1, profile.q**(profile.n*rank))
    histogram = tuple(sum((-1)**(r-k)*comb(r, k)*moments[r] for r in range(k, count+1))
                      for k in range(count+1))
    if any(p < 0 for p in histogram) or sum(histogram) != 1:
        raise RuntimeError("invalid exact pool law")
    law = PoolLaw(histogram, tuple(ranks), budget.used)
    if law.mean_valid != Fraction(count, profile.q**profile.n):
        raise RuntimeError("single-vector marginal disagreement")
    return law


def _score_probability(target):
    if type(target) is not int or not 0 <= target <= 2**256:
        raise ValueError("score target")
    return Fraction(target, 2**256)


def score_hit_probability(histogram, target):
    """Hypothesis: distinct scores are iid uniform conditional on A AND its valid set."""
    if type(histogram) not in (list, tuple) or not 2 <= len(histogram) <= MAX_POOL+1 or any(
            type(p) not in (int, Fraction) or p < 0 for p in histogram):
        raise ValueError("exact histogram")
    denominator = 1
    for p in histogram:
        if max(p.numerator.bit_length(), p.denominator.bit_length()) > MAX_LAW_BITS:
            raise ValueError("histogram arithmetic bound")
        denominator = lcm(denominator, p.denominator)
        if denominator.bit_length() > MAX_LAW_BITS:
            raise ValueError("histogram arithmetic bound")
    if sum(histogram) != 1:
        raise ValueError("exact histogram")
    success = _score_probability(target)
    return sum(p*(1-(1-success)**k) for k, p in enumerate(histogram))


def independent_hit_shortcut(profile, pool_size, target):
    """Deliberately compare an independence assumption; it can be false for a pool."""
    if not isinstance(profile, Profile) or type(pool_size) is not int or not 1 <= pool_size <= MAX_POOL:
        raise ValueError("profile/pool size")
    return 1-(1-_score_probability(target)/profile.q**profile.n)**pool_size
