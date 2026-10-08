import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import flint_survey, grinding_survey


class NewSurveyTests(unittest.TestCase):
    def test_failed_build_invalidates_both_experiment_reports(self):
        for module, names, arguments, builder in [
            (flint_survey, ("flint-survey-v1.json", "flint-summary-v1.json"), ["test", "--python", "unused"], "build_native"),
            (grinding_survey, ("grinding-v1.json", "grinding-summary-v1.json"), ["test"], "build_lab")]:
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                (root / "artifacts").mkdir()
                for name in names:
                    (root / "artifacts" / name).write_text('{"status":"passed"}')
                with patch.object(module, "ROOT", root), patch("sys.argv", arguments), patch.object(
                        module, builder, side_effect=RuntimeError("build failed")):
                    with self.assertRaisesRegex(RuntimeError, "build failed"):
                        module.main()
                for name in names:
                    self.assertEqual(json.loads((root / "artifacts" / name).read_text()), {"status": "running-or-incomplete"})

    def test_capped_oracle_excluded_from_flint_availability(self):
        record = {"oracle": {"stop": "pair-limit", "proof_count": 1},
                  "runs": [{"proof_count": 0, "construction_ns": 1, "reduction_ns": 2,
                            "probe_ns": 3, "basis_sha256": "x"}]}
        capped = flint_survey.aggregate([record])
        self.assertEqual(capped["oracle_capped"], 1)
        self.assertEqual(capped["with_solution"], 0)
        self.assertEqual(capped["miss_with_solution"], 0)
        record["oracle"]["stop"] = "domain-exhausted"
        complete = flint_survey.aggregate([record])
        self.assertEqual(complete["miss_with_solution"], 1)


if __name__ == "__main__":
    unittest.main()
