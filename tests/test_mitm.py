import hashlib
import unittest
from unittest.mock import patch

from reference.mitm import MitmSearch, run_mitm
from reference.search import exhaustive_solutions
from reference.sis import Profile, expand_matrix, verify
from reference.strategies import _score_message


class MitmTests(unittest.TestCase):
    def test_exact_sets_for_odd_even_and_one_coordinate(self):
        for m in range(1, 6):
            for index in range(8):
                p = Profile(7, 2, m, 8)
                a = expand_matrix(p, index.to_bytes(32, "little"))
                search = MitmSearch(p, a)
                proofs = list(search.solutions())
                self.assertEqual(set(proofs), set(exhaustive_solutions(p, a)))
                self.assertEqual(len(proofs), len(set(proofs)))
                self.assertTrue(all(verify(p, a, x) for x in proofs))
                self.assertEqual(search.reason, "domain-exhausted")

    def test_colliding_buckets_do_not_overwrite_vectors(self):
        p, a = Profile(7, 1, 4, 4), [[0, 0, 0, 0]]
        search = MitmSearch(p, a)
        proofs = list(search.solutions())
        self.assertEqual(set(proofs), set(exhaustive_solutions(p, a)))
        self.assertEqual(search.work.table_buckets, 1)
        self.assertGreater(search.work.table_entries, 1)
        self.assertNotIn((0, 0, 0, 0), proofs)
        self.assertIn((0, 0, 1, -1), proofs)
        self.assertIn((1, 0, 0, 0), proofs)

    def test_norm_boundary_and_modular_wrap(self):
        p, a = Profile(7, 1, 3, 5), [[1, 2, 3]]
        search = MitmSearch(p, a)
        proofs = list(search.solutions())
        self.assertEqual(set(proofs), set(exhaustive_solutions(p, a)))
        self.assertIn((2, -1, 0), proofs)  # Exact norm boundary and zero dot product.
        self.assertIn((1, 0, 2), proofs)   # Dot product q, not integer zero.

    def test_memory_and_collision_caps_are_explicit(self):
        p, a = Profile(7, 1, 4, 4), [[0] * 4]
        table_capped = MitmSearch(p, a, table_limit=1)
        self.assertEqual(list(table_capped.solutions()), [])
        self.assertEqual(table_capped.reason, "table-limit")
        self.assertEqual(table_capped.work.table_entries, 1)
        self.assertEqual(table_capped.work.right_proposals, 0)
        pair_capped = MitmSearch(p, a, pair_limit=1)
        partial = list(pair_capped.solutions())
        self.assertEqual(pair_capped.reason, "pair-limit")
        self.assertEqual(pair_capped.work.join_pairs, 1)
        self.assertTrue(all(verify(p, a, x) for x in partial))

    def test_interruption_and_one_shot_consumption(self):
        search = MitmSearch(Profile(7, 1, 2, 4), [[0, 0]])
        iterator = search.solutions()
        next(iterator)
        iterator.close()
        self.assertEqual(search.reason, "interrupted")
        with self.assertRaises(ValueError):
            search.solutions()

    def test_close_before_first_next_records_interruption(self):
        search = MitmSearch(Profile(7, 1, 2, 4), [[0, 0]])
        iterator = search.solutions()
        iterator.close()
        self.assertEqual(search.reason, "interrupted")
        self.assertEqual(search.work.left_proposals, 0)
        self.assertEqual(list(iterator), [])
        with self.assertRaises(ValueError):
            search.solutions()

    def test_no_solution_is_only_claimed_after_exhaustion(self):
        search = MitmSearch(Profile(7, 1, 1, 1), [[1]])
        self.assertEqual(list(search.solutions()), [])
        self.assertEqual(search.reason, "domain-exhausted")
        self.assertEqual(search.work.left_proposals, 1)
        self.assertEqual(search.work.right_proposals, 3)

    def test_score_stop_includes_preprocessing_and_strict_boundary(self):
        p, seed, a = Profile(7, 1, 2, 4), bytes(32), ((0, 0),)
        search = MitmSearch(p, a)
        first = list(search.solutions())[0]
        score = int.from_bytes(hashlib.sha256(_score_message(p, seed, first)).digest(), "big")
        with patch("reference.mitm.expand_matrix", return_value=a):
            hit = run_mitm(p, seed, target=score + 1)
            missed = run_mitm(p, seed, target=score)
            all_proofs = run_mitm(p, seed, target=0)
        self.assertEqual(hit["reason"], "score-hit")
        self.assertEqual(hit["proofs"], [first])
        self.assertEqual(hit["work"]["left_proposals"], 5)
        self.assertEqual(hit["work"]["table_entries"], 3)
        self.assertNotEqual(missed["proofs"], [first])
        self.assertEqual(set(all_proofs["proofs"]), set(exhaustive_solutions(p, a)))

    def test_input_and_half_box_bounds(self):
        p, a = Profile(7, 1, 2, 4), [[0, 0]]
        for options in ({"table_limit": 0}, {"table_limit": True}, {"table_limit": 100_001},
                        {"pair_limit": 0}, {"pair_limit": True}, {"pair_limit": 1_000_001}):
            with self.assertRaises(ValueError):
                MitmSearch(p, a, **options)
        for profile, matrix in ((None, a), (p, [[7, 0]]), (p, [[0]]),
                                (Profile(65521, 1, 128, 100), [[0] * 128])):
            with self.assertRaises(ValueError):
                MitmSearch(profile, matrix)
        for options in ({"target": True}, {"target": -1}, {"target": 2**256 + 1}):
            with self.assertRaises(ValueError):
                run_mitm(p, bytes(32), **options)
        with self.assertRaises(ValueError):
            run_mitm(p, b"short")


if __name__ == "__main__":
    unittest.main()
