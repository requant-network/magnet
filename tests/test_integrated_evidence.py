import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from reference.lattice_policies import COUNTERS
from scripts import integrated_survey


class IntegratedEvidenceTests(unittest.TestCase):
    def test_failed_build_invalidates_both_reports_before_optional_backend(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("integrated-v1.json", "integrated-summary-v1.json"):
                path = root / "artifacts" / name
                path.parent.mkdir(exist_ok=True)
                path.write_text('{"status":"passed"}')
            with patch.object(integrated_survey, "ROOT", root):
                with patch.object(integrated_survey, "build_lab", side_effect=RuntimeError("failed build")):
                    with patch.object(integrated_survey, "PracticalReducer") as reducer:
                        with self.assertRaises(RuntimeError):
                            integrated_survey.main()
                        reducer.assert_not_called()
            for name in ("integrated-v1.json", "integrated-summary-v1.json"):
                self.assertEqual(json.loads((root / "artifacts" / name).read_text())["status"], "running-or-incomplete")

    def test_failed_runs_and_cold_preparation_remain_in_all_run_totals(self):
        timers = dict.fromkeys(("construction_ns", "native_reduction_ns", "backend_audit_ns",
                               "reducer_call_ns", "sphere_ns_including_visitor"), 0)
        def run(cost, hit, reason):
            return {"result": {"work": dict.fromkeys(COUNTERS, cost), "hit": hit, "reason": reason,
                               "elapsed_ns": cost, "timers": timers}}
        cold, warm, failed = run(10, {}, "score-hit"), run(0, {}, "score-hit"), run(20, None, "sphere-node-limit")
        total = integrated_survey.summarize([cold, warm, failed])
        self.assertEqual(total["hit_occurrences"], 2)
        self.assertEqual(total["work"]["reduction_calls"], 30)
        self.assertEqual(total["work_per_hit_occurrence"]["reduction_calls"], {"numerator": 30, "denominator": 2})
        self.assertIsNone(integrated_survey.summarize([failed])["work_per_hit_occurrence"]["reduction_calls"])


if __name__ == "__main__":
    unittest.main()
