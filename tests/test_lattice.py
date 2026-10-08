"""Certificates, rank-deficient kernels, exact LLL inequalities and heuristic misses."""
from dataclasses import replace
import itertools
import json
from pathlib import Path
import random
import unittest

from reference.ball import BallSearch
from reference.sis import Profile, expand_matrix, verify
from solvers.lattice import LatticeWork, Reduction, kernel_basis, probe_basis, reduce_kernel
from solvers.lattice_audit import audit_certificate, determinant, reduced_inequalities


class LatticeTests(unittest.TestCase):
    def test_arithmetic_cap_after_committed_swap_preserves_lattice(self):
        p, matrix = Profile(17, 2, 4, 8), [[1, 0, 7, 8], [0, 1, 8, 7]]
        partial = reduce_kernel(p, matrix, bit_limit=9)
        self.assertEqual(partial.reason, "arithmetic-limit")
        self.assertGreater(partial.work.swaps + partial.work.size_reductions, 0)
        self.assertFalse(audit_certificate(p, matrix, partial)["lll_reduced"])

    def test_lll_reduced_basis_probe_can_miss_existing_solution(self):
        fixture = json.loads((Path(__file__).parent/'vectors/lattice-miss-v1.json').read_text(encoding='utf-8'))
        p = Profile(**fixture['profile'])
        matrix = expand_matrix(p, bytes.fromhex(fixture['seed']))
        basis = tuple(map(tuple, fixture['reduced_basis']))
        identity = tuple(tuple(int(i == j) for j in range(p.m)) for i in range(p.m))
        certificate = Reduction(basis, basis, identity, fixture['rank'], 'lll-reduced', LatticeWork())
        self.assertTrue(audit_certificate(p, matrix, certificate)['lll_reduced'])
        self.assertTrue(verify(p, matrix, fixture['accepted_vector']))
        probe = probe_basis(p, matrix, certificate)
        self.assertEqual(probe['reason'], 'probe-exhausted')
        self.assertEqual(probe['proofs'], [])
        self.assertEqual(probe['min_norm2'], 16)

    def test_kernel_rank_and_noninitial_pivots(self):
        cases = [(Profile(3, 2, 3, 2), [[0, 2, 1], [0, 1, 2]], 1),
                 (Profile(7, 2, 3, 5), [[0, 0, 0], [0, 0, 0]], 0),
                 (Profile(7, 3, 2, 5), [[1, 0], [0, 1], [1, 1]], 2),
                 (Profile(2, 1, 3, 3), [[1, 1, 0]], 1)]
        for p, matrix, rank in cases:
            with self.subTest(profile=p):
                basis, found_rank = kernel_basis(p, matrix)
                self.assertEqual(found_rank, rank)
                self.assertEqual(abs(determinant(basis)), p.q**rank)
                self.assertTrue(all(sum(a*x for a, x in zip(row, b)) % p.q == 0
                                    for b in basis for row in matrix))
                reduction = reduce_kernel(p, matrix)
                self.assertEqual(reduction.reason, "lll-reduced")
                self.assertTrue(audit_certificate(p, matrix, reduction)["lll_reduced"])

    def test_exact_small_space_outputs_are_oracle_subset(self):
        rng = random.Random(20261010)
        for q, width in itertools.product((2, 3, 7, 17), range(1, 6)):
            p = Profile(q, 2, width, min(5, q*q-1))
            for _ in range(3):
                matrix = [[rng.randrange(q) for _ in range(width)] for _ in range(2)]
                reduction = reduce_kernel(p, matrix)
                audit_certificate(p, matrix, reduction)
                result = probe_basis(p, matrix, reduction)
                oracle = set(BallSearch(p, matrix).solutions())
                self.assertLessEqual(set(result["proofs"]), oracle)
                self.assertTrue(set(result["basis_proofs"]) <= set(result["proofs"]))
                self.assertEqual(result["proposals"], width+8*(width*(width-1)//2))

    def test_exact_caps_and_arithmetic_partial_certificate(self):
        p, matrix = Profile(7, 1, 3, 5), [[1, 2, 3]]
        full = reduce_kernel(p, matrix)
        capped = [reduce_kernel(p, matrix, step_limit=1),
                  reduce_kernel(p, matrix, reduction_limit=1),
                  reduce_kernel(p, matrix, bit_limit=1)]
        self.assertEqual([r.reason for r in capped], ["step-limit", "reduction-limit", "arithmetic-limit"])
        for result in capped:
            self.assertFalse(audit_certificate(p, matrix, result)["lll_reduced"])
        exact = reduce_kernel(p, matrix, step_limit=full.work.steps,
                              reduction_limit=full.work.size_reductions)
        self.assertEqual(exact.reason, "lll-reduced")
        self.assertEqual(exact.basis, full.basis)
        self.assertEqual(probe_basis(p, matrix, full, proposal_limit=1)["reason"], "proposal-limit")
        proposals = probe_basis(p, matrix, full)["proposals"]
        self.assertEqual(probe_basis(p, matrix, full, proposal_limit=proposals)["reason"], "probe-exhausted")

    def test_certificate_detects_tampering(self):
        p, matrix = Profile(7, 1, 3, 5), [[1, 2, 3]]
        reduction = reduce_kernel(p, matrix)
        identity = tuple(tuple(int(i==j) for j in range(p.m)) for i in range(p.m))
        corruptions = [replace(reduction, rank=0), replace(reduction, transform=identity),
                       replace(reduction, transform=((2, 0, 0), (0, 1, 0), (0, 0, 1))),
                       replace(reduction, basis=reduction.initial_basis),
                       replace(reduction, initial_basis=identity), replace(reduction, reason="unknown")]
        for corrupt in corruptions:
            with self.assertRaises(ValueError):
                audit_certificate(p, matrix, corrupt)
        self.assertFalse(reduced_inequalities(((1, 0), (2, 1))))
        self.assertEqual(determinant(((0, 2), (3, 4))), -6)
        self.assertEqual(determinant(((1, 2), (2, 4))), 0)
        self.assertEqual(determinant(((7,),)), 7)

    def test_half_integer_size_reduction_and_determinism(self):
        for q in (2, 3, 65521):
            p, matrix = Profile(q, 1, 2, min(5, q*q-1)), [[1, 1]]
            first, second = reduce_kernel(p, matrix), reduce_kernel(p, matrix)
            self.assertEqual(first, second)
            self.assertTrue(audit_certificate(p, matrix, first)["lll_reduced"])
            self.assertIn((1, -1), probe_basis(p, matrix, first)["proofs"])

    def test_parameters_and_shapes(self):
        p, matrix = Profile(7, 1, 3, 5), [[1, 2, 3]]
        for key in ("step_limit", "reduction_limit", "bit_limit"):
            for value in (0, False, 10_001):
                with self.assertRaises(ValueError):
                    reduce_kernel(p, matrix, **{key: value})
        for profile, bad in [(None, []), (p, [[7, 2, 3]]), (p, [[1, 2]]),
                             (Profile(7, 1, 17, 1), [[0]*17])]:
            with self.assertRaises(ValueError):
                reduce_kernel(profile, bad)
        result = reduce_kernel(p, matrix)
        for bad in (None, replace(result, basis=None), replace(result, basis=((True, 0, 1),)*3)):
            with self.assertRaises(ValueError):
                probe_basis(p, matrix, bad)
        with self.assertRaises(ValueError):
            audit_certificate(p, matrix, None)


if __name__ == "__main__":
    unittest.main()
