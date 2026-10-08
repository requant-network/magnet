from dataclasses import replace
import unittest
from unittest.mock import patch

from reference.grinding import header_family, verify_scored_proof
from reference.header import ExpectedContext, LabHeader
from reference.lattice_cache import CandidateCache, instance_key
from reference.lattice_policies import LatticeBudget, POLICIES, run_lattice_policy
from reference.sis import Profile
from solvers.lattice import reduce_kernel


class ExactReducer:
    def __init__(self):
        self.calls = 0

    def __call__(self, p, matrix):
        self.calls += 1
        return {"reduction": reduce_kernel(p, matrix), "construction_ns": 0, "reduction_ns": 0, "audit_ns": 0}


class LatticePolicyTests(unittest.TestCase):
    def setUp(self):
        self.base = LabHeader(bytes(32), bytes([1])*32, bytes([2])*32, 1, 100, 0, Profile(7, 1, 3, 8))
        self.headers = header_family(self.base, "nonce", 8)

    def test_real_headers_hit_and_paid_acquisition(self):
        context = ExpectedContext(self.base.network, self.base.parent, self.base.height, self.base.profile)
        for policy in POLICIES:
            reducer = ExactReducer()
            result = run_lattice_policy(self.headers, policy, 2**256, reducer)
            self.assertEqual(result["reason"], "score-hit")
            self.assertTrue(verify_scored_proof(bytes.fromhex(result["hit"]["proof_hex"]), context, 2**256))
            self.assertGreater(result["work"]["sphere_nodes"], 0)
            self.assertEqual(result["work"]["reduction_calls"], reducer.calls)
            if policy == "reuse":
                subtotal = result["acquisition"]["work_through_first_score"]
                self.assertEqual(subtotal, result["work"])
                self.assertEqual(subtotal["score_hashes"], 1)

    def test_streaming_first_all_and_paid_reuse(self):
        # Controlled matrices isolate policy decisions; actual-header binding is tested above.
        for policy in ("first", "all", "reuse"):
            reducer = ExactReducer()
            with patch.object(LabHeader, "matrix", return_value=[[0, 0, 0]]):
                result = run_lattice_policy(self.headers, policy, 0, reducer)
            self.assertEqual(result["reason"], "family-exhausted")
            if policy == "all":
                self.assertGreater(result["work"]["score_hashes"], 8)
                self.assertEqual(reducer.calls, 8)
            elif policy == "first":
                self.assertEqual(result["work"]["score_hashes"], 8)
                self.assertEqual(reducer.calls, 8)
            else:
                self.assertEqual(reducer.calls, 1)
                self.assertEqual(result["work"]["reuse_checks"], 7)
                self.assertEqual(result["work"]["score_hashes"], 8)

    def test_warm_cache_rescores_and_keeps_cold_cost(self):
        reducer, cache = ExactReducer(), CandidateCache()
        cold = run_lattice_policy(self.headers, "cache-all", 0, reducer, cache=cache)
        warm = run_lattice_policy(self.headers, "cache-all", 0, reducer, cache=cache)
        self.assertEqual(cold["scores"], warm["scores"])
        self.assertEqual(warm["work"]["reduction_calls"], 0)
        self.assertEqual(warm["work"]["sphere_nodes"], 0)
        self.assertEqual(warm["work"]["cache_hits"], 8)
        self.assertGreater(warm["work"]["cache_read_checks"], 0)
        self.assertGreater(cold["work"]["reduction_calls"]+warm["work"]["reduction_calls"], 0)
        self.assertEqual(warm["work"]["headers"], 8)

    def test_common_caps_and_last_score_hit(self):
        with patch.object(LabHeader, "matrix", return_value=[[0, 0, 0]]):
            for budget, reason in [(LatticeBudget(nodes=1), "sphere-node-limit"),
                                   (LatticeBudget(reductions=1), "reduction-limit"),
                                   (LatticeBudget(scores=1), "score-limit"),
                                   (LatticeBudget(proofs_per_instance=1), "sphere-proof-limit"),
                                   (LatticeBudget(bits=1), "sphere-arithmetic-limit")]:
                # Complete-pool preparation encounters proof caps; streaming first intentionally does not.
                policy = "cache-all" if reason == "sphere-proof-limit" else "all"
                result = run_lattice_policy(self.headers, policy, 0, ExactReducer(), budget=budget)
                self.assertEqual(result["reason"], reason)
                self.assertLessEqual(result["work"]["sphere_nodes"], budget.nodes)
                self.assertLessEqual(result["work"]["reduction_calls"], budget.reductions)
                self.assertLessEqual(result["work"]["score_hashes"], budget.scores)
            hit = run_lattice_policy(self.headers, "all", 2**256, ExactReducer(), budget=LatticeBudget(scores=1))
            self.assertEqual(hit["reason"], "score-hit")
        one = run_lattice_policy(self.headers[:1], "all", 0, ExactReducer(), budget=LatticeBudget(reductions=1))
        self.assertEqual(one["reason"], "family-exhausted")

    def test_failed_reuse_does_not_secretly_reduce_or_score(self):
        reducer = ExactReducer()
        # The first vector from the zero matrix is excluded by the second matrix.
        with patch.object(LabHeader, "matrix", side_effect=[[[0, 0, 0]], [[1, 1, 1]]]):
            result = run_lattice_policy(self.headers[:2], "reuse", 0, reducer)
        self.assertEqual(reducer.calls, 1)
        self.assertEqual(result["instances"][1]["reason"], "reuse-invalid")
        self.assertEqual(result["work"]["score_hashes"], 1)

    def test_cache_corruption_rejected_before_score_and_partial_pool_not_retained(self):
        cache = CandidateCache()
        key = instance_key(self.base.profile, self.base.matrix())
        cache._entries[key] = ((999, 0, 0),)
        with self.assertRaises(ValueError):
            run_lattice_policy(self.headers[:1], "cache-all", 0, ExactReducer(), cache=cache)
        cache = CandidateCache()
        result = run_lattice_policy(self.headers, "cache-all", 0, ExactReducer(),
                                    budget=LatticeBudget(nodes=1), cache=cache)
        self.assertEqual(result["reason"], "sphere-node-limit")
        self.assertEqual(len(cache), 0)

    def test_invalid_config_rejects_before_reducer(self):
        reducer = ExactReducer()
        for kwargs in ({"budget": False}, {"cache": CandidateCache()}, {"policy": "unknown"}):
            args = {"policy": "first"} | kwargs
            with self.assertRaises(ValueError):
                run_lattice_policy(self.headers, target=0, reducer=reducer, **args)
        for kwargs in ({"nodes": True}, {"reductions": 65}, {"scores": 0}, {"proofs_per_instance": 257}):
            with self.assertRaises(ValueError):
                LatticeBudget(**kwargs)
        with self.assertRaises(ValueError):
            run_lattice_policy([self.base, replace(self.base, parent=bytes([3])*32)], "first", 0, reducer)
        self.assertEqual(reducer.calls, 0)


class CacheTests(unittest.TestCase):
    def test_empty_domains_exact_keys_eviction_and_boundaries(self):
        p = Profile(7, 1, 2, 2)
        cache = CandidateCache(capacity=1)
        empty = {"reason": "domain-exhausted", "proofs": []}
        cache.store(p, [[1, 2]], empty)
        self.assertEqual(cache.get(p, [[1, 2]]), ())
        self.assertIsNone(cache.get(p, [[1, 3]]))
        self.assertIsNone(cache.get(Profile(7, 1, 2, 3), [[1, 2]]))
        self.assertEqual(cache.store(p, [[1, 3]], empty), 1)
        self.assertEqual(len(cache), 1)
        self.assertIsNone(cache.get(p, [[1, 2]]))
        for capacity in (True, 0, 33):
            with self.assertRaises(ValueError):
                CandidateCache(capacity)

    def test_incomplete_invalid_and_duplicate_pools_rejected(self):
        p, a, cache = Profile(7, 1, 2, 2), [[0, 0]], CandidateCache(proof_limit=1)
        for sphere in ({"reason": "node-limit", "proofs": [(1, 0)]},
                       {"reason": "domain-exhausted", "proofs": [(2, 0)]},
                       {"reason": "domain-exhausted", "proofs": [(1, 0), (0, 1)]}):
            with self.assertRaises(ValueError):
                cache.store(p, a, sphere)
        with self.assertRaises(ValueError):
            CandidateCache().store(p, a, {"reason": "domain-exhausted", "proofs": [(1, 0), (1, 0)]})
        self.assertEqual(len(cache), 0)


if __name__ == "__main__":
    unittest.main()
