"""Frozen cohort, independent ledger tampering and failed-pair evidence tests."""

import copy
import json
from pathlib import Path
import tempfile
import subprocess
import unittest
from unittest.mock import patch

from reference.matched_coefficients import search
from reference.sis import Profile
from scripts import matched_coefficient_survey as study
from scripts import run_matched_coefficients as runner
from scripts.matched_coefficient_audits import audit_ledger
from scripts.coefficient_journal import Journal, recover
from tests.test_matched_coefficients import FakeLibrary


class MatchedCoefficientSurveyTests(unittest.TestCase):
    def test_frozen_shape_and_shared_challenges(self):
        jobs = study.jobs()
        self.assertEqual(len(jobs), 240)
        self.assertEqual(sum(label['kind'] == 'seeded' for _, _, _, label in jobs), 144)
        self.assertEqual(len({label['seed_hex'] for _, _, _, label in jobs if label['kind'] == 'seeded'}), 12)
        self.assertEqual([name for name, _, _ in study.fixtures()],
                         ['zero', 'triple-only', 'nonunit-only', 'scalar-copy', 'singleton', 'late-witness'])

    def test_independent_ledger_rejects_census_tail_and_byte_tampering(self):
        p, matrix = Profile(17, 1, 2, 5), [[0, 0]]
        settings = dict(bound=2, candidate_limit=20000, proof_limit=1, batch_size=7)
        result = search(p, matrix, library=FakeLibrary(p, matrix, 2), backend='fused-gpu', **settings)
        audit_ledger(p, matrix, settings, result)
        for mutate in (lambda r: r['weights']['1'].__setitem__('tested', 0),
                       lambda r: r.__setitem__('accepted_tail_discarded', 0),
                       lambda r: r['work'].__setitem__('explicit_d2h_bytes', 0)):
            damaged = copy.deepcopy(result)
            mutate(damaged)
            with self.assertRaises(RuntimeError):
                audit_ledger(p, matrix, settings, damaged)

    def test_no_summary_for_partial_or_zero_sample_pair(self):
        record = dict(outputs={'native-cpu': dict(elapsed_ns=1)})
        with self.assertRaises(RuntimeError):
            study.summarize([record])
        record['outputs']['fused-gpu'] = dict(elapsed_ns=0)
        with self.assertRaises(RuntimeError):
            study.summarize([record])

    def test_independent_ledger_rejects_proof_cap_overrun_at_domain_boundary(self):
        p, matrix = Profile(17, 1, 3, 5), [[0, 0, 0]]
        result = search(p, matrix, library=FakeLibrary(p, matrix, 2), backend='native-cpu',
                        bound=2, proof_limit=1, batch_size=4096)
        result['work']['batches'], result['chunk_width'] = 4, 7
        with self.assertRaises(RuntimeError):
            audit_ledger(p, matrix, dict(bound=2, proof_limit=1, candidate_limit=20000, batch_size=7), result)

    def test_interrupted_child_recovers_completed_and_partial_pairs(self):
        with tempfile.TemporaryDirectory() as folder:
            paths = [Path(folder)/'compact.json', Path(folder)/'raw.json', {'f': 'hash'}]
            journal = Journal(paths[1].with_suffix('.progress.jsonl'), paths[2])
            for index, backends in ((0, ('native-cpu', 'fused-gpu')), (1, ('native-cpu',))):
                journal.event(dict(kind='pair', record=dict(case=index, repetition=0, outputs={})))
                for backend in backends:
                    journal.event(dict(kind='output', case=index, repetition=0, backend=backend, output=dict(elapsed_ns=1)))
            journal.event(dict(kind='pending', current=dict(stage='search', backend='fused-gpu', unknown_work=True)))
            runner.interrupted_failure(paths, subprocess.TimeoutExpired('test', 240))
            raw = json.loads(paths[1].read_text())
            self.assertEqual(raw['completed_paired_records'], 1)
            self.assertEqual(len(raw['incomplete_records']), 2)
            self.assertEqual(len(raw['incomplete_records'][1]['outputs']), 1)
            self.assertFalse(raw['timing_ratios_published'])

    def test_journal_discards_partial_append_and_rejects_stale_sources(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'progress.jsonl'
            Journal(path, {'f': 'hash'})
            with path.open('ab') as stream:
                stream.write(b'{"kind":')
            records, current = recover(path, {'f': 'hash'})
            self.assertEqual(records, [])
            self.assertTrue(current['unknown_work'])
            with self.assertRaises(RuntimeError):
                recover(path, {'f': 'different'})

    def test_failure_retains_partial_pair_unknown_work_without_ratios(self):
        with tempfile.TemporaryDirectory() as folder:
            paths = [Path(folder)/'compact.json', Path(folder)/'raw.json']
            records = [dict(outputs={'native-cpu': dict(elapsed_ns=1)})]
            study.failure_report(paths, RuntimeError('test'), records, {}, dict(stage='GPU', unknown_work=True))
            compact, raw = [json.loads(p.read_text()) for p in paths]
            self.assertEqual(compact['status'], 'failed')
            self.assertFalse(compact['timing_ratios_published'])
            self.assertTrue(compact['in_progress_work']['unknown_work'])
            self.assertEqual(raw['incomplete_records'], records)

    def test_build_invalidates_previous_success(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root/'artifacts').mkdir()
            (root/'docs/research/results').mkdir(parents=True)
            paths = [root/'docs/research/results'/f'{study.VERSION}.json', root/'artifacts'/f'{study.VERSION}.json']
            for path in paths:
                path.write_text('{"status":"passed"}')
            journal_path = paths[1].with_suffix('.progress.jsonl')
            old_journal = Journal(journal_path, {})
            old_journal.event(dict(kind='pair', record=dict(case=0, repetition=0, outputs={})))
            old_journal.event(dict(kind='output', case=0, repetition=0, backend='native-cpu', output=dict(elapsed_ns=1)))
            def fail(*args, **kwargs):
                for path in paths:
                    self.assertEqual(json.loads(path.read_text())['status'], 'running-or-incomplete')
                self.assertEqual(recover(journal_path, {})[0], [])
                runner.interrupted_failure([*paths, {}], subprocess.TimeoutExpired('test', 240))
                self.assertEqual(json.loads(paths[1].read_text())['incomplete_records'], [])
                raise RuntimeError('test build failure')
            with patch('scripts.consensus_evidence.ROOT', root), \
                    patch('scripts.consensus_evidence.source_hashes', return_value={}), \
                    patch('sys.argv', ['runner']), patch.object(runner.subprocess, 'run', side_effect=fail):
                with self.assertRaises(RuntimeError):
                    runner.main()
            self.assertTrue(all(json.loads(p.read_text())['status'] == 'failed' for p in paths))


if __name__ == '__main__':
    unittest.main()
