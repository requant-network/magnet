"""Equal-size single/joint header families, target grid and descriptive work models."""

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
from reference.work_models import WORK_COMPONENTS, ideal_target_trials, joint_family, summarize_work
from scripts.grinding_survey import SETUPS, BATCHES, HEADERS
from scripts.lab_driver import build_lab, exchange, matrix_bytes, request
from scripts.native_driver import build_native, encode_request, run_requests
from scripts.native_survey import proof_digest
from scripts.sphere_survey import invalidate, source_hashes

DIVISORS = (8, 16, 32, 64)


def aggregate(records):
    return {"families": len(records), "header_occurrences": sum(len(r["headers"]) for r in records),
            "unique_headers": len({h["header_hex"] for r in records for h in r["headers"]}),
            "with_solution_occurrences": sum(h["proof_count"] > 0 for r in records for h in r["headers"]),
            "targets": {str(d): {"target": str(2**256//d), "ideal_independent_eligible_score_trials":
                                  str(ideal_target_trials(2**256//d)),
                                  "with_score_hit_occurrences": sum(h["score_hits"][str(d)] > 0
                                                                   for r in records for h in r["headers"]),
                                  "policies": {policy: summarize_work([r["runs"][str(d)][policy] for r in records]) | {
                                      "stops": dict(Counter(r["runs"][str(d)][policy]["reason"] for r in records))}
                                               for policy in POLICIES}} for d in DIVISORS}}


def main():
    paths = [ROOT / "artifacts/joint-v1.json", ROOT / "artifacts/joint-summary-v1.json"]
    invalidate(paths)
    lab, native = build_lab(), build_native(release=True)
    records, checks, audit_hashes = [], 0, 0
    for fields in SETUPS:
        profile = Profile(*fields)
        for batch in range(BATCHES):
            # Same bases as grinding-v1; joint axis is the only new family type.
            label = f"magnet-grinding-v1/{profile.q}/{profile.n}/{profile.m}/{profile.b2}/{batch}"
            blobs = [hashlib.sha256((label+suffix).encode()).digest() for suffix in ("/network", "/parent", "/payload")]
            base = LabHeader(*blobs, 1, 20261008, 0, profile)
            context = ExpectedContext(base.network, base.parent, base.height, profile)
            for field in (*FIELDS, "joint"):
                headers = joint_family(base, nonces=4, timestamps=4, payloads=4) if field == "joint" else header_family(base, field, HEADERS)
                matrices = [h.matrix() for h in headers]
                if exchange(lab, [request(2, h.encode()) for h in headers]) != [
                        h.seed()+matrix_bytes(a) for h, a in zip(headers, matrices, strict=True)]:
                    raise RuntimeError("joint native generation mismatch")
                oracles = run_requests(native, [encode_request(profile, a, "mitm") for a in matrices])
                if any(r["stop"] != "domain-exhausted" for r in oracles):
                    raise RuntimeError("joint availability oracle incomplete")
                availability = []
                for h, matrix, oracle in zip(headers, matrices, oracles, strict=True):
                    proofs = oracle["proofs"]
                    if len(set(proofs)) != len(proofs) or not all(verify(profile, matrix, x) for x in proofs):
                        raise RuntimeError("joint oracle invalid/duplicated")
                    digests = [int.from_bytes(score_digest(h, x), "big") for x in proofs]
                    audit_hashes += len(digests)
                    availability.append({"header_hex": h.encode().hex(), "seed": h.seed().hex(), "proof_count": len(proofs),
                                         "score_hits": {str(d): sum(x < 2**256//d for x in digests) for d in DIVISORS},
                                         "proof_set_sha256": proof_digest(proofs)})
                runs, native_checks = {}, []
                for divisor in DIVISORS:
                    target, runs[str(divisor)] = 2**256//divisor, {}
                    for policy in POLICIES:
                        begin = time.perf_counter_ns()
                        result = run_policy(headers, policy, target)
                        result["elapsed_ns"] = time.perf_counter_ns()-begin
                        if divisor != DIVISORS[0]:
                            previous = runs[str(DIVISORS[DIVISORS.index(divisor)-1])][policy]
                            if any(result["work"][name] < previous["work"][name] for name in WORK_COMPONENTS):
                                raise RuntimeError("target grid paid work not monotone")
                        if result["hit"] is not None:
                            packet = bytes.fromhex(result["hit"]["proof_hex"])
                            if not verify_scored_proof(packet, context, target):
                                raise RuntimeError("joint policy invalid scored proof")
                            native_checks.append(request(3, context.encode()+packet))
                        runs[str(divisor)][policy] = result
                if exchange(lab, native_checks) != [b"\x01"]*len(native_checks):
                    raise RuntimeError("joint native hit verification mismatch")
                checks += len(native_checks)
                records.append({"profile": asdict(profile), "batch": batch, "label": label,
                                "field": field, "headers": availability, "runs": runs})
        print("Joint profile complete:", fields, flush=True)
    report = {"status": "passed", "experiment": "joint-v1", "divisors": DIVISORS, "setups": SETUPS,
              "batches": BATCHES, "headers_per_family": HEADERS, "joint_axes": [4, 4, 4],
              "python": platform.python_version(), "platform": platform.platform(), "aggregate": aggregate(records),
              "native_hit_checks": checks, "oracle_audit_score_hashes": audit_hashes,
              "executable_sha256": {"sis-lab-debug": hashlib.sha256(lab.read_bytes()).hexdigest(),
                                    "sis-search-release": hashlib.sha256(native.read_bytes()).hexdigest()},
              "source_sha256": source_hashes(), "records": records}
    paths[0].write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8", newline="\n")
    summary = {k: v for k, v in report.items() if k != "records"}
    summary["fields"] = {field: aggregate([r for r in records if r["field"] == field]) for field in (*FIELDS, "joint")}
    paths[1].write_text(json.dumps(summary, indent=2)+"\n", encoding="utf-8", newline="\n")
    print("Joint hits by target divisor:", {d: {p: v["hit_occurrences"] for p, v in t["policies"].items()}
                                            for d, t in report["aggregate"]["targets"].items()}, flush=True)


if __name__ == "__main__":
    main()
