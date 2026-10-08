"""Evidence lifecycle and conditional denominators for lattice surveys."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import lattice_survey


class LatticeSurveyTests(unittest.TestCase):
    def test_failure_invalidates_both_reports(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            reports = root/'artifacts'
            reports.mkdir()
            names = ('lattice-survey-v1.json', 'lattice-survey-summary-v1.json')
            for name in names:
                (reports/name).write_text('{"status":"passed"}', encoding='utf-8')
            with patch.object(lattice_survey, 'ROOT', root), patch.object(
                    lattice_survey, 'build_native', side_effect=RuntimeError('build failed')):
                with self.assertRaisesRegex(RuntimeError, 'build failed'):
                    lattice_survey.main()
            self.assertTrue(all(json.loads((reports/name).read_text(encoding='utf-8')) ==
                                {'status': 'running-or-incomplete'} for name in names))

    def test_capped_oracle_excluded_but_capped_reduction_retained(self):
        record = {'reduction': {'reason': 'step-limit', 'work':
                               {'max_integer_bits': 3, 'max_fraction_bits': 5, 'steps': 1}},
                  'probe': {'reason': 'probe-exhausted', 'proofs': [(1, -1)], 'basis_proofs': []},
                  'oracle': {'stop': 'pair-limit', 'proof_count': 2},
                  'reduction_elapsed_ns': 10, 'probe_elapsed_ns': 20}
        capped = lattice_survey.aggregate([record])['counts']
        self.assertEqual(capped['lll_capped'], 1)
        self.assertEqual(capped['oracle_capped'], 1)
        self.assertEqual(capped['with_solution'], 0)
        self.assertEqual(capped['probe_vectors'], 0)
        record['oracle']['stop'] = 'domain-exhausted'
        completed = lattice_survey.aggregate([record])['counts']
        self.assertEqual(completed['oracle_complete'], 1)
        self.assertEqual(completed['lll_capped'], 1)
        self.assertEqual(completed['pair_only_success'], 1)
        self.assertEqual(completed['probe_vectors'], 1)


if __name__ == '__main__':
    unittest.main()
