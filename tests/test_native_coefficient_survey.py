"""Frozen experiment shape, positive samples and failure evidence lifecycle."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from reference.sis import Profile
from scripts import native_coefficient_survey as study


class NativeCoefficientSurveyTests(unittest.TestCase):
    def test_frozen_comparison_shape(self):
        cases, labels = study.comparison_cases()
        self.assertEqual(len(cases), 104)
        self.assertEqual(len(labels), len(cases))
        self.assertEqual({x['fixture'] for x in labels if x['kind'] == 'fixture'},
                         {'zero', 'triple-only', 'nonunit-only', 'scalar-copy', 'singleton'})

    def test_control_matches_fresh_step_zero_and_new_steps_differ(self):
        p = Profile(*study.PROFILES[0])
        first = study.matrix_at(p, study.REFRESH_SEEDS[0], 'fresh-matrix', 0)
        for step in range(study.STEPS):
            self.assertEqual(first, study.matrix_at(p, study.REFRESH_SEEDS[0], 'same-instance-control', step))
        self.assertNotEqual(first, study.matrix_at(p, study.REFRESH_SEEDS[0], 'fresh-matrix', 1))

    def test_positive_individual_samples(self):
        for values in ([], [1, 0, 3], [1, -1], [True], [1.0]):
            with self.assertRaises(RuntimeError):
                study.timing_summary(values)
        self.assertEqual(study.timing_summary([1, 7, 3])['median_ns'], 3)

    def test_failure_invalidates_success_before_build(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'artifacts').mkdir()
            (root/'docs/research/results').mkdir(parents=True)
            paths = (root/'docs/research/results'/f'{study.VERSION}.json', root/'artifacts'/f'{study.VERSION}.json')
            for path in paths:
                path.write_text('{"status":"passed"}')
            def fail():
                for path in paths:
                    self.assertEqual(json.loads(path.read_text())['status'], 'running-or-incomplete')
                raise RuntimeError('test build failure')
            with patch('scripts.consensus_evidence.ROOT', root), \
                    patch('scripts.consensus_evidence.source_hashes', return_value={}), \
                    patch.object(study, 'build_engines', side_effect=fail):
                with self.assertRaises(RuntimeError):
                    study.main()
            for path in paths:
                failed = json.loads(path.read_text())
                self.assertEqual(failed['status'], 'failed')
                self.assertTrue(failed['in_progress_work']['unknown_work'])


if __name__ == '__main__':
    unittest.main()
