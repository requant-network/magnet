"""Exact conditional fresh-uniform kernel transfer bounds, not a hardness claim."""

from fractions import Fraction
import math

from reference.sis import Profile


def transfer_probabilities(profile, donor_rank):
    """Condition on a fixed donor transcript, then sample independent uniform rows.

    All old-kernel vectors remain valid iff receiver rowspace is contained in the
    donor rowspace. Equal kernels additionally require the same receiver rank.
    The latter event is required to reuse a complete sphere-search certificate.
    """
    if (not isinstance(profile, Profile) or type(donor_rank) is not int
            or not 0 <= donor_rank <= min(profile.n, profile.m)):
        raise ValueError('kernel transfer profile/rank')
    q, n, m = profile.q, profile.n, profile.m
    contained = Fraction(1, q**(n*(m-donor_rank)))
    spanning = math.prod(q**n-q**i for i in range(donor_rank))
    equal = Fraction(spanning, q**(n*m))
    return contained, equal


def adaptive_transfer_bound(profile, capacity, opportunities):
    """Union bound, including a cache adapted to all previously observed headers.

    Each next receiving matrix must be fresh uniform conditional on that history.
    Lower-rank donors have smaller containment probability. This covers any full
    old-basis transfer, and hence also the stricter equal-kernel cache event.
    """
    for value in (capacity, opportunities):
        if type(value) is not int or not 0 <= value <= 1_000_000:
            raise ValueError('kernel transfer capacity/opportunities')
    probability, _ = transfer_probabilities(profile, min(profile.n, profile.m))
    return min(Fraction(1), capacity*opportunities*probability)
