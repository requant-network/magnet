import itertools
import unittest

from reference.sis import Profile, verify
from reference.small_coefficients import candidates, dense, direction, refresh, search, templates
from scripts.small_coefficient_audits import oracle


class SmallCoefficientTests(unittest.TestCase):
    def test_complete_box_order_and_norm_boundaries(self):
        for m, b2, bound in itertools.product(range(1, 6), (1, 3, 4, 5, 8, 9, 12), (1, 2)):
            p = Profile(17, 1, m, b2)
            patterns, _ = templates(p, bound)
            actual = [dense(m, pos, values) for pos, values in candidates(m, patterns)]
            self.assertEqual(actual, oracle(p, ((0,)*m,), bound))
            self.assertEqual(len(actual), len(set(actual)))

    def test_maximum_domain_and_late_support(self):
        p = Profile(65521, 64, 16, 12)
        patterns, _ = templates(p, 2)
        vectors = [dense(16, pos, values) for pos, values in candidates(16, patterns)]
        self.assertEqual(len(vectors), 18912)
        self.assertIn((0,)*13+(2, 2, 2), vectors[-32:])

    def test_nonunit_finds_missing_solution_and_keeps_legal_scalar_copy(self):
        p = Profile(17, 1, 2, 5)
        self.assertEqual(search(p, ((1, 2),), bound=1)['proofs'], [])
        self.assertEqual(search(p, ((1, 2),), bound=2)['proofs'], [(2, -1)])
        copied = search(Profile(17, 1, 2, 8), ((1, 1),), bound=2)
        self.assertEqual(copied['proofs'], [(1, -1), (2, -2)])
        self.assertEqual(copied['work']['primitive_returned'], 1)
        self.assertEqual(copied['work']['nonprimitive_returned'], 1)
        self.assertEqual(direction((1, -1)), direction((2, -2)))

    def test_exhaustive_small_matrices_match_verifier(self):
        p = Profile(3, 1, 3, 8)
        for row in itertools.product(range(3), repeat=3):
            expected = [v for v in oracle(p, (row,), 2) if verify(p, (row,), v)]
            result = search(p, (row,), bound=2)
            self.assertEqual(result['proofs'], expected)
            self.assertTrue(result['all_proofs_returned'])

    def test_exact_cap_and_simultaneous_output_exhaustion(self):
        p, matrix = Profile(7, 1, 1, 4), ((0,),)
        exact = search(p, matrix, bound=2, candidate_limit=2, proof_limit=2)
        self.assertEqual(exact['reason'], 'proof-limit')
        self.assertTrue(exact['domain_exhausted'])
        self.assertTrue(exact['all_proofs_returned'])
        self.assertFalse(exact['candidate_censored'])
        short = search(p, matrix, bound=2, candidate_limit=1, proof_limit=1)
        self.assertEqual(short['work']['screened'], 1)
        self.assertEqual(short['unchecked_domain_suffix'], 1)
        self.assertEqual(short['accepted_tail_discarded'], 0)
        self.assertFalse(short['all_proofs_returned'])

    def test_candidate_miss_cap_and_pattern_census(self):
        p, matrix = Profile(17, 2, 3, 8), ((1, 2, 4), (3, 5, 7))
        result = search(p, matrix, bound=2, candidate_limit=4)
        self.assertEqual(result['reason'], 'candidate-limit')
        self.assertTrue(result['candidate_censored'])
        self.assertEqual(sum(c['tested'] for c in result['coefficients'].values()), 4)
        self.assertEqual(sum(c['accepted'] for c in result['coefficients'].values()), len(result['proofs']))
        self.assertEqual(result['work']['row_reductions'], 4)
        self.assertEqual(result['work']['matrix_terms'], 4)

    def test_invalid_inputs_are_rejected(self):
        p = Profile(17, 1, 2, 5)
        for kwargs in ({'bound': True}, {'bound': 3}, {'bound': 0}, {'bound': 2, 'candidate_limit': True},
                       {'bound': 2, 'candidate_limit': 20001}, {'bound': 2, 'proof_limit': 257}):
            with self.assertRaises(ValueError): search(p, ((1, 2),), **kwargs)
        for profile in (Profile(17, 1, 17, 5), Profile(17, 1, 2, 13)):
            with self.assertRaises(ValueError): search(profile, ((0,)*profile.m,), bound=2)
        for matrix in (((1, True),), ((1, 17),), ((1,),)):
            with self.assertRaises(ValueError): search(p, matrix, bound=2)

    def test_refresh_pays_rejection_and_reports_scalar_direction_overlap(self):
        p = Profile(17, 2, 2, 8)
        vectors = [(1, -1), (2, -2)]
        kept = refresh(p, ((1, 1), (2, 2)), vectors, vectors)
        self.assertEqual(kept['acquired_overlap'], 2)
        self.assertEqual(kept['directions']['retained'], 1)
        self.assertEqual(kept['new_directions'], 0)
        self.assertEqual(kept['work']['matrix_terms'], 8)
        self.assertEqual(kept['work']['validation_matrix_entries'], 20)
        self.assertEqual(kept['work']['validation_vector_entries'], 10)
        rejected = refresh(p, ((1, 2), (2, 2)), vectors, [])
        self.assertEqual(rejected['carry_verdicts'], [False, False])
        self.assertEqual(rejected['work']['matrix_terms'], 4)
        self.assertEqual(rejected['work']['row_reductions'], 2)
        self.assertEqual(rejected['retained'], [])
        empty = refresh(p, ((0, 0), (0, 0)), [], [])
        self.assertEqual(empty['work']['validation_matrix_entries'], 4)
        self.assertEqual(empty['work']['validation_vector_entries'], 2)

    def test_refresh_stable_union_overflow_and_invalid_acquisition(self):
        p = Profile(17, 1, 2, 8)
        result = refresh(p, ((0, 0),), [(1, 0)], [(1, 0), (0, 1)], pool_limit=1)
        self.assertEqual(result['retained'], [(1, 0)])
        self.assertEqual(result['distinct_overflow'], 1)
        self.assertEqual(result['new_directions'], 1)
        for previous, acquired in (([(1, 0), (1, 0)], []), ([], [(0, 0)]), ([], [(3, 0)])):
            with self.assertRaises(ValueError): refresh(p, ((0, 0),), previous, acquired)
        with self.assertRaises(ValueError): refresh(p, ((1, 2),), [], [(1, 0)])


if __name__ == '__main__':
    unittest.main()
