"""Optional actual-backend differential against a complete tiny exhaustive oracle."""

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from reference.search import exhaustive_solutions
from reference.pool_campaign import PoolBudget, joint_headers, run_pool_campaign
from reference.header import LabHeader
from reference.sis import Profile, expand_matrix
from scripts.native_driver import build_native
from scripts.sphere_survey import source_hashes
from solvers.portfolio import BACKENDS, Portfolio


def run():
    output = ROOT / "docs/research/results/portfolio-complete-probe-v1.json"
    output.write_text('{"status":"running-or-incomplete"}\n', encoding="utf-8")
    native = build_native(release=True)
    samples = []
    for p in (Profile(7, 1, 3, 8), Profile(17, 2, 4, 8)):
        for i in range(12):
            seed = hashlib.sha256(f"portfolio-complete-v1/{i}".encode()).digest()
            a = expand_matrix(p, seed)
            exact = set(exhaustive_solutions(p, a))
            for backend in BACKENDS:
                r = Portfolio(backend, native, i).acquire(p, a, 10_000, 256)
                found = set(r["proofs"])
                if not found <= exact or r["reason"] == "domain-exhausted" and found != exact:
                    raise RuntimeError(f"portfolio exact-set differential failed: {backend}/{p}/{i}")
                samples.append({"q": p.q, "n": p.n, "m": p.m, "b2": p.b2, "seed_hex": seed.hex(),
                                "backend": backend, "stop": r["reason"], "oracle_proofs": len(exact),
                                "found": len(found), "work": r["work"], "certificate": r["certificate"]})
    header = LabHeader(bytes(32), bytes([1])*32, bytes([2])*32, 1, 100, 0, Profile(7, 1, 3, 8))
    paid = run_pool_campaign([joint_headers(header)]*2, "pool-all", 0, Portfolio("mitm", native, 1),
                             budget=PoolBudget(nodes=10))
    if paid["work"]["search_nodes"] != 10 or paid["reason"] != "node-limit" or paid["work"]["acquisitions"] != 1:
        raise RuntimeError("native paid campaign failed shared node ceiling")
    report = {"status": "passed", "cases": 24, "searches": len(samples), "mismatches": 0,
              "source_sha256": source_hashes(), "records": samples,
              "native_paid_boundary": paid["work"],
              "scope": "actual pinned FLINT/BKZ/sieve/native backends; complete-set equality only for domain-exhausted"}
    output.write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("status", "cases", "searches", "mismatches")}))


if __name__ == "__main__":
    run()
