"""Failed experiments must not leave stale successful evidence."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import native_survey


class NativeSurveyTests(unittest.TestCase):
    def test_failed_survey_invalidates_both_outputs(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            reports = root / "artifacts"
            reports.mkdir()
            names = ("native-survey-v1.json", "native-survey-summary-v1.json")
            for name in names:
                (reports / name).write_text('{"status":"passed"}', encoding="utf-8")
            with patch.object(native_survey, "ROOT", root), patch.object(
                    native_survey, "build_native", side_effect=RuntimeError("build failed")):
                with self.assertRaisesRegex(RuntimeError, "build failed"):
                    native_survey.main()
            for name in names:
                self.assertEqual(json.loads((reports / name).read_text(encoding="utf-8")),
                                 {"status": "running-or-incomplete"})


if __name__ == "__main__":
    unittest.main()
