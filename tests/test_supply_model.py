from fractions import Fraction
from itertools import product
import unittest

from reference.sis import Profile, verify
from reference.supply_model import independent_hit_shortcut, pool_law, score_hit_probability


def enumerate_histogram(profile, pool):
    counts = [0]*(len(pool)+1)
    for flat in product(range(profile.q), repeat=profile.n*profile.m):
        matrix = tuple(flat[i*profile.m:(i+1)*profile.m] for i in range(profile.n))
        counts[sum(verify(profile, matrix, vector) for vector in pool)] += 1
    return tuple(Fraction(c, profile.q**(profile.n*profile.m)) for c in counts)


class SupplyModelTests(unittest.TestCase):
    def test_exact_laws_match_complete_matrix_spaces(self):
        for q, n in ((2, 1), (3, 1), (3, 2), (5, 1)):
            p = Profile(q, n, 2, min(q*q-1, 8))
            pools = [((1, 0),), ((1, 0), (0, 1)), ((1, 0), (0, 1), (1, 1))]
            if q > 2:
                pools += [((1, 0), (2, 0)), ((1, -1), (1, 1))]
            for pool in pools:
                with self.subTest(q=q, n=n, pool=pool):
                    law = pool_law(p, pool)
                    self.assertEqual(law.histogram, enumerate_histogram(p, pool))
                    self.assertEqual(law.mean_valid, Fraction(len(pool), q**n))

    def test_distinct_integer_proofs_can_share_the_same_acceptance_event(self):
        law = pool_law(Profile(7, 1, 2, 8), ((1, 0), (2, 0)))
        self.assertEqual(law.histogram, (Fraction(6, 7), 0, Fraction(1, 7)))
        self.assertEqual(score_hit_probability(law.histogram, 2**255), Fraction(3, 28))
        self.assertEqual(independent_hit_shortcut(Profile(7, 1, 2, 8), 2, 2**255), Fraction(27, 196))

    def test_pairwise_independence_does_not_imply_joint_independence(self):
        p = Profile(7, 1, 2, 8)
        law = pool_law(p, ((1, 0), (0, 1), (1, 1)))
        ranks = dict(law.subset_ranks)
        self.assertTrue(all(ranks[mask] == 2 for mask in (3, 5, 6)))
        self.assertEqual(ranks[7], 2)
        self.assertEqual(law.histogram[2], 0)
        self.assertNotEqual(score_hit_probability(law.histogram, 2**256),
                            independent_hit_shortcut(p, 3, 2**256))

    def test_rank_uses_prime_field_not_real_linear_algebra(self):
        law = pool_law(Profile(2, 1, 2, 3), ((1, -1), (1, 1)))
        self.assertEqual(dict(law.subset_ranks)[3], 1)
        self.assertEqual(law.histogram, (Fraction(1, 2), 0, Fraction(1, 2)))

    def test_independent_basis_and_target_boundaries(self):
        p = Profile(7, 2, 2, 8)
        law = pool_law(p, ((1, 0), (0, 1)))
        previous = Fraction(-1)
        for target in (0, 1, 3, 2**252, 2**255, 2**256):
            actual = score_hit_probability(law.histogram, target)
            self.assertEqual(actual, independent_hit_shortcut(p, 2, target))
            self.assertGreaterEqual(actual, previous)
            previous = actual
        self.assertEqual(score_hit_probability(law.histogram, 2**256), law.any_valid)

    def test_maximum_profile_exact_arithmetic_is_finite(self):
        p = Profile(65521, 64, 128, 65521**2-1)
        pool = tuple(tuple(int(j == i) for j in range(128)) for i in range(6))
        law = pool_law(p, pool)
        self.assertEqual(len(law.subset_ranks), 63)
        self.assertEqual(law.histogram[6], Fraction(1, 65521**384))
        self.assertLessEqual(law.histogram[0].denominator.bit_length(), 6144)
        score_hit_probability(law.histogram, 1)

    def test_input_validation_and_arithmetic_cap(self):
        p = Profile(7, 1, 2, 8)
        invalid = ((), ((0, 0),), ((-1, 0),), ((3, 0),), ((True, 0),),
                   ((1,),), ((1, 0), (1, 0)), ((1, 0),)*7, 'pool')
        for pool in invalid:
            with self.assertRaises(ValueError):
                pool_law(p, pool)
        for budget in (0, True, 250001):
            with self.assertRaises(ValueError):
                pool_law(p, ((1, 0),), arithmetic_budget=budget)
        pool = ((1, 0), (0, 1), (1, 1))
        exact = pool_law(p, pool).rank_arithmetic_units
        self.assertEqual(exact, 27)  # 5 singleton + 13 pair + 9 triple scalar units.
        self.assertEqual(pool_law(p, pool, arithmetic_budget=27).rank_arithmetic_units, 27)
        with self.assertRaisesRegex(ValueError, 'arithmetic cap'):
            pool_law(p, pool, arithmetic_budget=26)
        for target in (-1, True, 2**256+1):
            with self.assertRaises(ValueError):
                score_hit_probability((Fraction(1, 2), Fraction(1, 2)), target)
        for histogram in ((1,), (0, 0), (Fraction(3, 2), Fraction(-1, 2)), (True, 0), (0.5, 0.5)):
            with self.assertRaises(ValueError):
                score_hit_probability(histogram, 1)

    def test_score_helper_bounds_external_fraction_arithmetic(self):
        for histogram in ((1-Fraction(1, 2**8000), Fraction(1, 2**8000)),
                          (2**8000, 0),
                          (Fraction(1, 2**4000), Fraction(1, 3**2600), 0)):
            with self.assertRaisesRegex(ValueError, 'arithmetic bound'):
                score_hit_probability(histogram, 1)


if __name__ == '__main__':
    unittest.main()
