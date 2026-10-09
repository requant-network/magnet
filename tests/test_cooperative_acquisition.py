import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from reference.component_meter import ComponentMeter, ComponentStop
from reference.cooperative_campaign import paid_verify, step
from reference.cooperative_solvers import ALGORITHMS, Acquisition
from reference.sis import Profile
from scripts.cooperative_audits import audit_record, oracle, verification_work
from scripts import cooperative_survey as survey


class CooperativeTests(unittest.TestCase):
    def test_meter_atomic_monotonic_snapshots_and_zero_weight(self):
        m = ComponentMeter(7)
        m.sync('matrix', dict(entries=3, shake_output_bytes=2000))
        self.assertEqual(m.used, 3)
        before = copy.deepcopy(m.report())
        for snapshot in ({'entries': 2}, {'entries': True}, {'entries': 3}, {1: 4}):
            with self.assertRaises(ValueError): m.sync('matrix', snapshot)
            self.assertEqual(m.report(), before)
        m.add('matrix', entries=4)
        with self.assertRaises(ComponentStop): m.check()
        m.add('cleanup', units=2)
        self.assertEqual(m.report()['overshoot'], 2)
        self.assertEqual(m.report()['post_boundary_units'], 2)

    def test_invalid_caps_and_inputs_reject(self):
        p = Profile(7, 1, 2, 5)
        for kwargs in ({'budget': True}, {'budget': 0}, {'budget': 1, 'pool_limit': 9},
                       {'budget': 1, 'proof_limit': False}):
            with self.assertRaises(ValueError): step(p, bytes(32), 'ball', 'exact', [], **kwargs)
        for algorithm, policy in (('unknown', 'exact'), ('ball', 'unknown')):
            with self.assertRaises(ValueError): step(p, bytes(32), algorithm, policy, [], budget=100)
        with self.assertRaises(ValueError): step(Profile(7, 1, 7, 8), bytes(32), 'ball', 'exact', [], budget=1)
        with self.assertRaises(ValueError): step(p, bytes(32), 'ball', 'exact', [(0, 0)], budget=1)

    def test_complete_solvers_match_independent_domains(self):
        for row in ((1, 2, 3), (0, 0, 0), (6, 1, 2)):
            p = Profile(7, 1, 3, 8)
            for algorithm in ALGORITHMS:
                source = Acquisition(p, (row,), algorithm, ComponentMeter(1000000))
                vectors = list(source.solutions())
                self.assertEqual(source.reason, 'domain-exhausted')
                self.assertEqual(set(vectors), oracle(p, (row,), algorithm))
                self.assertEqual(len(vectors), len(set(vectors)))

    def test_paid_validation_matches_independent_negative_and_positive_ledgers(self):
        p = Profile(7, 2, 3, 8)
        matrix = ((1, 2, 3), (2, 4, 6))
        vectors = [(2, -1, 0), (1, 0, 0), (-1, 0, 0), (0, 0, 0), (3, 0, 0)]
        meter = ComponentMeter(10000)
        actual = [paid_verify(p, matrix, v, meter, 'verify') for v in vectors]
        expected, flags = verification_work(p, matrix, vectors)
        self.assertEqual(actual, flags)
        self.assertEqual(meter.phases['verify'], expected)

    def test_preparation_stop_preserves_unknown_carry_as_excluded(self):
        p = Profile(7, 1, 2, 5)
        r = step(p, bytes(32), 'ball', 'exact', [(1, 0)], budget=1)
        self.assertEqual(r['unchecked_carry'], 1)
        self.assertEqual(r['retained'], [])
        self.assertEqual(r['solver_reason'], 'not-started')
        self.assertTrue(r['budget_reached'])

    def test_proof_transaction_commits_before_budget_stop(self):
        p = Profile(7, 1, 4, 8)
        r = step(p, bytes(32), 'sparse1', 'exact', [], budget=50)
        self.assertEqual(r['reason'], 'component-budget')
        self.assertEqual(len(r['acquired']), 1)
        self.assertEqual(r['acquired'], r['retained'])
        self.assertGreater(r['meter']['post_boundary_units'], 0)
        audit_record(p, r)

    def test_partial_carry_does_not_keep_unchecked_vectors(self):
        p = Profile(7, 1, 2, 5)
        with patch('reference.cooperative_campaign.expand_matrix', return_value=((0, 0),)):
            r = step(p, bytes(32), 'ball', 'exact', [(1, 0), (0, 1)], budget=27)
        self.assertEqual(len(r['carry']), 1)
        self.assertEqual(r['retained'], [(1, 0)])
        self.assertEqual(r['unchecked_carry'], 1)
        audit_record(p, r)

    def test_direction_retains_original_legal_vector(self):
        p = Profile(7, 1, 2, 8)
        with patch('reference.cooperative_campaign.expand_matrix', return_value=((0, 0),)):
            r = step(p, bytes(32), 'sparse2', 'direction', [(2, 0), (1, 0)], budget=50000)
        self.assertEqual(r['retained'][0], (2, 0))
        self.assertNotIn((1, 0), r['retained'])
        self.assertTrue(all(x['count'] == 1 for x in r['retained_direction_multiplicities']))
        audit_record(p, r)

    def test_simultaneous_proof_and_budget_flags(self):
        p = Profile(7, 1, 2, 5)
        with patch('reference.cooperative_campaign.expand_matrix', return_value=((0, 0),)):
            full = step(p, bytes(32), 'sparse1', 'exact', [], budget=50000, proof_limit=1)
            r = step(p, bytes(32), 'sparse1', 'exact', [], budget=full['meter']['used'], proof_limit=1)
        self.assertTrue(r['proof_cap_hit'])
        self.assertTrue(r['budget_reached'])
        self.assertEqual(r['reason'], 'proof-limit')
        audit_record(p, r)

    def test_last_sparse_candidate_preserves_exhaustion_flag_on_stop(self):
        p = Profile(7, 1, 1, 1)
        with patch('reference.cooperative_campaign.expand_matrix', return_value=((0,),)):
            full = step(p, bytes(32), 'sparse1', 'exact', [], budget=50000)
            r = step(p, bytes(32), 'sparse1', 'exact', [], budget=full['meter']['used'])
        self.assertTrue(r['domain_exhausted'])
        self.assertTrue(r['budget_reached'])
        self.assertEqual(r['acquired'], [(1,)])

    def test_closes_legacy_iterator_and_flushes_paid_deltas(self):
        p = Profile(7, 1, 4, 8)
        for algorithm in ('ball', 'mitm'):
            source = Acquisition(p, ((0,)*4,), algorithm, ComponentMeter(1000000))
            iterator = source.solutions()
            next(iterator)
            iterator.close()
            self.assertEqual(source.engine.reason, 'interrupted')
            self.assertEqual(source.reason, 'interrupted')
            self.assertGreater(source.meter.used, 0)

    def test_evidence_tampering_blocked(self):
        p = Profile(7, 1, 4, 8)
        r = step(p, bytes(32), 'sparse2', 'exact', [], budget=5000)
        audit_record(p, r)
        for phase, counter in (('matrix', 'entries'), ('verification', 'matrix_terms'), ('retention', 'comparisons')):
            broken = copy.deepcopy(r)
            broken['meter']['phases'][phase][counter] += 1
            with self.assertRaises(RuntimeError): audit_record(p, broken)
        for key in ('overlaps', 'overflow', 'unchecked_carry'):
            broken = copy.deepcopy(r)
            broken[key] += 1
            with self.assertRaises(RuntimeError): audit_record(p, broken)
        broken = copy.deepcopy(r)
        broken['retained_direction_multiplicities'] = []
        with self.assertRaises(RuntimeError): audit_record(p, broken)
        for phase, key in (('setup', 'shape_entries'), ('solver_setup', 'template_visits')):
            broken = copy.deepcopy(r)
            difference = broken['meter']['phases'][phase][key]
            broken['meter']['phases'][phase][key] = 0
            broken['meter']['used'] -= difference
            with self.assertRaises(RuntimeError): audit_record(p, broken)
        stopped = step(p, bytes(32), 'sparse2', 'exact', [], budget=750)
        for key, value in (('reason', 'proof-limit'), ('solver_reason', 'domain-exhausted')):
            broken = copy.deepcopy(stopped)
            broken[key] = value
            with self.assertRaises(RuntimeError): audit_record(p, broken)
        broken = copy.deepcopy(stopped)
        broken['meter']['first_boundary']['used'] = broken['meter']['used']+1
        broken['meter']['post_boundary_units'] = -1
        with self.assertRaises(RuntimeError): audit_record(p, broken)

    def test_legacy_materialization_cannot_be_removed_from_reconciled_total(self):
        p = Profile(7, 1, 4, 8)
        r = step(p, bytes(32), 'ball', 'exact', [], budget=50000)
        audit_record(p, r)
        broken = copy.deepcopy(r)
        amount = broken['meter']['phases'].pop('solver_output')['vector_entries']
        broken['meter']['used'] -= amount
        with self.assertRaises(RuntimeError): audit_record(p, broken)

    def test_legacy_exhaustion_unobserved_at_closed_yield(self):
        p = Profile(7, 1, 1, 1)
        with patch('reference.cooperative_campaign.expand_matrix', return_value=((0,),)):
            for algorithm in ('ball', 'mitm'):
                full = step(p, bytes(32), algorithm, 'exact', [], budget=50000)
                stopped = step(p, bytes(32), algorithm, 'exact', [], budget=full['meter']['used'])
                self.assertEqual(stopped['acquired'], [(1,)])
                self.assertTrue(stopped['budget_reached'])
                self.assertFalse(stopped['domain_exhausted'])

    def test_labels_share_schedule_and_repeat_only_control(self):
        p = Profile(*survey.PROFILES[0])
        self.assertEqual(len({survey.label_for(p, 'fresh', i) for i in range(4)}), 4)
        self.assertEqual({survey.label_for(p, 'control', i) for i in range(4)}, {survey.label_for(p, 'fresh', 0)})

    def test_failed_build_invalidates_old_evidence(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            (root/'docs/research/results').mkdir(parents=True)
            (root/'artifacts').mkdir()
            with patch('scripts.consensus_evidence.ROOT', root), \
                 patch('scripts.consensus_evidence.source_hashes', return_value={}), \
                 patch.object(survey, 'build_verifier', side_effect=RuntimeError('forced')):
                with self.assertRaises(RuntimeError): survey.main()
            for folder in ('artifacts', 'docs/research/results'):
                r = json.loads((root/folder/(survey.VERSION+'.json')).read_text())
                self.assertEqual(r['status'], 'failed')
                self.assertIsNone(r['in_progress_work'])


if __name__ == '__main__':
    unittest.main()
