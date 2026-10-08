"""Exact bounded enumeration of a certified full SIS kernel lattice."""

from fractions import Fraction
import math

from reference.sis import Profile, verify
from solvers.lattice_audit import audit_certificate


class _Limit(Exception):
    pass


def coefficient_interval(center, radius_squared):
    """Exact integer interval; no floating-point square root at a norm boundary."""
    center, radius_squared = Fraction(center), Fraction(radius_squared)
    if radius_squared < 0:
        return 1, 0
    a, b = center.numerator, center.denominator
    distance = math.isqrt(radius_squared.numerator * b*b // radius_squared.denominator)
    return -(-(a-distance)//b), (a+distance)//b


def enumerate_kernel(profile, matrix, reduction, *, node_limit=1_000_000,
                     proof_limit=100_000, bit_limit=4096, on_proof=None):
    if not isinstance(profile, Profile):
        raise ValueError("invalid sphere profile")
    if on_proof is not None and not callable(on_proof):
        raise ValueError("invalid sphere visitor")
    for value, maximum in ((node_limit, 1_000_000), (proof_limit, 100_000), (bit_limit, 4096)):
        if type(value) is not int or not 1 <= value <= maximum:
            raise ValueError("invalid sphere budget")
    # Bound before audit, whose separate contract admits larger integers.
    for name in ("initial_basis", "basis", "transform"):
        square = getattr(reduction, name, None)
        if (type(square) not in (list, tuple) or len(square) != profile.m or profile.m > 16
                or any(type(row) not in (list, tuple) or len(row) != profile.m for row in square)
                or any(type(x) is not int or abs(x).bit_length() > 256 for row in square for x in row)):
            raise ValueError("invalid bounded sphere certificate")
    certificate = audit_certificate(profile, matrix, reduction)
    basis = reduction.basis
    work = {"nodes": 0, "leaves": 0, "reconstruction_terms": 0,
            "sis_checks": 0, "max_fraction_bits": 0}
    proofs, mu, norms, orthogonal = [], [], [], []
    result = {"reason": "domain-exhausted", "proofs": proofs, "work": work, "audit": certificate}

    def bounded(value):
        value = Fraction(value)
        bits = max(abs(value.numerator).bit_length(), value.denominator.bit_length())
        work["max_fraction_bits"] = max(work["max_fraction_bits"], bits)
        if bits > bit_limit:
            raise _Limit("arithmetic-limit")
        return value

    coefficients = [0] * profile.m

    def walk(level, remaining):
        if level < 0:
            work["leaves"] += 1
            vector = tuple(sum(coefficients[i] * basis[i][j] for i in range(profile.m))
                           for j in range(profile.m))
            work["reconstruction_terms"] += profile.m * profile.m
            if next((x for x in vector if x), 0) <= 0:
                return
            work["sis_checks"] += 1
            if not verify(profile, matrix, vector):
                raise RuntimeError("sphere emitted invalid SIS vector")
            if len(proofs) == proof_limit:
                raise _Limit("proof-limit")
            proofs.append(vector)
            if on_proof is not None:
                stop = on_proof(vector)
                if type(stop) is not bool:
                    raise ValueError("sphere visitor must return bool")
                if stop:
                    raise _Limit("visitor-stop")
            return
        center = bounded(-sum((mu[j][level]*coefficients[j] for j in range(level+1, profile.m)), Fraction(0)))
        radius_squared = bounded(remaining/norms[level])
        lower, upper = coefficient_interval(center, radius_squared)
        for coefficient in range(lower, upper+1):
            if work["nodes"] == node_limit:
                raise _Limit("node-limit")
            work["nodes"] += 1
            coefficients[level] = coefficient
            cost = bounded(bounded(coefficient-center)**2 * norms[level])
            if cost > remaining:
                raise RuntimeError("incorrect sphere interval")
            walk(level-1, bounded(remaining-cost))

    try:
        for row in basis:
            original = tuple(bounded(x) for x in row)
            residual, row_mu = list(original), []
            for star, norm in zip(orthogonal, norms, strict=True):
                coefficient = bounded(sum((a*b for a, b in zip(original, star)), Fraction(0))/norm)
                row_mu.append(coefficient)
                residual = [bounded(a-coefficient*b) for a, b in zip(residual, star)]
            norm = bounded(sum((x*x for x in residual), Fraction(0)))
            if norm <= 0:
                raise RuntimeError("dependent certified sphere basis")
            orthogonal.append(residual)
            mu.append(row_mu)
            norms.append(norm)
        walk(profile.m-1, Fraction(profile.b2))
    except _Limit as error:
        result["reason"] = str(error)
    finally:
        # The recursive closure otherwise retains the entire search until cyclic GC.
        walk = None
    result["proofs"] = sorted(proofs)
    return result
