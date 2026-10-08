"""Nonce/time/payload families with paid acquisition and common score thresholds."""

from collections import Counter
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import platform
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from reference.grinding import FIELDS, POLICIES, header_family, run_policy, score_digest, verify_scored_proof
from reference.header import ExpectedContext, LabHeader
from reference.sis import Profile, verify
from scripts.lab_driver import build_lab, exchange, matrix_bytes, request
from scripts.native_driver import build_native, encode_request, run_requests
from scripts.native_survey import proof_digest

SETUPS = [(7, 1, 3, 8), (17, 2, 4, 8), (17, 2, 4, 3), (257, 2, 4, 8)]
BATCHES, HEADERS = 2, 64
TARGET = 2**256 // 16


def summarize(records):
    return {"families": len(records), "header_occurrences": sum(len(r["headers"]) for r in records),
            "unique_headers": len({h["header_hex"] for r in records for h in r["headers"]}),
            "with_solution": sum(h["proof_count"] > 0 for r in records for h in r["headers"]),
            "with_score_hit": sum(h["score_hits"] > 0 for r in records for h in r["headers"]),
            "policies": {policy: {"runs": len(records),
                                  "score_hits": sum(r["policies"][policy]["hit"] is not None for r in records),
                                  "stops": dict(Counter(r["policies"][policy]["reason"] for r in records)),
                                  "work": {name: sum(r["policies"][policy]["work"][name] for r in records)
                                           for name in ("headers_processed", "matrix_entries_expanded", "vector_checks",
                                                        "score_hashes", "score_input_bytes")}}
                         for policy in POLICIES}}


def main():
    outputs = [ROOT / "artifacts/grinding-v1.json", ROOT / "artifacts/grinding-summary-v1.json"]
    outputs[0].parent.mkdir(exist_ok=True)
    for path in outputs:
        path.write_text('{"status":"running-or-incomplete"}\n', encoding="utf-8", newline="\n")
    lab, native = build_lab(), build_native(release=True)
    records, checks, audit_hashes = [], 0, 0
    for fields in SETUPS:
        profile = Profile(*fields)
        for batch in range(BATCHES):
            label = f"magnet-grinding-v1/{profile.q}/{profile.n}/{profile.m}/{profile.b2}/{batch}"
            blobs = [hashlib.sha256((label + suffix).encode()).digest() for suffix in ("/network", "/parent", "/payload")]
            base = LabHeader(*blobs, 1, 20261008, 0, profile)
            context = ExpectedContext(base.network, base.parent, base.height, profile)
            for field in FIELDS:
                headers = header_family(base, field, HEADERS)
                matrices = [h.matrix() for h in headers]
                if exchange(lab, [request(2, h.encode()) for h in headers]) != [
                        h.seed() + matrix_bytes(a) for h, a in zip(headers, matrices, strict=True)]:
                    raise RuntimeError("grinding generation mismatch")
                oracles = run_requests(native, [encode_request(profile, a, "mitm") for a in matrices])
                if any(r["stop"] != "domain-exhausted" for r in oracles):
                    raise RuntimeError("grinding availability oracle incomplete")
                availability = []
                for h, matrix, oracle in zip(headers, matrices, oracles, strict=True):
                    if len(set(oracle["proofs"])) != len(oracle["proofs"]) or not all(
                            verify(profile, matrix, x) for x in oracle["proofs"]):
                        raise RuntimeError("grinding oracle invalid or duplicated")
                    hits = sum(int.from_bytes(score_digest(h, x), "big") < TARGET for x in oracle["proofs"])
                    audit_hashes += len(oracle["proofs"])
                    availability.append({"header_hex": h.encode().hex(), "seed": h.seed().hex(),
                                         "proof_count": len(oracle["proofs"]), "score_hits": hits,
                                         "proof_set_sha256": proof_digest(oracle["proofs"])})
                policies, verification_requests = {}, []
                for policy in POLICIES:
                    start = time.perf_counter_ns()
                    result = run_policy(headers, policy, TARGET)
                    result["elapsed_ns"] = time.perf_counter_ns() - start
                    if result["hit"] is not None:
                        packet = bytes.fromhex(result["hit"]["proof_hex"])
                        if not verify_scored_proof(packet, context, TARGET):
                            raise RuntimeError("grinding policy emitted an invalid scored proof")
                        verification_requests.append(request(3, context.encode() + packet))
                    policies[policy] = result
                if exchange(lab, verification_requests) != [b"\x01"] * len(verification_requests):
                    raise RuntimeError("native grinding hit verification mismatch")
                checks += len(verification_requests)
                records.append({"profile": asdict(profile), "batch": batch, "label": label, "field": field,
                                "headers": availability, "policies": policies})
        print("Grinding profile completed", fields, flush=True)
    sources = [ROOT / "Cargo.toml", ROOT / "Cargo.lock", ROOT / "benchmarks/flint-win.lock"]
    for folder, pattern in [("reference", "*.py"), ("solvers", "*.py"), ("scripts", "*.py"), ("tests", "*.py"),
                            ("tests/vectors", "*.json"), ("crates", "*.rs"), ("spec", "*.md")]:
        sources.extend((ROOT / folder).rglob(pattern))
    report = {"status": "passed", "experiment": "grinding-v1", "target": str(TARGET),
              "setups": SETUPS, "batches": BATCHES, "headers_per_family": HEADERS,
              "python": platform.python_version(), "platform": platform.platform(),
              "aggregate": summarize(records), "native_hit_checks": checks, "oracle_audit_score_hashes": audit_hashes,
              "executable_sha256": {"sis-lab-debug": hashlib.sha256(lab.read_bytes()).hexdigest(),
                                    "sis-search-release": hashlib.sha256(native.read_bytes()).hexdigest()},
              "source_sha256": {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(sources)},
              "records": records}
    outputs[0].write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    summary = {k: v for k, v in report.items() if k != "records"}
    summary["families"] = [{"profile": r["profile"], "batch": r["batch"], "label": r["label"], "field": r["field"],
                             "with_solution": sum(h["proof_count"] > 0 for h in r["headers"]),
                             "with_score_hit": sum(h["score_hits"] > 0 for h in r["headers"]),
                             "policies": {policy: {k: v for k, v in result.items() if k not in ("score_samples", "hit")} | {
                                 "hit": {k: v for k, v in result["hit"].items() if k != "proof_hex"}
                                 if result["hit"] else None} for policy, result in r["policies"].items()}}
                            for r in records]
    outputs[1].write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(report["aggregate"], flush=True)


if __name__ == "__main__":
    main()
