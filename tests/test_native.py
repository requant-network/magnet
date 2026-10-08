"""Native wire bounds are tested without launching a compiler from unit tests."""
import struct
import unittest

from reference.sis import Profile
from scripts.native_driver import REQUEST, RESPONSE, decode_response, encode_request


class NativeWireTests(unittest.TestCase):
    def test_request_bounds(self):
        p = Profile(7, 1, 2, 5)
        request = encode_request(p, [[1, 2]], "ball", repeats=3)
        self.assertEqual(REQUEST.size, 36)
        self.assertEqual(REQUEST.unpack_from(request), (b"NAT1", 1, 50_000_000, 1_000_000,
                                                       10_000_000, 100_000, 3))
        self.assertEqual(request[-8:], bytes(8))
        for key, values in {"nodes": (False, 0, 50_000_001), "table": (0, 1_000_001),
                            "pairs": (0, 10_000_001), "proofs": (0, 100_001),
                            "repeats": (0, 10)}.items():
            for value in values:
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    encode_request(p, [[1, 2]], "ball", **{key: value})
        with self.assertRaises(ValueError):
            encode_request(p, [[1, 2]], "unknown")

    def test_response_exact_payload(self):
        body = RESPONSE.pack(b"NSR1", 0, 2, 1, 1, 64, *([0] * 9 + [1]))
        body += struct.pack("<Qii", 42, 2, -1)
        decoded = decode_response(body)
        self.assertEqual(RESPONSE.size, 108)
        self.assertEqual(decoded["proofs"], [(2, -1)])
        self.assertEqual(decoded["elapsed_ns"], [42])
        for invalid in [b"", body[:-1], body + b"x"]:
            with self.assertRaises(ValueError):
                decode_response(invalid)
        for offset, value in [(0, 0), (4, 255), (5, 1), (8, 0), (10, 1), (16, 0), (100, 0)]:
            invalid = bytearray(body)
            invalid[offset] = value
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                decode_response(invalid)


if __name__ == "__main__":
    unittest.main()
