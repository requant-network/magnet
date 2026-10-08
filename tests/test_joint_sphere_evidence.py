import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts import joint_survey, sphere_survey


class EvidenceTests(unittest.TestCase):
    def test_both_new_surveys_invalidate_old_success_before_failed_build(self):
        for module, names in [(sphere_survey, ("sphere-v1.json", "sphere-summary-v1.json")),
                              (joint_survey, ("joint-v1.json", "joint-summary-v1.json"))]:
            with self.subTest(module=module.__name__), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                for name in names:
                    path = root / "artifacts" / name
                    path.parent.mkdir(exist_ok=True)
                    path.write_text('{"status":"passed"}')
                argv = ["survey", "--python", "unused"] if module is sphere_survey else ["survey"]
                with patch.object(module, "ROOT", root), patch.object(sys, "argv", argv):
                    with patch.object(module, "build_native", side_effect=RuntimeError("failed build")):
                        if module is joint_survey:
                            with patch.object(module, "build_lab", return_value=Path("unused")):
                                with self.assertRaises(RuntimeError):
                                    module.main()
                        else:
                            with self.assertRaises(RuntimeError):
                                module.main()
                for name in names:
                    self.assertEqual(json.loads((root / "artifacts" / name).read_text())["status"], "running-or-incomplete")

    def test_sphere_availability_requires_both_complete(self):
        def record(sphere_reason, oracle_reason, count):
            return {"sphere": {"reason": sphere_reason, "proof_count": count,
                               "work": dict.fromkeys(("nodes", "leaves", "reconstruction_terms", "sis_checks"), 1)},
                    "oracle": {"stop": oracle_reason}, "probe_count": 0,
                    "sphere_elapsed_ns": 1, "construction_ns": 1, "reduction_ns": 1}
        result = sphere_survey.aggregate([record("domain-exhausted", "domain-exhausted", 1),
                                          record("domain-exhausted", "domain-exhausted", 0),
                                          record("node-limit", "domain-exhausted", 0),
                                          record("domain-exhausted", "pair-limit", 0)])
        self.assertEqual(result["instances"], 4)
        self.assertEqual(result["both_complete"], 2)
        self.assertEqual(result["complete_with_solution"], 1)
        self.assertEqual(result["complete_empty"], 1)


if __name__ == "__main__":
    unittest.main()
