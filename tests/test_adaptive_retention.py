from dataclasses import asdict
import json
import unittest
from unittest.mock import patch

from reference.adaptive_retention import FutureSupplyRetainer
from reference.header import LabHeader
from reference.pool_campaign import PoolBudget, run_pool_campaign
from reference.sis import Profile
from scripts.adaptive_worker import decode


class FixedSolver:
    def acquire(self, profile, matrix, nodes, proofs):
        return {'proofs': ((1, 0, 0), (0, 1, 0), (0, 0, 1), (0, 2, 0)),
                'work': {'nodes': 1}, 'reason': 'test-fixture-not-cost-model'}


class AdaptiveRetentionTests(unittest.TestCase):
    def setUp(self):
        self.profile = Profile(7, 1, 3, 8)
        self.header = LabHeader(bytes(32), bytes([1])*32, bytes([2])*32, 1, 100, 0, self.profile)
        self.candidates = ((1, 0, 0), (0, 1, 0), (0, 0, 1), (0, 2, 0))

    def test_drops_a_redundant_event_instead_of_fifo_independent_vector(self):
        retainer = FutureSupplyRetainer(2**256)
        selected = retainer(self.profile, self.candidates, 3)
        self.assertEqual(selected, (self.candidates[0], self.candidates[2], self.candidates[3]))
        # Three independent events: 1-(6/7)^3. FIFO has only two: 1-(6/7)^2.
        record = retainer.snapshot()['records'][0]
        self.assertEqual(record['chosen_eviction'], 1)
        self.assertEqual(record['probabilities'][1], {'numerator': 127, 'denominator': 343})
        self.assertEqual(record['probabilities'][0], {'numerator': 13, 'denominator': 49})
        self.assertEqual(retainer.evaluations, 4)

    def test_zero_target_tie_is_fifo_and_budget_persists(self):
        retainer = FutureSupplyRetainer(0, decisions=1)
        self.assertEqual(retainer(self.profile, self.candidates, 3), self.candidates[1:])
        for _ in range(5):
            self.assertEqual(retainer(self.profile, self.candidates, 3), self.candidates[1:])
        snapshot = retainer.snapshot()
        self.assertEqual(snapshot['decisions'], 1)
        self.assertEqual(snapshot['evaluations'], 4)
        self.assertEqual(snapshot['fifo_fallbacks'], 5)
        self.assertGreater(snapshot['rank_arithmetic_units'], 0)

    def test_capacity_one_and_two_keep_order_and_evaluate_all_options(self):
        for capacity in (1, 2):
            retainer = FutureSupplyRetainer(2**255)
            candidates = self.candidates[:capacity+1]
            self.assertEqual(retainer(self.profile, candidates, capacity), candidates[1:])
            self.assertEqual(retainer.evaluations, capacity+1)

    def test_campaign_retention_changes_only_future_pool_not_acquired_score_order(self):
        with patch.object(LabHeader, 'matrix', return_value=((0, 0, 0),)):
            fifo = run_pool_campaign([[self.header]], 'pool-all', 0, FixedSolver(), capacity=3, combine=False)
            retainer = FutureSupplyRetainer(2**256)
            ranked = run_pool_campaign([[self.header]], 'pool-all', 0, FixedSolver(), capacity=3,
                                       combine=False, retain=retainer)
        self.assertEqual(fifo['pool'], self.candidates[1:])
        self.assertEqual(ranked['pool'], (self.candidates[0], self.candidates[2], self.candidates[3]))
        self.assertEqual(fifo['scores'], ranked['scores'])
        self.assertEqual(fifo['work'], ranked['work'])
        self.assertEqual(retainer.snapshot()['decisions'], 1)

    def test_default_fifo_equals_explicit_fifo_callback(self):
        with patch.object(LabHeader, 'matrix', return_value=((0, 0, 0),)):
            a = run_pool_campaign([[self.header]]*2, 'pool-all', 0, FixedSolver(), capacity=3, combine=False)
            b = run_pool_campaign([[self.header]]*2, 'pool-all', 0, FixedSolver(), capacity=3,
                                  combine=False, retain=lambda p, c, n: c[1:])
        a.pop('elapsed_ns'); b.pop('elapsed_ns')
        self.assertEqual(a, b)

    def test_invalid_callback_cannot_introduce_or_reorder_proofs(self):
        invalid = (tuple(reversed(self.candidates[1:])), (self.candidates[0],)*3,
                   ((1, 1, 1),)+self.candidates[2:], list(self.candidates[1:]),
                   ((True, 0, 0),)+self.candidates[2:])
        for selected in invalid:
            with patch.object(LabHeader, 'matrix', return_value=((0, 0, 0),)):
                with self.assertRaisesRegex(RuntimeError, 'retained subset/order'):
                    run_pool_campaign([[self.header]], 'pool-all', 0, FixedSolver(), capacity=3,
                                      retain=lambda p, c, n: selected)

    def test_last_score_hit_still_wins_and_retention_does_not_reset_on_stage(self):
        retain = FutureSupplyRetainer(2**255, decisions=1)
        with patch.object(LabHeader, 'matrix', return_value=((0, 0, 0),)):
            result = run_pool_campaign([[self.header]]*3, 'pool-all', 2**256, FixedSolver(), capacity=3,
                                       combine=False, budget=PoolBudget(scores=1), retain=retain)
        self.assertEqual(result['stages'][0]['reason'], 'score-hit')
        self.assertEqual(result['stages'][1]['reason'], 'score-limit')
        self.assertEqual(result['stages'][2]['reason'], 'not-visited')
        self.assertEqual(retain.snapshot()['decisions'], 1)

    def test_strict_worker_rejects_unknown_fields_and_type_confusion(self):
        query = {'version': 'WAX1', 'backend': 'mitm', 'policy': 'pool-all', 'target': '1',
                 'stages': [[self.header.encode().hex()]], 'capacity': 3, 'combine': False,
                 'budget': asdict(PoolBudget()), 'seed': 1, 'retention': 'future-supply', 'decisions': 64}
        self.assertEqual(decode(json.dumps(query).encode())[1][0][0], self.header)
        for key, value in (('version', 'WXP1'), ('retention', 'hindsight'), ('capacity', 4),
                           ('decisions', True), ('decisions', 65), ('target', '01'), ('other', 1)):
            with self.assertRaises(ValueError):
                decode(json.dumps({**query, key: value}).encode())
        for capacity in (0, 4, True):
            with self.assertRaises(ValueError):
                FutureSupplyRetainer(1)(self.profile, self.candidates, capacity)


if __name__ == '__main__':
    unittest.main()
