"""Explicit isolated-environment practical lattice policies and paid pool amortization."""

from collections import Counter
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import platform
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from reference.grinding import header_family, score_digest, verify_scored_proof
from reference.header import ExpectedContext, LabHeader
from reference.lattice_cache import CandidateCache
from reference.lattice_policies import COUNTERS, LatticeBudget, POLICIES, run_lattice_policy
from reference.sis import Profile, verify
from reference.work_models import joint_family
from scripts.lab_driver import build_lab, exchange, matrix_bytes, request
from scripts.native_driver import build_native, encode_request, run_requests
from scripts.native_survey import proof_digest
from scripts.sphere_survey import invalidate, source_hashes
from solvers.practical import PracticalReducer

SETUPS = [(2, 1, 3, 1), (17, 2, 8, 8), (257, 3, 14, 12), (257, 4, 16, 8)]
DIVISORS, BATCHES, HEADERS = (8, 32), 2, 16
BUDGET = LatticeBudget()


def summarize(runs):
    hits = sum(r["result"]["hit"] is not None for r in runs)
    work = {name: sum(r["result"]["work"][name] for r in runs) for name in COUNTERS}
    return {"runs": len(runs), "hit_occurrences": hits,
            "stops": dict(Counter(r["result"]["reason"] for r in runs)), "work": work,
            "elapsed_sum_ns": sum(r["result"]["elapsed_ns"] for r in runs),
            "timer_sums_ns": {name: sum(r["result"]["timers"][name] for r in runs)
                              for name in ("construction_ns", "native_reduction_ns", "backend_audit_ns",
                                           "reducer_call_ns", "sphere_ns_including_visitor")},
            "work_per_hit_occurrence": {name: {"numerator": value, "denominator": hits}
                                        if hits else None for name, value in work.items()}}


def summarize_records(records):
    runs = [r for record in records for r in record["runs"]]
    groups = sorted({(r["policy"], r["phase"]) for r in runs})
    return {"families": len(records), "header_occurrences": sum(len(r["headers"]) for r in records),
            "unique_headers": len({h["header_hex"] for r in records for h in r["headers"]}),
            "unique_instances": len({h["instance_sha256"] for r in records for h in r["headers"]}),
            "with_solution_occurrences": sum(h["proof_count"] > 0 for r in records for h in r["headers"]),
            "total": summarize(runs),
            "policies": {p+"/"+phase: summarize([r for r in runs if r["policy"] == p and r["phase"] == phase])
                         for p, phase in groups},
            "targets": {str(d): {p+"/"+phase: summarize([r for r in runs if r["divisor"] == d
                                                        and r["policy"] == p and r["phase"] == phase])
                                  for p, phase in groups} for d in DIVISORS}}


def main():
    paths = [ROOT / "artifacts/integrated-v1.json", ROOT / "artifacts/integrated-summary-v1.json"]
    invalidate(paths)
    # This whole script must run in the isolated pinned environment. No fallback/install.
    lab, native, reducer = build_lab(), build_native(release=True), PracticalReducer()
    records, diagnostics, native_checks, scored_checks = [], [], 0, 0
    for fields in SETUPS:
        p = Profile(*fields)
        for batch in range(BATCHES):
            label = f"magnet-integrated-v1/{p.q}/{p.n}/{p.m}/{p.b2}/{batch}"
            blobs = [hashlib.sha256((label+s).encode()).digest() for s in ("/network", "/parent", "/payload")]
            base = LabHeader(*blobs, 1, 20261008, 0, p)
            context = ExpectedContext(base.network, base.parent, base.height, p)
            for field in ("nonce", "joint"):
                headers = header_family(base, "nonce", HEADERS) if field == "nonce" else joint_family(
                    base, nonces=2, timestamps=2, payloads=4)
                matrices = [h.matrix() for h in headers]
                if exchange(lab, [request(2, h.encode()) for h in headers]) != [
                        h.seed()+matrix_bytes(a) for h, a in zip(headers, matrices, strict=True)]:
                    raise RuntimeError("integrated generation mismatch")
                oracles = run_requests(native, [encode_request(p, a, "mitm") for a in matrices])
                availability, exact = [], []
                for h, a, oracle in zip(headers, matrices, oracles, strict=True):
                    proofs = set(oracle["proofs"])
                    if (oracle["stop"] != "domain-exhausted" or len(proofs) != len(oracle["proofs"])
                            or not all(verify(p, a, v) for v in proofs)):
                        raise RuntimeError("integrated complete oracle invalid")
                    scores = [int.from_bytes(score_digest(h, v), "big") for v in proofs]
                    exact.append(proofs)
                    availability.append({"header_hex": h.encode().hex(), "seed": h.seed().hex(),
                                         "instance_sha256": hashlib.sha256(h.encode()[-16:]+matrix_bytes(a)).hexdigest(),
                                         "proof_count": len(proofs), "proof_set_sha256": proof_digest(proofs),
                                         "score_hits": {str(d): sum(x < 2**256//d for x in scores) for d in DIVISORS}})
                runs, checks = [], []

                def audit(result, target):
                    nonlocal scored_checks
                    for instance in result["instances"]:
                        if "sphere" not in instance:
                            continue
                        sphere = instance["sphere"]
                        found = set(sphere["proofs"])
                        if not found <= exact[instance["index"]] or (sphere["reason"] == "domain-exhausted"
                                                                   and found != exact[instance["index"]]):
                            raise RuntimeError("integrated lattice/oracle set mismatch")
                    for s in result["scores"]:
                        h = headers[s["header_index"]]
                        if tuple(s["vector"]) not in exact[s["header_index"]] or score_digest(h, s["vector"]).hex() != s["digest"]:
                            raise RuntimeError("integrated score audit mismatch")
                        scored_checks += 1
                    if result["hit"]:
                        packet = bytes.fromhex(result["hit"]["proof_hex"])
                        if not verify_scored_proof(packet, context, target):
                            raise RuntimeError("integrated invalid hit")
                        checks.append(request(3, context.encode()+packet))

                for divisor in DIVISORS:
                    target = 2**256//divisor
                    for policy in POLICIES:
                        cache = CandidateCache() if policy == "cache-all" else None
                        cold = run_lattice_policy(headers, policy, target, reducer, budget=BUDGET, cache=cache)
                        audit(cold, target)
                        runs.append({"divisor": divisor, "policy": policy, "phase": "cold", "result": cold})
                        if cache is not None:
                            for phase, replay_cache in (("warm-replay", cache), ("cold-reset-replay", CandidateCache())):
                                replay = run_lattice_policy(headers, policy, target, reducer, budget=BUDGET, cache=replay_cache)
                                audit(replay, target)
                                if cold["reason"] in ("score-hit", "family-exhausted"):
                                    if replay["scores"] != cold["scores"] or replay["reason"] != cold["reason"]:
                                        raise RuntimeError("cache replay changed score stream")
                                    if phase == "warm-replay" and replay["work"]["reduction_calls"] != 0:
                                        raise RuntimeError("fitting warm cache performed new reduction")
                                runs.append({"divisor": divisor, "policy": policy, "phase": phase, "result": replay})
                if batch == 0 and field == "nonce":
                    cache = CandidateCache(capacity=1)
                    churn_runs = []
                    for phase in ("cold", "replay"):
                        result = run_lattice_policy(headers, "cache-all", 0, reducer, budget=BUDGET, cache=cache)
                        audit(result, 0)
                        churn_runs.append({"policy": "cache-all", "phase": phase, "result": result})
                    diagnostics.append({"profile": asdict(p), "label": label, "capacity": 1, "target": "0", "runs": churn_runs})
                if exchange(lab, checks) != [b"\x01"]*len(checks):
                    raise RuntimeError("integrated native hit verification mismatch")
                native_checks += len(checks)
                records.append({"profile": asdict(p), "batch": batch, "label": label, "field": field,
                                "headers": availability, "runs": runs})
        print("Integrated profile completed:", fields, flush=True)
    report = {"status": "passed", "experiment": "integrated-v1", "python": platform.python_version(),
              "platform": platform.platform(), "backend": reducer.backend, "backend_setup_ns": reducer.setup_ns,
              "setups": SETUPS, "batches": BATCHES, "headers_per_family": HEADERS, "divisors": DIVISORS,
              "joint_axes": [2, 2, 4], "budget": asdict(BUDGET), "cache_capacity": 32,
              "aggregate": summarize_records(records), "native_hit_checks": native_checks, "score_audit_occurrences": scored_checks,
              "executable_sha256": {"sis-lab-debug": hashlib.sha256(lab.read_bytes()).hexdigest(),
                                    "sis-search-release": hashlib.sha256(native.read_bytes()).hexdigest()},
              "source_sha256": source_hashes(), "records": records, "churn_diagnostics": diagnostics}
    paths[0].write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8", newline="\n")
    summary = {k: v for k, v in report.items() if k not in ("records", "churn_diagnostics")}
    summary["profiles"] = {",".join(map(str, fields)): summarize_records([r for r in records if r["profile"] == asdict(Profile(*fields))])
                           for fields in SETUPS}
    summary["churn_diagnostics"] = [{k: v for k, v in r.items() if k != "runs"} | {
        "phases": {run["phase"]: summarize([run]) for run in r["runs"]}} for r in diagnostics]
    paths[1].write_text(json.dumps(summary, indent=2)+"\n", encoding="utf-8", newline="\n")
    print("Integrated runs/hits:", summary["aggregate"]["total"]["runs"], summary["native_hit_checks"], flush=True)


if __name__ == "__main__":
    main()
