import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from reference.lattice_policies import COUNTERS
from reference.sis import Profile
from scripts import windows_survey


class WindowsEvidenceTests(unittest.TestCase):
    def test_failed_build_invalidates_both_reports(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("windows-v1.json", "windows-summary-v1.json"):
                path = root / "artifacts" / name
                path.parent.mkdir(exist_ok=True)
                path.write_text('{"status":"passed"}')
            with patch.object(windows_survey, "ROOT", root), patch.object(
                    windows_survey, "build_lab", side_effect=RuntimeError("failed build")), patch.object(
                    windows_survey, "run_window") as worker, patch(
                    "sys.argv", ["windows_survey", "--python", "unused-python"]):
                with self.assertRaises(RuntimeError):
                    windows_survey.main()
                worker.assert_not_called()
            for name in ("windows-v1.json", "windows-summary-v1.json"):
                self.assertEqual(json.loads((root / "artifacts" / name).read_text())["status"], "running-or-incomplete")

    def test_fresh_schedules_do_not_replay_headers(self):
        profile = Profile(257, 3, 14, 12)
        for schedule in ("fresh-nonce", "fresh-parent"):
            _, stages = windows_survey.stages_for(profile, schedule)
            self.assertEqual(len({h.encode() for stage in stages for h in stage}), 24)
            self.assertEqual(len({h.seed() for stage in stages for h in stage}), 24)
            parents = {stage[0].parent for stage in stages}
            heights = {stage[0].height for stage in stages}
            if schedule == "fresh-nonce":
                self.assertEqual(len(parents), 1)
                self.assertEqual(len(heights), 1)
                self.assertEqual([stage[0].nonce for stage in stages], [0, 8, 16])
            else:
                self.assertEqual(len(parents), 3)
                self.assertEqual(heights, {1, 2, 3})
                self.assertEqual([stage[0].nonce for stage in stages], [0, 0, 0])
        with self.assertRaises(ValueError):
            windows_survey.stages_for(profile, "replay")

    def test_censored_work_and_hits_never_become_zero_cost_wins(self):
        def record(known, cost, hit, elapsed):
            return {"window": {"logical_work_known": known, "outcome": "completed" if known else "wall-timeout",
                               "snapshot": {"stages": [{"work": dict.fromkeys(COUNTERS, cost), "hit": hit}]},
                               "resource": {"elapsed_ns": elapsed, "peak_process_commit_bytes": 10,
                                            "deadline_overshoot_ns": 3}}}
        failed, winner, censored = record(True, 20, None, 100), record(True, 10, {}, 200), record(False, 99, {}, 300)
        complete = windows_survey.summarize([failed, winner])
        self.assertEqual(complete["completed_stage_hit_occurrences"], 1)
        self.assertEqual(complete["unconditional_work_per_hit"]["reduction_calls"], {"numerator": 30, "denominator": 1})
        total = windows_survey.summarize([failed, winner, censored])
        self.assertEqual(total["completed_stage_hit_occurrences"], 1)
        self.assertEqual(total["completed_only_work"]["reduction_calls"], 30)
        self.assertEqual(total["all_attempt_elapsed_ns"], 600)
        self.assertEqual(total["unknown_logical_work_windows"], 1)
        self.assertIsNone(total["unconditional_work_per_hit"])
        self.assertIsNone(windows_survey.summarize([failed])["completed_work_per_hit"]["reduction_calls"])
        self.assertEqual(windows_survey.summarize([censored])["completed_stage_hit_occurrences"], 0)


if __name__ == "__main__":
    unittest.main()
