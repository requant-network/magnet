"""OS-bounded cold processes over fresh nonce/parent schedules and lab admission."""

import argparse
from collections import Counter
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import platform
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from reference.grinding import header_family, score_digest
from reference.header import ExpectedContext, LabHeader
from reference.header_rules import LabRules, admit_proof
from reference.lattice_policies import COUNTERS, LatticeBudget, POLICIES
from reference.sis import Profile, verify
from scripts.lab_driver import build_lab, exchange, matrix_bytes, request
from scripts.native_driver import build_native, encode_request, run_requests
from scripts.native_survey import proof_digest
from scripts.sphere_survey import invalidate, source_hashes
from scripts.window_driver import run_window

SETUPS = [(2, 1, 3, 1), (17, 2, 8, 8), (257, 3, 14, 12), (257, 4, 16, 8)]
WINDOWS = [(200, 48), (200, 128), (400, 48), (400, 128), (1200, 48), (1200, 128)]
TARGET, STAGES, COUNT = 2**256//16, 3, 8


def stages_for(profile, schedule):
    if schedule not in ("fresh-nonce", "fresh-parent"):
        raise ValueError("unknown fresh schedule")
    label = f"magnet-windows-v1/{profile.q}/{profile.n}/{profile.m}/{profile.b2}"
    blobs = [hashlib.sha256((label+s).encode()).digest() for s in ("/network", "/parent", "/payload")]
    base = LabHeader(*blobs, 1, 20261008, 0, profile)
    stages = []
    for index in range(STAGES):
        if schedule == "fresh-nonce":
            start = replace(base, nonce=index*COUNT)
        else:
            parent = base.parent if index == 0 else hashlib.sha256(base.parent+index.to_bytes(8, "little")).digest()
            start = replace(base, parent=parent, height=index+1)
        stages.append(header_family(start, "nonce", COUNT))
    return label, tuple(stages)


def summarize(records):
    known = [r for r in records if r["window"]["logical_work_known"]]
    work = {name: sum(stage["work"][name] for r in known for stage in r["window"]["snapshot"]["stages"])
            for name in COUNTERS}
    hits = sum(stage["hit"] is not None for r in known for stage in r["window"]["snapshot"]["stages"])
    return {"attempts": len(records), "outcomes": dict(Counter(r["window"]["outcome"] for r in records)),
            "completed_windows": len(known), "unknown_logical_work_windows": len(records)-len(known),
            "completed_stage_hit_occurrences": hits, "completed_only_work": work,
            "all_attempt_elapsed_ns": sum(r["window"]["resource"]["elapsed_ns"] for r in records),
            "max_process_commit_bytes": max((r["window"]["resource"]["peak_process_commit_bytes"] for r in records), default=0),
            "max_deadline_overshoot_ns": max((r["window"]["resource"]["deadline_overshoot_ns"] for r in records), default=0),
            "completed_work_per_hit": {k: {"numerator": v, "denominator": hits} if hits else None for k, v in work.items()},
            "unconditional_work_per_hit": None if len(known) != len(records) else {
                k: {"numerator": v, "denominator": hits} if hits else None for k, v in work.items()}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--python", type=Path, required=True, help="explicit pinned FLINT interpreter")
    args = parser.parse_args()
    paths = [ROOT / "artifacts/windows-v1.json", ROOT / "artifacts/windows-summary-v1.json"]
    invalidate(paths)
    lab, native = build_lab(), build_native(release=True)
    records, cohorts, native_checks, backend = [], [], 0, None
    for fields in SETUPS:
        profile = Profile(*fields)
        for schedule in ("fresh-nonce", "fresh-parent"):
            label, stages = stages_for(profile, schedule)
            headers = [h for stage in stages for h in stage]
            matrices = [h.matrix() for h in headers]
            if exchange(lab, [request(2, h.encode()) for h in headers]) != [
                    h.seed()+matrix_bytes(a) for h, a in zip(headers, matrices, strict=True)]:
                raise RuntimeError("window independent generation mismatch")
            oracle = run_requests(native, [encode_request(profile, a, "mitm") for a in matrices])
            exact, availability = [], []
            for h, a, result in zip(headers, matrices, oracle, strict=True):
                proofs = set(result["proofs"])
                if (result["stop"] != "domain-exhausted" or len(proofs) != len(result["proofs"])
                        or not all(verify(profile, a, v) for v in proofs)):
                    raise RuntimeError("window oracle incomplete/invalid")
                exact.append(proofs)
                availability.append({"header_hex": h.encode().hex(), "seed": h.seed().hex(),
                                     "instance_sha256": hashlib.sha256(h.encode()[-16:]+matrix_bytes(a)).hexdigest(),
                                     "proof_count": len(proofs), "proof_set_sha256": proof_digest(proofs)})
            cohorts.append({"profile": asdict(profile), "schedule": schedule, "label": label, "headers": availability})
            rules = [LabRules(ExpectedContext(s[0].network, s[0].parent, s[0].height, profile), TARGET,
                              s[0].timestamp-1, s[0].timestamp+1, (s[0].payload,)) for s in stages]
            if any(not rule.permits(h) for rule, stage in zip(rules, stages) for h in stage):
                raise RuntimeError("window input violates trusted lab surface")
            for wall_ms, memory_mib in WINDOWS:
                for policy in POLICIES:
                    payload = {"version": "WLP1", "policy": policy, "target": TARGET,
                               "stages": [[h.encode().hex() for h in s] for s in stages],
                               "budget": asdict(LatticeBudget()), "cache_capacity": 16}
                    window = run_window(args.python, payload, wall_ms=wall_ms, memory_mib=memory_mib)
                    snapshot, checks = window["snapshot"], []
                    if snapshot is not None and "stages" in snapshot:
                        if backend is not None and backend != snapshot["backend"]:
                            raise RuntimeError("window backend changed")
                        backend = snapshot["backend"]
                        if (type(snapshot["stages"]) is not list or len(snapshot["stages"]) > STAGES
                                or window["logical_work_known"] and len(snapshot["stages"]) != STAGES):
                            raise RuntimeError("window stage count")
                        for index, result in enumerate(snapshot["stages"]):
                            if result["policy"] != policy or result["target"] != str(TARGET):
                                raise RuntimeError("window policy/target mismatch")
                            for instance in result["instances"]:
                                if "sphere" in instance:
                                    found = set(map(tuple, instance["sphere"]["proofs"]))
                                    expected = exact[index*COUNT+instance["index"]]
                                    if not found <= expected or instance["sphere"]["reason"] == "domain-exhausted" and found != expected:
                                        raise RuntimeError("window sphere set mismatch")
                            for score in result["scores"]:
                                h = stages[index][score["header_index"]]
                                if (tuple(score["vector"]) not in exact[index*COUNT+score["header_index"]]
                                        or score_digest(h, score["vector"]).hex() != score["digest"]):
                                    raise RuntimeError("window score audit mismatch")
                            if result["hit"] is not None:
                                packet = bytes.fromhex(result["hit"]["proof_hex"])
                                if not admit_proof(packet, rules[index]):
                                    raise RuntimeError("window hit violates lab admission")
                                checks.append(request(3, rules[index].context.encode()+packet))
                    if exchange(lab, checks) != [b"\x01"]*len(checks):
                        raise RuntimeError("window native hit mismatch")
                    native_checks += len(checks)  # Includes recovered aborted-stage diagnostics; not win totals.
                    records.append({"profile": asdict(profile), "schedule": schedule, "label": label,
                                    "policy": policy, "window": window})
            print("Windows cohort completed:", fields, schedule, flush=True)
    if not any(r["window"]["logical_work_known"] for r in records):
        raise RuntimeError("no complete native window; increase explicit research allowance")
    report = {"status": "passed", "experiment": "windows-v1", "python": platform.python_version(),
              "method": "Fixed-order one-pass Windows Job attempts; fresh worker per policy/window; one backend setup and cache per worker; logical budgets and reuse reset per stage.",
              "clock_scope": "Immediately before ResumeThread through observed exit/termination; includes imports, setup, policy and checkpoint I/O; excludes CreateProcess/job setup, request serialization and parent/oracle audits.",
              "memory_scope": "Windows process/job committed virtual memory; not RSS, machine RAM, energy or a memory-hardness claim.",
              "censoring": "Only whole completed workers contribute logical work/hit totals; aborted work is unknown and unconditional per-hit work is null if any attempt is censored.",
              "platform": platform.platform(), "backend": backend, "setups": SETUPS, "windows": WINDOWS,
              "stages": STAGES, "headers_per_stage": COUNT, "target": str(TARGET), "source_sha256": source_hashes(),
              "aggregate": summarize(records), "native_hit_checks_including_recovered": native_checks,
              "executable_sha256": {"sis-lab-debug": hashlib.sha256(lab.read_bytes()).hexdigest(),
                                    "sis-search-release": hashlib.sha256(native.read_bytes()).hexdigest()},
              "cohorts": cohorts, "records": records}
    paths[0].write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8", newline="\n")
    summary = {k: v for k, v in report.items() if k not in ("records", "cohorts")}
    summary["cohorts"] = [{k: v for k, v in c.items() if k != "headers"} | {
        "header_occurrences": len(c["headers"]), "with_solution": sum(h["proof_count"] > 0 for h in c["headers"]),
        "distinct_headers": len({h["header_hex"] for h in c["headers"]}),
        "distinct_instances": len({h["instance_sha256"] for h in c["headers"]})} for c in cohorts]
    summary["availability"] = {"header_occurrences": sum(len(c["headers"]) for c in cohorts),
                               "distinct_headers": len({h["header_hex"] for c in cohorts for h in c["headers"]}),
                               "distinct_instances": len({h["instance_sha256"] for c in cohorts for h in c["headers"]}),
                               "with_solution_occurrences": sum(h["proof_count"] > 0 for c in cohorts for h in c["headers"])}
    summary["groups"] = {f"{wall}/{memory}/{policy}/{schedule}": summarize([r for r in records if
                          r["window"]["resource"]["wall_ms"] == wall and r["window"]["resource"]["memory_mib"] == memory
                          and r["policy"] == policy and r["schedule"] == schedule])
                          for wall, memory in WINDOWS for policy in POLICIES for schedule in ("fresh-nonce", "fresh-parent")}
    paths[1].write_text(json.dumps(summary, indent=2)+"\n", encoding="utf-8", newline="\n")
    print("Window outcomes:", summary["aggregate"]["outcomes"], flush=True)


if __name__ == "__main__":
    main()
