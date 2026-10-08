"""Exact norm-ball comparison and common cooperative time/allocation windows."""

from collections import Counter
from dataclasses import asdict
import gc
import hashlib
import json
from pathlib import Path
import platform
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from reference.ball import BallSearch
from reference.budgets import ALGORITHMS, POLICIES, run_budgeted
from reference.mitm import MitmSearch
from reference.sis import Profile, expand_matrix, verify

SETUPS = [(17, 2, 4, 32), (17, 2, 6, 16), (17, 2, 8, 8)]
BATCHES = 2
EXACT_INSTANCES = 8
REPEATS = 3
TIME_LIMIT_NS = 50_000_000
MEMORY_LIMITS = (32 * 1024, 128 * 1024, 256 * 1024)
TARGETS = {"one-in-16": 2**252, "one-in-256": 2**248}


def exact_run(profile, seed, algorithm):
    matrix = expand_matrix(profile, seed)
    search = (BallSearch if algorithm == "ball" else MitmSearch)(profile, matrix)
    iterator = search.solutions()
    try:
        proofs = list(iterator)
    finally:
        iterator.close()
    return {"proofs": proofs, "reason": search.reason, "work": asdict(search.work)}


def exact_comparison(profile):
    totals = {a: {"work": Counter(), "proofs": 0, "sum_instance_median_wall_ns": 0} for a in ALGORITHMS}
    records = []
    for batch in range(BATCHES):
        for index in range(EXACT_INSTANCES):
            label = f"magnet-sis-ball-v1/{profile.q}/{profile.n}/{profile.m}/{profile.b2}/{batch}/{index}"
            seed = hashlib.sha256(label.encode("ascii")).digest()
            results, clocks = {}, {a: [] for a in ALGORITHMS}
            for repetition in range(REPEATS):
                order = list(ALGORITHMS)
                if (batch + index + repetition) % 2:
                    order.reverse()
                for algorithm in order:
                    start = time.perf_counter_ns()
                    result = exact_run(profile, seed, algorithm)
                    elapsed = time.perf_counter_ns() - start
                    clocks[algorithm].append(elapsed)
                    if algorithm in results and results[algorithm] != result:
                        raise RuntimeError("deterministic exact search differs across repetitions")
                    results[algorithm] = result
            matrix = expand_matrix(profile, seed)
            for algorithm, result in results.items():
                if result["reason"] != "domain-exhausted":
                    raise RuntimeError("exact comparison hit a safety cap")
                if (len(result["proofs"]) != len(set(result["proofs"]))
                        or not all(verify(profile, matrix, x) for x in result["proofs"])):
                    raise RuntimeError("invalid or duplicate exact output")
                totals[algorithm]["work"].update(result["work"])
                totals[algorithm]["proofs"] += len(result["proofs"])
                totals[algorithm]["sum_instance_median_wall_ns"] += statistics.median(clocks[algorithm])
            if set(results["ball"]["proofs"]) != set(results["mitm"]["proofs"]):
                raise RuntimeError("exact solvers disagree")
            records.append({"seed": seed.hex(), "results": results, "clocks": clocks})
    return {"instances": BATCHES * EXACT_INSTANCES, "algorithms": totals, "records": records}


def budget_comparison(profile):
    cases = [(a, p) for a in ALGORITHMS for p in POLICIES]
    groups = []
    for memory in MEMORY_LIMITS:
        for target_name, target in TARGETS.items():
            records = []
            for batch in range(BATCHES):
                label = f"magnet-sis-budget-v1/{profile.q}/{profile.n}/{profile.m}/{profile.b2}/{batch}"
                root_seed = hashlib.sha256(label.encode("ascii")).digest()
                for repetition in range(REPEATS):
                    shift = (batch + repetition) % len(cases)
                    order = cases[shift:] + cases[:shift]
                    if repetition % 2:
                        order.reverse()
                    for algorithm, policy in order:
                        gc.collect()  # Outside the budget window for every case.
                        result = run_budgeted(profile, root_seed, algorithm, policy,
                                              time_limit_ns=TIME_LIMIT_NS, memory_limit_bytes=memory,
                                              target=target)
                        if result["reason"] not in ("time-limit", "memory-limit"):
                            raise RuntimeError("window hit an instance/solver safety limit")
                        for sample in result["hit_samples"]:
                            a = expand_matrix(profile, bytes.fromhex(sample["seed"]))
                            if not verify(profile, a, sample["vector"]):
                                raise RuntimeError("hit sample acceptance audit failed")
                        records.append({"batch": batch, "repetition": repetition,
                                        "root_seed": root_seed.hex(), "algorithm": algorithm,
                                        "policy": policy, "result": result})
            summary = []
            for algorithm, policy in cases:
                results = [r["result"] for r in records if r["algorithm"] == algorithm and r["policy"] == policy]
                summary.append({"algorithm": algorithm, "policy": policy, "windows": len(results),
                                "stops": dict(Counter(r["reason"] for r in results)),
                                "hits": sum(r["work"].get("hits", 0) for r in results),
                                "score_hashes": sum(r["work"].get("score_hashes", 0) for r in results),
                                "matrix_expansions": sum(r["work"].get("matrix_expansions", 0) for r in results),
                                "median_hits_per_window": statistics.median(r["work"].get("hits", 0) for r in results),
                                "median_elapsed_ns": statistics.median(r["elapsed_ns"] for r in results),
                                "max_elapsed_ns": max(r["elapsed_ns"] for r in results),
                                "max_peak_traced_bytes": max(r["peak_traced_bytes"] for r in results)})
            groups.append({"memory_limit_bytes": memory, "target": target_name,
                           "summary": summary, "records": records})
    return groups


def main():
    destination = ROOT / "artifacts"
    destination.mkdir(exist_ok=True)
    output = destination / "budget-survey.json"
    output.write_text('{"status":"running-or-incomplete"}\n', encoding="utf-8")
    report = {"status": "complete", "version": "budget-survey-v1",
              "warning": "Cooperative instrumented Python budgets and toy profiles; no calibrated consensus work.",
              "environment": {"python": platform.python_version(), "platform": platform.platform(),
                              "processor": platform.processor()},
              "configuration": {"batches": BATCHES, "exact_instances_per_batch": EXACT_INSTANCES,
                                "repeats": REPEATS, "time_limit_ns": TIME_LIMIT_NS,
                                "memory_limit_bytes": MEMORY_LIMITS,
                                "target_hex": {k: hex(v) for k, v in TARGETS.items()}},
              "method": "Untraced exact comparisons, separate common traced-budget windows; rotated case order; same root seed prefix per batch.",
              "setups": []}
    for setup in SETUPS:
        profile = Profile(*setup)
        result = {"profile": asdict(profile), "exact": exact_comparison(profile),
                  "budgets": budget_comparison(profile)}
        report["setups"].append(result)
        print(json.dumps({"profile": result["profile"], "exact": result["exact"]["algorithms"],
                          "budgets": [{k: v for k, v in group.items() if k != "records"} for group in result["budgets"]]}), flush=True)
    paths = ["reference/sis.py", "reference/strategies.py", "reference/mitm.py", "reference/ball.py",
             "reference/budgets.py", "scripts/budget_survey.py", "tests/test_ball_budgets.py"]
    report["source_sha256"] = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths}
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
