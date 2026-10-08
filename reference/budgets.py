"""Cooperative local wall-time and traced-allocation experiments, not chainwork."""

from collections import Counter
from dataclasses import asdict
import hashlib
import math
import struct
import time
import tracemalloc

from reference.ball import BallSearch
from reference.mitm import MitmSearch
from reference.sis import Profile, expand_matrix, verify
from reference.strategies import _score_message

ALGORITHMS = {"ball": BallSearch, "mitm": MitmSearch}
POLICIES = ("continue", "restart", "reuse")
MAX_INSTANCES = 4096


class BudgetExceeded(Exception):
    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


class Budget:
    def __init__(self, start, time_limit_ns, memory_limit_bytes, clock):
        self.deadline = start + time_limit_ns
        self.memory_limit_bytes, self.clock = memory_limit_bytes, clock

    def check(self):
        if tracemalloc.get_traced_memory()[1] > self.memory_limit_bytes:
            raise BudgetExceeded("memory-limit")
        if self.clock() >= self.deadline:
            raise BudgetExceeded("time-limit")


def run_budgeted(profile, root_seed, algorithm, policy, *, time_limit_ns=50_000_000,
                 memory_limit_bytes=128 * 1024, target=2**252, max_instances=MAX_INSTANCES,
                 clock=time.perf_counter_ns):
    """Same public seed prefix per policy; score hits start the next instance.

    Every scored vector is independently verified inside the measured window.
    Caps are checked cooperatively; one operation and cleanup may overshoot.
    """
    if not isinstance(profile, Profile) or type(root_seed) is not bytes or len(root_seed) != 32:
        raise ValueError("expected Profile and exactly 32 root seed bytes")
    if algorithm not in ALGORITHMS or policy not in POLICIES:
        raise ValueError("unknown algorithm or policy")
    limits = ((time_limit_ns, 2_000_000_000), (memory_limit_bytes, 64 * 1024 * 1024),
              (max_instances, MAX_INSTANCES))
    if any(type(v) is not int or not 1 <= v <= maximum for v, maximum in limits):
        raise ValueError("budget outside laboratory bounds")
    if type(target) is not int or not 0 <= target <= 2**256 or not callable(clock):
        raise ValueError("invalid score target or clock")
    if tracemalloc.is_tracing():
        raise ValueError("requires its own tracemalloc session")
    work = Counter()
    solver_work, instance_stops = Counter(), Counter()
    transcript = hashlib.sha256()
    hit_samples = []
    reason = "instance-limit"
    start = clock()
    budget = Budget(start, time_limit_ns, memory_limit_bytes, clock)

    def score(seed, matrix, vector):
        budget.check()
        if not verify(profile, matrix, vector):
            raise RuntimeError("solver emitted an invalid proof")
        message = _score_message(profile, seed, vector)
        digest = hashlib.sha256(message).digest()
        transcript.update(message)
        work["score_hashes"] += 1
        work["score_input_bytes"] += len(message)
        hit = int.from_bytes(digest, "big") < target
        if hit:
            work["hits"] += 1
            if len(hit_samples) < 8:
                hit_samples.append({"seed": seed.hex(), "vector": vector})
        budget.check()
        return hit

    tracemalloc.start()
    try:
        for index in range(max_instances):
            budget.check()
            seed = hashlib.sha256(b"MagnetNetwork/SIS-LAB/budget-seed/v1\x00"
                                  + root_seed + struct.pack("<I", index)).digest()
            work["matrix_expansions"] += 1
            matrix = expand_matrix(profile, seed)
            budget.check()
            search = ALGORITHMS[algorithm](profile, matrix, checkpoint=budget.check)
            iterator = search.solutions()
            instance_reason = None
            try:
                for vector in iterator:
                    if score(seed, matrix, vector):
                        instance_reason = "score-hit"
                        break
                    if policy == "restart":
                        instance_reason = "policy-restart"
                        break
                    if policy == "reuse":
                        budget.check()
                        divisor = math.gcd(*vector)
                        primitive = tuple(v // divisor for v in vector)
                        norm = sum(v * v for v in primitive)
                        work["reuse_setups"] += 1
                        work["gcd_inputs"] += profile.m
                        work["reuse_coordinate_ops"] += profile.m
                        for factor in range(1, math.isqrt(profile.b2 // norm) + 1):
                            budget.check()
                            proposal = tuple(factor * v for v in primitive)
                            work["reuse_coordinate_ops"] += profile.m
                            if proposal != vector and score(seed, matrix, proposal):
                                instance_reason = "score-hit"
                                break
                        instance_reason = instance_reason or "policy-restart"
                        break
                instance_reason = instance_reason or search.reason
            finally:
                iterator.close()
                solver_work.update(asdict(search.work))
            instance_stops[instance_reason] += 1
            if instance_reason not in ("score-hit", "policy-restart", "domain-exhausted"):
                reason = "solver-limit"
                break
        budget.check()
    except BudgetExceeded as failure:
        reason = failure.reason
    finally:
        try:
            elapsed = clock() - start
            peak = tracemalloc.get_traced_memory()[1]
        finally:
            tracemalloc.stop()
    return {"reason": reason, "elapsed_ns": elapsed, "peak_traced_bytes": peak,
            "work": dict(work), "solver_work": dict(solver_work), "instance_stops": dict(instance_stops),
            "transcript_sha256": transcript.hexdigest(), "hit_samples": hit_samples}
