import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from reference.sis import Profile
from scripts import binding_survey


class BindingSurveyTests(unittest.TestCase):
    def test_failed_build_invalidates_both_outputs(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            reports = root / "artifacts"
            reports.mkdir()
            names = ["header-binding-v1.json", "header-binding-summary-v1.json"]
            for name in names:
                (reports / name).write_text('{"status":"passed"}', encoding="utf-8")
            with patch.object(binding_survey, "ROOT", root), patch.object(
                    binding_survey, "build_lab", side_effect=RuntimeError("build failed")):
                with self.assertRaisesRegex(RuntimeError, "build failed"):
                    binding_survey.main()
            for name in names:
                self.assertEqual(json.loads((reports / name).read_text()), {"status": "running-or-incomplete"})

    def test_oracle_space_bounded_and_canonical(self):
        box, vectors = binding_survey.candidates(Profile(7, 1, 3, 8))
        self.assertEqual(box, 125)
        self.assertEqual(len(vectors), len(set(vectors)))
        self.assertTrue(all(next(x for x in v if x) > 0 and sum(x*x for x in v) <= 8 for v in vectors))
        with self.assertRaisesRegex(ValueError, "oracle space"):
            binding_survey.candidates(Profile(7, 1, 128, 8))
        for count in [0, 513, True]:
            with self.assertRaisesRegex(ValueError, "count bound"):
                binding_survey.run_study(None, None, Profile(7, 1, 3, 8), count)


if __name__ == "__main__":
    unittest.main()
