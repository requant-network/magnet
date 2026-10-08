from dataclasses import asdict, replace
import json
import unittest
from unittest.mock import patch

from reference.campaign import POLICIES, run_campaign
from reference.grinding import header_family, verify_scored_proof
from reference.header import ExpectedContext, LabHeader
from reference.lattice_policies import COUNTERS, LatticeBudget
from reference.sis import Profile
from scripts.window_worker import decode
from tests.test_lattice_policies import ExactReducer


class CampaignTests(unittest.TestCase):
    def setUp(self):
        self.base = LabHeader(bytes(32), bytes([1])*32, bytes([2])*32, 1, 100, 0, Profile(7, 1, 3, 8))
        self.stages = [header_family(replace(self.base, parent=bytes([i+1])*32, height=i+1), "nonce", 3) for i in range(3)]

    def test_initial_acquisition_is_paid_and_carried_across_contexts(self):
        with patch.object(LabHeader, "matrix", return_value=[[0, 0, 0]]):
            restart = run_campaign(self.stages, "restart-first", 0, ExactReducer())
            carry = run_campaign(self.stages, "carry-first", 0, ExactReducer())
        self.assertEqual(restart["work"]["reduction_calls"], 9)
        self.assertEqual(carry["work"]["reduction_calls"], 1)
        self.assertEqual(carry["work"]["reuse_checks"], 8)
        self.assertEqual(carry["work"]["score_hashes"], 9)
        self.assertGreater(carry["acquisitions"][0]["work_through_first_score"]["sphere_nodes"], 0)
        self.assertEqual(len({s["digest"] for s in carry["scores"]}), 9)
        for name in COUNTERS:
            self.assertEqual(carry["work"][name], sum(s["work"][name] for s in carry["stages"]))

    def test_failed_carry_has_no_hidden_score_or_fallback(self):
        stages = [self.stages[0][:1], self.stages[1][:1]]
        with patch.object(LabHeader, "matrix", side_effect=[[[0, 0, 0]], [[1, 1, 1]]]):
            carry = run_campaign(stages, "carry-first", 0, ExactReducer())
        self.assertEqual(carry["work"]["score_hashes"], 1)
        self.assertEqual(carry["work"]["reduction_calls"], 1)
        with patch.object(LabHeader, "matrix", side_effect=[[[0, 0, 0]], [[1, 1, 1]], [[1, 1, 1]]]):
            fallback = run_campaign(stages, "carry-fallback", 0, ExactReducer())
        self.assertEqual(fallback["work"]["reduction_calls"], 2)
        self.assertEqual(fallback["work"]["headers"], 3)  # Paid carry check plus fresh derivation.
        self.assertEqual(fallback["work"]["score_hashes"], 2)
        self.assertEqual(len(fallback["acquisitions"]), 2)

    def test_global_limits_do_not_reset_at_stage_boundaries(self):
        with patch.object(LabHeader, "matrix", return_value=[[0, 0, 0]]):
            for policy in POLICIES:
                result = run_campaign(self.stages, policy, 0, ExactReducer(), budget=LatticeBudget(scores=1))
                self.assertEqual(result["work"]["score_hashes"], 1)
                self.assertEqual(result["reason"], "score-limit")
                self.assertIsNone(result["stages"][0]["hit"])
            hit = run_campaign(self.stages, "carry-first", 2**256, ExactReducer(), budget=LatticeBudget(scores=1))
        self.assertIsNotNone(hit["stages"][0]["hit"])
        self.assertIsNone(hit["stages"][1]["hit"])
        self.assertEqual(hit["work"]["score_hashes"], 1)
        for budget in (LatticeBudget(nodes=1), LatticeBudget(reductions=1), LatticeBudget(bits=1)):
            result = run_campaign(self.stages, "restart-first", 0, ExactReducer(), budget=budget)
            self.assertLessEqual(result["work"]["sphere_nodes"], budget.nodes)
            self.assertLessEqual(result["work"]["reduction_calls"], budget.reductions)
            self.assertLessEqual(result["work"]["score_hashes"], budget.scores)

    def test_actual_header_hits_are_context_bound(self):
        for policy in POLICIES:
            result = run_campaign(self.stages, policy, 2**256, ExactReducer())
            self.assertGreaterEqual(len(result["scores"]), 1)
            for stage in result["stages"]:
                if stage["hit"]:
                    h = self.stages[stage["index"]][stage["hit"]["header_index"]]
                    context = ExpectedContext(h.network, h.parent, h.height, h.profile)
                    self.assertTrue(verify_scored_proof(bytes.fromhex(stage["hit"]["proof_hex"]), context, 2**256))

    def test_final_unsuccessful_carried_score_retains_limit_reason(self):
        with patch.object(LabHeader, "matrix", return_value=[[0, 0, 0]]):
            result = run_campaign([self.stages[0][:2]], "carry-first", 0,
                                  ExactReducer(), budget=LatticeBudget(scores=2))
        self.assertEqual(result["reason"], "score-limit")
        self.assertEqual(result["work"]["score_hashes"], 2)
        self.assertIsNone(result["stages"][0]["hit"])

    def test_invalid_context_and_protocol_reject_before_reducer(self):
        reducer = ExactReducer()
        for stages in ([], [[self.base, replace(self.base, height=2)]],
                       [[self.base], [replace(self.base, network=bytes([9])*32)]],
                       [[self.base], [replace(self.base, profile=Profile(7, 1, 3, 7))]]):
            with self.assertRaises(ValueError):
                run_campaign(stages, "carry-first", 0, reducer)
        r = {"version": "WCP1", "policy": "carry-first", "target": 0,
             "stages": [[h.encode().hex() for h in s] for s in self.stages],
             "budget": asdict(LatticeBudget()), "cache_capacity": 1}
        self.assertEqual(len(decode(json.dumps(r).encode())[1]), 3)
        for changes in ({"cache_capacity": 2}, {"policy": "all"}, {"version": "WLP1"}):
            with self.assertRaises(ValueError):
                decode(json.dumps(r | changes).encode())
        self.assertEqual(reducer.calls, 0)


if __name__ == "__main__":
    unittest.main()
