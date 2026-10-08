"""Longer128-header campaigns with paid startup, persistent pools and30s ceilings."""

import argparse
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from reference.pool_campaign import PoolBudget, joint_headers
from reference.sis import Profile
from scripts.lab_driver import build_lab
from scripts.native_driver import build_native
from scripts.portfolio_survey import SEEDS, stages_for, audit_snapshot, summarize
from scripts.sphere_survey import invalidate, source_hashes
from scripts.window_driver import run_window
from solvers.portfolio import BACKENDS

TARGET = 2**248
BUDGET = PoolBudget(nodes=1_000_000, acquisitions=128, checks=15_000, scores=10_000, proofs=64)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--python", required=True, type=Path)
    args = parser.parse_args()
    raw, output = ROOT / "artifacts/soak-v1.json", ROOT / "docs/research/results/soak-v1.json"
    invalidate((raw, output))
    lab, native = build_lab(target_dir=ROOT / "artifacts/admission-current"), build_native(release=True)
    hashes = source_hashes()
    cases = []
    for profile in (Profile(17, 2, 8, 8), Profile(257, 3, 14, 12)):
        for seed in SEEDS:
            label, old = stages_for(profile, seed)
            stages = tuple(joint_headers(replace(stage[0], nonce=10_000), nonces=4, times=2, payloads=2) for stage in old)
            for backend in BACKENDS:
                for capacity, combine in ((4, False), (16, True)):
                    cases.append((label, seed, stages, backend, capacity, combine))
    order_seed = 2026100821
    random.Random(order_seed).shuffle(cases)
    records = []
    for i, (label, seed, stages, backend, capacity, combine) in enumerate(cases):
        query = {"version": "WXP1", "backend": backend, "policy": "pool-all", "capacity": capacity,
                 "combine": combine, "target": str(TARGET), "seed": seed, "budget": asdict(BUDGET),
                 "stages": [[h.encode().hex() for h in stage] for stage in stages]}
        window = run_window(args.python.resolve(), query, wall_ms=30_000, memory_mib=128, worker="portfolio_worker.py")
        records.append({"label": label, "backend": backend, "seed": seed, "capacity": capacity, "combine": combine,
                        "window": window, "audit": audit_snapshot(window["snapshot"], stages, lab, target=TARGET)})
        print(f"soak {i+1}/{len(cases)} {backend} {label.split('/')[1]}: {window['outcome']}", flush=True)
    raw.write_text(json.dumps({"records": records}, indent=2)+"\n", encoding="utf-8")
    groups = {}
    for r in records:
        key = f"{r['label'].split('/')[1]}/{r['backend']}/pool{r['capacity']}/combine{r['combine']}"
        groups.setdefault(key, []).append(r)
    report = {"status": "completed", "version": "soak-v1", "seeds": SEEDS, "order_seed": order_seed,
              "target": str(TARGET), "budget": asdict(BUDGET), "wall_ms": 30_000, "memory_mib": 128,
              "stages_per_campaign": 8, "headers_per_stage": 16, "source_sha256": hashes,
              "source_unchanged": hashes == source_hashes(),
              "native_sha256": hashlib.sha256(native.read_bytes()).hexdigest(),
              "overall": summarize(records), "groups": {k: summarize(v) for k, v in sorted(groups.items())},
              "audit": {k: sum(r["audit"][k] for r in records) for k in ("visited_headers", "native_admitted_hits", "scores_checked")},
              "limitations": ["finite eight-stage campaign, not an asymptotic steady-state proof",
                              "up to30s per worker, includes paid cold setup and all warm stages",
                              "concurrent endurance fuzzer on same host", "no GPU or energy comparison"]}
    output.write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({k: report["overall"][k] for k in ("attempts", "outcomes", "completed_stage_hits")}))


if __name__ == "__main__":
    main()
