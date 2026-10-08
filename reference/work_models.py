"""Joint research header families and descriptive work accounting, not consensus."""

from dataclasses import replace
from fractions import Fraction

from reference.grinding import header_family
from reference.header import LabHeader

WORK_COMPONENTS = ("headers_processed", "matrix_entries_expanded", "vector_checks",
                   "score_hashes", "score_input_bytes")


def joint_family(base, *, nonces, timestamps, payloads):
    """Timestamp-major, payload-middle, nonce-minor Cartesian family (at most 512)."""
    if not isinstance(base, LabHeader) or any(type(x) is not int or x < 1 or x > 512
                                             for x in (nonces, timestamps, payloads)):
        raise ValueError("joint family type/bound")
    if nonces * timestamps * payloads > 512:
        raise ValueError("joint family product bound")
    # Reuse single-axis derivations, including their scalar overflow checks.
    nonce_axis = header_family(base, "nonce", nonces)
    time_axis = header_family(base, "timestamp", timestamps)
    payload_axis = header_family(base, "payload", payloads)
    return tuple(replace(base, timestamp=t.timestamp, payload=p.payload, nonce=n.nonce)
                 for t in time_axis for p in payload_axis for n in nonce_axis)


def ideal_target_trials(target):
    """Uniform independent eligible-score assumption; not CPU work or chain weight."""
    if type(target) is not int or not 1 <= target <= 2**256:
        raise ValueError("positive research target required")
    return Fraction(2**256, target)


def search_loop_calls(result):
    """Policy enumeration loop entries; unit tests still perform charged SIS checks."""
    policy = result["policy"]
    if policy == "unit":
        return 0
    if policy in ("first", "all"):
        return result["work"]["headers_processed"]
    if policy == "reuse":
        acquired = result["acquisition"]
        return acquired["header_index"] + 1 if acquired else result["work"]["headers_processed"]
    raise ValueError("unknown policy")


def summarize_work(results):
    """All attempts enter denominators; repeated proofs remain experiment occurrences."""
    hits = sum(r["hit"] is not None for r in results)
    total = {name: sum(r["work"][name] for r in results) for name in WORK_COMPONENTS}
    loop_calls = sum(search_loop_calls(r) for r in results)
    return {"runs": len(results), "hit_occurrences": hits, "work": total,
            "search_loop_calls": loop_calls,
            "domain_preparation_box_vectors": sum(r["domain_preparation"]["box_vectors"] for r in results),
            "work_per_hit_occurrence": {name: {"numerator": value, "denominator": hits}
                                        if hits else None for name, value in total.items()}}
