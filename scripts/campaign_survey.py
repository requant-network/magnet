"""Seeded, shuffled, repeated OS windows for paid cross-context vector campaigns."""

import argparse
from collections import Counter
from dataclasses import asdict, replace
import hashlib
import json
import os
from pathlib import Path
import platform
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from reference.admission_wire import admission_request
from reference.campaign import POLICIES
from reference.grinding import header_family, score_digest
from reference.header import ExpectedContext, LabHeader
from reference.header_rules import LabRules, admit_proof
from reference.lattice_policies import LatticeBudget
from reference.sis import Profile, verify
from scripts.lab_driver import build_lab, exchange, matrix_bytes, request
from scripts.native_driver import build_native, encode_request, run_requests
from scripts.native_survey import proof_digest
from scripts.sphere_survey import invalidate, source_hashes
from scripts.window_driver import run_window
from scripts.windows_survey import SETUPS, summarize

SEEDS, ORDER_SEED = (2026100811, 2026100812, 2026100813), 2026100814
WALLS, MEMORY, REPEATS, TARGET = (400, 1200), 64, 2, 2**256//16


def stages_for(profile, schedule, seed):
    if schedule not in ("fresh-nonce", "fresh-parent") or type(seed) is not int or not 0 <= seed < 2**64:
        raise ValueError("campaign schedule/seed")
    label = f"magnet-campaign-v1/{profile.q}/{profile.n}/{profile.m}/{profile.b2}/{seed}"
    blobs = [hashlib.sha256((label+s).encode()).digest() for s in ("/network", "/parent", "/payload")]
    base = LabHeader(*blobs, 1, 100, 0, profile)
    stages = []
    for i in range(3):
        start = replace(base, nonce=i*8) if schedule == "fresh-nonce" else replace(
            base, parent=base.parent if i == 0 else hashlib.sha256(base.parent+i.to_bytes(8, "little")).digest(), height=i+1)
        stages.append(header_family(start, "nonce", 8))
    return label, tuple(stages)


def jobs_for(count):
    if type(count) is not int or not 1 <= count <= 64:
        raise ValueError("campaign cohort count")
    jobs = [(i, repeat, wall, policy) for i in range(count) for repeat in range(REPEATS)
            for wall in WALLS for policy in POLICIES]
    random.Random(ORDER_SEED).shuffle(jobs)
    return jobs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--python", type=Path, required=True)
    args = parser.parse_args()
    paths = [ROOT / "artifacts/campaign-v1.json", ROOT / "artifacts/campaign-summary-v1.json"]
    invalidate(paths)
    lab, native = build_lab(), build_native(release=True)
    cohorts, prepared = [], []
    for fields in SETUPS:
        p = Profile(*fields)
        for schedule in ("fresh-nonce", "fresh-parent"):
            for seed in SEEDS:
                label, stages = stages_for(p, schedule, seed)
                headers = [h for stage in stages for h in stage]
                matrices = [h.matrix() for h in headers]
                if exchange(lab, [request(2, h.encode()) for h in headers]) != [
                        h.seed()+matrix_bytes(a) for h, a in zip(headers, matrices, strict=True)]:
                    raise RuntimeError("campaign generation mismatch")
                oracle = run_requests(native, [encode_request(p, a, "mitm") for a in matrices])
                exact, evidence = [], []
                for h, a, result in zip(headers, matrices, oracle, strict=True):
                    pool = set(result["proofs"])
                    if (result["stop"] != "domain-exhausted" or len(pool) != len(result["proofs"])
                            or not all(verify(p, a, v) for v in pool)):
                        raise RuntimeError("campaign oracle incomplete/invalid")
                    exact.append(pool)
                    evidence.append({"header_hex": h.encode().hex(), "seed": h.seed().hex(),
                                     "instance_sha256": hashlib.sha256(h.encode()[-16:]+matrix_bytes(a)).hexdigest(),
                                     "proof_count": len(pool), "proof_set_sha256": proof_digest(pool)})
                rules = [LabRules(ExpectedContext(s[0].network, s[0].parent, s[0].height, p), TARGET,
                                  99, 101, (s[0].payload,)) for s in stages]
                cohorts.append({"profile": asdict(p), "schedule": schedule, "seed": seed,
                                "label": label, "headers": evidence})
                prepared.append((stages, exact, rules))
    records, backend, hit_checks = [], None, 0
    order = jobs_for(len(cohorts))
    for sequence, (index, repeat, wall, policy) in enumerate(order):
        stages, exact, rules = prepared[index]
        payload = {"version": "WCP1", "policy": policy, "target": TARGET,
                   "stages": [[h.encode().hex() for h in s] for s in stages],
                   "budget": asdict(LatticeBudget()), "cache_capacity": 1}
        window = run_window(args.python, payload, wall_ms=wall, memory_mib=MEMORY)
        snapshot, checks = window["snapshot"], []
        if snapshot is not None and "stages" in snapshot:
            if (snapshot["policy"] != policy or snapshot["target"] != str(TARGET)
                    or len(snapshot["stages"]) > 3 or window["logical_work_known"] and len(snapshot["stages"]) != 3):
                raise RuntimeError("campaign snapshot shape/policy")
            if backend is not None and backend != snapshot["backend"]:
                raise RuntimeError("campaign backend changed")
            backend = snapshot["backend"]
            for entry in snapshot["instances"]:
                if "fresh" not in entry:
                    continue
                for instance in entry["fresh"]["instances"]:
                    if "sphere" in instance:
                        found = set(map(tuple, instance["sphere"]["proofs"]))
                        wanted = exact[8*entry["stage"]+entry["index"]]
                        if not found <= wanted or instance["sphere"]["reason"] == "domain-exhausted" and found != wanted:
                            raise RuntimeError("campaign sphere/oracle mismatch")
            for score in snapshot["scores"]:
                h = stages[score["stage"]][score["header_index"]]
                if (tuple(score["vector"]) not in exact[8*score["stage"]+score["header_index"]]
                        or score_digest(h, score["vector"]).hex() != score["digest"]):
                    raise RuntimeError("campaign score mismatch")
            for stage in snapshot["stages"]:
                if stage["hit"] is not None:
                    packet = bytes.fromhex(stage["hit"]["proof_hex"])
                    if not admit_proof(packet, rules[stage["index"]]):
                        raise RuntimeError("campaign Python admission mismatch")
                    checks.append(admission_request(rules[stage["index"]], packet))
            if exchange(lab, checks) != [b"\x01"]*len(checks):
                raise RuntimeError("campaign Rust full admission mismatch")
            hit_checks += len(checks)  # Aborted recovered diagnostics are not complete-worker wins.
        records.append({k: v for k, v in cohorts[index].items() if k != "headers"} |
                       {"cohort": index, "repeat": repeat, "sequence": sequence, "policy": policy, "window": window})
        if (sequence+1) % 24 == 0:
            print(f"Campaign attempts: {sequence+1}/{len(order)}", flush=True)
    if not any(r["window"]["logical_work_known"] for r in records):
        raise RuntimeError("no completed native campaign")
    report = {"status": "passed", "experiment": "campaign-v1", "source_sha256": source_hashes(),
              "python": platform.python_version(), "platform": platform.platform(),
              "hardware": {"processor": platform.processor(), "logical_cpus": os.cpu_count()},
              "backend": backend, "seeds": SEEDS, "order_seed": ORDER_SEED, "repeats": REPEATS,
              "walls_ms": WALLS, "memory_mib": MEMORY, "target": str(TARGET), "budget": asdict(LatticeBudget()),
              "method": "One deterministic shuffled order, three salted cohorts, two same-input repeats; fresh process/setup per attempt; one carried vector and one shared budget across all stages; no matrix cache.",
              "clock_scope": "ResumeThread through observed exit; includes startup/setup, campaign and checkpoint I/O; excludes process/job setup, parent/oracle audits.",
              "aggregate": summarize(records), "native_full_admission_hit_checks_including_recovered": hit_checks,
              "executable_sha256": {"sis-lab-debug": hashlib.sha256(lab.read_bytes()).hexdigest(),
                                    "sis-search-release": hashlib.sha256(native.read_bytes()).hexdigest()},
              "cohorts": cohorts, "records": records}
    paths[0].write_text(json.dumps(report, indent=2)+"\n", encoding="utf8", newline="\n")
    summary = {k: v for k, v in report.items() if k not in ("cohorts", "records")}
    summary["cohorts"] = [{k: v for k, v in c.items() if k != "headers"} | {
        "with_solution_occurrences": sum(h["proof_count"] > 0 for h in c["headers"]),
        "distinct_instances": len({h["instance_sha256"] for h in c["headers"]})} for c in cohorts]
    summary["availability"] = {"header_occurrences": sum(len(c["headers"]) for c in cohorts),
                               "distinct_headers": len({h["header_hex"] for c in cohorts for h in c["headers"]}),
                               "distinct_instances": len({h["instance_sha256"] for c in cohorts for h in c["headers"]})}
    summary["groups"] = {f"{wall}/{policy}/{schedule}": summarize([r for r in records if
                         r["window"]["resource"]["wall_ms"] == wall and r["policy"] == policy and r["schedule"] == schedule])
                         for wall in WALLS for policy in POLICIES for schedule in ("fresh-nonce", "fresh-parent")}
    summary["per_seed"] = {str(seed): summarize([r for r in records if r["seed"] == seed]) for seed in SEEDS}
    summary["completed_campaign_stops"] = dict(Counter(r["window"]["snapshot"]["reason"] for r in records if r["window"]["logical_work_known"]))
    paths[1].write_text(json.dumps(summary, indent=2)+"\n", encoding="utf8", newline="\n")
    print("Campaign outcomes:", summary["aggregate"]["outcomes"], flush=True)


if __name__ == "__main__":
    main()
