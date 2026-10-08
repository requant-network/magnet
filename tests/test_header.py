from dataclasses import replace
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from reference.header import ExpectedContext, HEADER, LabHeader, MAX_PROOF, encode_proof, verify_proof
from reference.search import exhaustive_solutions
from reference.sis import Profile


class HeaderTests(unittest.TestCase):
    def setUp(self):
        self.h = LabHeader(bytes(range(32)), bytes(32), b"P" * 32, 4, 5, 6, Profile(7, 1, 3, 8))
        self.context = ExpectedContext(self.h.network, self.h.parent, self.h.height, self.h.profile)
        self.vector = next(exhaustive_solutions(self.h.profile, self.h.matrix()))
        self.packet = encode_proof(self.h, self.vector)

    def test_frozen_cross_language_fixture(self):
        fixture = json.loads((Path(__file__).parent / "vectors/header-v1.json").read_text())
        h = LabHeader.decode(bytes.fromhex(fixture["header_hex"]))
        self.assertEqual(h.encode().hex(), fixture["header_hex"])
        self.assertEqual(h.seed().hex(), fixture["seed_hex"])
        self.assertEqual([list(row) for row in h.matrix()], fixture["matrix"])
        context = ExpectedContext(h.network, h.parent, h.height, h.profile)
        self.assertTrue(verify_proof(bytes.fromhex(fixture["proof_hex"]), context))

    def test_exact_encoding_and_roundtrip(self):
        self.assertEqual(HEADER.size, 140)
        self.assertEqual(len(self.context.encode()), 88)
        self.assertEqual(MAX_PROOF, 652)
        self.assertEqual(LabHeader.decode(self.h.encode()), self.h)
        self.assertTrue(verify_proof(self.packet, self.context))
        self.assertFalse(verify_proof(self.packet + b"\0", self.context))
        self.assertFalse(verify_proof(self.packet[:-1], self.context))
        self.assertFalse(verify_proof(b"\0" * 653, self.context))
        for end in range(len(self.packet)):
            self.assertFalse(verify_proof(self.packet[:end], self.context))

    def test_all_header_fields_bind_seed(self):
        replacements = dict(network=b"N" * 32, parent=b"Q" * 32, payload=b"R" * 32,
                            height=7, timestamp=8, nonce=9)
        for field, value in replacements.items():
            self.assertNotEqual(replace(self.h, **{field: value}).seed(), self.h.seed())
        for p in [Profile(17, 1, 3, 8), Profile(7, 2, 3, 8),
                  Profile(7, 1, 4, 8), Profile(7, 1, 3, 9)]:
            self.assertNotEqual(replace(self.h, profile=p).seed(), self.h.seed())

    def test_invalid_headers_and_vector_types(self):
        for fields in [dict(network=b""), dict(parent=bytearray(32)), dict(payload="0" * 32),
                       dict(height=True), dict(timestamp=-1), dict(nonce=2**64), dict(profile=None)]:
            with self.assertRaises(ValueError):
                replace(self.h, **fields)
        for data in [self.h.encode()[:-1], self.h.encode() + b"\0", b"MGH2" + self.h.encode()[4:]]:
            with self.assertRaises(ValueError):
                LabHeader.decode(data)
        for vector in [(1,), (True, 0, 0), (2**31, 0, 0), (-2**31 - 1, 0, 0)]:
            with self.assertRaises(ValueError):
                encode_proof(self.h, vector)

    def test_untrusted_profile_and_context_cannot_trigger_generation(self):
        for context in [replace(self.context, network=b"Z" * 32),
                        replace(self.context, parent=b"Z" * 32), replace(self.context, height=3),
                        replace(self.context, profile=Profile(7, 1, 3, 9))]:
            with patch.object(LabHeader, "matrix", side_effect=AssertionError("must reject early")):
                self.assertFalse(verify_proof(self.packet, context))
        with self.assertRaises(ValueError):
            verify_proof(self.packet, None)
        easier = replace(self.h, profile=Profile(2, 1, 3, 3))
        self.assertFalse(verify_proof(encode_proof(easier, (1, 0, 0)), self.context))

    def test_sign_norm_and_sampling_exhaustion_reject(self):
        for vector in [(0, 0, 0), tuple(-x for x in self.vector), (-2**31, 2**31 - 1, 0)]:
            with patch.object(LabHeader, "matrix", side_effect=AssertionError("must reject early")):
                self.assertFalse(verify_proof(encode_proof(self.h, vector), self.context))
        with patch.object(LabHeader, "matrix", side_effect=ValueError("sampling budget exhausted")):
            self.assertFalse(verify_proof(self.packet, self.context))

    def test_solution_transplant_is_a_predicate_not_universal_rejection(self):
        # Toy solutions can satisfy multiple distinct matrices. Preserve both outcomes.
        accepted = rejected = False
        for nonce in range(50):
            h = replace(self.h, nonce=nonce)
            result = verify_proof(encode_proof(h, self.vector), self.context)
            accepted |= result
            rejected |= not result
        self.assertTrue(accepted)
        self.assertTrue(rejected)


if __name__ == "__main__":
    unittest.main()
