"""Exact toy study of solution reuse and pre-oracle sparse screening."""

import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from reference.reuse import derive_solutions, matrix_rank, sparse_solutions
from reference.search import exhaustive_solutions
from reference.sis import Profile, expand_matrix

SETUPS = [(17, 2, 3, 64, 128), (17, 2, 4, 32, 128), (31, 2, 4, 64, 64)]
BOUNDS = [2, 4, 8, 16, 32, 64]


def run_setup(q, n, m, maximum_b2, count):
    generation_profile = Profile(q, n, m, maximum_b2)
    bounds = [b for b in BOUNDS if b <= maximum_b2]
    records = []
    for index in range(count):
        label = f"magnet-sis-reuse-v1/{q}/{n}/{m}/{maximum_b2}/{index}"
        seed = hashlib.sha256(label.encode("ascii")).digest()
        matrix = expand_matrix(generation_profile, seed)
        # Run the cheap probe before the oracle. The SAME matrix is used at every B2.
        probes = {b: sparse_solutions(Profile(q, n, m, b), matrix) for b in bounds}
        full = list(exhaustive_solutions(generation_profile, matrix))
        levels = []
        for b2 in bounds:
            p = Profile(q, n, m, b2)
            solutions = [x for x in full if sum(v * v for v in x) <= b2]
            one, attempts_one = derive_solutions(p, matrix, solutions[:1])
            two, attempts_two = derive_solutions(p, matrix, solutions[:2])
            sparse, sparse_attempts = probes[b2]
            if not (one | two | sparse) <= set(solutions):
                raise RuntimeError("attack output disagrees with exhaustive oracle")
            levels.append({"b2": b2, "solutions": len(solutions),
                           "from_first": len(one), "from_first_two": len(two),
                           "first_seed_count": min(1, len(solutions)),
                           "two_seed_count": min(2, len(solutions)),
                           "derive_attempts_one": attempts_one, "derive_attempts_two": attempts_two,
                           "sparse_solutions": len(sparse), "sparse_attempts": sparse_attempts,
                           "oracle_box_size": (2 * math.isqrt(b2) + 1)**m})
        records.append({"seed": seed.hex(), "rank": matrix_rank(generation_profile, matrix),
                        "levels": levels})
    summary = []
    for i, b2 in enumerate(bounds):
        levels = [r["levels"][i] for r in records]
        summary.append({"b2": b2, "instances": count,
                        "solvable": sum(x["solutions"] > 0 for x in levels),
                        "multiple_proofs": sum(x["solutions"] > 1 for x in levels),
                        "max_proofs": max(x["solutions"] for x in levels),
                        "sparse_hits": sum(x["sparse_solutions"] > 0 for x in levels),
                        "sparse_misses_with_solution": sum(x["sparse_solutions"] == 0 and x["solutions"] > 0 for x in levels),
                        "extra_from_one": sum(x["from_first"] - x["first_seed_count"] for x in levels),
                        "max_from_one": max(x["from_first"] for x in levels),
                        "extra_from_two": sum(x["from_first_two"] - x["two_seed_count"] for x in levels)})
    return {"generation_profile": {"q": q, "n": n, "m": m, "b2": maximum_b2},
            "rank_deficient": sum(r["rank"] < min(n, m) for r in records),
            "summary": summary, "records": records}


def main():
    destination = ROOT / "artifacts"
    destination.mkdir(exist_ok=True)
    output = destination / "reuse-survey.json"
    output.write_text('{"status":"running-or-incomplete"}\n', encoding="utf-8")
    report = {"status": "complete", "version": "reuse-survey-v1",
              "warning": "Toy exhaustive results only. No security or mining-speed estimate.",
              "method": "Fixed matrix across B2; oracle-ordered seeds; sparse probe before oracle.",
              "setups": []}
    for setup in SETUPS:
        result = run_setup(*setup)
        report["setups"].append(result)
        print(json.dumps({k: v for k, v in result.items() if k != "records"}, indent=2), flush=True)
    paths = ["reference/sis.py", "reference/search.py", "reference/reuse.py", "scripts/reuse_survey.py"]
    report["source_sha256"] = {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in paths}
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
