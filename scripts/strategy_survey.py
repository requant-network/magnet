"""Compare bounded search policies on a fixed, reproducible seed schedule."""

from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from reference.sis import Profile, expand_matrix, verify
from reference.strategies import STRATEGIES, run_strategy

SETUPS = [(17, 2, 3, 8, 128), (17, 2, 3, 64, 128),
          (17, 2, 4, 32, 128), (31, 2, 4, 64, 64)]
PROPOSAL_LIMIT = 100_000
TARGET = 2**252


def run_setup(q, n, m, b2, count):
    profile = Profile(q, n, m, b2)
    totals = {s: {"work": Counter(), "first_solution_work": Counter(),
                  "stops": Counter(), "instances_with_solution": 0} for s in STRATEGIES}
    records = []
    for index in range(count):
        label = f"magnet-sis-strategies-v1/{q}/{n}/{m}/{b2}/{index}"
        seed = hashlib.sha256(label.encode("ascii")).digest()
        results = {}
        for strategy in STRATEGIES:
            result = run_strategy(profile, seed, strategy, proposal_limit=PROPOSAL_LIMIT, target=TARGET)
            # Independent acceptance audit, outside the search and its counters.
            matrix = expand_matrix(profile, seed)
            if (len(set(result["proofs"])) != len(result["proofs"])
                    or not all(verify(profile, matrix, x) for x in result["proofs"])):
                raise RuntimeError("strategy emitted duplicate or invalid proofs")
            total = totals[strategy]
            total["work"].update(result["work"])
            total["stops"][result["reason"]] += 1
            if result["first_solution_work"] is not None:
                total["instances_with_solution"] += 1
                total["first_solution_work"].update(result["first_solution_work"])
            results[strategy] = result
        records.append({"seed": seed.hex(), "results": results})
    return {"profile": {"q": q, "n": n, "m": m, "b2": b2}, "instances": count,
            "strategies": totals, "records": records}


def main():
    destination = ROOT / "artifacts"
    destination.mkdir(exist_ok=True)
    output = destination / "strategy-survey.json"
    output.write_text('{"status":"running-or-incomplete"}\n', encoding="utf-8")
    report = {"status": "complete", "version": "strategy-survey-v1",
              "warning": "Toy component accounting. No calibrated work, hashrate or security claim.",
              "proposal_limit_per_instance": PROPOSAL_LIMIT, "target_hex": hex(TARGET),
              "score_rule": "SHA256(domain || LE profile || seed || LE vector) < target; big-endian digest",
              "method": "Same seeds per policy; stop at first score hit, policy restart, exhaustion or cap.",
              "setups": []}
    for setup in SETUPS:
        result = run_setup(*setup)
        report["setups"].append(result)
        print(json.dumps({"profile": result["profile"], "strategies": result["strategies"]}), flush=True)
    paths = ["reference/sis.py", "reference/search.py", "reference/strategies.py",
             "scripts/strategy_survey.py", "tests/test_strategies.py"]
    report["source_sha256"] = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths}
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
