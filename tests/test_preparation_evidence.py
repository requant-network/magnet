"""D4 tamper rejection, wire bounds and evidence failure lifecycle."""

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from reference.preparation_campaign import run_preparation
from scripts.preparation_audits import audit_campaign
from scripts.preparation_worker import decode
from scripts import preparation_survey as survey
from scripts import window_driver
from scripts.window_worker import publish
from tests.test_kernel_reuse import ExactSolver


class PreparationEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.headers = survey.headers((3, 1, 2, 2), survey.LABELS[0])

    def test_wire_is_bounded_and_exact(self):
        payload = dict(version='WDP1', headers=[h.encode().hex() for h in self.headers], policy='cold')
        self.assertEqual(decode(json.dumps(payload).encode()), (self.headers, 'cold'))
        for mutation in ({'extra': 0}, {'version': 'WDP2'}, {'policy': 'sieve'}, {'headers': []},
                         {'headers': [self.headers[0].encode().hex().upper()]}, {'headers': ['00']}):
            with self.assertRaises(ValueError):
                decode(json.dumps({**payload, **mutation}).encode())
        with self.assertRaises(ValueError):
            decode(b'x'*65537)

    def test_audit_rejects_provenance_matrix_certificate_and_ledger_tampering(self):
        record = run_preparation(self.headers, 'kernel-cache', ExactSolver())
        audit_campaign(self.headers, record)
        hit = next(i for i, s in enumerate(record['stages']) if s['reused_from'])
        for mutation in ('donor', 'matrix', 'rank', 'ledger', 'fingerprint', 'score'):
            bad = json.loads(json.dumps(record))
            stage = bad['stages'][hit]
            if mutation == 'donor':
                stage['reused_from'] = self.headers[-1].encode().hex()
            elif mutation == 'matrix':
                stage['matrix'][0][0] = (stage['matrix'][0][0]+1) % 3
            elif mutation == 'rank':
                stage['certificate']['rank'] += 1
            elif mutation == 'ledger':
                bad['work']['cache_hits'] += 1
            elif mutation == 'fingerprint':
                stage['fingerprint_work']['pivots'] += 1
            else:
                proof_stage = next(s for s in bad['stages'] if s['scores'])
                proof_stage['scores'][0]['digest_hex'] = '00'*32
            with self.assertRaises(ValueError, msg=mutation):
                audit_campaign(self.headers, bad)

    def test_paid_stop_and_checkpoint_prefix_are_auditable(self):
        for options in ({'nodes': 1}, {'reductions': 1}):
            record = run_preparation(self.headers, 'cold', ExactSolver(), **options)
            audit_campaign(self.headers, record, **options)
        record = run_preparation(self.headers, 'kernel-cache', ExactSolver())
        record.pop('elapsed_ns')
        audit_campaign(self.headers, record)

    def test_failed_build_invalidates_success_and_retains_frozen_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            dest, raw, contract = [Path(directory)/p for p in ('report.json', 'raw.json', 'contract.md')]
            dest.write_text('{"status":"passed"}')
            raw.write_text('{"status":"passed"}')
            contract.write_text('frozen protocol')
            def begin(name):
                dest.write_text('{"status":"running-or-incomplete"}')
                raw.write_text('{"status":"running-or-incomplete"}')
                return dest, raw, {'test.py': 'sourcehash'}
            with patch.object(survey, 'begin_report', side_effect=begin), patch.object(survey, 'CONTRACT', contract), \
                    patch.object(survey, 'build_lab', side_effect=RuntimeError('build failed')):
                with self.assertRaisesRegex(RuntimeError, 'build failed'):
                    survey.main()
            self.assertEqual(json.loads(dest.read_bytes())['status'], 'failed-or-incomplete')
            result = json.loads(raw.read_bytes())
            self.assertTrue(result['comparisons_suppressed'])
            self.assertIsNone(result['executable_sha256'])
            self.assertEqual(result['contract_sha256'], hashlib.sha256(contract.read_bytes()).hexdigest())
            self.assertEqual(result['source_sha256'], {'test.py': 'sourcehash'})

    def test_worker_error_and_memory_error_retain_paid_checkpoint_and_resources(self):
        record = run_preparation(self.headers, 'cold', ExactSolver())
        for error, code in ((dict(status='worker-error', error_type='RuntimeError', message='failure'), 78),
                            (dict(status='memory-error'), 77)):
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve()
                def job(command, **kwargs):
                    dest = Path(command[3])
                    publish(dest.with_name('checkpoint-8.json'), dict(status='checkpoint', campaign=record))
                    publish(dest.with_name('error.json'), error)
                    return dict(status='exited', exit_code=code, elapsed_ms=100)
                with patch.object(window_driver, 'ROOT', root), patch.object(window_driver, 'run_job', side_effect=job):
                    result = window_driver.run_window('python', {}, wall_ms=15000, memory_mib=192, worker='preparation_worker.py')
                self.assertEqual(result['terminal_error'], error)
                self.assertEqual(result['snapshot']['campaign'], json.loads(json.dumps(record)))
                self.assertEqual(result['resource']['exit_code'], code)
                self.assertFalse(result['logical_work_known'])
                self.assertTrue(result['artifact_directory'].startswith('artifacts/'))

    def test_interruption_keeps_native_identity_and_unknown_current_work(self):
        with tempfile.TemporaryDirectory() as directory:
            dest, raw, contract, binary = [Path(directory)/p for p in ('report.json', 'raw.json', 'contract.md', 'lab.exe')]
            contract.write_bytes(b'contract')
            binary.write_bytes(b'native identity')
            interruption = KeyboardInterrupt()
            interruption.window_evidence = dict(resource=None, snapshot={'paid_prefix': 1},
                                                artifact_directory='artifacts/window-owned', logical_work_known=False)
            with patch.object(survey, 'begin_report', return_value=(dest, raw, {})), \
                    patch.object(survey, 'CONTRACT', contract), patch.object(survey, 'build_lab', return_value=binary), \
                    patch.object(survey, 'run_window', side_effect=interruption):
                with self.assertRaises(KeyboardInterrupt):
                    survey.main()
            result = json.loads(raw.read_bytes())
            self.assertEqual(result['executable_sha256'], hashlib.sha256(binary.read_bytes()).hexdigest())
            self.assertEqual(result['current']['execution'], 'unknown-unfinished')
            self.assertEqual(result['current']['window'], interruption.window_evidence)
            self.assertTrue(result['comparisons_suppressed'])

    def test_interrupted_job_attaches_checkpoint_and_owned_attempt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            def job(command, **kwargs):
                publish(Path(command[3]).with_name('checkpoint-1.json'), dict(status='checkpoint', campaign={'paid_prefix': 1}))
                raise KeyboardInterrupt()
            with patch.object(window_driver, 'ROOT', root), patch.object(window_driver, 'run_job', side_effect=job):
                try:
                    window_driver.run_window('python', {}, wall_ms=15000, memory_mib=192, worker='preparation_worker.py')
                except KeyboardInterrupt as error:
                    evidence = error.window_evidence
                else:
                    self.fail('interruption was swallowed')
            self.assertEqual(evidence['snapshot']['campaign'], {'paid_prefix': 1})
            self.assertIsNone(evidence['resource'])
            self.assertFalse(evidence['logical_work_known'])
            self.assertTrue(evidence['artifact_directory'].startswith('artifacts/'))


if __name__ == '__main__':
    unittest.main()
