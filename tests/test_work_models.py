from dataclasses import replace
from fractions import Fraction
import unittest

from reference.grinding import header_family, run_policy
from reference.header import LabHeader
from reference.sis import Profile
from reference.work_models import ideal_target_trials, joint_family, search_loop_calls, summarize_work


class WorkModelsTests(unittest.TestCase):
    def setUp(self):
        self.base = LabHeader(bytes(32), bytes([1])*32, bytes([2])*32, 1, 100, 0, Profile(7, 1, 3, 8))

    def test_joint_order_context_and_single_axis_compatibility(self):
        family = joint_family(self.base, nonces=4, timestamps=4, payloads=4)
        self.assertEqual(len(family), 64)
        self.assertEqual(len({h.encode() for h in family}), 64)
        self.assertEqual(family[0], self.base)
        self.assertEqual(family[3].nonce, 3)
        self.assertEqual(family[4].payload, header_family(self.base, "payload", 2)[1].payload)
        self.assertEqual(family[16].timestamp, 101)
        for field, counts in [("nonce", (64, 1, 1)), ("timestamp", (1, 64, 1)), ("payload", (1, 1, 64))]:
            n, t, p = counts
            self.assertEqual(joint_family(self.base, nonces=n, timestamps=t, payloads=p),
                             header_family(self.base, field, 64))
        self.assertTrue(all((h.network, h.parent, h.height, h.profile) ==
                            (self.base.network, self.base.parent, self.base.height, self.base.profile) for h in family))

    def test_joint_preallocation_bounds_and_overflow(self):
        for values in [(True, 1, 1), (0, 1, 1), (8, 8, 9), (513, 1, 1)]:
            with self.assertRaises(ValueError):
                joint_family(self.base, nonces=values[0], timestamps=values[1], payloads=values[2])
        for field in ("nonce", "timestamp"):
            with self.assertRaises(ValueError):
                joint_family(replace(self.base, **{field: 2**64-1}), nonces=2, timestamps=2, payloads=1)
        with self.assertRaises(ValueError):
            joint_family(None, nonces=1, timestamps=1, payloads=1)

    def test_ideal_trials_are_exact_and_limited_in_meaning(self):
        self.assertEqual(ideal_target_trials(2**256), 1)
        self.assertEqual(ideal_target_trials(2**256//64), 64)
        self.assertEqual(ideal_target_trials(3), Fraction(2**256, 3))
        for target in (True, 0, -1, 2**256+1):
            with self.assertRaises(ValueError):
                ideal_target_trials(target)

    def test_failed_attempts_and_duplicate_occurrences_are_retained(self):
        family = header_family(self.base, "nonce", 64)
        failure = run_policy(family, "all", 0)
        hit = run_policy(family, "all", 2**256)
        self.assertIsNotNone(hit["hit"])
        summary = summarize_work([failure, hit, hit])
        self.assertEqual(summary["hit_occurrences"], 2)
        self.assertEqual(summary["work"]["vector_checks"], failure["work"]["vector_checks"] + 2*hit["work"]["vector_checks"])
        self.assertEqual(summary["work_per_hit_occurrence"]["vector_checks"]["denominator"], 2)
        self.assertIsNone(summarize_work([failure])["work_per_hit_occurrence"]["vector_checks"])
        self.assertEqual(search_loop_calls(failure), 64)
        self.assertEqual(search_loop_calls(run_policy(family, "unit", 0)), 0)
        reuse = run_policy(family, "reuse", 0)
        self.assertEqual(search_loop_calls(reuse), reuse["acquisition"]["header_index"]+1)

    def test_target_grid_monotone_paid_work(self):
        family = joint_family(self.base, nonces=4, timestamps=4, payloads=4)
        for policy in ("unit", "first", "all", "reuse"):
            previous = None
            for divisor in (8, 16, 32, 64):
                target = 2**256//divisor
                result = run_policy(family, policy, target)
                if result["hit"]:
                    self.assertLess(int(result["hit"]["digest"], 16), target)
                if previous:
                    for name in result["work"]:
                        self.assertGreaterEqual(result["work"][name], previous["work"][name])
                previous = result


if __name__ == "__main__":
    unittest.main()
