from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from reference.adaptive_retention import FutureSupplyRetainer
from reference.pool_campaign import PoolBudget, run_pool_campaign
from reference.search import exhaustive_solutions
from reference.sis import Profile
from scripts import adaptive_audit, adaptive_survey, consensus_evidence


class ToySolver:
    def acquire(self, profile, matrix, nodes, proofs):
        return {'proofs': tuple(exhaustive_solutions(profile, matrix))[:proofs],
                'work': {'nodes': 1, 'sparse_checks': 1}, 'reason': 'test-fixture-not-cost-model'}


class AdaptiveAuditTests(unittest.TestCase):
    def setUp(self):
        self.p = Profile(7, 1, 3, 8)
        self.label, self.stages = adaptive_survey.stages_for(self.p, 1)
        self.stages = tuple(stage[:2] for stage in self.stages)
        self.budget = PoolBudget(nodes=100, proofs=6)
        self.query = {'target': '0', 'policy': 'pool-all', 'retention': 'future-supply',
                      'decisions': 1, 'capacity': 3, 'combine': False, 'backend': 'sparse-first'}

    def snapshot(self, *, partial=False):
        retainer = FutureSupplyRetainer(0, decisions=1)
        records = []
        def checkpoint(campaign):
            records.append({'status': 'checkpoint', 'campaign': deepcopy(campaign),
                            'retention': deepcopy(retainer.snapshot())})
        campaign = run_pool_campaign(self.stages, 'pool-all', 0, ToySolver(), capacity=3,
                                     combine=False, budget=self.budget, retain=retainer, on_stage=checkpoint)
        return records[0] if partial else {'status': 'completed', 'campaign': campaign, 'retention': retainer.snapshot()}

    def test_replay_and_checkpoints_cover_selection_fallbacks(self):
        for partial in (False, True):
            snapshot = self.snapshot(partial=partial)
            # Echoing expected responses isolates transcript replay; actual native
            # generation/proof/score audit is exercised by the explicit survey.
            with patch.object(adaptive_audit, 'exchange') as exchange:
                exchange.side_effect = lambda *args: []
                with self.assertRaisesRegex(RuntimeError, 'independent adaptive'):
                    adaptive_audit.audit_snapshot(snapshot, self.stages, 'unused', query=self.query, budget=self.budget)
            self.assertEqual(snapshot['retention']['decisions'], 1)
        self.assertGreater(self.snapshot()['retention']['fifo_fallbacks'], 0)

    def test_tampered_retention_or_paid_work_refuses_evidence_before_native(self):
        for field in ('retention', 'nodes', 'vectors'):
            snapshot = self.snapshot()
            if field == 'retention':
                snapshot['retention']['records'][0]['chosen_eviction'] ^= 1
            elif field == 'nodes':
                snapshot['campaign']['work']['search_nodes'] += 1
            else:
                snapshot['campaign']['instances'][0]['acquired']['proofs'] = ((1, 0, 0),)
            with patch.object(adaptive_audit, 'exchange') as native:
                with self.assertRaises(RuntimeError):
                    adaptive_audit.audit_snapshot(snapshot, self.stages, 'unused', query=self.query, budget=self.budget)
                native.assert_not_called()

    def test_json_serialized_snapshot_reaches_native_audit(self):
        snapshot = json.loads(json.dumps(self.snapshot()))
        with patch.object(adaptive_audit, 'exchange', return_value=[]):
            with self.assertRaisesRegex(RuntimeError, 'independent adaptive'):
                adaptive_audit.audit_snapshot(snapshot, self.stages, 'unused', query=self.query, budget=self.budget)

    def test_coordinated_outer_charge_tampering_refuses_evidence(self):
        snapshot = self.snapshot()
        for instance in snapshot['campaign']['instances']:
            if 'acquired' in instance:
                instance['acquired']['work']['nodes'] = 0
        snapshot['campaign']['work']['search_nodes'] = 0
        for stage in snapshot['campaign']['stages']:
            stage['work']['search_nodes'] = 0
        with patch.object(adaptive_audit, 'exchange') as native:
            with self.assertRaisesRegex(RuntimeError, 'sparse accounting identity'):
                adaptive_audit.audit_snapshot(snapshot, self.stages, 'unused', query=self.query, budget=self.budget)
            native.assert_not_called()

    def test_censoring_keeps_unknown_unconditional_work_and_checkpoint_hits_separate(self):
        snapshot = self.snapshot(partial=True)
        snapshot.update(setup_ns=1, backend={'backend': 'mitm'})
        record = {'window': {'snapshot': snapshot, 'outcome': 'wall-timeout', 'logical_work_known': False,
                            'resource': {'elapsed_ns': 123, 'peak_job_commit_bytes': 32}},
                  'audit': {'hit_occurrences': 2}}
        summary = adaptive_survey.summarize([record])
        self.assertEqual(summary['completed_campaigns'], 0)
        self.assertEqual(summary['all_attempt_elapsed_ns'], 123)
        self.assertEqual(summary['checkpoint_hit_occurrences'], 2)
        self.assertIsNone(summary['all_attempt_work_per_hit'])
        self.assertFalse(summary['all_attempt_retention_work_known'])

    def test_matched_comparisons_do_not_treat_censored_pairs_as_equal(self):
        snapshot = self.snapshot()
        def record(name, known):
            return {'label': 'one', 'backend': 'mitm', 'wall_ms': 500, 'policy': 'pool-fallback',
                    'retention': name, 'window': {'logical_work_known': known, 'snapshot': snapshot}}
        result = adaptive_survey.paired_retention([record('fifo', True), record('future-supply', False)])
        self.assertEqual(result['both_completed_pairs'], 0)
        self.assertEqual(result['censored_or_incomplete_pairs'], 1)
        self.assertEqual(result['completed_pair_outcomes'], {})
        with self.assertRaisesRegex(RuntimeError, 'unpaired'):
            adaptive_survey.paired_retention([record('fifo', True)])

    def test_failed_build_invalidates_compact_and_raw_reports(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'docs/research/results').mkdir(parents=True)
            (root/'artifacts').mkdir()
            paths = [root/folder/'adaptive-retention-v1.json' for folder in ('docs/research/results', 'artifacts')]
            for path in paths:
                path.write_text('{"status":"passed"}')
            with patch.object(consensus_evidence, 'ROOT', root), patch.object(
                    consensus_evidence, 'source_hashes', return_value={}), patch.object(
                    adaptive_survey, 'build_lab', side_effect=RuntimeError('failed build')), patch(
                    'sys.argv', ['test', '--python', 'unused']):
                with self.assertRaisesRegex(RuntimeError, 'failed build'):
                    adaptive_survey.main()
            self.assertTrue(all(json.loads(p.read_text()) == {'status': 'running-or-incomplete'} for p in paths))


if __name__ == '__main__':
    unittest.main()
