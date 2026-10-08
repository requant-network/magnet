import hashlib
import itertools
import json
import math
from pathlib import Path
import random
import struct
import unittest
from unittest.mock import patch

from reference.search import exhaustive_solutions
from reference.sis import (
    DOMAIN, MAX_PACKET, Profile, decode_case, encode_case, expand_matrix,
    verify, verify_packet,
)


class ReferenceTests(unittest.TestCase):
    def setUp(self):
        self.p = Profile(7, 1, 2, 5)
        self.a = ((1, 2),)
        self.packet = encode_case(self.p, self.a, (2, -1))

    def test_manual_vectors(self):
        path = Path(__file__).parent / "vectors" / "manual.json"
        for case in json.loads(path.read_text(encoding="utf-8")):
            with self.subTest(case=case["name"]):
                p = Profile(**case["profile"])
                data = encode_case(p, case["matrix"], case["vector"])
                self.assertEqual(verify_packet(data), case["valid"])
                if "packet_hex" in case:
                    self.assertEqual(data.hex(), case["packet_hex"])

    def test_profiles_reject_invalid_values(self):
        for fields in [(4, 1, 2, 5), (1, 1, 2, 1), (65537, 1, 2, 5),
                       (7, 0, 2, 5), (7, 65, 2, 5), (7, 1, 129, 5),
                       (7, 1, 2, 0), (7, 1, 2, 49), (7, 1, 2, -1),
                       (True, 1, 2, 1), (7, True, 2, 5), (7, 1, 2, 5.0)]:
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                Profile(*fields)

    def test_malformed_shapes_and_coordinates(self):
        for matrix, vector in [([], [2, -1]), ([[1]], [2, -1]),
                               ([[1, 7]], [2, -1]), ([[1, -1]], [2, -1]),
                               ([[1, True]], [2, -1]), (self.a, [2]),
                               (self.a, [True, -1]), (self.a, [2**31, -1]),
                               (self.a, [-2**31 - 1, 0])]:
            self.assertFalse(verify(self.p, matrix, vector))
            with self.assertRaises(ValueError):
                encode_case(self.p, matrix, vector)

    def test_arithmetic_rejection(self):
        for vector in [(0, 0), (1, 0), (7, 0), (-2, 1), (-2**31, 2**31 - 1)]:
            self.assertFalse(verify(self.p, self.a, vector))

    def test_lengths_magic_and_residue(self):
        for end in range(len(self.packet)):
            self.assertFalse(verify_packet(self.packet[:end]))
        self.assertFalse(verify_packet(self.packet + b"\x00"))
        self.assertFalse(verify_packet(b"SIS2" + self.packet[4:]))
        self.assertFalse(verify_packet(b"\x00" * (MAX_PACKET + 1)))
        self.assertFalse(verify_packet(self.packet[:20] + struct.pack("<I", 7) + self.packet[24:]))

    def test_roundtrip(self):
        self.assertEqual(decode_case(self.packet), (self.p, self.a, (2, -1)))

    def test_smallest_prime(self):
        self.assertTrue(verify(Profile(2, 1, 2, 2), ((1, 1),), (1, 1)))

    def test_largest_packet_and_norm(self):
        p = Profile(65521, 64, 128, 65521**2 - 1)
        a = ((0,) * 128,) * 64
        x = (65520,) + (0,) * 127
        packet = encode_case(p, a, x)
        self.assertEqual(len(packet), MAX_PACKET)
        self.assertTrue(verify_packet(packet))
        self.assertFalse(verify(p, a, (65521,) + (0,) * 127))

    def test_exhaustive_matches_verifier(self):
        rng = random.Random(20261008)
        for q, m, b2 in [(2, 2, 2), (3, 3, 4), (7, 2, 5), (7, 3, 8)]:
            p = Profile(q, 1, m, b2)
            for _ in range(8):
                a = (tuple(rng.randrange(q) for _ in range(m)),)
                radius = math.isqrt(b2)
                domain = itertools.product(range(-radius, radius + 1), repeat=m)
                accepted = {x for x in domain if verify(p, a, x)}
                self.assertEqual(accepted, set(exhaustive_solutions(p, a)))
        self.assertEqual(list(exhaustive_solutions(self.p, self.a)), [(2, -1)])

    def test_search_budget(self):
        with self.assertRaisesRegex(ValueError, "budget"):
            list(exhaustive_solutions(Profile(7, 1, 128, 5), ((1,) * 128,)))

    def test_no_solution_is_distinct_from_search_timeout(self):
        self.assertEqual(list(exhaustive_solutions(Profile(7, 1, 1, 1), ((1,),))), [])

    def test_shake256_known_answer(self):
        # SHAKE256 empty-message prefix from the standard known-answer sequence.
        self.assertEqual(hashlib.shake_256(b"").hexdigest(32),
                         "46b9dd2b0ba88d13233b3feb743eeb243fcd52ea62b81b82b50c27646ed5762f")

    def test_generator_frozen_vector(self):
        self.assertEqual(expand_matrix(Profile(7, 2, 3, 5), bytes(32)),
                         ((1, 0, 6), (6, 0, 6)))

    def test_generator_rejection_sampling_independent_stream(self):
        # q=32771 rejects close to half the 16-bit words; not a modulo-only test.
        p = Profile(32771, 3, 8, 5)
        seed = bytes(range(32))
        message = DOMAIN + struct.pack("<IHHQ", p.q, p.n, p.m, p.b2) + seed
        accepted, cursor, rejected = [], 0, 0
        while len(accepted) < p.n * p.m:
            prefix = hashlib.shake_256(message).digest(cursor + 2)
            word = int.from_bytes(prefix[cursor:cursor + 2], "little")
            cursor += 2
            if word >= p.q:  # For this q the cutoff is exactly q.
                rejected += 1
            else:
                accepted.append(word)
        self.assertGreater(rejected, 0)
        self.assertEqual([a for row in expand_matrix(p, seed) for a in row], accepted)

    def test_generator_bounds_and_seed(self):
        for seed in [b"", b"a" * 31, b"a" * 33, "0" * 32]:
            with self.assertRaises(ValueError):
                expand_matrix(self.p, seed)
        p = Profile(65521, 64, 128, 5)
        matrix = expand_matrix(p, bytes(32))
        self.assertEqual((len(matrix), len(matrix[0])), (64, 128))
        self.assertTrue(all(0 <= a < p.q for row in matrix for a in row))

    def test_generator_sampling_budget_is_enforced(self):
        with patch("reference.sis.hashlib.shake_256") as shake:
            shake.return_value.digest.return_value = b"\xff\xff" * (4 * 2 + 1024)
            with self.assertRaisesRegex(ValueError, "budget exhausted"):
                expand_matrix(self.p, bytes(32))
            shake.return_value.digest.assert_called_once_with(2 * (4 * 2 + 1024))


if __name__ == "__main__":
    unittest.main()
