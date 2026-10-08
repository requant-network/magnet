from dataclasses import asdict
import json
import unittest

from reference.sis import Profile
from scripts.flint_driver import decode_response
from solvers.flint_worker import MAX_INPUT, decode_request


class FlintProtocolTests(unittest.TestCase):
    def test_request_rejects_before_optional_backend_import(self):
        p = Profile(7, 1, 2, 5)
        case = {"profile": asdict(p), "matrix": [[1, 2]]}
        valid = {"version": "MFL1", "cases": [case]}
        self.assertEqual(decode_request(json.dumps(valid).encode()), [(p, [[1, 2]])])
        for value in [{**valid, "version": "MFL2"}, {**valid, "extra": 0}, {**valid, "cases": []},
                      {**valid, "cases": [case] * 101}, {"version": "MFL1", "cases": [
                          {"profile": asdict(Profile(7, 1, 17, 5)), "matrix": [[0] * 17]}]},
                      {"version": "MFL1", "cases": [{**case, "matrix": [[7, 2]]}]}]:
            with self.assertRaises(ValueError):
                decode_request(json.dumps(value).encode())
        with self.assertRaises(ValueError):
            decode_request(b" " * (MAX_INPUT + 1))

    def test_certificate_tampering_and_inexact_reducedness_rejected(self):
        p, matrix = Profile(7, 1, 2, 5), [[1, 2]]
        item = {"profile": asdict(p), "initial_basis": [[7, 0], [-2, 1]],
                "basis": [[-2, 1], [1, 3]], "transform": [[0, 1], [1, 3]],
                "rank": 1, "reason": "lll-reduced", "construction_ns": 1, "reduction_ns": 2}
        packet = {"version": "MFR1", "backend": {"package": "python-flint", "version": "0.9.0"}, "results": [item]}
        _, result = decode_response(json.dumps(packet).encode(), [(p, matrix)])
        self.assertTrue(result[0]["certificate"]["lll_reduced"])
        for modified in [{**item, "transform": [[0, 1], [1, 2]]},
                         {**item, "basis": item["initial_basis"], "transform": [[1, 0], [0, 1]]},
                         {**item, "reduction_ns": True}, {**item, "reason": "timeout"}]:
            with self.assertRaises(ValueError):
                decode_response(json.dumps({**packet, "results": [modified]}).encode(), [(p, matrix)])


if __name__ == "__main__":
    unittest.main()
