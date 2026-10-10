"""Exhaustive field models and paid recipient-certificate transfer regressions."""

from dataclasses import replace
from fractions import Fraction
import itertools
import unittest

from reference.header import LabHeader
from reference.kernel_reuse import adaptive_transfer_bound, transfer_probabilities
from reference.preparation_campaign import run_preparation
from reference.sis import Profile, verify
from solvers.lattice import LatticeWork, kernel_basis, reduce_kernel
from solvers.lattice_audit import audit_certificate
from solvers.portfolio import PreparedLattice
from solvers.sphere import enumerate_kernel


class ExactSolver:
    backend = 'lll75'

    def prepare(self, profile, matrix, nodes):
        reduction = reduce_kernel(profile, matrix)
        return PreparedLattice(profile, tuple(map(tuple, matrix)), reduction, {'bkz_nodes': 0}, {},
                               audit_certificate(profile, matrix, reduction))

    def search_prepared(self, prepared, nodes, proofs, *, seed):
        return enumerate_kernel(prepared.profile, prepared.matrix, prepared.reduction,
                                node_limit=nodes, proof_limit=proofs)


class KernelReuseTests(unittest.TestCase):
    def test_every_q3_donor_receiver_pair_including_rank_zero(self):
        for n in (1, 2):
            p = Profile(3, n, 2, 2)
            matrices = [tuple(tuple(flat[i*2:(i+1)*2]) for i in range(n))
                        for flat in itertools.product(range(3), repeat=n*2)]
            bases = [kernel_basis(p, a) for a in matrices]
            for donor, rank in bases:
                contained = sum(all(sum(a*x for a, x in zip(row, vector)) % p.q == 0
                                    for row in receiver for vector in donor) for receiver in matrices)
                equal = sum(b == donor and r == rank for b, r in bases)
                self.assertEqual((Fraction(contained, len(matrices)), Fraction(equal, len(matrices))),
                                 transfer_probabilities(p, rank))
            for vector in ((1, 0), (0, 1), (1, 1), (1, -1)):
                self.assertEqual(Fraction(sum(verify(p, a, vector) for a in matrices), len(matrices)),
                                 Fraction(1, p.q**n))

    def test_same_kernel_different_matrix_and_proper_subset_are_distinct(self):
        p = Profile(3, 1, 2, 2)
        reduction = reduce_kernel(p, [[1, 1]])
        self.assertEqual(kernel_basis(p, [[1, 1]]), kernel_basis(p, [[2, 2]]))
        audit_certificate(p, [[2, 2]], reduction)
        self.assertTrue(all(sum(a*x for a, x in zip([0, 0], v)) % 3 == 0 for v in reduction.basis))
        with self.assertRaises(ValueError):
            audit_certificate(p, [[0, 0]], reduction)

    def test_adaptive_bound_and_invalid_arguments(self):
        p = Profile(17, 2, 8, 8)
        self.assertEqual(adaptive_transfer_bound(p, 8, 256), Fraction(2048, 17**12))
        self.assertEqual(adaptive_transfer_bound(p, 0, 256), 0)
        self.assertEqual(adaptive_transfer_bound(Profile(3, 2, 2, 2), 8, 256), 1)
        for rank in (-1, True, 3):
            with self.assertRaises(ValueError):
                transfer_probabilities(p, rank)
        with self.assertRaises(ValueError):
            adaptive_transfer_bound(p, True, 256)

    def test_campaign_preserves_outputs_and_pays_fingerprinting(self):
        p = Profile(3, 1, 2, 2)
        base = LabHeader(bytes(32), bytes([1])*32, bytes([2])*32, 1, 100, 0, p)
        headers = tuple(replace(base, nonce=i) for i in range(8))
        cold = run_preparation(headers, 'cold', ExactSolver())
        warm = run_preparation(headers, 'kernel-cache', ExactSolver())
        self.assertEqual([s['proofs'] for s in cold['stages']], [s['proofs'] for s in warm['stages']])
        self.assertEqual([s['scores'] for s in cold['stages']], [s['scores'] for s in warm['stages']])
        self.assertEqual(cold['work']['reductions'], 8)
        self.assertEqual(warm['work']['fingerprint_calls'], 8)
        self.assertEqual(warm['work']['reductions']+warm['work']['cache_hits'], 8)
        self.assertGreater(warm['work']['cache_hits'], 0)
        self.assertTrue(all(s['fingerprint_work'] is not None for s in warm['stages']))

    def test_shared_limits_keep_paid_last_generation_and_search(self):
        p = Profile(17, 2, 4, 8)
        base = LabHeader(bytes(32), bytes([1])*32, bytes([2])*32, 1, 100, 0, p)
        headers = tuple(replace(base, nonce=i) for i in range(8))
        capped = run_preparation(headers, 'kernel-cache', ExactSolver(), reductions=1)
        self.assertEqual(capped['reason'], 'reduction-limit')
        self.assertEqual(capped['work']['headers'], len(capped['stages']))
        self.assertIsNone(capped['stages'][-1]['certificate'])
        self.assertEqual(capped['stages'][-1]['search_reason'], 'not-started')
        capped = run_preparation(headers, 'cold', ExactSolver(), nodes=1)
        self.assertEqual(capped['reason'], 'node-limit')
        self.assertEqual(capped['work']['search_nodes'], 1)
        self.assertEqual(capped['work']['headers'], 1)

    def test_context_and_resource_bounds_rejected_before_work(self):
        p = Profile(3, 1, 2, 2)
        base = LabHeader(bytes(32), bytes([1])*32, bytes([2])*32, 1, 100, 0, p)
        for headers, options in (([base, base], {}), ([base, replace(base, network=bytes([3])*32)], {}),
                                 ([base], {'nodes': True}), ([base], {'cache_limit': 0})):
            with self.assertRaises(ValueError):
                run_preparation(headers, 'cold', ExactSolver(), **options)


if __name__ == '__main__':
    unittest.main()
