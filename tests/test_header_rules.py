from dataclasses import replace
import unittest
from unittest.mock import patch

from reference.grinding import score_digest
from reference.header import ExpectedContext, LabHeader, encode_proof
from reference.header_rules import LabRules, admit_proof
from reference.search import exhaustive_solutions
from reference.sis import Profile


class HeaderRulesTests(unittest.TestCase):
    def setUp(self):
        self.header = LabHeader(bytes(32), bytes([1])*32, bytes([2])*32, 1, 100, 0, Profile(7, 1, 3, 8))
        self.context = ExpectedContext(self.header.network, self.header.parent, 1, self.header.profile)
        self.rules = LabRules(self.context, 2**256, 99, 101, (self.header.payload,))
        self.vector = next(iter(exhaustive_solutions(self.header.profile, self.header.matrix())))
        self.packet = encode_proof(self.header, self.vector)

    def test_trusted_surface_and_strict_external_target(self):
        self.assertTrue(admit_proof(self.packet, self.rules))
        digest = int.from_bytes(score_digest(self.header, self.vector), "big")
        self.assertFalse(admit_proof(self.packet, replace(self.rules, target=digest)))
        self.assertTrue(admit_proof(self.packet, replace(self.rules, target=digest+1)))
        for timestamp in (99, 101):
            self.assertTrue(self.rules.permits(replace(self.header, timestamp=timestamp)))

    def test_invalid_surface_rejected_before_matrix_derivation(self):
        for header in (replace(self.header, parent=bytes([3])*32), replace(self.header, height=2),
                       replace(self.header, timestamp=102), replace(self.header, payload=bytes([3])*32),
                       replace(self.header, profile=Profile(7, 1, 3, 7))):
            with patch.object(LabHeader, "matrix", side_effect=AssertionError("must reject early")):
                self.assertFalse(admit_proof(encode_proof(header, self.vector), self.rules))
        with patch.object(LabHeader, "matrix", side_effect=AssertionError("zero target")):
            self.assertFalse(admit_proof(self.packet, replace(self.rules, target=0)))

    def test_malformed_proofs_and_invalid_trusted_configuration(self):
        for packet in (b"", self.packet[:-1], self.packet+b"x", bytes(653), "text", b"BAD!"+self.packet[4:]):
            self.assertFalse(admit_proof(packet, self.rules))
        for changes in ({"target": True}, {"earliest": True}, {"latest": 98}, {"payloads": ()},
                        {"payloads": (self.header.payload,)*2}, {"payloads": [self.header.payload]}, {"context": None}):
            with self.assertRaises(ValueError):
                replace(self.rules, **changes)


if __name__ == "__main__":
    unittest.main()
