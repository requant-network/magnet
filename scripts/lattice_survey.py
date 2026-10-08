"""Exact LLL candidate availability against an independent complete SIS oracle."""
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
from scripts.native_driver import build_native, encode_request, run_requests
from scripts.native_survey import proof_digest
from solvers.lattice import probe_basis, reduce_kernel
from solvers.lattice_audit import audit_certificate

# 1000 cheap matrices plus 100 larger matrices. First six of each larger
# profile reproduce the native-v1 inputs (two batches of three).
SETUPS = [(17, 2, 4, 8, 500), (17, 2, 6, 16, 8), (17, 2, 8, 8, 8),
          (257, 3, 10, 8, 8), (257, 3, 12, 12, 8),
          (257, 3, 14, 12, 9), (17, 2, 12, 12, 9)]
BATCHES = 2


def run_instance(executable, profile, seed):
    matrix = expand_matrix(profile, seed)
    start = time.perf_counter_ns()
    reduction = reduce_kernel(profile, matrix)
    reduction_ns = time.perf_counter_ns() - start
    start = time.perf_counter_ns()
    probe = probe_basis(profile, matrix, reduction)
    probe_ns = time.perf_counter_ns() - start
    certificate = audit_certificate(profile, matrix, reduction)
    oracle = run_requests(executable, [encode_request(profile, matrix, "mitm")])[0]
    exact = set(oracle["proofs"])
    if len(exact) != len(oracle["proofs"]) or not all(verify(profile, matrix, x) for x in exact):
        raise RuntimeError("invalid or duplicate independent oracle output")
    if not all(verify(profile, matrix, x) for x in probe["proofs"]):
        raise RuntimeError("invalid lattice candidate")
    if oracle["stop"] == "domain-exhausted" and not set(probe["proofs"]) <= exact:
        raise RuntimeError("lattice proof missing from exhaustive oracle")
    return {"seed": seed.hex(), "reduction": asdict(reduction), "certificate": certificate,
            "reduction_elapsed_ns": reduction_ns, "probe_elapsed_ns": probe_ns, "probe": probe,
            "oracle": {k: v for k, v in oracle.items() if k != "proofs"} | {
                "proof_count": len(exact), "proof_set_sha256": proof_digest(exact),
                "min_accepted_norm2": min((sum(x*x for x in v) for v in exact), default=None)}}


def aggregate(records):
    counts = Counter()
    work = Counter()
    for record in records:
        reduction, probe, oracle = record["reduction"], record["probe"], record["oracle"]
        for name, value in reduction["work"].items():
            if not name.startswith("max_"):
                work[name] += value
        counts["lll_complete"] += reduction["reason"] == "lll-reduced"
        counts["lll_capped"] += reduction["reason"] != "lll-reduced"
        if oracle["stop"] != "domain-exhausted":
            counts["oracle_capped"] += 1
            continue
        counts["oracle_complete"] += 1
        counts["with_solution"] += oracle["proof_count"] > 0
        counts["without_solution"] += oracle["proof_count"] == 0
        counts["basis_success"] += bool(probe["basis_proofs"])
        counts["pair_only_success"] += bool(probe["proofs"]) and not probe["basis_proofs"]
        counts["probe_success"] += bool(probe["proofs"])
        counts["miss_with_solution"] += oracle["proof_count"] > 0 and not probe["proofs"]
        counts["oracle_vectors"] += oracle["proof_count"]
        counts["probe_vectors"] += len(probe["proofs"])
    # Keep zero categories visible, not silently absent from a compact report.
    names = ("lll_complete", "lll_capped", "oracle_complete", "oracle_capped", "with_solution",
             "without_solution", "basis_success", "pair_only_success", "probe_success",
             "miss_with_solution", "oracle_vectors", "probe_vectors")
    return {"counts": {name: counts[name] for name in names}, "work_totals": dict(work),
            "reduction_stops": dict(Counter(r["reduction"]["reason"] for r in records)),
            "probe_stops": dict(Counter(r["probe"]["reason"] for r in records)),
            "oracle_stops": dict(Counter(r["oracle"]["stop"] for r in records)),
            "max_integer_bits": max(r["reduction"]["work"]["max_integer_bits"] for r in records),
            "max_fraction_bits": max(r["reduction"]["work"]["max_fraction_bits"] for r in records),
            "reduction_median_ns": statistics.median(r["reduction_elapsed_ns"] for r in records),
            "probe_median_ns": statistics.median(r["probe_elapsed_ns"] for r in records),
            "reduction_sum_ns": sum(r["reduction_elapsed_ns"] for r in records),
            "probe_sum_ns": sum(r["probe_elapsed_ns"] for r in records)}


def main():
    destination = ROOT / "artifacts/lattice-survey-v1.json"
    summary_path = destination.parent / "lattice-survey-summary-v1.json"
    destination.parent.mkdir(exist_ok=True)
    for path in (destination, summary_path):
        path.write_text('{"status":"running-or-incomplete"}\n', encoding="utf-8")
    executable = build_native(release=True)
    studies = []
    for setup in SETUPS:
        profile, per_batch = Profile(*setup[:4]), setup[4]
        records = []
        for batch in range(BATCHES):
            for index in range(per_batch):
                historical = per_batch != 500 and index < 3
                domain = "magnet-sis-native-v1" if historical else "magnet-sis-lattice-v1"
                label = f"{domain}/{profile.q}/{profile.n}/{profile.m}/{profile.b2}/{batch}/{index}"
                seed = hashlib.sha256(label.encode("ascii")).digest()
                records.append(run_instance(executable, profile, seed) | {
                    "batch": batch, "index": index, "shared_native_v1_input": historical})
            print(setup, "batch", batch, "completed", flush=True)
        study = {"profile": asdict(profile), "instances": len(records), "per_batch": per_batch,
                 "aggregate": aggregate(records), "records": records}
        studies.append(study)
        print("Counts:", study["aggregate"]["counts"], flush=True)
    paths = [ROOT / "Cargo.toml", ROOT / "Cargo.lock"]
    for folder, pattern in (("reference", "*.py"), ("solvers", "*.py"), ("crates", "*.rs"),
                            ("scripts", "*.py"), ("tests", "*.py"), ("tests/vectors", "*.json"), ("spec", "*.md")):
        paths.extend((ROOT / folder).rglob(pattern))
    result = {"status": "passed", "experiment": "lattice-survey-v1", "setups": SETUPS,
              "batches": BATCHES, "repetitions": 1, "python": platform.python_version(),
              "platform": platform.platform(), "processor": platform.processor(),
              "native_executable_sha256": hashlib.sha256(executable.read_bytes()).hexdigest(),
              "source_sha256": {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in sorted(paths)},
              "measurement": {"reduction": "basis construction and exact LLL; pre-expanded A",
                              "probe": "rows/pairs, sign/norm checks, SIS verification and deduplication",
                              "excluded": "SHAKE expansion, certificate audit and oracle comparison",
                              "oracle": "native release MITM solver timer; decoding/IPC/audits excluded",
                              "interpretation": "single-pass local reference timings; not a speed ranking",
                              "memory": "no allocation/RSS measurement; bit maxima are not byte ceilings"},
              "studies": studies}
    destination.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    summary = result | {"studies": [{k: v for k, v in study.items() if k != "records"} for study in studies]}
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print("Saved complete and compact lattice reports under artifacts/", flush=True)


if __name__ == "__main__":
    main()
