from dataclasses import replace
import unittest
from unittest.mock import patch

from reference.grinding import (POLICIES, header_family, run_policy, score_digest, verify_scored_proof)
from reference.header import ExpectedContext, LabHeader, encode_proof
from reference.sis import Profile


class GrindingTests(unittest.TestCase):
    def setUp(self):
        self.h = LabHeader(bytes(32), b"P"*32, b"D"*32, 1, 5, 0, Profile(7, 1, 1, 1))
        self.ctx = ExpectedContext(self.h.network, self.h.parent, self.h.height, self.h.profile)

    def test_families_preserve_context_and_change_only_chosen_field(self):
        for field in ("nonce", "timestamp", "payload"):
            family = header_family(self.h, field, 10)
            self.assertEqual(family[0], self.h)
            self.assertEqual(len({h.seed() for h in family}), 10)
            for header in family:
                self.assertTrue(self.ctx.matches(header))
                self.assertEqual(replace(header, **{field: getattr(self.h, field)}), self.h)
        for count in (0, 513, True):
            with self.assertRaises(ValueError):
                header_family(self.h, "nonce", count)
        with self.assertRaises(ValueError):
            header_family(replace(self.h, nonce=2**64-1), "nonce", 2)

    def test_strict_score_boundary_and_invalid_solution(self):
        # Use an actual generated zero column so the bound verifier is exercised.
        header = next(h for h in header_family(self.h, "nonce", 100) if h.matrix() == ((0,),))
        packet = encode_proof(header, (1,))
        digest = int.from_bytes(score_digest(header, (1,)), "big")
        self.assertFalse(verify_scored_proof(packet, self.ctx, digest))
        self.assertTrue(verify_scored_proof(packet, self.ctx, digest+1))
        self.assertFalse(verify_scored_proof(encode_proof(header, (0,)), self.ctx, 2**256))
        self.assertFalse(verify_scored_proof(packet, replace(self.ctx, height=2), 2**256))
        for target in (-1, 2**256+1, True):
            with self.assertRaises(ValueError):
                verify_scored_proof(packet, self.ctx, target)

    def test_failed_acquisition_is_charged_before_reuse(self):
        headers = header_family(self.h, "nonce", 5)
        # Two empty instances, one acquisition, one rejected reuse, one accepted reuse.
        with patch.object(LabHeader, "matrix", side_effect=[((1,),), ((2,),), ((0,),), ((3,),), ((0,),)]):
            result = run_policy(headers, "reuse", 0)
        self.assertEqual(result["reason"], "family-exhausted")
        self.assertEqual(result["work"]["headers_processed"], 5)
        self.assertEqual(result["work"]["vector_checks"], 5)
        self.assertEqual(result["work"]["score_hashes"], 2)
        self.assertEqual(result["acquisition"]["work_through_acquisition"]["vector_checks"], 3)
        self.assertEqual(result["acquisition"]["header_index"], 2)

    def test_caps_first_hits_and_unavailable_family_are_distinct(self):
        headers = header_family(self.h, "nonce", 5)
        for policy in POLICIES:
            with patch.object(LabHeader, "matrix", return_value=((0,),)):
                result = run_policy(headers, policy, 2**256)
            self.assertEqual(result["reason"], "score-hit")
            self.assertEqual(result["work"]["headers_processed"], 1)
            self.assertEqual(result["work"]["vector_checks"], 1)
            with patch.object(LabHeader, "matrix", return_value=((1,),)):
                result = run_policy(headers, policy, 0, proposal_limit=2)
            self.assertEqual(result["reason"], "proposal-limit")
            self.assertEqual(result["work"]["headers_processed"], 2)
            self.assertEqual(result["work"]["vector_checks"], 2)
            self.assertEqual(result["work"]["score_hashes"], 0)

    def test_all_scores_more_vectors_than_first_after_unsuccessful_hash(self):
        headers = (replace(self.h, profile=Profile(7, 1, 2, 2)),)
        with patch.object(LabHeader, "matrix", return_value=((0, 0),)):
            first = run_policy(headers, "first", 0)
            all_vectors = run_policy(headers, "all", 0)
        self.assertEqual(first["work"]["score_hashes"], 1)
        self.assertEqual(all_vectors["work"]["score_hashes"], 4)

    def test_last_allowed_candidate_can_hit_or_exhaust_family(self):
        headers = header_family(self.h, "nonce", 2)
        with patch.object(LabHeader, "matrix", side_effect=[((1,),), ((0,),)]):
            hit = run_policy(headers, "first", 2**256, proposal_limit=2)
        self.assertEqual(hit["reason"], "score-hit")
        self.assertEqual(hit["work"]["vector_checks"], 2)
        with patch.object(LabHeader, "matrix", return_value=((1,),)):
            empty = run_policy(headers, "first", 0, proposal_limit=2)
        self.assertEqual(empty["reason"], "family-exhausted")
        self.assertEqual(empty["work"]["vector_checks"], 2)


if __name__ == "__main__":
    unittest.main()
