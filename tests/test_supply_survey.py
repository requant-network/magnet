import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from reference.grinding import SCORE_DOMAIN, score_digest
from reference.header import LabHeader, encode_proof
from reference.sis import Profile
from scripts import consensus_evidence, supply_survey
from scripts.lab_driver import matrix_bytes


class SupplySurveyTests(unittest.TestCase):
    def setUp(self):
        self.profile = Profile(7, 1, 2, 8)
        self.header = LabHeader(bytes(32), bytes([1])*32, bytes([2])*32, 2, 200, 0, self.profile)

    def test_scans_full_pool_and_retains_zero_target_failures(self):
        pool = ((1, 0), (0, 1))
        expected = [self.header.seed()+matrix_bytes(((0, 0),))]
        for vector in pool:
            expected += [b'\x01', score_digest(self.header, vector), b'\x00', b'\x01']
        with patch.object(LabHeader, 'matrix', return_value=((0, 0),)), patch.object(
                supply_survey, 'exchange', return_value=expected):
            record, raw = supply_survey.measure_headers('unused', self.profile, pool,
                                                        (self.header,), targets=(0, 2**256))
        self.assertEqual(record['valid_count_histogram'], [0, 0, 1])
        self.assertEqual(record['work']['scores'], 2)
        self.assertEqual(record['work']['vector_checks'], 2)
        self.assertEqual(record['work']['matrix_entries'], 2)
        self.assertEqual(record['work']['score_bytes'], sum(
            len(SCORE_DOMAIN)+len(encode_proof(self.header, v)) for v in pool))
        self.assertEqual(record['native_audit_requests'], 9)
        self.assertEqual([r['observed_header_hits'] for r in record['targets']], [0, 1])
        self.assertEqual(len(raw[0]['digests']), 2)

    def test_native_disagreement_refuses_cohort_evidence(self):
        with patch.object(supply_survey, 'exchange', return_value=[]):
            with self.assertRaisesRegex(RuntimeError, 'independent generation'):
                supply_survey.measure_headers('unused', self.profile, ((1, 0),), (self.header,))

    def test_setup_only_native_generation_disagreement_is_rejected(self):
        response = {'work': dict.fromkeys(supply_survey.WORK_NAMES, 0),
                    'proofs': [(1, 0)], 'stop': 'proof-limit'}
        with patch.object(LabHeader, 'matrix', return_value=((0, 0),)), patch.object(
                supply_survey, 'run_requests', return_value=[response]), patch.object(
                supply_survey, 'exchange', return_value=[b'wrong generation', b'\x01']):
            with self.assertRaisesRegex(RuntimeError, 'independent setup'):
                supply_survey.acquire_pool('search', 'lab', self.profile, 'setup-test')

    def test_failed_setup_retains_all_attempts_and_work(self):
        response = {'work': {name: 3 for name in supply_survey.WORK_NAMES},
                    'proofs': [], 'stop': 'node-limit'}
        # The fake native response echoes only this test's requested generation.
        def echo(commands):
            header = LabHeader.decode(commands[0][5:])
            return [header.seed()+matrix_bytes(header.matrix())]
        with patch.object(supply_survey, 'run_requests', return_value=[response]), patch.object(
                supply_survey, 'exchange', side_effect=lambda _, commands: echo(commands)):
            pool, setup = supply_survey.acquire_pool('search', 'lab', self.profile, 'failed-setup')
        self.assertEqual(pool, ())
        self.assertEqual(setup['status'], 'nonce-cap-no-vector')
        self.assertEqual(setup['work']['headers'], 16)
        self.assertEqual(setup['native_work']['nodes'], 48)
        self.assertEqual(setup['native_audit_requests'], 16)
        self.assertEqual(len(setup['records']), 16)

    def test_cohort_duplicates_and_bounds_reject_before_native_audit(self):
        with patch.object(supply_survey, 'exchange') as native:
            for headers in ((), (self.header,)*2, (self.header,)*257, ('invalid',)):
                with self.assertRaises(ValueError):
                    supply_survey.measure_headers('unused', self.profile, ((1, 0),), headers)
            native.assert_not_called()

    def test_exact_space_mismatch_and_cap_are_errors(self):
        with patch.object(supply_survey, 'verify', return_value=False):
            with self.assertRaisesRegex(RuntimeError, 'exact matrix'):
                supply_survey.exact_case(self.profile, ((1, 0),))
        with self.assertRaisesRegex(ValueError, 'space cap'):
            supply_survey.exact_case(Profile(7, 4, 8, 8), ((1,)+(0,)*7,))

    def test_false_exact_evidence_rejected_under_optimized_python(self):
        code = ('from unittest.mock import patch\nfrom scripts import supply_survey\n'
                'from reference.sis import Profile\n'
                'with patch.object(supply_survey,"verify",return_value=False):\n'
                ' supply_survey.exact_case(Profile(7,1,2,8),((1,0),))\n')
        result = subprocess.run([sys.executable, '-O', '-c', code], capture_output=True, timeout=10)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b'exact matrix distribution disagreement', result.stderr)

    def test_failed_build_invalidates_both_reports(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'docs/research/results').mkdir(parents=True)
            (root/'artifacts').mkdir()
            paths = [root/folder/'precommitted-supply-v1.json'
                     for folder in ('docs/research/results', 'artifacts')]
            for path in paths:
                path.write_text('{"status":"passed"}')
            with patch.object(consensus_evidence, 'ROOT', root), patch.object(
                    consensus_evidence, 'source_hashes', return_value={}), patch.object(
                    supply_survey, 'build_lab', side_effect=RuntimeError('failed build')):
                with self.assertRaisesRegex(RuntimeError, 'failed build'):
                    supply_survey.main()
            self.assertTrue(all(json.loads(p.read_text()) == {'status': 'running-or-incomplete'} for p in paths))


if __name__ == '__main__':
    unittest.main()
