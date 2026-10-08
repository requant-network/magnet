"""WXP1 controlled portfolio worker; spawned only under Windows Job ceilings."""

import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from reference.header import LabHeader
from reference.pool_campaign import POLICIES, PoolBudget, run_pool_campaign
from scripts.window_worker import MAX_INPUT, publish
from solvers.portfolio import BACKENDS, Portfolio


def decode(data):
    if type(data) is not bytes or len(data) > MAX_INPUT:
        raise ValueError("portfolio input bounds")
    request = json.loads(data)
    fields = {"version", "backend", "policy", "target", "stages", "capacity", "combine", "budget", "seed"}
    if type(request) is not dict or set(request) != fields or request["version"] != "WXP1":
        raise ValueError("portfolio version/fields")
    if request["backend"] not in BACKENDS or request["policy"] not in POLICIES:
        raise ValueError("portfolio backend/policy")
    target_wire = request["target"]
    if (type(target_wire) is not str or not target_wire.isascii() or not target_wire.isdigit()
            or len(target_wire) > 78 or str(int(target_wire)) != target_wire or not 0 <= int(target_wire) <= 2**256):
        raise ValueError("portfolio target")
    if (type(request["capacity"]) is not int or not 1 <= request["capacity"] <= 16
            or type(request["combine"]) is not bool or type(request["seed"]) is not int
            or not 0 <= request["seed"] < 2**64):
        raise ValueError("portfolio capacity/combine/seed")
    if type(request["budget"]) is not dict or set(request["budget"]) != {"nodes", "acquisitions", "checks", "scores", "proofs"}:
        raise ValueError("portfolio budget fields")
    budget = PoolBudget(**request["budget"])
    if type(request["stages"]) is not list or not 1 <= len(request["stages"]) <= 8:
        raise ValueError("portfolio stages")
    stages = []
    for stage in request["stages"]:
        if type(stage) is not list or not 1 <= len(stage) <= 16:
            raise ValueError("portfolio stage size")
        headers = []
        for wire in stage:
            if type(wire) is not str or len(wire) != 280 or any(c not in "0123456789abcdef" for c in wire):
                raise ValueError("portfolio header encoding")
            h = LabHeader.decode(bytes.fromhex(wire))
            if h.profile.m > 16:
                raise ValueError("portfolio dimension")
            headers.append(h)
        base = headers[0]
        if any((h.network, h.parent, h.height, h.profile) !=
               (base.network, base.parent, base.height, base.profile) for h in headers):
            raise ValueError("portfolio stage context")
        stages.append(headers)
    if any((s[0].network, s[0].profile) != (stages[0][0].network, stages[0][0].profile) for s in stages):
        raise ValueError("portfolio campaign context")
    return request, stages, budget


def main():
    source, destination = map(Path, sys.argv[1:3])
    try:
        begin = time.perf_counter_ns()
        with source.open("rb") as stream:
            request, stages, budget = decode(stream.read(MAX_INPUT+1))
        # Fixed build artifact, never a path supplied by the JSON input.
        native = ROOT / "target/release/sis-search.exe"
        solver = Portfolio(request["backend"], native, request["seed"])
        def checkpoint(campaign):
            publish(destination.parent / f"checkpoint-{len(campaign['stages'])}.json",
                    {"status": "checkpoint", "campaign": campaign, "backend": solver.metadata, "setup_ns": solver.setup_ns})
        campaign = run_pool_campaign(stages, request["policy"], int(request["target"]), solver,
                                     capacity=request["capacity"], combine=request["combine"], budget=budget, on_stage=checkpoint)
        publish(destination, {"status": "completed", "campaign": campaign, "backend": solver.metadata,
                              "setup_ns": solver.setup_ns, "worker_elapsed_ns": time.perf_counter_ns()-begin})
    except MemoryError:
        publish(destination.parent / "error.json", {"status": "memory-error"})
        raise SystemExit(77)
    except Exception as error:
        publish(destination.parent / "error.json", {"status": "worker-error", "error_type": type(error).__name__, "message": str(error)[:512]})
        raise SystemExit(78)


if __name__ == "__main__":
    main()
