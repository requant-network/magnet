"""Local end-to-end time and separate traced-allocation probes on toy SIS."""

from collections import Counter
import gc
import hashlib
import json
from pathlib import Path
import platform
import statistics
import sys
import time
import tracemalloc

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from reference.mitm import MAX_JOIN_PAIRS, MAX_TABLE_ENTRIES, run_mitm
from reference.sis import Profile, expand_matrix, verify
from reference.strategies import run_strategy

SETUPS = [(17, 2, 3, 8), (17, 2, 4, 32), (17, 2, 6, 8), (17, 2, 6, 16)]
BATCHES = 2
INSTANCES_PER_BATCH = 8
REPEATS = 3
TARGETS = {"all-proofs": 0, "one-in-16": 2**252, "one-in-256": 2**248}


def search(algorithm, profile, seed, target):
    if algorithm == "mitm":
        return run_mitm(profile, seed, target=target)
    if algorithm == "full-search":
        return run_strategy(profile, seed, "full-search", target=target, proposal_limit=1_000_000)
    raise ValueError("unknown algorithm")


def audit(profile, seed, result):
    matrix = expand_matrix(profile, seed)
    if result["reason"] not in ("domain-exhausted", "score-hit"):
        raise RuntimeError("comparison stopped at a cap or interrupted search")
    if (len(result["proofs"]) != len(set(result["proofs"]))
            or not all(verify(profile, matrix, x) for x in result["proofs"])):
        raise RuntimeError("invalid or duplicate emitted proofs")


def run_setup(q, n, m, b2):
    profile = Profile(q, n, m, b2)
    totals = {label: {algorithm: {"work": Counter(), "stops": Counter(),
                                 "sum_instance_median_wall_ns": 0}
                      for algorithm in ("full-search", "mitm")} for label in TARGETS}
    records = []
    memory_probes = []
    for batch in range(BATCHES):
        for index in range(INSTANCES_PER_BATCH):
            label = f"magnet-sis-mitm-v1/{q}/{n}/{m}/{b2}/{batch}/{index}"
            seed = hashlib.sha256(label.encode("ascii")).digest()
            target_results = {}
            for target_index, (name, target) in enumerate(TARGETS.items()):
                results = {}
                clocks = {a: {"wall_ns": []} for a in ("full-search", "mitm")}
                for repetition in range(REPEATS):
                    order = ["full-search", "mitm"]
                    if (batch + index + target_index + repetition) % 2:
                        order.reverse()
                    for algorithm in order:
                        wall_start = time.perf_counter_ns()
                        result = search(algorithm, profile, seed, target)
                        wall_elapsed = time.perf_counter_ns() - wall_start
                        clocks[algorithm]["wall_ns"].append(wall_elapsed)
                        if algorithm in results and result != results[algorithm]:
                            raise RuntimeError("non-reproducible deterministic search result")
                        results[algorithm] = result
                for algorithm, result in results.items():
                    audit(profile, seed, result)  # Untimed; no oracle is supplied to search.
                    total = totals[name][algorithm]
                    total["work"].update(result["work"])
                    total["stops"][result["reason"]] += 1
                    total["sum_instance_median_wall_ns"] += statistics.median(clocks[algorithm]["wall_ns"])
                if results["full-search"]["reason"] != results["mitm"]["reason"]:
                    raise RuntimeError("complete solvers disagree on score-hit existence")
                if target == 0 and set(results["full-search"]["proofs"]) != set(results["mitm"]["proofs"]):
                    raise RuntimeError("complete solvers disagree on exact solution set")
                target_results[name] = {a: {**r, "clocks": clocks[a]} for a, r in results.items()}
            if batch == 0 and index == 0:
                # One representative all-proofs probe per profile, separate from clocks.
                for algorithm in ("full-search", "mitm"):
                    gc.collect()
                    tracemalloc.start()
                    try:
                        result = search(algorithm, profile, seed, 0)
                        _, peak = tracemalloc.get_traced_memory()
                    finally:
                        tracemalloc.stop()
                    if result != {k: v for k, v in target_results["all-proofs"][algorithm].items() if k != "clocks"}:
                        raise RuntimeError("memory probe differs from timed search")
                    memory_probes.append({"seed": seed.hex(), "algorithm": algorithm,
                                          "target": "all-proofs", "python_peak_traced_bytes": peak})
            records.append({"batch": batch, "index": index, "seed": seed.hex(), "targets": target_results})
    return {"profile": {"q": q, "n": n, "m": m, "b2": b2},
            "instances": BATCHES * INSTANCES_PER_BATCH, "targets": totals,
            "memory_probes": memory_probes, "records": records}


def main():
    destination = ROOT / "artifacts"
    destination.mkdir(exist_ok=True)
    output = destination / "mitm-survey.json"
    output.write_text('{"status":"running-or-incomplete"}\n', encoding="utf-8")
    # Warm up shared paths; this public seed is not part of the recorded sample.
    for algorithm in ("full-search", "mitm"):
        search(algorithm, Profile(7, 1, 2, 4), bytes(32), 0)
    report = {"status": "complete", "version": "mitm-survey-v1",
              "warning": "Local instrumented Python toy baselines; no large-SIS security or mining estimate.",
              "environment": {"python": platform.python_version(), "platform": platform.platform(),
                              "processor": platform.processor()},
              "configuration": {"batches": BATCHES, "instances_per_batch": INSTANCES_PER_BATCH,
                                "timing_repeats": REPEATS, "target_hex": {k: hex(v) for k, v in TARGETS.items()},
                                "full_proposal_limit": 1_000_000, "mitm_table_limit": MAX_TABLE_ENTRIES,
                                "mitm_pair_limit": MAX_JOIN_PAIRS},
              "method": "Alternating algorithm order, end-to-end clocks; audit outside clocks; separate representative tracemalloc runs.",
              "setups": []}
    for setup in SETUPS:
        result = run_setup(*setup)
        report["setups"].append(result)
        print(json.dumps({"profile": result["profile"], "targets": result["targets"],
                          "memory_probes": result["memory_probes"]}), flush=True)
    paths = ["reference/sis.py", "reference/search.py", "reference/strategies.py", "reference/mitm.py",
             "scripts/mitm_survey.py", "tests/test_mitm.py"]
    report["source_sha256"] = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths}
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
