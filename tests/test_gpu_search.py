"""Independent domain, truncation and accounting tests without CUDA dependency."""

import itertools
import unittest

from reference.gpu_search import candidates, search
from reference.sis import Profile, verify
from scripts.gpu_search_survey import reconcile, schedule


class SparseGpuSearchTests(unittest.TestCase):
    def test_domain_equals_exhaustive_unit_sparse_inputs(self):
        for m in range(1, 6):
            p = Profile(7, 1, m, 2)
            actual = list(candidates(p))
            expected = [v for v in itertools.product((-1, 0, 1), repeat=m)
                        if 1 <= sum(x*x for x in v) <= 2 and next(x for x in v if x) > 0]
            self.assertEqual(set(actual), set(expected))
            self.assertEqual(len(actual), len(set(actual)))
            self.assertEqual(len(actual), m*m)

    def test_frozen_order_and_b2_one(self):
        p = Profile(7, 1, 3, 2)
        self.assertEqual(list(candidates(p)), [(1, 0, 0), (0, 1, 0), (0, 0, 1),
            (1, 1, 0), (1, -1, 0), (1, 0, 1), (1, 0, -1), (0, 1, 1), (0, 1, -1)])
        self.assertEqual(list(candidates(Profile(7, 1, 3, 1))), [(1, 0, 0), (0, 1, 0), (0, 0, 1)])

    def test_full_set_independent_oracle(self):
        for q in (2, 7):
            p = Profile(q, 2, 3, 2)
            a = [[1, 1, 0], [0, 0, 0]]
            result = search(p, a, backend='python', batch_size=2)
            expected = [v for v in candidates(p) if verify(p, a, v)]
            self.assertEqual(result['proofs'], expected)
            self.assertTrue(result['all_proofs_returned'])
            self.assertEqual(result['work']['generated'], 9)

    def test_proof_cap_pays_for_chunk_tail(self):
        result = search(Profile(7, 1, 3, 2), [[0]*3], backend='python', proof_limit=1, batch_size=4)
        self.assertEqual(result['proofs'], [(1, 0, 0)])
        self.assertEqual(result['work']['screened'], 4)
        self.assertEqual(result['work']['accepted_seen'], 4)
        self.assertEqual(result['reason'], 'proof-limit')
        self.assertFalse(result['all_proofs_returned'])

    def test_caps_exhaustion_and_last_chunk_precedence(self):
        p = Profile(7, 1, 2, 2)
        limited = search(p, [[0, 0]], backend='python', candidate_limit=3, batch_size=4)
        self.assertEqual((limited['reason'], limited['work']['screened']), ('candidate-limit', 3))
        exhausted = search(p, [[0, 0]], backend='python', proof_limit=4, batch_size=4)
        self.assertEqual(exhausted['reason'], 'proof-limit')
        self.assertTrue(exhausted['domain_exhausted'])
        self.assertTrue(exhausted['all_proofs_returned'])
        miss = search(Profile(7, 1, 1, 1), [[1]], backend='python', candidate_limit=1)
        self.assertEqual(miss['reason'], 'domain-exhausted')
        self.assertTrue(miss['all_proofs_returned'])

    def test_invalid_arguments_reject_before_optional_runtime(self):
        p = Profile(7, 1, 2, 2)
        for args in ({'candidate_limit': True}, {'candidate_limit': 16385}, {'proof_limit': 0},
                     {'batch_size': 257}, {'backend': 'other'}):
            with self.assertRaises(ValueError):
                search(p, [[1, 2]], **({'backend': 'cuda'} | args))
        with self.assertRaises(ValueError):
            search(p, [[7, 0]], backend='cuda')

    def test_all_failed_proposals_and_payload_ledgers(self):
        p = Profile(17, 2, 2, 2)
        r = search(p, [[1, 2], [0, 1]], backend='python', batch_size=3)
        self.assertEqual(r['proofs'], [])
        self.assertEqual(r['work']['batches'], 2)
        self.assertEqual(r['work']['matrix_grid_slots'], 16)
        self.assertEqual(r['work']['explicit_h2d_bytes'], 0)
        self.assertEqual(r['work']['explicit_d2h_bytes'], 0)

    def test_comparison_refuses_output_or_charge_tampering(self):
        p = Profile(7, 1, 3, 2)
        a = search(p, [[0, 0, 0]], backend='python')
        b = search(p, [[0, 0, 0]], backend='python')
        b['work']['screened'] = 0
        with self.assertRaisesRegex(RuntimeError, 'ledger'):
            reconcile(a, b)
        b = search(p, [[0, 0, 0]], backend='python')
        b['proofs'] = b['proofs'][1:]
        with self.assertRaisesRegex(RuntimeError, 'proofs'):
            reconcile(a, b)

    def test_schedule_preserves_seeded_and_boundary_cases(self):
        jobs = schedule()
        self.assertEqual(len(jobs), 42)
        self.assertEqual(sum(j['fixture'] is None for j in jobs), 30)
        self.assertEqual(len({j['seed_hex'] for j in jobs if j['seed_hex']}), 10)
        self.assertTrue(any(j['profile']['n'] == 64 for j in jobs))
        self.assertTrue(any(j['profile']['b2'] == 1 for j in jobs))


if __name__ == '__main__':
    unittest.main()
