import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from reference.sis import Profile
from scripts import campaign_survey


class CampaignEvidenceTests(unittest.TestCase):
    def test_shuffle_repeats_are_complete_reproducible_and_not_blocked(self):
        jobs = campaign_survey.jobs_for(24)
        self.assertEqual(jobs, campaign_survey.jobs_for(24))
        self.assertEqual(len(jobs), 288)
        self.assertEqual(len(set(jobs)), 288)
        self.assertEqual({j[1] for j in jobs}, {0, 1})
        self.assertGreater(len({j[0] for j in jobs[:12]}), 1)
        with self.assertRaises(ValueError):
            campaign_survey.jobs_for(True)

    def test_seeded_schedules_change_instances_and_preserve_surface(self):
        profile = Profile(257, 3, 14, 12)
        all_headers = set()
        for seed in campaign_survey.SEEDS:
            _, stages = campaign_survey.stages_for(profile, "fresh-parent", seed)
            encoded = {h.encode() for stage in stages for h in stage}
            self.assertEqual(len(encoded), 24)
            self.assertFalse(encoded & all_headers)
            all_headers |= encoded
            self.assertEqual({s[0].height for s in stages}, {1, 2, 3})
            self.assertEqual(len({s[0].network for s in stages}), 1)
        with self.assertRaises(ValueError):
            campaign_survey.stages_for(profile, "replay", 0)

    def test_failed_build_invalidates_reports_before_any_job(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "artifacts").mkdir()
            names = ("campaign-v1.json", "campaign-summary-v1.json")
            for name in names:
                (root / "artifacts" / name).write_text('{"status":"passed"}')
            with (patch.object(campaign_survey, "ROOT", root), patch.object(campaign_survey, "build_lab",
                    side_effect=RuntimeError("failed build")), patch.object(campaign_survey, "run_window") as job,
                    patch("sys.argv", ["campaign_survey", "--python", "unused"])):
                with self.assertRaises(RuntimeError):
                    campaign_survey.main()
                job.assert_not_called()
            for name in names:
                self.assertEqual(json.loads((root / "artifacts" / name).read_text())["status"], "running-or-incomplete")


if __name__ == "__main__":
    unittest.main()
