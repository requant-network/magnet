"""Bounded toy search policies with component counters, not consensus work."""

from dataclasses import asdict, dataclass
import hashlib
import itertools
import math
import struct

from reference.search import MAX_CANDIDATES
from reference.sis import Profile, expand_matrix

STRATEGIES = ("first-restart", "first-reuse", "full-search", "sparse-reuse-full")
SCORE_DOMAIN = b"MagnetNetwork/SIS-LAB/strategy-score/v1\x00"


@dataclass
class Work:
    matrix_expansions: int = 0
    shake_output_bytes: int = 0
    proposals: int = 0
    norm_terms: int = 0
    sign_terms: int = 0
    matrix_terms: int = 0
    row_reductions: int = 0
    reuse_setups: int = 0
    gcd_inputs: int = 0
    reuse_coordinate_ops: int = 0
    score_hashes: int = 0
    score_input_bytes: int = 0


def _score_message(profile, seed, vector):
    return (SCORE_DOMAIN + struct.pack("<IHHQ", profile.q, profile.n, profile.m, profile.b2)
            + seed + struct.pack(f"<{profile.m}i", *vector))


def _sparse_candidates(m, radius):
    # Include out-of-ball pairs: evaluation and norm rejection are charged.
    for i in range(m):
        for a in range(1, radius + 1):
            x = [0] * m
            x[i] = a
            yield tuple(x)
    for i, j in itertools.combinations(range(m), 2):
        for a in range(1, radius + 1):
            for b in range(-radius, radius + 1):
                if b:
                    x = [0] * m
                    x[i], x[j] = a, b
                    yield tuple(x)


def _multiples(profile, vector, work):
    work.reuse_setups += 1
    work.gcd_inputs += profile.m
    divisor = math.gcd(*vector)
    primitive = tuple(v // divisor for v in vector)
    work.reuse_coordinate_ops += profile.m
    norm = sum(v * v for v in primitive)
    work.norm_terms += profile.m
    for k in range(1, math.isqrt(profile.b2 // norm) + 1):
        work.reuse_coordinate_ops += profile.m
        yield tuple(k * v for v in primitive)


def _valid(profile, matrix, vector, work):
    work.proposals += 1
    work.norm_terms += profile.m
    norm = sum(v * v for v in vector)
    if not 0 < norm <= profile.b2:
        return False
    for coordinate in vector:
        work.sign_terms += 1
        if coordinate:
            if coordinate < 0:
                return False
            break
    # Evaluate every row, including after a failed row, for explicit accounting.
    residues = [sum(a * x for a, x in zip(row, vector)) % profile.q for row in matrix]
    work.matrix_terms += profile.n * profile.m
    work.row_reductions += profile.n
    return not any(residues)


def run_strategy(profile, seed, strategy, *, proposal_limit=100_000, target=2**252):
    """Search one generated instance; no known vectors or oracle are accepted.

    target uses digest < target, including 0 (never) and 2**256 (always).
    A proposal cap is a safety bound, NOT an equal-time or equal-work budget.
    """
    if not isinstance(profile, Profile) or type(seed) is not bytes or len(seed) != 32:
        raise ValueError("expected Profile and exactly 32 seed bytes")
    if strategy not in STRATEGIES:
        raise ValueError("unknown strategy")
    if type(proposal_limit) is not int or not 1 <= proposal_limit <= MAX_CANDIDATES:
        raise ValueError("proposal limit outside laboratory budget")
    if type(target) is not int or not 0 <= target <= 2**256:
        raise ValueError("invalid score target")
    radius = math.isqrt(profile.b2)
    if (2 * radius + 1)**profile.m > MAX_CANDIDATES:
        raise ValueError("instance exceeds exhaustive laboratory budget")
    matrix = expand_matrix(profile, seed)
    work = Work(matrix_expansions=1, shake_output_bytes=2 * (4 * profile.n * profile.m + 1024))
    full = itertools.product(range(-radius, radius + 1), repeat=profile.m)
    candidates = (itertools.chain(_sparse_candidates(profile.m, radius), full)
                  if strategy == "sparse-reuse-full" else full)
    reuse = None
    first_work = None
    seen = set()
    proofs = []
    reason = "proposal-limit"
    while work.proposals < proposal_limit:
        if reuse is not None:
            vector = next(reuse, None)
            if vector is None:
                reuse = None
                if strategy == "first-reuse":
                    reason = "policy-restart"
                    break
                continue
        else:
            vector = next(candidates, None)
            if vector is None:
                reason = "domain-exhausted"
                break
        if not _valid(profile, matrix, vector, work) or vector in seen:
            continue
        seen.add(vector)
        if first_work is None:
            first_work = asdict(work)
            if strategy in ("first-reuse", "sparse-reuse-full"):
                reuse = _multiples(profile, vector, work)
        message = _score_message(profile, seed, vector)
        digest = hashlib.sha256(message).digest()
        work.score_hashes += 1
        work.score_input_bytes += len(message)
        proofs.append(vector)
        if int.from_bytes(digest, "big") < target:
            reason = "score-hit"
            break
        if strategy == "first-restart":
            reason = "policy-restart"
            break
    return {"reason": reason, "work": asdict(work), "first_solution_work": first_work,
            "proofs": proofs}
