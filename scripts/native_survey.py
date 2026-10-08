"""Reproducible native CPU scale study; no score, header or work calibration."""
from collections import Counter
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import platform
import statistics
import struct
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from reference.ball import BallSearch
from reference.mitm import MitmSearch
from reference.sis import Profile, expand_matrix, verify
from scripts.native_driver import build_native, encode_request, run_requests

SETUPS = [(17, 2, 6, 16), (17, 2, 8, 8), (257, 3, 10, 8),
          (257, 3, 12, 12), (257, 3, 14, 12), (17, 2, 12, 12)]
BATCHES, INSTANCES, REPEATS = 2, 3, 3
ALGORITHMS = ("ball", "mitm")


def proof_digest(proofs):
    digest = hashlib.sha256()
    for vector in sorted(proofs):
        digest.update(struct.pack(f"<{len(vector)}i", *vector))
    return digest.hexdigest()


def audit(profile, matrix, result):
    proofs = result["proofs"]
    if len(proofs) != len(set(proofs)) or not all(verify(profile, matrix, x) for x in proofs):
        raise RuntimeError("invalid or duplicated search output")


def python_run(profile, matrix, algorithm):
    start = time.perf_counter_ns()
    search = (BallSearch if algorithm == "ball" else MitmSearch)(profile, matrix)
    iterator = search.solutions()
    try:
        proofs = list(iterator)
    finally:
        iterator.close()
    elapsed = time.perf_counter_ns() - start
    return {"stop": search.reason, "proofs": proofs, "work": asdict(search.work), "elapsed_ns": [elapsed]}


def compact(result):
    return {k: v for k, v in result.items() if k != "proofs"} | {
        "proof_count": len(result["proofs"]), "proof_set_sha256": proof_digest(result["proofs"])}


def study(executable, profile, compare_python):
    records = []
    for batch in range(BATCHES):
        for index in range(INSTANCES):
            label = f"magnet-sis-native-v1/{profile.q}/{profile.n}/{profile.m}/{profile.b2}/{batch}/{index}"
            seed = hashlib.sha256(label.encode("ascii")).digest()
            matrix = expand_matrix(profile, seed)
            final, times = {}, {}
            for repetition in range(REPEATS):
                order = list(ALGORITHMS)
                if (batch + index + repetition) % 2:
                    order.reverse()
                for algorithm in order:
                    runs = [("native-" + algorithm, run_requests(executable, [
                        encode_request(profile, matrix, algorithm)])[0])]
                    if compare_python:
                        runs.append(("python-" + algorithm, python_run(profile, matrix, algorithm)))
                    for name, result in runs:
                        audit(profile, matrix, result)
                        if result["stop"] != "domain-exhausted":
                            raise RuntimeError("exact scale study hit a safety cap")
                        transcript = compact(result)
                        elapsed = transcript.pop("elapsed_ns")
                        if name in final:
                            previous = compact(final[name])
                            previous.pop("elapsed_ns")
                            if previous != transcript:
                                raise RuntimeError("deterministic result differs across repetitions")
                        final[name] = result
                        times.setdefault(name, []).extend(elapsed)
            sets = [set(x["proofs"]) for x in final.values()]
            if any(vectors != sets[0] for vectors in sets[1:]):
                raise RuntimeError("scale study exact sets differ")
            records.append({"batch": batch, "index": index, "seed": seed.hex(),
                            "results": {name: compact(result) | {"elapsed_ns": times[name]}
                                        for name, result in final.items()}})
    totals = {}
    for name in records[0]["results"]:
        runs = [record["results"][name] for record in records]
        work = Counter()
        for run in runs:
            work.update(run["work"])
        totals[name] = {"proofs": sum(x["proof_count"] for x in runs), "work": dict(work),
                       "sum_instance_median_ns": sum(statistics.median(x["elapsed_ns"]) for x in runs)}
        if name.startswith("native"):
            capacities = [x["owned_capacity_bytes"] for x in runs]
            totals[name]["capacity_bytes_min_max"] = [min(capacities), max(capacities)]
    ratio = totals["native-ball"]["sum_instance_median_ns"] / totals["native-mitm"]["sum_instance_median_ns"]
    return {"profile": asdict(profile), "instances": len(records), "python_comparison": compare_python,
            "native_ball_over_mitm_time": ratio, "totals": totals, "records": records}


def main():
    destination = ROOT / "artifacts/native-survey-v1.json"
    summary_path = destination.parent / "native-survey-summary-v1.json"
    destination.parent.mkdir(exist_ok=True)
    for report_path in (destination, summary_path):
        report_path.write_text('{"status":"running-or-incomplete"}\n', encoding="utf-8")
    executable = build_native(release=True)
    studies = []
    for index, setup in enumerate(SETUPS):
        study_result = study(executable, Profile(*setup), index < 2)
        studies.append(study_result)
        print(setup, "proofs:", study_result["totals"]["native-ball"]["proofs"],
              "ball/MITM time:", round(study_result["native_ball_over_mitm_time"], 3), flush=True)
    profile = Profile(257, 3, 16, 12)
    seed = hashlib.sha256(b"magnet-sis-native-v1/cap-probe").digest()
    matrix = expand_matrix(profile, seed)
    caps = run_requests(executable, [encode_request(profile, matrix, a, nodes=1_000_000) for a in ALGORITHMS])
    for result in caps:
        audit(profile, matrix, result)
    if [x["stop"] for x in caps] != ["node-limit", "half-box-limit"]:
        raise RuntimeError("cap probe unexpectedly completed")
    paths = [ROOT / "Cargo.toml", ROOT / "Cargo.lock"]
    for folder, pattern in (("reference", "*.py"), ("crates", "*.rs"), ("scripts", "*.py"), ("spec", "*.md")):
        paths.extend((ROOT / folder).rglob(pattern))
    result = {"status": "passed", "experiment": "native-survey-v1", "batches": BATCHES,
              "instances_per_batch": INSTANCES, "repeats": REPEATS, "setups": SETUPS,
              "python": platform.python_version(), "platform": platform.platform(),
              "processor": platform.processor(),
              "rustc": subprocess.check_output(["rustc", "-vV"], text=True).strip(),
              "base_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
              "executable_sha256": hashlib.sha256(executable.read_bytes()).hexdigest(),
              "source_sha256": {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in sorted(paths)},
              "measurement": {"native": "release solver-only, one request per fresh process, one thread",
                              "python": "solver-only, already expanded matrix, untraced, one process",
                              "excludes": "matrix expansion, IPC, scoring and proof audit",
                              "memory": "charged Vec capacities; excludes stack, allocator and process overhead",
                              "order": "native algorithm order alternates; Python follows corresponding native run"},
              "studies": studies,
              "cap_probe": {"profile": asdict(profile), "seed": seed.hex(), "nodes": 1_000_000,
                            "results": dict(zip(ALGORITHMS, map(compact, caps)))}}
    destination.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    summary = result | {"studies": [{k: v for k, v in s.items() if k != "records"} for s in studies]}
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print("Saved native survey and compact summary under artifacts/", flush=True)


if __name__ == "__main__":
    main()
