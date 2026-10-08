import unittest

from reference.reuse import canonical, derive_solutions, matrix_rank, sparse_solutions
from reference.search import exhaustive_solutions
from reference.sis import Profile, expand_matrix, verify


class ReuseTests(unittest.TestCase):
    def test_one_solution_yields_four_distinct_proofs(self):
        p = Profile(17, 1, 2, 80)
        derived, attempts = derive_solutions(p, [[1, 2]], [(4, -2)])
        self.assertEqual(derived, {(2, -1), (4, -2), (6, -3), (8, -4)})
        self.assertEqual(attempts, 4)

    def test_gcd_one_does_not_stop_combinations(self):
        p = Profile(17, 1, 3, 6)
        a = [[1, 1, 1]]
        derived, _ = derive_solutions(p, a, [(1, -1, 0), (0, 1, -1)])
        self.assertIn((1, 0, -1), derived)
        self.assertIn((1, -2, 1), derived)
        self.assertTrue(all(verify(p, a, x) for x in derived))

    def test_invalid_seeds_and_budgets(self):
        p, a = Profile(17, 1, 2, 80), [[1, 2]]
        for seeds in [[(0, 0)], [(-2, 1)], [(1, 0)], [(2, -1)] * 3]:
            with self.assertRaises(ValueError):
                derive_solutions(p, a, seeds)
        with self.assertRaises(ValueError):
            derive_solutions(p, a, [(2, -1)], coefficient_limit=100)
        large = Profile(65521, 1, 1, 65521**2 - 1)
        with self.assertRaisesRegex(ValueError, "budget"):
            derive_solutions(large, [[0]], [(1,)])
        with self.assertRaisesRegex(ValueError, "budget"):
            sparse_solutions(Profile(65521, 1, 128, 65521**2 - 1), [[0] * 128])

    def test_full_rank_can_have_easy_solution(self):
        p, a = Profile(17, 2, 3, 2), [[1, 1, 0], [0, 0, 1]]
        self.assertEqual(matrix_rank(p, a), 2)
        self.assertIn((1, -1, 0), sparse_solutions(p, a)[0])

    def test_sparse_can_miss_a_valid_solution(self):
        p, a = Profile(17, 2, 3, 3), [[1, 1, 0], [0, 1, 1]]
        self.assertEqual(sparse_solutions(p, a)[0], set())
        self.assertEqual(list(exhaustive_solutions(p, a)), [(1, -1, 1)])

    def test_sparse_is_exact_for_support_at_most_two(self):
        for m in [1, 2, 3, 4]:
            p = Profile(7, 2, m, 8)
            for seed in range(10):
                a = expand_matrix(p, seed.to_bytes(32, "little"))
                full = list(exhaustive_solutions(p, a))
                self.assertEqual(sparse_solutions(p, a)[0],
                                 {x for x in full if sum(v != 0 for v in x) <= 2})
                derived, _ = derive_solutions(p, a, full[:2])
                self.assertTrue(derived <= set(full))

    def test_threshold_nesting_on_the_same_matrix(self):
        a = [[1, 2, 3]]
        previous = set()
        for b2 in [1, 2, 4, 8, 16]:
            current = set(exhaustive_solutions(Profile(17, 1, 3, b2), a))
            self.assertTrue(previous <= current)
            previous = current

    def test_rank_and_sign(self):
        p = Profile(7, 2, 3, 8)
        self.assertEqual(matrix_rank(p, [[0, 0, 0], [0, 0, 0]]), 0)
        self.assertEqual(matrix_rank(p, [[1, 2, 3], [2, 4, 6]]), 1)
        self.assertEqual(matrix_rank(p, [[0, 1, 2], [1, 0, 2]]), 2)
        self.assertEqual(canonical((0, -1, 2)), (0, 1, -2))


if __name__ == "__main__":
    unittest.main()
