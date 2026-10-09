import json
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from reference.sis import Profile
from scripts import small_coefficient_survey as survey
from reference.small_coefficients import search
from scripts.small_coefficient_audits import audit_search, native_verdicts


class SmallCoefficientEvidenceTests(unittest.TestCase):
    def test_independent_ledger_audit_rejects_work_census_and_censor_tampering(self):
        p, matrix = Profile(17, 2, 3, 8), ((1, 2, 3), (3, 4, 5))
        result = search(p, matrix, bound=2, candidate_limit=7, proof_limit=2)
        audit_search(p, matrix, 2, result, 7, 2)
        for field in ('generated', 'matrix_terms', 'row_reductions', 'validation_matrix_entries'):
            broken = copy.deepcopy(result)
            broken['work'][field] += 1
            with self.assertRaises(RuntimeError): audit_search(p, matrix, 2, broken, 7, 2)
        for field, value in (('weights', {}), ('coefficients', {}), ('all_proofs_returned', True),
                             ('unchecked_domain_suffix', 0), ('reason', 'domain-exhausted')):
            broken = copy.deepcopy(result)
            broken[field] = value
            with self.assertRaises(RuntimeError): audit_search(p, matrix, 2, broken, 7, 2)

    def test_frozen_schedule_freshness_and_control_mapping(self):
        for values in survey.PROFILES:
            p = Profile(*values)
            fresh = [survey.matrix_at(p, 'fresh-matrix', i) for i in range(survey.STEPS)]
            repeated = [survey.matrix_at(p, 'same-instance-control', i) for i in range(survey.STEPS)]
            self.assertEqual(len({seed for seed, _ in fresh}), 6)
            self.assertEqual(len({matrix for _, matrix in fresh}), 6)
            self.assertTrue(all(x == fresh[0] for x in repeated))

    def test_native_audit_rejects_missing_extra_wrong_or_diagnostic_output(self):
        class Result:
            stderr = b''
            stdout = b'\x01'
        result = Result()
        with patch('scripts.small_coefficient_audits.subprocess.run', return_value=result):
            native_verdicts(Path('unused'), [b'packet'], [1])
            for output, errors in ((b'', b''), (b'\x01\x01', b''), (b'\x00', b''), (b'\x01', b'error')):
                result.stdout, result.stderr = output, errors
                with self.assertRaises(RuntimeError): native_verdicts(Path('unused'), [b'packet'], [1])
        with self.assertRaises(ValueError): native_verdicts(Path('unused'), [b'packet'], [])

    def test_failed_build_invalidates_old_success_before_native_launch(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            (root/'docs/research/results').mkdir(parents=True)
            (root/'artifacts').mkdir()
            for folder in ('artifacts', 'docs/research/results'):
                (root/folder/(survey.VERSION+'.json')).write_text('{"status":"passed","old":true}')
            with patch('scripts.consensus_evidence.ROOT', root), \
                 patch('scripts.consensus_evidence.source_hashes', return_value={'frozen': 'hash'}), \
                 patch.object(survey, 'build_verifier', side_effect=RuntimeError('forced build failure')):
                with self.assertRaises(RuntimeError): survey.main()
            for folder in ('artifacts', 'docs/research/results'):
                report = json.loads((root/folder/(survey.VERSION+'.json')).read_text())
                self.assertEqual(report['status'], 'failed')
                self.assertEqual(report['completed_records'], 0)
                self.assertIsNone(report['in_progress_work'])
                self.assertNotIn('old', report)


if __name__ == '__main__':
    unittest.main()
