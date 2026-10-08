from dataclasses import asdict, replace
from fractions import Fraction
import json
import gc
import math
import random
import unittest
import weakref
from unittest.mock import patch

from reference.header import LabHeader
from reference.pool_campaign import PoolBudget, joint_headers, run_pool_campaign
from reference.search import exhaustive_solutions
from reference.sis import Profile, verify
from scripts.portfolio_worker import decode
from scripts.portfolio_survey import audit_snapshot, summarize
from solvers.blockwise import gram_schmidt, multiply, primitive_completion, projected_shortest
from solvers.lattice_audit import determinant
from solvers.portfolio import gauss_sieve, sparse_probe


class TinySolver:
    def __init__(self):
        self.calls = 0

    def acquire(self, p, matrix, nodes, proofs):
        self.calls += 1
        vectors = sorted(exhaustive_solutions(p, matrix))[:proofs]
        return {"proofs": vectors, "work": {"nodes": 1}, "reason": "test-fixture-not-cost-model"}


class PoolTests(unittest.TestCase):
    def setUp(self):
        self.base = LabHeader(bytes(32), bytes([1])*32, bytes([2])*32, 1, 100, 0, Profile(7, 1, 3, 8))

    def test_paid_pool_and_fifo_across_stages(self):
        solver = TinySolver()
        result = run_pool_campaign([[self.base]]*8, "pool-fallback", 0, solver, capacity=4, combine=False)
        self.assertEqual(solver.calls, 1)
        self.assertEqual(result["work"]["acquisitions"], 1)
        self.assertGreater(result["work"]["pool_evictions"], 0)
        self.assertEqual(result["work"]["pool_checks"], 7*4)
        self.assertEqual(len(result["pool"]), 4)
        self.assertEqual(len(result["stages"]), 8)

    def test_combination_attempts_are_paid_and_verified(self):
        with patch.object(LabHeader, "matrix", return_value=[[0, 0, 0]]):
            result = run_pool_campaign([[self.base]]*2, "pool-fallback", 0, TinySolver(), capacity=4)
        self.assertEqual(result["work"]["combination_checks"], 12)
        self.assertTrue(all(verify(self.base.profile, [[0, 0, 0]], sample["vector"]) for sample in result["scores"]))
        self.assertEqual(len({tuple(x["vector"]) for x in result["scores"] if x["stage"] == 1}),
                         len([x for x in result["scores"] if x["stage"] == 1]))

    def test_global_limits_and_final_hit(self):
        budget = PoolBudget(scores=1, checks=1, acquisitions=1, nodes=1)
        result = run_pool_campaign([[self.base]]*3, "pool-all", 2**256, TinySolver(), budget=budget)
        self.assertEqual(result["stages"][0]["reason"], "score-hit")
        self.assertEqual(result["stages"][1]["reason"], "score-limit")
        self.assertEqual(result["stages"][2]["reason"], "not-visited")
        self.assertEqual(result["reason"], "score-limit")
        result = run_pool_campaign([[self.base]]*3, "pool-all", 0, TinySolver(), budget=replace(budget, scores=100))
        self.assertEqual(result["work"]["acquisitions"], 1)
        self.assertEqual(result["reason"], "check-limit")

    def test_new_context_and_joint_surface(self):
        family = joint_headers(self.base)
        self.assertEqual(len({h.encode() for h in family}), 8)
        self.assertEqual(len({h.payload for h in family}), 2)
        stages = [family, joint_headers(replace(self.base, parent=bytes([9])*32, height=2))]
        result = run_pool_campaign(stages, "pool-all", 2**256, TinySolver())
        self.assertEqual(len(result["stages"]), 2)
        self.assertTrue(all(s["hit"] is not None for s in result["stages"]))
        for bad in (dict(nonces=True), dict(nonces=8, times=8), dict(nonces=2)):
            base = replace(self.base, nonce=2**64-1) if bad == dict(nonces=2) else self.base
            with self.assertRaises(ValueError):
                joint_headers(base, **bad)

    def test_reject_configuration_before_solver(self):
        solver = TinySolver()
        for kwargs in (dict(capacity=True), dict(combine=1), dict(budget="bad")):
            with self.assertRaises(ValueError):
                run_pool_campaign([[self.base]], "pool-all", 1, solver, **kwargs)
        with self.assertRaises(ValueError):
            run_pool_campaign([[self.base, replace(self.base, height=2)]], "pool-all", 1, solver)
        self.assertEqual(solver.calls, 0)

    def test_worker_strict_surface(self):
        request = {"version": "WXP1", "backend": "lll99", "policy": "pool-all", "target": "1",
                   "stages": [[self.base.encode().hex()]], "capacity": 4, "combine": True,
                   "budget": asdict(PoolBudget()), "seed": 1}
        self.assertEqual(decode(json.dumps(request).encode())[1][0][0], self.base)
        for key, value in (("target", "01"), ("capacity", True), ("seed", -1), ("backend", "fake"),
                           ("stages", [[]]), ("combine", 1)):
            with self.assertRaises(ValueError):
                decode(json.dumps({**request, key: value}).encode())

    def test_resource_failure_is_censored_and_not_zero_work(self):
        self.assertEqual(audit_snapshot({"status": "memory-error"}, [], None)["scores_checked"], 0)
        failed = {"window": {"logical_work_known": False, "snapshot": {"status": "memory-error"},
                              "outcome": "worker-memory-error", "resource": {"elapsed_ns": 100, "peak_job_commit_bytes": 64}}}
        result = summarize([failed])
        self.assertEqual(result["completed_campaigns"], 0)
        self.assertEqual(result["all_attempt_elapsed_ns"], 100)
        self.assertIsNone(result["all_attempt_work_per_hit"])

    def test_bkz_one_node_boundary_is_a_partial_search_not_worker_error(self):
        # The ordinary gate has no FLINT dependency. Isolate the boundary decision,
        # retaining actual kernel construction, certificate audit and sphere search.
        import types
        from solvers.portfolio import Portfolio
        from solvers.lattice import reduce_kernel
        reduced = reduce_kernel(self.base.profile, self.base.matrix())
        class Matrix:
            def __init__(self, _):
                pass
            def lll(self, **_):
                return self, self
            def tolist(self):
                return reduced.basis
        class Transform(Matrix):
            def tolist(self):
                return reduced.transform
        class Input(Matrix):
            def lll(self, **_):
                return Matrix(None), Transform(None)
        solver = Portfolio.__new__(Portfolio)
        solver.backend, solver.seed, solver.calls = "bkz8", 1, 0
        with patch.dict("sys.modules", {"flint": types.SimpleNamespace(fmpz_mat=Input)}):
            result = solver.acquire(self.base.profile, self.base.matrix(), 1, 32)
        self.assertEqual(result["work"]["bkz_nodes"], 0)
        self.assertEqual(result["work"]["nodes"], 1)
        self.assertEqual(result["reason"], "node-limit")


class BlockwiseTests(unittest.TestCase):
    def test_random_primitive_completion_preserves_lattice(self):
        rng = random.Random(2026100816)
        for width in range(1, 17):
            for _ in range(20):
                row = tuple(rng.randrange(-10, 11) for _ in range(width))
                if math.gcd(*row) == 1:
                    operation = primitive_completion(row)
                    self.assertEqual(operation[0], row)
                    self.assertEqual(abs(determinant(operation)), 1)
        for row in ((2, 4), (0, 0), (True, 1)):
            with self.assertRaises(ValueError):
                primitive_completion(row)

    def test_projected_svp_finds_improvement_and_censors_limit(self):
        basis = ((10, 0), (1, 1))
        result = projected_shortest(basis, 0, 2, 1000)
        self.assertTrue(result["complete"])
        self.assertIsNotNone(result["coefficients"])
        vector = multiply((result["coefficients"],), basis)[0]
        self.assertEqual(sum(x*x for x in vector), 2)
        self.assertFalse(projected_shortest(basis, 0, 2, 1)["complete"])
        mu, norms = gram_schmidt(basis)
        self.assertEqual(norms, [Fraction(100), Fraction(1)])
        self.assertEqual(mu[1][0], Fraction(1, 10))

    def test_projected_search_releases_gso_without_cyclic_gc(self):
        class WeakList(list):
            pass
        references = []
        def tracked(basis):
            mu, norms = gram_schmidt(basis)
            mu, norms = WeakList(mu), WeakList(norms)
            references.extend((weakref.ref(mu), weakref.ref(norms)))
            return mu, norms
        enabled = gc.isenabled()
        gc.disable()
        try:
            with patch("solvers.blockwise.gram_schmidt", side_effect=tracked):
                for nodes in (1, 1000):
                    projected_shortest(((10, 0), (1, 1)), 0, 2, nodes)
                    self.assertTrue(all(reference() is None for reference in references))
        finally:
            if enabled:
                gc.enable()

    def test_sieve_seeded_valid_bounded_and_partial(self):
        p, a, basis = Profile(7, 1, 3, 8), [[0, 0, 0]], ((1, 0, 0), (0, 1, 0), (0, 0, 1))
        first = gauss_sieve(p, a, basis, 1000, 20, 1)
        self.assertEqual(first, gauss_sieve(p, a, basis, 1000, 20, 1))
        self.assertTrue(first["proofs"])
        self.assertFalse(first["complete"])
        self.assertLessEqual(first["work"]["nodes"], 1000)
        self.assertTrue(all(verify(p, a, x) for x in first["proofs"]))

    def test_sparse_screen_matches_bounded_support_domain(self):
        p, a = Profile(7, 1, 3, 8), [[3, 0, 5]]
        expected = {x for x in exhaustive_solutions(p, a) if sum(v != 0 for v in x) <= 2}
        result = sparse_probe(p, a, 1000, 256)
        self.assertEqual(set(result["proofs"]), expected)
        self.assertEqual(result["reason"], "sparse-support-exhausted")
        self.assertEqual(sparse_probe(p, a, 1, 256)["reason"], "node-limit")
