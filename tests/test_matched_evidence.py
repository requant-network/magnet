"""Census, provenance handoff, failed pair and build invalidation gates."""

import copy
import json
from pathlib import Path
import tempfile
import subprocess
import unittest
from unittest.mock import patch

from reference.matched_sparse import SearchFailure
from reference.sis import Profile
from reference.sparse_domain import reference_search
from scripts import run_matched_sparse
from scripts.matched_sparse_audits import audit_ledger, reconcile
from scripts.matched_sparse_cases import jobs, matrix_for
from scripts.matched_sparse_survey import failure_report, summarize


class MatchedEvidenceTests(unittest.TestCase):
    def result(self, backend='native-cpu'):
        p = Profile(7, 1, 3, 3)
        settings = dict(max_weight=3, candidate_limit=13, proof_limit=1, batch_size=13)
        result = reference_search(p, [[0]*3], **settings)
        result.update(backend=backend, elapsed_ns=100, logical_host_matrix_bytes=24,
                      logical_device_bytes=37 if backend == 'fused-gpu' else 0)
        result['work'].update(host_matrix_copy_bytes=24, explicit_h2d_bytes=24 if backend == 'fused-gpu' else 0,
                              explicit_d2h_bytes=13 if backend == 'fused-gpu' else 0)
        return p, settings, result

    def test_full_schedule_is_seeded_and_family_pairs_share_inputs(self):
        pending = jobs()
        self.assertEqual(len(pending), 84)
        self.assertEqual(pending, jobs())
        self.assertEqual(len({j['seed_hex'] for j in pending if j['seed_hex']}), 10)
        pairs = {}
        for job in pending:
            key = (job['label'], job['candidate_limit'], job['proof_limit'], job['batch_size'])
            matrix = matrix_for(job)
            if key in pairs:
                self.assertEqual(matrix, pairs[key])
            pairs[key] = matrix
        self.assertEqual(len(pairs), 42)

    def test_weight_census_corruption_blocks_evidence(self):
        p, settings, original = self.result()
        audit_ledger(p, settings, original)
        for key, value in (('domain', 3), ('tested', 3), ('discarded', 0), ('accepted', 5), ('emitted', 5)):
            broken = copy.deepcopy(original)
            broken['weights']['3'][key] = value
            with self.assertRaises(RuntimeError): audit_ledger(p, settings, broken)

    def test_transfer_ledger_corruption_blocks_evidence(self):
        p, settings, original = self.result('fused-gpu')
        for key in ('host_matrix_copy_bytes', 'explicit_h2d_bytes', 'explicit_d2h_bytes', 'support_slots', 'scheduled_column_reads'):
            broken = copy.deepcopy(original)
            broken['work'][key] += 1
            with self.assertRaises(RuntimeError): audit_ledger(p, settings, broken)

    def test_exact_prefix_and_tail_reconciliation(self):
        _, _, original = self.result()
        for key in ('unchecked_domain_suffix', 'accepted_tail_discarded', 'candidate_cap_truncates_domain',
                    'candidate_censored', 'proof_cap_hit'):
            broken = copy.deepcopy(original)
            broken[key] = not original[key] if type(original[key]) is bool else original[key]+1
            with self.assertRaises(RuntimeError): reconcile(original, broken)

    def test_failure_report_preserves_unpaired_record_without_ratios(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = (Path(directory)/'compact.json', Path(directory)/'raw.json')
            diagnostic = dict(stage='mask-completion', elapsed_ns=50, completed_screened=7, completed_batches=1)
            records = [dict(outputs={'native-cpu': {'elapsed_ns': 100}})]
            failure_report(paths, SearchFailure(diagnostic), records, {'test.py': 'digest'}, 0)
            compact, raw = [json.loads(path.read_text()) for path in paths]
            self.assertEqual(compact['status'], 'failed')
            self.assertEqual(compact['failure']['completed_screened'], 7)
            self.assertEqual(compact['completed_paired_records'], 0)
            self.assertFalse(compact['timing_ratios_published'])
            self.assertEqual(raw['incomplete_records'], records)

    def test_failed_build_invalidates_previous_success(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = (root/'compact.json', root/'raw.json', {})
            for path in paths[:2]: path.write_text('{"status":"passed"}')
            with patch.object(run_matched_sparse, 'begin_report', return_value=paths), \
                    patch.object(run_matched_sparse.subprocess, 'run', side_effect=RuntimeError('failed build')), \
                    patch('sys.argv', ['run_matched_sparse.py']):
                with self.assertRaises(RuntimeError): run_matched_sparse.main()
            for path in paths[:2]: self.assertEqual(json.loads(path.read_text())['status'], 'failed')

    def test_paired_times_keep_repetitions_and_disallow_zero_cost(self):
        records = []
        for repeat in range(3):
            _, _, cpu = self.result()
            _, _, gpu = self.result('fused-gpu')
            cpu['elapsed_ns'], gpu['elapsed_ns'] = 100+10*repeat, 200+20*repeat
            records.append(dict(repetition=repeat, job=dict(group='fixture', max_weight=3),
                                outputs={'native-cpu': cpu, 'fused-gpu': gpu}))
        result = summarize(records)['fixture/weight3']
        self.assertEqual(result['descriptive_cpu_over_gpu_ratios'], [0.5]*3)
        self.assertEqual(result['per_case_ratio_median'], 0.5)
        records[0]['outputs']['fused-gpu']['elapsed_ns'] = 0
        # One zero per-repeat input must refuse ratio publication.
        with self.assertRaises(RuntimeError): summarize(records)

    def test_positive_group_sum_cannot_hide_zero_or_negative_individual_time(self):
        records = []
        for repeat in range(3):
            for _ in range(2):
                _, _, cpu = self.result()
                _, _, gpu = self.result('fused-gpu')
                records.append(dict(repetition=repeat, job=dict(group='fixture', max_weight=3),
                                    outputs={'native-cpu': cpu, 'fused-gpu': gpu}))
        for value in (0, -1, True):
            records[0]['outputs']['native-cpu']['elapsed_ns'] = value
            with self.assertRaisesRegex(RuntimeError, 'individual timing'): summarize(records)

    def test_native_replacement_during_cuda_build_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = (root/'compact.json', root/'raw.json', {})
            binaries = {name: root/name for name in ('sis-column', 'sis-verify')}
            for binary in binaries.values(): binary.write_bytes(b'original')
            output = b'\n'.join(json.dumps(dict(reason='compiler-artifact', executable=str(path),
                                                target=dict(name=name, kind=['bin']))).encode()
                                for name, path in binaries.items())
            calls = 0
            def build(command, **kwargs):
                nonlocal calls
                calls += 1
                if calls == 1: return subprocess.CompletedProcess(command, 0, output, b'')
                binaries['sis-column'].write_bytes(b'replacement')
                return subprocess.CompletedProcess(command, 0)
            with patch.object(run_matched_sparse, 'ROOT', root), \
                    patch.object(run_matched_sparse, 'begin_report', return_value=paths), \
                    patch.object(run_matched_sparse, 'source_hashes', return_value={}), \
                    patch.object(run_matched_sparse.subprocess, 'run', side_effect=build), \
                    patch('sys.argv', ['run_matched_sparse.py']):
                with self.assertRaisesRegex(RuntimeError, 'native binary changed'): run_matched_sparse.main()
            self.assertEqual(calls, 2)
            self.assertEqual(json.loads(paths[0].read_text())['status'], 'failed')


if __name__ == '__main__':
    unittest.main()
