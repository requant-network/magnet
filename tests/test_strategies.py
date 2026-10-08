import hashlib
import struct
import unittest
from unittest.mock import patch

from reference.search import exhaustive_solutions
from reference.sis import Profile, expand_matrix, verify
from reference.strategies import SCORE_DOMAIN, STRATEGIES, _score_message, run_strategy


class StrategyTests(unittest.TestCase):
    def test_full_search_matches_independent_oracle(self):
        for m in (1, 2, 3):
            p = Profile(7, 2, m, 8)
            for index in range(8):
                seed = index.to_bytes(32, "little")
                matrix = expand_matrix(p, seed)
                expected = set(exhaustive_solutions(p, matrix))
                for strategy in ("full-search", "sparse-reuse-full"):
                    result = run_strategy(p, seed, strategy, target=0)
                    self.assertEqual(set(result["proofs"]), expected)
                    self.assertEqual(result["reason"], "domain-exhausted")
                    self.assertEqual(result["work"]["score_hashes"], len(expected))

    def test_acquisition_and_reuse_are_charged(self):
        p = Profile(101, 1, 2, 80)
        with patch("reference.strategies.expand_matrix", return_value=((1, 2),)):
            first = run_strategy(p, bytes(32), "first-restart", target=0)
            reused = run_strategy(p, bytes(32), "first-reuse", target=0)
        self.assertEqual(first["proofs"], [(2, -1)])
        self.assertEqual(set(reused["proofs"]), {(2, -1), (4, -2), (6, -3), (8, -4)})
        self.assertEqual(reused["first_solution_work"], first["first_solution_work"])
        self.assertEqual(reused["work"]["proposals"], first["work"]["proposals"] + 4)
        self.assertEqual(reused["work"]["score_hashes"], 4)  # Duplicate seed is not rescored.
        self.assertEqual(reused["work"]["matrix_expansions"], 1)
        self.assertGreater(reused["first_solution_work"]["matrix_terms"], 0)
        self.assertGreater(reused["work"]["reuse_coordinate_ops"], 0)

    def test_caps_and_no_solution_are_distinct(self):
        p, seed = Profile(7, 1, 1, 1), bytes(32)
        with patch("reference.strategies.expand_matrix", return_value=((1,),)):
            capped = run_strategy(p, seed, "full-search", proposal_limit=1, target=0)
            exhausted = run_strategy(p, seed, "full-search", target=0)
        self.assertEqual(capped["reason"], "proposal-limit")
        self.assertEqual(capped["work"]["proposals"], 1)
        self.assertEqual(exhausted["reason"], "domain-exhausted")
        self.assertIsNone(exhausted["first_solution_work"])
        self.assertEqual(exhausted["work"]["proposals"], 3)
        self.assertEqual(exhausted["work"]["matrix_terms"], 1)
        self.assertEqual(exhausted["work"]["norm_terms"], 3)

    def test_first_score_hit_stops_all_policies(self):
        p, seed = Profile(101, 1, 2, 80), bytes(32)
        with patch("reference.strategies.expand_matrix", return_value=((1, 2),)):
            for strategy in STRATEGIES:
                result = run_strategy(p, seed, strategy, target=2**256)
                self.assertEqual(result["reason"], "score-hit")
                self.assertEqual(result["work"]["score_hashes"], 1)
                self.assertTrue(verify(p, ((1, 2),), result["proofs"][0]))

    def test_cap_charges_duplicate_reuse_without_rescoring(self):
        p, seed = Profile(101, 1, 2, 80), bytes(32)
        with patch("reference.strategies.expand_matrix", return_value=((1, 2),)):
            first = run_strategy(p, seed, "first-restart", target=0)
            limit = first["work"]["proposals"] + 1
            capped = run_strategy(p, seed, "first-reuse", proposal_limit=limit, target=0)
        self.assertEqual(capped["reason"], "proposal-limit")
        self.assertEqual(capped["work"]["proposals"], limit)
        self.assertEqual(capped["work"]["score_hashes"], 1)
        self.assertEqual(capped["proofs"], first["proofs"])
        self.assertEqual(capped["work"]["matrix_terms"], first["work"]["matrix_terms"] + 2)

    def test_score_encoding_and_strict_threshold(self):
        p, seed, x = Profile(101, 1, 2, 80), bytes(32), (2, -1)
        message = _score_message(p, seed, x)
        self.assertEqual(message, SCORE_DOMAIN + struct.pack("<IHHQ", 101, 1, 2, 80)
                         + seed + struct.pack("<2i", 2, -1))
        variants = [_score_message(p, b"1" * 32, x), _score_message(p, seed, (4, -2)),
                    _score_message(Profile(101, 1, 2, 79), seed, x)]
        self.assertTrue(all(message != variant for variant in variants))
        score = int.from_bytes(hashlib.sha256(message).digest(), "big")
        with patch("reference.strategies.expand_matrix", return_value=((1, 2),)):
            self.assertEqual(run_strategy(p, seed, "first-restart", target=score)["reason"], "policy-restart")
            self.assertEqual(run_strategy(p, seed, "first-restart", target=score + 1)["reason"], "score-hit")

    def test_input_and_search_bounds(self):
        p = Profile(7, 1, 2, 8)
        for options in ({"proposal_limit": 0}, {"proposal_limit": True}, {"proposal_limit": 1_000_001},
                        {"target": -1}, {"target": True}, {"target": 2**256 + 1}):
            with self.assertRaises(ValueError):
                run_strategy(p, bytes(32), "full-search", **options)
        for profile, seed, strategy in ((p, b"", "full-search"), (p, bytes(32), "unknown"),
                                       (None, bytes(32), "full-search"),
                                       (Profile(65521, 1, 128, 100), bytes(32), "full-search")):
            with self.assertRaises(ValueError):
                run_strategy(profile, seed, strategy)


if __name__ == "__main__":
    unittest.main()
