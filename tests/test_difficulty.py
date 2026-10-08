from fractions import Fraction
import unittest

from reference.difficulty import LOW_TARGET, HIGH_TARGET, INITIAL_TARGET, adjust, expected_score_trials, simulate


class DifficultyTests(unittest.TestCase):
    def test_exact_rounding_clamp_and_saturation(self):
        self.assertEqual(adjust(INITIAL_TARGET,30,60),INITIAL_TARGET//2)
        self.assertEqual(adjust(INITIAL_TARGET,0,60),INITIAL_TARGET//4)
        self.assertEqual(adjust(INITIAL_TARGET,6000,60),INITIAL_TARGET*4)
        self.assertEqual(adjust(LOW_TARGET,0,60),LOW_TARGET)
        self.assertEqual(adjust(HIGH_TARGET,6000,60),HIGH_TARGET)
        t=LOW_TARGET+7
        self.assertEqual(adjust(t,2,3),t*2//3 if t*2//3>=LOW_TARGET else LOW_TARGET)
        for args in ((True,1,1),(INITIAL_TARGET,True,1),(INITIAL_TARGET,1,0),(INITIAL_TARGET,-1,1)):
            with self.assertRaises(ValueError): adjust(*args)

    def test_inverse_target_is_exact_trials_not_elapsed_work(self):
        self.assertEqual(expected_score_trials(2**252),16)
        self.assertEqual(expected_score_trials(3),Fraction(2**256,3))
        self.assertEqual(expected_score_trials(2**256),1)
        for value in (0,True,2**256+1):
            with self.assertRaises(ValueError): expected_score_trials(value)

    def test_fixed_common_randomness_capacity_and_reuse(self):
        args=dict(seed=81,method="fixed",interval=60,capacity=1)
        baseline=simulate(**args)
        supply=simulate(**{**args,"capacity":2},reuse=2)
        self.assertEqual(baseline["final_target"],supply["final_target"])
        for a,b in zip(baseline["records"][:64],supply["records"][:64]):
            self.assertEqual(a,b)
        for a,b in zip(baseline["records"][64:],supply["records"][64:]):
            self.assertAlmostEqual(a["actual_interval_seconds"],4*b["actual_interval_seconds"])
        self.assertEqual(baseline,simulate(**args))

    def test_hypotheses_are_bounded_and_timestamp_rejections_recorded(self):
        for method in ("fixed","window","per-block"):
            for attack in ("none","future","past","oscillating"):
                r=simulate(seed=20261008,method=method,interval=30,capacity=10,attack=attack)
                self.assertEqual(r["events"],128)
                for event in r["records"]:
                    self.assertTrue(LOW_TARGET<=int(event["target"])<=HIGH_TARGET)
                    if event["accepted_time"]:
                        self.assertLessEqual(event["timestamp"],event["local_seconds"]+120)
        with self.assertRaises(ValueError): simulate(seed=1,method="unknown",interval=30,capacity=1)
        with self.assertRaises(ValueError): simulate(seed=True,method="fixed",interval=30,capacity=1)


if __name__=="__main__": unittest.main()
