"""Paid single-vector campaigns across trusted contexts; no oracle acquisition."""

from dataclasses import asdict, replace
import time

from reference.grinding import SCORE_DOMAIN, _target, score_digest
from reference.header import LabHeader, encode_proof
from reference.lattice_policies import COUNTERS, LatticeBudget, run_lattice_policy
from reference.sis import verify

POLICIES = ("restart-first", "carry-first", "carry-fallback")


def run_campaign(stages, policy, target, reducer, *, budget=None, on_stage=None):
    _target(target)
    budget = LatticeBudget() if budget is None else budget
    if (policy not in POLICIES or not callable(reducer) or not isinstance(budget, LatticeBudget)
            or type(stages) not in (list, tuple) or not 1 <= len(stages) <= 3
            or on_stage is not None and not callable(on_stage)):
        raise ValueError("invalid campaign configuration")
    for stage in stages:
        if (type(stage) not in (list, tuple) or not 1 <= len(stage) <= 16
                or any(not isinstance(h, LabHeader) or h.profile.m > 16 for h in stage)):
            raise ValueError("invalid campaign stage")
        first = stage[0]
        if any((h.network, h.parent, h.height, h.profile) !=
               (first.network, first.parent, first.height, first.profile) for h in stage):
            raise ValueError("campaign stage context mismatch")
    first = stages[0][0]
    if any((stage[0].network, stage[0].profile) != (first.network, first.profile) for stage in stages):
        raise ValueError("campaign network/profile mismatch")
    begin = time.perf_counter_ns()
    work = dict.fromkeys(COUNTERS, 0)
    result = {"policy": policy, "target": str(target), "budget": asdict(budget), "work": work,
              "stages": [], "instances": [], "scores": [], "acquisitions": [], "reason": "campaign-exhausted"}
    carried, halted = None, False
    for stage_index, headers in enumerate(stages):
        before = dict(work)
        stage = {"index": stage_index, "hit": None, "reason": "not-visited" if halted else "stage-exhausted"}
        for header_index, h in enumerate(headers):
            if halted:
                break
            if work["score_hashes"] == budget.scores:
                stage["reason"], halted = "score-limit", True
                break
            fresh, sample = policy == "restart-first" or carried is None, None
            if not fresh:
                matrix = h.matrix()
                work["headers"] += 1
                work["matrix_entries"] += h.profile.n*h.profile.m
                work["reuse_checks"] += 1
                valid = verify(h.profile, matrix, carried)
                result["instances"].append({"stage": stage_index, "index": header_index,
                                            "reason": "carry-valid" if valid else "carry-invalid"})
                if valid:
                    digest = score_digest(h, carried)
                    work["score_hashes"] += 1
                    work["score_bytes"] += len(SCORE_DOMAIN) + len(encode_proof(h, carried))
                    sample = {"stage": stage_index, "header_index": header_index,
                              "vector": carried, "digest": digest.hex()}
                else:
                    fresh = policy == "carry-fallback"
            if fresh:
                if work["reduction_calls"] == budget.reductions or work["sphere_nodes"] == budget.nodes:
                    stage["reason"] = "reduction-limit" if work["reduction_calls"] == budget.reductions else "node-limit"
                    halted = True
                    break
                remaining = replace(budget, reductions=1, nodes=budget.nodes-work["sphere_nodes"],
                                    scores=budget.scores-work["score_hashes"])
                attempt = run_lattice_policy([h], "first", target, reducer, budget=remaining)
                for name in COUNTERS:
                    work[name] += attempt["work"][name]
                result["instances"].append({"stage": stage_index, "index": header_index, "fresh": attempt})
                if attempt["scores"]:
                    sample = attempt["scores"][0] | {"stage": stage_index, "header_index": header_index}
                    carried = tuple(sample["vector"])
                    result["acquisitions"].append({"stage": stage_index, "header_index": header_index,
                                                  "vector": carried, "work_through_first_score": dict(work)})
                if attempt["reason"] not in ("family-exhausted", "score-hit"):
                    stage["reason"], halted = attempt["reason"], True
            if sample is not None:
                result["scores"].append(sample)
                if int(sample["digest"], 16) < target:
                    stage["hit"] = sample | {"proof_hex": encode_proof(h, sample["vector"]).hex()}
                    stage["reason"] = "score-hit"
                    # A hit on the final score wins for this stage; later stages
                    # still obey the same campaign-wide ceiling.
                    halted = False
                    break
                if work["score_hashes"] == budget.scores:
                    stage["reason"], halted = "score-limit", True
                    break
            if halted:
                break
        stage["work"] = {name: work[name]-before[name] for name in COUNTERS}
        result["stages"].append(stage)
        if halted and stage["reason"] != "not-visited":
            result["reason"] = stage["reason"]
        result["elapsed_ns"] = time.perf_counter_ns()-begin
        if on_stage is not None:
            on_stage(result)
    return result
