"""Practical native LLL versus exact certificates/probes and complete native SIS."""

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
from reference.sis import Profile, expand_matrix, verify
from scripts.flint_driver import run_flint
from scripts.lattice_survey import SETUPS, BATCHES
from scripts.native_driver import build_native, encode_request, run_requests
from scripts.native_survey import proof_digest
from solvers.lattice import probe_basis, reduce_kernel
from solvers.lattice_audit import audit_certificate

REPEATS = 3


def inputs():
    cases = []
    for setup in SETUPS:
        p, count = Profile(*setup[:4]), setup[4]
        for batch in range(BATCHES):
            for index in range(count):
                historical = count != 500 and index < 3
                domain = "magnet-sis-native-v1" if historical else "magnet-sis-lattice-v1"
                label = f"{domain}/{p.q}/{p.n}/{p.m}/{p.b2}/{batch}/{index}"
                cases.append((p, hashlib.sha256(label.encode()).digest(), "lattice-v1", historical))
    for fields in [(257, 3, 14, 12), (65521, 4, 16, 8), (257, 4, 16, 8), (32771, 4, 12, 8)]:
        p = Profile(*fields)
        for index in range(25):
            label = f"magnet-flint-v1/{p.q}/{p.n}/{p.m}/{p.b2}/{index}"
            cases.append((p, hashlib.sha256(label.encode()).digest(), "extension", False))
    fixture = json.loads((ROOT / "tests/vectors/lattice-miss-v1.json").read_text())
    cases.append((Profile(**fixture["profile"]), bytes.fromhex(fixture["seed"]), "frozen-miss", True))
    return cases


def aggregate(records):
    complete = [r for r in records if r["oracle"]["stop"] == "domain-exhausted"]
    return {"instances": len(records), "oracle_complete": len(complete),
            "oracle_capped": len(records) - len(complete),
            "oracle_stops": dict(Counter(r["oracle"]["stop"] for r in records)),
            "with_solution": sum(r["oracle"]["proof_count"] > 0 for r in complete),
            "without_solution": sum(r["oracle"]["proof_count"] == 0 for r in complete),
            "probe_success": sum(bool(r["runs"][0]["proof_count"]) for r in complete),
            "miss_with_solution": sum(r["oracle"]["proof_count"] > 0 and not r["runs"][0]["proof_count"] for r in complete),
            "construction_median_ns": statistics.median(x["construction_ns"] for r in records for x in r["runs"]),
            "reduction_median_ns": statistics.median(x["reduction_ns"] for r in records for x in r["runs"]),
            "probe_median_ns": statistics.median(x["probe_ns"] for r in records for x in r["runs"]),
            "reduced_basis_changed_across_repeats": sum(len({x["basis_sha256"] for x in r["runs"]}) != 1 for r in records)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--python", type=Path, required=True, help="isolated pinned FLINT interpreter")
    args = parser.parse_args()
    paths = [ROOT / "artifacts/flint-survey-v1.json", ROOT / "artifacts/flint-summary-v1.json"]
    paths[0].parent.mkdir(exist_ok=True)
    for path in paths:
        path.write_text('{"status":"running-or-incomplete"}\n', encoding="utf-8", newline="\n")
    native = build_native(release=True)
    cases, records, backend, process_ns = inputs(), [], None, 0
    for start in range(0, len(cases), 100):
        batch = cases[start:start + 100]
        matrices = [(p, expand_matrix(p, seed)) for p, seed, _, _ in batch]
        reductions = []
        for _ in range(REPEATS):
            result = run_flint(args.python, matrices)
            if backend is not None and backend != result["backend"]:
                raise RuntimeError("FLINT backend changed during experiment")
            backend = result["backend"]
            process_ns += result["process_elapsed_ns"]
            reductions.append(result["records"])
        oracles = run_requests(native, [encode_request(p, a, "mitm") for p, a in matrices])
        for index, ((p, seed, group, compare), (__, matrix), oracle) in enumerate(zip(batch, matrices, oracles, strict=True)):
            exact, runs = set(oracle["proofs"]), []
            if len(exact) != len(oracle["proofs"]) or not all(verify(p, matrix, x) for x in exact):
                raise RuntimeError("native FLINT oracle invalid or duplicated")
            for repeat in range(REPEATS):
                entry = reductions[repeat][index]
                start_probe = time.perf_counter_ns()
                probe = probe_basis(p, matrix, entry["reduction"])
                elapsed_probe = time.perf_counter_ns() - start_probe
                if oracle["stop"] == "domain-exhausted" and not set(probe["proofs"]) <= exact:
                    raise RuntimeError("FLINT probe outside complete oracle")
                certificate = asdict(entry["reduction"])
                certificate.pop("work")  # Native internal operation counts are unavailable.
                runs.append({"certificate": certificate, "audit": entry["certificate"],
                             "construction_ns": entry["construction_ns"], "reduction_ns": entry["reduction_ns"],
                             "probe_ns": elapsed_probe, "probe": probe, "proof_count": len(probe["proofs"]),
                             "basis_sha256": hashlib.sha256(json.dumps(certificate["basis"], separators=(",", ":")).encode()).hexdigest()})
            record = {"profile": asdict(p), "seed": seed.hex(), "group": group, "runs": runs,
                      "oracle": {k: v for k, v in oracle.items() if k != "proofs"} | {
                          "proof_count": len(exact), "proof_set_sha256": proof_digest(exact)}}
            if compare:
                begin = time.perf_counter_ns()
                reference = reduce_kernel(p, matrix)
                reference_ns = time.perf_counter_ns() - begin
                audit = audit_certificate(p, matrix, reference)
                probe = probe_basis(p, matrix, reference)
                record["exact_reference"] = {"reduction_ns_including_construction": reference_ns,
                                             "audit": audit, "probe": probe, "reason": reference.reason}
            records.append(record)
        print("FLINT complete:", len(records), "/", len(cases), flush=True)
    sources = [ROOT / "Cargo.toml", ROOT / "Cargo.lock", ROOT / "benchmarks/flint-win.lock"]
    for folder, pattern in [("reference", "*.py"), ("solvers", "*.py"), ("scripts", "*.py"), ("tests", "*.py"),
                            ("tests/vectors", "*.json"), ("crates", "*.rs"), ("spec", "*.md")]:
        sources.extend((ROOT / folder).rglob(pattern))
    report = {"status": "passed", "experiment": "flint-survey-v1", "repeats": REPEATS,
              "python": platform.python_version(), "platform": platform.platform(), "backend": backend,
              "native_executable_sha256": hashlib.sha256(native.read_bytes()).hexdigest(),
              "worker_process_sum_ns": process_ns, "aggregate": aggregate(records),
              "source_sha256": {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(sources)},
              "records": records}
    paths[0].write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    groups = {}
    for record in records:
        key = ",".join(str(record["profile"][field]) for field in ("q", "n", "m", "b2"))
        groups.setdefault(key, []).append(record)
    summary = {k: v for k, v in report.items() if k != "records"}
    summary["profiles"] = {key: aggregate(value) for key, value in groups.items()}
    summary["reference_comparisons"] = [{"profile": r["profile"], "seed": r["seed"],
                                          "group": r["group"], "exact_reference": {
                                              "reduction_ns_including_construction": r["exact_reference"]["reduction_ns_including_construction"],
                                              "reason": r["exact_reference"]["reason"], "audit": r["exact_reference"]["audit"],
                                              "proof_count": len(r["exact_reference"]["probe"]["proofs"]),
                                              "proof_set_sha256": proof_digest(r["exact_reference"]["probe"]["proofs"])},
                                          "flint_proofs": r["runs"][0]["proof_count"],
                                          "flint_construction_reduction_median_ns": statistics.median(
                                              x["construction_ns"] + x["reduction_ns"] for x in r["runs"])}
                                         for r in records if "exact_reference" in r]
    paths[1].write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(report["aggregate"], flush=True)


if __name__ == "__main__":
    main()
