"""Bounded exhaustive experiment; results do not estimate real mining security."""

import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from reference.search import exhaustive_solutions
from reference.sis import Profile, expand_matrix


def main():
    profile = Profile(17, 2, 3, 8)
    records = []
    for index in range(128):
        seed = hashlib.sha256(f"magnet-sis-toy-survey-v1/{index}".encode("ascii")).digest()
        matrix = expand_matrix(profile, seed)
        start = time.perf_counter()
        solutions = list(exhaustive_solutions(profile, matrix))
        records.append({"index": index, "seed": seed.hex(), "solutions": len(solutions),
                        "enumeration_seconds": time.perf_counter() - start})
    report = {"warning": "Tiny exhaustive instances only; not mining performance or a security estimate.",
              "profile": {"q": 17, "n": 2, "m": 3, "b2": 8}, "instances": len(records),
              "solvable": sum(r["solutions"] > 0 for r in records),
              "total_solutions": sum(r["solutions"] for r in records), "records": records}
    destination = ROOT / "artifacts"
    destination.mkdir(exist_ok=True)
    (destination / "toy-survey.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "records"}, indent=2))


if __name__ == "__main__":
    main()
