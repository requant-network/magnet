"""Controlled file protocol for one externally bounded Windows experiment."""

import json
import hashlib
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
MAX_INPUT, MAX_OUTPUT = 65_536, 8_388_608


def publish(path, value):
    wire = json.dumps(value, separators=(",", ":")).encode()
    if len(wire) > MAX_OUTPUT:
        raise ValueError("window output bound")
    # Never overwrite or rename a watched Windows file. A killed partial write
    # has no valid completion marker; previous immutable checkpoints survive.
    with path.open("xb") as stream:
        stream.write(wire)
    marker = len(wire).to_bytes(8, "little") + hashlib.sha256(wire).digest()
    with path.with_suffix(path.suffix + ".ready").open("xb") as stream:
        stream.write(marker)


def decode(data):
    from reference.header import ExpectedContext, LabHeader
    from reference.grinding import _target
    from reference.lattice_policies import LatticeBudget, POLICIES
    from reference.campaign import POLICIES as CAMPAIGNS
    if type(data) is not bytes or len(data) > MAX_INPUT:
        raise ValueError("window input bound")
    r = json.loads(data)
    if (type(r) is not dict or set(r) != {"version", "policy", "target", "stages", "budget", "cache_capacity"}
            or r["version"] not in ("WLP1", "WCP1")
            or r["policy"] not in (POLICIES if r["version"] == "WLP1" else CAMPAIGNS)):
        raise ValueError("window protocol fields")
    _target(r["target"])
    if type(r["cache_capacity"]) is not int or not 1 <= r["cache_capacity"] <= 32:
        raise ValueError("window cache capacity")
    if r["version"] == "WCP1" and r["cache_capacity"] != 1:
        raise ValueError("campaign has one carried vector and no matrix cache")
    if type(r["budget"]) is not dict or set(r["budget"]) != {"nodes", "reductions", "scores", "proofs_per_instance", "bits"}:
        raise ValueError("window budget fields")
    budget = LatticeBudget(**r["budget"])
    if type(r["stages"]) is not list or not 1 <= len(r["stages"]) <= 3:
        raise ValueError("window stage count")
    stages = []
    for stage in r["stages"]:
        if type(stage) is not list or not 1 <= len(stage) <= 16:
            raise ValueError("window header count")
        headers = []
        for wire in stage:
            if type(wire) is not str or len(wire) != 280:
                raise ValueError("window header encoding")
            header = LabHeader.decode(bytes.fromhex(wire))
            if header.encode().hex() != wire or header.profile.m > 16:
                raise ValueError("window canonical header/dimension")
            headers.append(header)
        first = headers[0]
        context = ExpectedContext(first.network, first.parent, first.height, first.profile)
        if any(not context.matches(h) for h in headers):
            raise ValueError("window stage context mismatch")
        stages.append(tuple(headers))
    if r["version"] == "WCP1" and any((stage[0].network, stage[0].profile) !=
                                     (stages[0][0].network, stages[0][0].profile) for stage in stages):
        raise ValueError("campaign network/profile mismatch")
    return r, stages, budget


def main():
    source, destination = map(Path, sys.argv[1:3])
    try:
        if len(sys.argv) == 4:  # Fixed resource-control probes; never accepted by policy protocol.
            if sys.argv[3] == "sleep":
                time.sleep(5)
            elif sys.argv[3] == "allocate":
                allocation = bytearray(256*1024*1024)
                allocation[0] = 1
            else:
                raise ValueError("unknown diagnostic")
            publish(destination, {"status": "diagnostic-complete"})
            return
        with source.open("rb") as stream:
            r, stages, budget = decode(stream.read(MAX_INPUT+1))
        from reference.lattice_cache import CandidateCache
        from reference.lattice_policies import run_lattice_policy
        from solvers.practical import PracticalReducer
        reducer = PracticalReducer()
        if r["version"] == "WCP1":
            from reference.campaign import run_campaign
            def checkpoint(result):
                publish(destination.with_name(f"checkpoint-{len(result['stages'])}.json"),
                        result | {"status": "running", "backend": reducer.backend, "backend_setup_ns": reducer.setup_ns})
            result = run_campaign(stages, r["policy"], r["target"], reducer, budget=budget, on_stage=checkpoint)
            publish(destination, result | {"status": "completed", "backend": reducer.backend,
                                           "backend_setup_ns": reducer.setup_ns})
            return
        cache = CandidateCache(r["cache_capacity"], budget.proofs_per_instance) if r["policy"] == "cache-all" else None
        report = {"status": "running", "backend": reducer.backend, "backend_setup_ns": reducer.setup_ns, "stages": []}
        for index, headers in enumerate(stages, 1):
            report["stages"].append(run_lattice_policy(headers, r["policy"], r["target"], reducer, budget=budget, cache=cache))
            publish(destination.with_name(f"checkpoint-{index}.json"), report)
        report["status"] = "completed"
        publish(destination, report)
    except MemoryError:
        publish(destination.with_name("error.json"), {"status": "memory-error"})
        raise SystemExit(77)
    except Exception as error:
        publish(destination.with_name("error.json"), {"status": "worker-error", "error_type": type(error).__name__, "message": str(error)[:256]})
        raise SystemExit(78)


if __name__ == "__main__":
    main()
