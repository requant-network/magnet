"""Certified exact sphere enumeration versus independently complete native MITM."""

import argparse
from collections import Counter
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import platform
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from reference.sis import expand_matrix, verify
from scripts.flint_driver import run_flint
from scripts.flint_survey import inputs
from scripts.native_driver import build_native, encode_request, run_requests
from scripts.native_survey import proof_digest
from solvers.lattice import probe_basis
from solvers.sphere import enumerate_kernel


def aggregate(records):
    comparable = [r for r in records if r["oracle"]["stop"] == r["sphere"]["reason"] == "domain-exhausted"]
    return {"instances": len(records), "both_complete": len(comparable),
            "sphere_stops": dict(Counter(r["sphere"]["reason"] for r in records)),
            "oracle_stops": dict(Counter(r["oracle"]["stop"] for r in records)),
            "complete_with_solution": sum(r["sphere"]["proof_count"] > 0 for r in comparable),
            "complete_empty": sum(r["sphere"]["proof_count"] == 0 for r in comparable),
            "proof_occurrences": sum(r["sphere"]["proof_count"] for r in records),
            "probe_missed_vectors": sum(r["sphere"]["proof_count"]-r["probe_count"] for r in comparable),
            "sphere_median_ns_including_audit": statistics.median(r["sphere_elapsed_ns"] for r in records),
            "construction_median_ns": statistics.median(r["construction_ns"] for r in records),
            "reduction_median_ns": statistics.median(r["reduction_ns"] for r in records),
            "work": {name: sum(r["sphere"]["work"][name] for r in records)
                     for name in ("nodes", "leaves", "reconstruction_terms", "sis_checks")}}


def source_hashes():
    sources = [ROOT / "Cargo.toml", ROOT / "Cargo.lock", ROOT / "benchmarks/flint-win.lock"]
    for folder, pattern in [("reference", "*.py"), ("solvers", "*.py"), ("scripts", "*.py"), ("tests", "*.py"),
                            ("tests/vectors", "*.json"), ("crates", "*.rs"), ("spec", "*.md")]:
        sources.extend((ROOT / folder).rglob(pattern))
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(sources)}


def invalidate(paths):
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{"status":"running-or-incomplete"}\n', encoding="utf-8", newline="\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--python", type=Path, required=True, help="isolated pinned FLINT interpreter")
    args = parser.parse_args()
    paths = [ROOT / "artifacts/sphere-v1.json", ROOT / "artifacts/sphere-summary-v1.json"]
    invalidate(paths)
    native = build_native(release=True)
    # Exactly the 1000 cheap historical inputs, 100 extension inputs and labelled frozen repeat.
    cases = [c for c in inputs() if c[0].m == 4 or c[2] != "lattice-v1"]
    records, backend, process_ns = [], None, 0
    for start in range(0, len(cases), 100):
        batch = cases[start:start+100]
        matrices = [(p, expand_matrix(p, seed)) for p, seed, _, _ in batch]
        reductions = run_flint(args.python, matrices)
        if backend is not None and backend != reductions["backend"]:
            raise RuntimeError("sphere backend changed during experiment")
        backend = reductions["backend"]
        process_ns += reductions["process_elapsed_ns"]
        oracles = run_requests(native, [encode_request(p, a, "mitm") for p, a in matrices])
        for case, (_, matrix), entry, oracle in zip(batch, matrices, reductions["records"], oracles, strict=True):
            p, seed, group, _ = case
            exact = set(oracle["proofs"])
            if len(exact) != len(oracle["proofs"]) or not all(verify(p, matrix, x) for x in exact):
                raise RuntimeError("sphere native oracle invalid/duplicated")
            begin = time.perf_counter_ns()
            sphere = enumerate_kernel(p, matrix, entry["reduction"])
            elapsed = time.perf_counter_ns()-begin
            found = set(sphere["proofs"])
            if len(found) != len(sphere["proofs"]):
                raise RuntimeError("sphere duplicated proofs")
            if oracle["stop"] == "domain-exhausted" and not found <= exact:
                raise RuntimeError("sphere proof absent from complete oracle")
            if sphere["reason"] == oracle["stop"] == "domain-exhausted" and found != exact:
                raise RuntimeError("complete sphere/oracle sets differ")
            probe = probe_basis(p, matrix, entry["reduction"])
            if sphere["reason"] == "domain-exhausted" and not set(probe["proofs"]) <= found:
                raise RuntimeError("complete sphere missing probe vector")
            certificate = asdict(entry["reduction"])
            certificate.pop("work")
            records.append({"profile": asdict(p), "seed": seed.hex(), "group": group,
                            "certificate": certificate, "sphere": {k: v for k, v in sphere.items() if k != "proofs"} | {
                                "proof_count": len(found), "proofs": sorted(found), "proof_set_sha256": proof_digest(found)},
                            "probe_count": len(probe["proofs"]), "sphere_elapsed_ns": elapsed,
                            "construction_ns": entry["construction_ns"], "reduction_ns": entry["reduction_ns"],
                            "oracle": {k: v for k, v in oracle.items() if k != "proofs"} | {
                                "proof_count": len(exact), "proof_set_sha256": proof_digest(exact)}})
        print("Sphere complete:", len(records), "/", len(cases), flush=True)
    report = {"status": "passed", "experiment": "sphere-v1", "python": platform.python_version(),
              "platform": platform.platform(), "backend": backend, "worker_process_sum_ns": process_ns,
              "bounds": {"node_limit": 1_000_000, "proof_limit": 100_000, "bit_limit": 4096},
              "aggregate": aggregate(records), "source_sha256": source_hashes(),
              "native_executable_sha256": hashlib.sha256(native.read_bytes()).hexdigest(), "records": records}
    paths[0].write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8", newline="\n")
    groups = {}
    for record in records:
        key = ",".join(str(record["profile"][f]) for f in ("q", "n", "m", "b2"))
        groups.setdefault(key, []).append(record)
    summary = {k: v for k, v in report.items() if k != "records"}
    summary["profiles"] = {k: aggregate(v) for k, v in groups.items()}
    summary["frozen_repeat"] = [{k: v for k, v in r.items() if k not in ("certificate", "sphere")} | {
        "sphere": {k: v for k, v in r["sphere"].items() if k != "proofs"}} for r in records if r["group"] == "frozen-miss"]
    paths[1].write_text(json.dumps(summary, indent=2)+"\n", encoding="utf-8", newline="\n")
    print(report["aggregate"], flush=True)


if __name__ == "__main__":
    main()
