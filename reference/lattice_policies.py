"""Paid on-demand lattice policies; no oracle vectors, targets or lookahead."""

from dataclasses import asdict, dataclass
import hashlib
import time

from reference.grinding import SCORE_DOMAIN, _target
from reference.header import ExpectedContext, LabHeader, encode_proof
from reference.lattice_cache import CandidateCache
from reference.sis import verify
from solvers.sphere import enumerate_kernel

POLICIES = ("first", "all", "reuse", "cache-all")
COUNTERS = ("headers", "matrix_entries", "reduction_calls", "sphere_calls", "sphere_nodes",
            "sphere_leaves", "sphere_checks", "reuse_checks", "cache_fill_checks", "cache_read_checks",
            "score_hashes", "score_bytes", "cache_lookups", "cache_hits", "cache_evictions")


@dataclass(frozen=True)
class LatticeBudget:
    nodes: int = 100_000
    reductions: int = 64
    scores: int = 4096
    proofs_per_instance: int = 256
    bits: int = 4096

    def __post_init__(self):
        for value, maximum in zip(asdict(self).values(), (1_000_000, 64, 100_000, 256, 4096), strict=True):
            if type(value) is not int or not 1 <= value <= maximum:
                raise ValueError("invalid lattice policy budget")


def run_lattice_policy(headers, policy, target, reducer, *, budget=None, cache=None):
    _target(target)
    budget = LatticeBudget() if budget is None else budget
    if not isinstance(budget, LatticeBudget) or policy not in POLICIES or not callable(reducer):
        raise ValueError("invalid lattice policy configuration")
    if (type(headers) not in (list, tuple) or not 1 <= len(headers) <= 64
            or any(not isinstance(h, LabHeader) or h.profile.m > 16 for h in headers)):
        raise ValueError("invalid lattice header family")
    base = headers[0]
    context = ExpectedContext(base.network, base.parent, base.height, base.profile)
    if any(not context.matches(h) for h in headers):
        raise ValueError("lattice family context mismatch")
    if policy == "cache-all":
        cache = CandidateCache(proof_limit=budget.proofs_per_instance) if cache is None else cache
        if not isinstance(cache, CandidateCache) or cache.proof_limit != budget.proofs_per_instance:
            raise ValueError("invalid lattice cache")
    elif cache is not None:
        raise ValueError("cache belongs to cache-all policy")
    begin = time.perf_counter_ns()
    work = dict.fromkeys(COUNTERS, 0)
    timers = dict.fromkeys(("construction_ns", "native_reduction_ns", "backend_audit_ns",
                           "reducer_call_ns", "sphere_ns_including_visitor"), 0)
    result = {"policy": policy, "target": str(target), "budget": asdict(budget), "work": work,
              "timers": timers, "reason": "family-exhausted", "hit": None, "acquisition": None,
              "instances": [], "scores": []}
    transcript, acquired = hashlib.sha256(), None

    def score(header, index, vector):
        if work["score_hashes"] == budget.scores:
            result["reason"] = "score-limit"
            return True
        packet = encode_proof(header, vector)
        message = SCORE_DOMAIN+packet
        digest = hashlib.sha256(message).digest()
        work["score_hashes"] += 1
        work["score_bytes"] += len(message)
        transcript.update(message)
        entry = {"header_index": index, "vector": vector, "digest": digest.hex()}
        result["scores"].append(entry)
        if int.from_bytes(digest, "big") < target:
            result["hit"] = entry | {"proof_hex": packet.hex()}
            result["reason"] = "score-hit"
            return True
        if work["score_hashes"] == budget.scores:
            result["reason"] = "score-limit"
            return True
        return False

    for index, header in enumerate(headers):
        if work["score_hashes"] == budget.scores:
            result["reason"] = "score-limit"
            break
        matrix = header.matrix()
        work["headers"] += 1
        work["matrix_entries"] += header.profile.n*header.profile.m
        if policy == "reuse" and acquired is not None:
            work["reuse_checks"] += 1
            valid = verify(header.profile, matrix, acquired)
            result["instances"].append({"index": index, "reason": "reuse-valid" if valid else "reuse-invalid"})
            if valid and score(header, index, acquired):
                break
            continue
        pool = None
        if cache is not None:
            work["cache_lookups"] += 1
            pool = cache.get(header.profile, matrix)
            if pool is not None:
                work["cache_hits"] += 1
                result["instances"].append({"index": index, "reason": "cache-hit", "proof_count": len(pool)})
        if pool is None:
            if work["sphere_nodes"] == budget.nodes:
                result["reason"] = "node-limit"
                break
            if work["reduction_calls"] == budget.reductions:
                result["reason"] = "reduction-limit"
                break
            work["reduction_calls"] += 1
            start = time.perf_counter_ns()
            entry = reducer(header.profile, matrix)
            timers["reducer_call_ns"] += time.perf_counter_ns()-start
            for name, key in (("construction_ns", "construction_ns"), ("native_reduction_ns", "reduction_ns"),
                              ("backend_audit_ns", "audit_ns")):
                value = entry[key]
                if type(value) is not int or value < 0:
                    raise ValueError("invalid reducer timer")
                timers[name] += value

            def visitor(vector):
                nonlocal acquired
                if policy == "reuse":
                    acquired = vector
                    result["acquisition"] = {"header_index": index, "vector": vector}
                stop = score(header, index, vector)
                return stop or policy in ("first", "reuse")

            start = time.perf_counter_ns()
            sphere = enumerate_kernel(header.profile, matrix, entry["reduction"],
                                      node_limit=budget.nodes-work["sphere_nodes"],
                                      proof_limit=budget.proofs_per_instance, bit_limit=budget.bits,
                                      on_proof=visitor if cache is None else None)
            timers["sphere_ns_including_visitor"] += time.perf_counter_ns()-start
            work["sphere_calls"] += 1
            for name, key in (("sphere_nodes", "nodes"), ("sphere_leaves", "leaves"), ("sphere_checks", "sis_checks")):
                work[name] += sphere["work"][key]
            if policy == "reuse" and result["acquisition"] is not None:
                result["acquisition"]["work_through_first_score"] = dict(work)
            certificate = asdict(entry["reduction"])
            certificate.pop("work")
            result["instances"].append({"index": index, "certificate": certificate, "sphere": sphere})
            if result["reason"] in ("score-hit", "score-limit"):
                break
            if sphere["reason"] not in ("domain-exhausted", "visitor-stop"):
                result["reason"] = "sphere-"+sphere["reason"]
                break
            if cache is None:
                continue
            work["cache_fill_checks"] += len(sphere["proofs"])
            work["cache_evictions"] += cache.store(header.profile, matrix, sphere)
            pool = tuple(sphere["proofs"])
        # Every cached/precomputed vector is revalidated; every score binds current header.
        for vector in pool:
            work["cache_read_checks"] += 1
            if not verify(header.profile, matrix, vector):
                raise ValueError("invalid cached vector")
            if score(header, index, vector):
                break
        if result["reason"] in ("score-hit", "score-limit"):
            break
    result["score_transcript_sha256"] = transcript.hexdigest()
    result["elapsed_ns"] = time.perf_counter_ns()-begin
    result["cache_entries_after"] = len(cache) if cache is not None else 0
    return result
