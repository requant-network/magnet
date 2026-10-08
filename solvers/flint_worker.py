"""Optional pinned FLINT subprocess worker. Controlled local research input only."""

from dataclasses import asdict
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from reference.sis import Profile, _check_shape
from solvers.lattice import kernel_basis

MAX_INPUT = 1_048_576
MAX_BATCH = 100
MAX_BITS = 256
VERSION = "0.9.0"


def decode_request(data):
    if type(data) is not bytes or len(data) > MAX_INPUT:
        raise ValueError("FLINT request size/type")
    request = json.loads(data)
    if type(request) is not dict or set(request) != {"version", "cases"} or request["version"] != "MFL1":
        raise ValueError("FLINT request version/fields")
    cases = request["cases"]
    if type(cases) is not list or not 1 <= len(cases) <= MAX_BATCH:
        raise ValueError("FLINT batch bound")
    result = []
    for case in cases:
        if type(case) is not dict or set(case) != {"profile", "matrix"}:
            raise ValueError("FLINT case fields")
        if type(case["profile"]) is not dict or set(case["profile"]) != {"q", "n", "m", "b2"}:
            raise ValueError("FLINT profile fields")
        p = Profile(**case["profile"])
        if p.m > 16:
            raise ValueError("FLINT laboratory dimension bound")
        _check_shape(p, case["matrix"], [0] * p.m)
        result.append((p, case["matrix"]))
    return result


def backend_metadata():
    distribution = importlib.metadata.distribution("python-flint")
    if distribution.version != VERSION:
        raise ValueError("expected pinned python-flint 0.9.0")
    files = [p for p in distribution.files if str(p).endswith((".pyd", ".dll", ".so"))
             or ".dist-info/licenses/" in str(p) or str(p).endswith(".dist-info/METADATA")]
    return {"package": "python-flint", "version": VERSION,
            "worker_python": sys.version, "worker_platform": platform.platform(),
            "license_expression": distribution.metadata.get("License-Expression"),
            "file_sha256": {str(p).replace("\\", "/"): hashlib.sha256(distribution.locate_file(p).read_bytes()).hexdigest()
                            for p in sorted(files, key=str)}}


def reduce_case(profile, matrix):
    """Shared native reduction; callers validate inputs and audit outputs."""
    import flint  # No import/install in the standard-library local check gate.
    start = time.perf_counter_ns()
    initial, rank = kernel_basis(profile, matrix)
    construction_ns = time.perf_counter_ns() - start
    start = time.perf_counter_ns()
    basis, transform = flint.fmpz_mat(initial).lll(
        transform=True, delta=0.75, eta=0.5, rep="zbasis", gram="approx")
    reduced = tuple(tuple(int(x) for x in row) for row in basis.tolist())
    operation = tuple(tuple(int(x) for x in row) for row in transform.tolist())
    reduction_ns = time.perf_counter_ns() - start
    if any(abs(x).bit_length() > MAX_BITS for square in (reduced, operation) for row in square for x in row):
        raise ValueError("FLINT output arithmetic bound")
    return {"profile": asdict(profile), "initial_basis": initial, "basis": reduced,
            "transform": operation, "rank": rank, "reason": "lll-reduced",
            "construction_ns": construction_ns, "reduction_ns": reduction_ns}


def run(cases):
    import flint
    metadata = backend_metadata()
    # Warm the code path once; neither import nor this warmup is in core timers.
    flint.fmpz_mat([[1]]).lll(transform=True, delta=0.75, eta=0.5)
    results = [reduce_case(profile, matrix) for profile, matrix in cases]
    return {"version": "MFR1", "backend": metadata, "results": results}


def main():
    try:
        cases = decode_request(sys.stdin.buffer.read(MAX_INPUT + 1))
        result = run(cases)
        sys.stdout.write(json.dumps(result, separators=(",", ":")))
    except (ValueError, TypeError, ImportError, KeyError) as error:
        sys.stderr.write(f"flint-worker: {error}\n")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
