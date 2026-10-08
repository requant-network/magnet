"""Isolated FLINT client; independently audit every returned integer certificate."""

from dataclasses import asdict
import json
from pathlib import Path
import subprocess
import time

from solvers.flint_worker import MAX_INPUT, decode_request
from solvers.lattice import LatticeWork, Reduction
from solvers.lattice_audit import audit_certificate

ROOT = Path(__file__).resolve().parents[1]
MAX_RESPONSE = 8_388_608


def decode_response(data, cases):
    if type(data) is not bytes or len(data) > MAX_RESPONSE:
        raise ValueError("FLINT response bound")
    response = json.loads(data)
    if type(response) is not dict or set(response) != {"version", "backend", "results"} or response["version"] != "MFR1":
        raise ValueError("FLINT response fields/version")
    backend = response["backend"]
    if type(backend) is not dict or backend.get("package") != "python-flint" or backend.get("version") != "0.9.0":
        raise ValueError("FLINT backend version")
    if type(response["results"]) is not list or len(response["results"]) != len(cases):
        raise ValueError("FLINT result count")
    decoded = []
    for item, (profile, matrix) in zip(response["results"], cases, strict=True):
        fields = {"profile", "initial_basis", "basis", "transform", "rank", "reason", "construction_ns", "reduction_ns"}
        if type(item) is not dict or set(item) != fields or item["profile"] != asdict(profile):
            raise ValueError("FLINT result fields/profile")
        for name in ("construction_ns", "reduction_ns"):
            if type(item[name]) is not int or not 0 <= item[name] < 2**64:
                raise ValueError("FLINT timer encoding")
        if item["reason"] != "lll-reduced":
            raise ValueError("FLINT reduction did not complete")
        reduction = Reduction(item["initial_basis"], item["basis"], item["transform"],
                              item["rank"], item["reason"], LatticeWork())
        certificate = audit_certificate(profile, matrix, reduction)
        decoded.append({"reduction": reduction, "certificate": certificate,
                        "construction_ns": item["construction_ns"], "reduction_ns": item["reduction_ns"]})
    return backend, decoded


def run_flint(python, cases, *, timeout=60):
    cases = tuple(cases)
    payload = json.dumps({"version": "MFL1", "cases": [{"profile": asdict(p), "matrix": a} for p, a in cases]}).encode()
    if len(payload) > MAX_INPUT:
        raise ValueError("FLINT request size")
    decode_request(payload)
    start = time.perf_counter_ns()
    result = subprocess.run([str(python), str(ROOT / "solvers/flint_worker.py")],
                            input=payload, capture_output=True, timeout=timeout, check=True, cwd=ROOT)
    elapsed = time.perf_counter_ns() - start
    if result.stderr:
        raise RuntimeError("unexpected FLINT worker diagnostics")
    backend, records = decode_response(result.stdout, cases)
    return {"backend": backend, "records": records, "process_elapsed_ns": elapsed}
