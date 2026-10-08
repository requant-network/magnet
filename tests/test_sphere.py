from fractions import Fraction
import gc
import json
from pathlib import Path
import random
import unittest
import weakref

from reference.search import exhaustive_solutions
from reference.sis import Profile
from solvers.lattice import LatticeWork, Reduction, kernel_basis, reduce_kernel
from solvers.sphere import coefficient_interval, enumerate_kernel


class SphereTests(unittest.TestCase):
    def test_completed_and_capped_search_release_without_cyclic_gc(self):
        was_enabled = gc.isenabled()
        gc.disable()
        try:
            for budget in ({}, {"node_limit": 1}, {"proof_limit": 1}, {"bit_limit": 1}):
                p = Profile(7, 1, 2, 5)
                reduction = reduce_kernel(p, [[0, 0]])
                observed = weakref.ref(p)
                result = enumerate_kernel(p, [[0, 0]], reduction, **budget)
                del p, reduction, result
                self.assertIsNone(observed())
        finally:
            if was_enabled:
                gc.enable()

    def test_exact_rational_boundary_intervals(self):
        rng = random.Random(20261010)
        for _ in range(1000):
            center = Fraction(rng.randint(-20, 20), rng.randint(1, 10))
            radius = Fraction(rng.randint(0, 50), rng.randint(1, 10))
            low, high = coefficient_interval(center, radius)
            expected = [x for x in range(-30, 31) if (x-center)**2 <= radius]
            self.assertEqual(list(range(low, high+1)), expected)
        self.assertEqual(coefficient_interval(Fraction(1, 2), Fraction(1, 4)), (0, 1))
        self.assertEqual(coefficient_interval(Fraction(-1, 2), Fraction(1, 4)), (-1, 0))
        self.assertEqual(coefficient_interval(0, -1), (1, 0))

    def test_complete_sets_across_rank_and_basis_cases(self):
        rng = random.Random(20261011)
        for p in [Profile(2, 1, 3, 2), Profile(7, 2, 3, 5), Profile(17, 2, 4, 8)]:
            for index in range(16):
                matrix = [[rng.randrange(p.q) for _ in range(p.m)] for _ in range(p.n)]
                if index == 0:
                    matrix = [[0]*p.m for _ in range(p.n)]
                elif index == 1:
                    matrix = [[0] + row[1:] for row in matrix]
                reduced = reduce_kernel(p, matrix)
                result = enumerate_kernel(p, matrix, reduced)
                self.assertEqual(result["reason"], "domain-exhausted")
                self.assertEqual(set(result["proofs"]), set(exhaustive_solutions(p, matrix)))
                self.assertEqual(len(result["proofs"]), len(set(result["proofs"])))
                initial, rank = kernel_basis(p, matrix)
                identity = tuple(tuple(int(i == j) for j in range(p.m)) for i in range(p.m))
                raw = Reduction(initial, initial, identity, rank, "step-limit", LatticeWork())
                self.assertEqual(enumerate_kernel(p, matrix, raw)["proofs"], result["proofs"])

    def test_frozen_probe_miss_is_recovered_completely(self):
        fixture = json.loads((Path(__file__).parent / "vectors/lattice-miss-v1.json").read_text())
        p = Profile(**fixture["profile"])
        from reference.sis import expand_matrix
        matrix = expand_matrix(p, bytes.fromhex(fixture["seed"]))
        reduction = reduce_kernel(p, matrix)
        result = enumerate_kernel(p, matrix, reduction)
        self.assertEqual(result["reason"], "domain-exhausted")
        self.assertIn(tuple(fixture["accepted_vector"]), result["proofs"])

    def test_caps_are_distinct_from_completed_empty_space(self):
        p, matrix = Profile(7, 1, 2, 5), [[0, 0]]
        reduction = reduce_kernel(p, matrix)
        with self.assertRaises(ValueError):
            enumerate_kernel(None, matrix, reduction)
        full = enumerate_kernel(p, matrix, reduction)
        at_limit = enumerate_kernel(p, matrix, reduction, node_limit=full["work"]["nodes"], proof_limit=len(full["proofs"]))
        self.assertEqual(at_limit["reason"], "domain-exhausted")
        self.assertEqual(enumerate_kernel(p, matrix, reduction, node_limit=1)["reason"], "node-limit")
        limited = enumerate_kernel(p, matrix, reduction, proof_limit=1)
        self.assertEqual(limited["reason"], "proof-limit")
        self.assertEqual(len(limited["proofs"]), 1)
        self.assertEqual(enumerate_kernel(p, matrix, reduction, bit_limit=1)["reason"], "arithmetic-limit")
        p, matrix = Profile(7, 1, 1, 1), [[1]]
        self.assertEqual(enumerate_kernel(p, matrix, reduce_kernel(p, matrix))["proofs"], [])

    def test_invalid_budgets_and_certificate_rejected(self):
        p, matrix = Profile(7, 1, 2, 5), [[1, 2]]
        reduction = reduce_kernel(p, matrix)
        for budget in [{"node_limit": True}, {"node_limit": 0}, {"proof_limit": 100001}, {"bit_limit": 4097}]:
            with self.assertRaises(ValueError):
                enumerate_kernel(p, matrix, reduction, **budget)
        reduction.transform = ((1, 0), (0, 1))
        with self.assertRaises(ValueError):
            enumerate_kernel(p, matrix, reduction)


if __name__ == "__main__":
    unittest.main()
