"""Paid multi-vector FIFO campaigns with shared search/check/score ceilings."""

from dataclasses import asdict, dataclass, replace
import hashlib
from itertools import combinations, product
import time

from reference.grinding import SCORE_DOMAIN, _target, score_digest
from reference.header import LabHeader, encode_proof
from reference.reuse import canonical
from reference.sis import verify

POLICIES = ("restart-all", "pool-fallback", "pool-all")
WORK = ("headers", "matrix_entries", "acquisitions", "search_nodes", "pool_checks",
        "combination_checks", "score_hashes", "score_bytes", "pool_inserts", "pool_evictions", "duplicates")


@dataclass(frozen=True)
class PoolBudget:
    nodes: int = 100_000
    acquisitions: int = 128
    checks: int = 8192
    scores: int = 4096
    proofs: int = 32

    def __post_init__(self):
        for name, maximum in (("nodes", 1_000_000), ("acquisitions", 128), ("checks", 100_000),
                              ("scores", 100_000), ("proofs", 256)):
            if type(getattr(self, name)) is not int or not 1 <= getattr(self, name) <= maximum:
                raise ValueError("pool budget outside laboratory bounds")


def joint_headers(base, *, nonces=2, times=2, payloads=2):
    """Finite allowed Cartesian surface, deterministic ordering, no sampled free winner."""
    if not isinstance(base, LabHeader):
        raise ValueError("base header required")
    for value in (nonces, times, payloads):
        if type(value) is not int or not 1 <= value <= 8:
            raise ValueError("joint axis count outside 1..8")
    if nonces*times*payloads > 16 or base.nonce+nonces > 2**64 or base.timestamp+times > 2**64:
        raise ValueError("joint family size/overflow")
    commitments = [base.payload] + [hashlib.sha256(b"MagnetNetwork/joint-payload/v1\0"+base.payload+
                                                  i.to_bytes(8, "little")).digest() for i in range(1, payloads)]
    return tuple(replace(base, nonce=base.nonce+n, timestamp=base.timestamp+t, payload=payload)
                 for payload, t, n in product(commitments, range(times), range(nonces)))


def run_pool_campaign(stages, policy, target, solver, *, capacity=4, combine=True, budget=None, on_stage=None,
                      retain=None):
    _target(target)
    budget = PoolBudget() if budget is None else budget
    if (type(stages) not in (list, tuple) or not 1 <= len(stages) <= 8 or policy not in POLICIES
            or not hasattr(solver, "acquire") or not isinstance(budget, PoolBudget)
            or type(capacity) is not int or not 1 <= capacity <= 16 or type(combine) is not bool
            or on_stage is not None and not callable(on_stage) or retain is not None and not callable(retain)):
        raise ValueError("pool campaign configuration")
    for stage in stages:
        if (type(stage) not in (tuple, list) or not 1 <= len(stage) <= 16
                or any(not isinstance(h, LabHeader) or h.profile.m > 16 for h in stage)):
            raise ValueError("pool stage bounds")
        base = stage[0]
        if any((h.network, h.parent, h.height, h.profile) !=
               (base.network, base.parent, base.height, base.profile) for h in stage):
            raise ValueError("stage context mismatch")
    first = stages[0][0]
    if any((stage[0].network, stage[0].profile) != (first.network, first.profile) for stage in stages):
        raise ValueError("campaign network/profile mismatch")
    begin = time.perf_counter_ns()
    work = dict.fromkeys(WORK, 0)
    result = {"policy": policy, "capacity": capacity, "combine": combine, "target": str(target),
              "budget": asdict(budget), "work": work, "stages": [], "instances": [],
              "scores": [], "reason": "campaign-exhausted"}
    pool, halted = [], False
    def insert(vector):
        if vector in pool:
            work["duplicates"] += 1
            return
        candidates = tuple(pool)+(vector,)
        if len(candidates) > capacity:
            selected = candidates[1:] if retain is None else retain(first.profile, candidates, capacity)
            # Retention is an ordered subsequence, never a new source of vectors.
            if (type(selected) is not tuple or len(selected) != capacity or any(
                    type(x) is not tuple or any(type(v) is not int for v in x) for x in selected)
                    or selected not in tuple(
                    candidates[:i]+candidates[i+1:] for i in range(len(candidates)))):
                raise RuntimeError("invalid retained subset/order")
            pool[:] = selected
            work["pool_evictions"] += 1
        else:
            pool.append(vector)
        work["pool_inserts"] += 1
    for stage_index, headers in enumerate(stages):
        before = dict(work)
        stage = {"index": stage_index, "reason": "not-visited" if halted else "stage-exhausted", "hit": None}
        for index, header in enumerate(headers):
            if halted:
                break
            if work["score_hashes"] == budget.scores:
                stage["reason"], halted = "score-limit", True
                break
            matrix = header.matrix()
            work["headers"] += 1
            work["matrix_entries"] += header.profile.n*header.profile.m
            if policy == "restart-all":
                pool.clear()
            candidates, scored = [], set()
            instance = {"stage": stage_index, "index": index, "header_hex": header.encode().hex(),
                        "matrix_sha256": hashlib.sha256(b"".join(x.to_bytes(4, "little") for row in matrix for x in row)).hexdigest(),
                        "pool_before": tuple(pool), "valid_carried": []}
            result["instances"].append(instance)
            def check(vector, kind):
                nonlocal halted
                if work["pool_checks"]+work["combination_checks"] == budget.checks:
                    stage["reason"], halted = "check-limit", True
                    return False
                work[kind] += 1
                return verify(header.profile, matrix, vector)
            def score(vector, origin):
                nonlocal halted
                if vector in scored:
                    return False
                if work["score_hashes"] == budget.scores:
                    stage["reason"], halted = "score-limit", True
                    return False
                scored.add(vector)
                digest = score_digest(header, vector)
                work["score_hashes"] += 1
                work["score_bytes"] += len(SCORE_DOMAIN)+len(encode_proof(header, vector))
                sample = {"stage": stage_index, "index": index, "vector": vector, "digest": digest.hex(), "origin": origin}
                result["scores"].append(sample)
                if int.from_bytes(digest, "big") < target:
                    stage["hit"] = sample | {"proof_hex": encode_proof(header, vector).hex()}
                    stage["reason"] = "score-hit"
                    return True
                if work["score_hashes"] == budget.scores:
                    stage["reason"], halted = "score-limit", True
                return False
            for vector in tuple(pool):
                valid = check(vector, "pool_checks")
                if valid:
                    candidates.append(vector)
                    instance["valid_carried"].append(vector)
                    if score(vector, "carried"):
                        break
                if halted:
                    break
            if combine and not halted and stage["hit"] is None:
                # Only current-matrix-valid vectors can seed combinations. Every
                # +/- candidate (including zero, duplicate and invalid) is paid.
                for left, right in combinations(tuple(candidates), 2):
                    for sign in (-1, 1):
                        vector = canonical(tuple(a+sign*b for a, b in zip(left, right)))
                        if check(vector, "combination_checks"):
                            insert(vector)
                            if score(vector, "combination"):
                                break
                        if halted:
                            break
                    if halted or stage["hit"] is not None:
                        break
            fresh = policy != "pool-fallback" or not candidates
            if not halted and stage["hit"] is None and fresh:
                if work["acquisitions"] == budget.acquisitions or work["search_nodes"] == budget.nodes:
                    stage["reason"] = "acquisition-limit" if work["acquisitions"] == budget.acquisitions else "node-limit"
                    halted = True
                else:
                    work["acquisitions"] += 1
                    acquired = solver.acquire(header.profile, matrix, budget.nodes-work["search_nodes"], budget.proofs)
                    charged = acquired["work"]["nodes"]
                    if type(charged) is not int or not 0 <= charged <= budget.nodes-work["search_nodes"]:
                        raise RuntimeError("solver exceeded campaign node accounting")
                    if (len(acquired["proofs"]) > budget.proofs or len(set(map(tuple, acquired["proofs"]))) != len(acquired["proofs"])
                            or not all(verify(header.profile, matrix, x) for x in acquired["proofs"])):
                        raise RuntimeError("invalid acquired proof pool")
                    work["search_nodes"] += charged
                    instance["acquired"] = acquired
                    # Acquisition is eager and fully charged before scoring. Retain
                    # the entire bounded pool even if its first score is a hit.
                    for vector in acquired["proofs"]:
                        insert(tuple(vector))
                    for vector in acquired["proofs"]:
                        if score(tuple(vector), "acquired") or halted:
                            break
            if stage["hit"] is not None or halted:
                break
        stage["work"] = {name: work[name]-before[name] for name in WORK}
        stage["pool_after"] = tuple(pool)
        result["stages"].append(stage)
        if halted and stage["reason"] != "not-visited":
            result["reason"] = stage["reason"]
        result["elapsed_ns"] = time.perf_counter_ns()-begin
        if on_stage is not None:
            on_stage(result)
    result["pool"] = tuple(pool)
    return result
