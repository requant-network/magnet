from dataclasses import replace
import json
from pathlib import Path
import unittest

from reference.admission_wire import decode_rules, encode_rules, target_bytes
from reference.grinding import score_digest
from reference.header import LabHeader
from reference.header_rules import admit_proof


class AdmissionWireTests(unittest.TestCase):
    def test_frozen_cross_language_fixture(self):
        fixture = json.loads((Path(__file__).parent / "vectors/admission-v1.json").read_text())
        packet = bytes.fromhex(fixture["proof_hex"])
        rules = decode_rules(bytes.fromhex(fixture["rules_hex"]))
        self.assertEqual(encode_rules(rules).hex(), fixture["rules_hex"])
        header = LabHeader.decode(packet[:140])
        self.assertEqual(score_digest(header, fixture["vector"]).hex(), fixture["score_hex"])
        for case in fixture["targets"]:
            self.assertEqual(admit_proof(packet, replace(rules, target=int(case["target"]))), case["accepted"])

    def test_rules_and_target_canonical_bounds(self):
        fixture = json.loads((Path(__file__).parent / "vectors/admission-v1.json").read_text())
        wire = bytes.fromhex(fixture["rules_hex"])
        for target in (-1, True, 2**256+1):
            with self.assertRaises(ValueError):
                target_bytes(target)
        self.assertEqual(target_bytes(2**256), b"\x01"+bytes(32))
        for bad in (b"", wire[:-1], wire+b"x", b"x"*395, wire[:88]+b"\x02"+wire[89:],
                    wire[:137]+b"\x00"+wire[138:], wire[:137]+b"\x02"+wire[138:]*2):
            with self.assertRaises(ValueError):
                decode_rules(bad)
        rules = decode_rules(wire)
        maximum = replace(rules, payloads=tuple(bytes([i])*32 for i in range(8)))
        self.assertEqual(len(encode_rules(maximum)), 394)
        self.assertEqual(decode_rules(encode_rules(maximum)), maximum)


if __name__ == "__main__":
    unittest.main()
