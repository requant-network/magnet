"""Seeded paid solver/pool/joint-grinding comparison under local Windows ceilings."""

import argparse
from collections import Counter
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import platform
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from reference.admission_wire import admission_request
from reference.grinding import score_digest
from reference.header import ExpectedContext, LabHeader, encode_proof
from reference.header_rules import LabRules, admit_proof
from reference.pool_campaign import PoolBudget, WORK, joint_headers
from reference.sis import Profile, verify
from scripts.lab_driver import build_lab, exchange, matrix_bytes, request
from scripts.native_driver import build_native, encode_request, run_requests
from scripts.sphere_survey import invalidate, source_hashes
from scripts.window_driver import run_window
from solvers.portfolio import BACKENDS

SEEDS = (2026100818, 2026100819)
ORDER_SEED = 2026100820
PROFILES = (Profile(2, 1, 3, 1), Profile(17, 2, 8, 8), Profile(257, 3, 14, 12),
            Profile(769, 4, 16, 24), Profile(12289, 4, 16, 64))
CONFIGS = (("restart-all", 1, False), ("pool-fallback", 1, False),
           ("pool-all", 4, False), ("pool-all", 4, True), ("pool-all", 16, True))
WINDOWS = (500, 4000)
BUDGET = PoolBudget(nodes=100_000, acquisitions=64, checks=8192, scores=4096, proofs=32)
TARGET = 2**252


def stages_for(profile, seed):
    label = f"portfolio-v1/q{profile.q}/n{profile.n}/m{profile.m}/b{profile.b2}/{seed}"
    def digest(suffix):
        return hashlib.sha256((label+suffix).encode()).digest()
    base = LabHeader(digest("network"), digest("parent"), digest("payload"), 1, 100, 0, profile)
    stages = []
    for i in range(8):
        # Fresh parent/height each stage; joint nonce/time/payload family. Thus
        # cross-stage reuse is not simply replay of a previous challenge.
        stages.append(joint_headers(replace(base, parent=hashlib.sha256(base.parent+i.to_bytes(8, "little")).digest(),
                                           height=i+1, timestamp=100+2*i)))
    return label, tuple(stages)


def audit_snapshot(snapshot, stages, lab, *, target=TARGET):
    if snapshot is None or snapshot.get("status") == "memory-error":
        return {"visited_headers": 0, "native_admitted_hits": 0, "scores_checked": 0}
    campaign = snapshot["campaign"]
    visited, checks = 0, 0
    for instance in campaign["instances"]:
        h = stages[instance["stage"]][instance["index"]]
        if instance["header_hex"] != h.encode().hex():
            raise RuntimeError("portfolio visited a header outside trusted surface")
        matrix = h.matrix()
        if instance["matrix_sha256"] != hashlib.sha256(matrix_bytes(matrix)).hexdigest():
            raise RuntimeError("portfolio matrix fingerprint mismatch")
        if not all(verify(h.profile, matrix, x) for x in instance["valid_carried"]):
            raise RuntimeError("invalid carried vector")
        acquired = instance.get("acquired")
        if acquired is not None and not all(verify(h.profile, matrix, x) for x in acquired["proofs"]):
            raise RuntimeError("invalid acquired vector")
        visited += 1
    for score in campaign["scores"]:
        h = stages[score["stage"]][score["index"]]
        if not verify(h.profile, h.matrix(), score["vector"]) or score_digest(h, score["vector"]).hex() != score["digest"]:
            raise RuntimeError("invalid portfolio score")
        checks += 1
    native = []
    for stage in campaign["stages"]:
        hit = stage["hit"]
        if hit is None:
            continue
        headers = stages[stage["index"]]
        base = headers[0]
        context = ExpectedContext(base.network, base.parent, base.height, base.profile)
        h = headers[hit["index"]]
        if (hit["stage"] != stage["index"] or encode_proof(h, hit["vector"]).hex() != hit["proof_hex"]
                or score_digest(h, hit["vector"]).hex() != hit["digest"] or int(hit["digest"], 16) >= target):
            raise RuntimeError("portfolio hit is outside its recorded exact joint header")
        rules = LabRules(context, target, min(h.timestamp for h in headers), max(h.timestamp for h in headers),
                         tuple(dict.fromkeys(h.payload for h in headers)))
        proof = bytes.fromhex(hit["proof_hex"])
        if not admit_proof(proof, rules):
            raise RuntimeError("portfolio hit failed trusted admission")
        native.append(admission_request(rules, proof))
    if native and exchange(lab, native) != [b"\x01"]*len(native):
        raise RuntimeError("portfolio hit failed independent native admission")
    return {"visited_headers": visited, "native_admitted_hits": len(native), "scores_checked": checks}


def summarize(records):
    completed = [r for r in records if r["window"]["logical_work_known"]]
    work = {name: sum(r["window"]["snapshot"]["campaign"]["work"][name] for r in completed) for name in WORK}
    hits = sum(sum(s["hit"] is not None for s in r["window"]["snapshot"]["campaign"]["stages"]) for r in completed)
    stages = sum(sum(s["reason"] != "not-visited" for s in r["window"]["snapshot"]["campaign"]["stages"]) for r in completed)
    acquired = [i["acquired"] for r in completed for i in r["window"]["snapshot"]["campaign"]["instances"] if "acquired" in i]
    return {"attempts": len(records), "outcomes": dict(Counter(r["window"]["outcome"] for r in records)),
            "completed_campaigns": len(completed), "completed_visited_stages": stages, "completed_stage_hits": hits,
            "completed_work": work, "completed_reason_counts": dict(Counter(r["window"]["snapshot"]["campaign"]["reason"] for r in completed)),
            "all_attempt_elapsed_ns": sum(r["window"]["resource"]["elapsed_ns"] for r in records),
            "completed_setup_ns": sum(r["window"]["snapshot"]["setup_ns"] for r in completed),
            "completed_acquisition_stops": dict(Counter(x["reason"] for x in acquired)),
            "completed_stage_groups": {label: {
                "visited": sum(s["reason"] != "not-visited" for r in completed for s in r["window"]["snapshot"]["campaign"]["stages"] if (s["index"] == 0) == (label == "cold")),
                "hits": sum(s["hit"] is not None for r in completed for s in r["window"]["snapshot"]["campaign"]["stages"] if (s["index"] == 0) == (label == "cold")),
                "work": {name: sum(s["work"][name] for r in completed for s in r["window"]["snapshot"]["campaign"]["stages"]
                                   if (s["index"] == 0) == (label == "cold")) for name in WORK}}
                for label in ("cold", "warm")},
            "max_job_commit_bytes": max((r["window"]["resource"]["peak_job_commit_bytes"] for r in records), default=0),
            "completed_only_work_per_hit": {k: {"numerator": v, "denominator": hits} if hits else None for k, v in work.items()},
            "all_attempt_work_per_hit": None if len(completed) != len(records) else {
                k: {"numerator": v, "denominator": hits} if hits else None for k, v in work.items()}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--python", required=True, type=Path)
    args = parser.parse_args()
    raw = ROOT / "artifacts/portfolio-v1.json"
    output = ROOT / "docs/research/results/portfolio-v1.json"
    invalidate((raw, output))
    lab, native = build_lab(target_dir=ROOT / "artifacts/admission-current"), build_native(release=True)
    hashes = source_hashes()
    cases, oracle_records = [], []
    for profile in PROFILES:
        for seed in SEEDS:
            label, stages = stages_for(profile, seed)
            headers = [h for stage in stages for h in stage]
            generated = exchange(lab, [request(2, h.encode()) for h in headers])
            if generated != [h.seed()+matrix_bytes(h.matrix()) for h in headers]:
                raise RuntimeError("portfolio native generation mismatch")
            # A separately bounded baseline; only domain-exhausted establishes
            # availability/emptiness. Its cost is outside the worker and never free input.
            baseline = run_requests(native, [encode_request(h.profile, h.matrix(), "mitm", nodes=100_000,
                                        table=100_000, pairs=1_000_000, proofs=256) for h in headers])
            for h, sample in zip(headers, baseline, strict=True):
                if not all(verify(h.profile, h.matrix(), x) for x in sample["proofs"]):
                    raise RuntimeError("portfolio baseline proof invalid")
            oracle_records.append({"label": label, "profile": asdict(profile), "headers": len(headers),
                                   "stops": dict(Counter(x["stop"] for x in baseline)),
                                   "complete_with_solution": sum(x["stop"] == "domain-exhausted" and bool(x["proofs"]) for x in baseline),
                                   "observed_with_solution": sum(bool(x["proofs"]) for x in baseline),
                                   "unknown_availability": sum(x["stop"] != "domain-exhausted" and not x["proofs"] for x in baseline),
                                   "complete_empty": sum(x["stop"] == "domain-exhausted" and not x["proofs"] for x in baseline)})
            for backend in BACKENDS:
                for policy, capacity, combine in CONFIGS:
                    for wall_ms in WINDOWS:
                        cases.append((label, seed, stages, backend, policy, capacity, combine, wall_ms))
    random.Random(ORDER_SEED).shuffle(cases)
    records = []
    for i, (label, seed, stages, backend, policy, capacity, combine, wall_ms) in enumerate(cases):
        query = {"version": "WXP1", "backend": backend, "policy": policy, "capacity": capacity,
                 "combine": combine, "target": str(TARGET), "seed": seed,
                 "budget": asdict(BUDGET), "stages": [[h.encode().hex() for h in stage] for stage in stages]}
        window = run_window(args.python.resolve(), query, wall_ms=wall_ms, memory_mib=128, worker="portfolio_worker.py")
        audit = audit_snapshot(window["snapshot"], stages, lab)
        records.append({"label": label, "seed": seed, "backend": backend, "policy": policy, "capacity": capacity,
                        "combine": combine, "wall_ms": wall_ms, "window": window, "audit": audit})
        if i % 10 == 0:
            print(f"portfolio {i+1}/{len(cases)} {backend}: {window['outcome']}", flush=True)
    raw.write_text(json.dumps({"records": records, "baseline": oracle_records}, indent=2)+"\n", encoding="utf-8")
    groups = {}
    for r in records:
        key = f"{r['label'].split('/')[1]}/{r['backend']}/{r['policy']}/pool{r['capacity']}/combine{r['combine']}/{r['wall_ms']}ms"
        groups.setdefault(key, []).append(r)
    report = {"status": "completed", "version": "portfolio-v1", "platform": platform.platform(),
              "seeds": SEEDS, "order_seed": ORDER_SEED, "target": str(TARGET), "budget": asdict(BUDGET),
              "windows_ms": WINDOWS, "memory_mib": 128, "source_sha256": hashes,
              "source_unchanged": hashes == source_hashes(),
              "native_sha256": hashlib.sha256(native.read_bytes()).hexdigest(),
              "lab_sha256": hashlib.sha256(lab.read_bytes()).hexdigest(), "baseline": oracle_records,
              "overall": summarize(records), "groups": {k: summarize(v) for k, v in sorted(groups.items())},
              "audit": {k: sum(r["audit"][k] for r in records) for k in ("visited_headers", "native_admitted_hits", "scores_checked")},
              "limitations": ["tiny dimensions <=16; no production hardness", "timed local machine with concurrent endurance fuzzer",
                              "backend nodes have different meanings; no universal weight", "finite sieve; bounded BKZ tours, not optimized fplll",
                              "censored work unknown, cooperative caps retained", "two salted seeds; no hardware/energy comparison"]}
    output.write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(report["overall"], indent=2), flush=True)


if __name__ == "__main__":
    main()
