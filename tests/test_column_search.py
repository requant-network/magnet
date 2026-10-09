"""Column optimization contracts using independent dense CPU baseline."""

import itertools
import unittest

from reference.column_search import search, supports, support_at, vector_for
from reference.gpu_search import candidates, search as dense_search
from reference.sis import Profile
from scripts.column_search_survey import audit_ledger, jobs, reconcile


class ColumnSearchTests(unittest.TestCase):
    def test_support_decode_full_order_is_independent(self):
        for m in range(1, 9):
            p = Profile(17, 1, m, 2)
            starts = [i*(2*m-i-1)//2 for i in range(m)]
            expected = list(candidates(p))
            actual = [vector_for(m, s) for s in supports(p)]
            decoded = [vector_for(m, support_at(m, i, starts)) for i in range(m*m)]
            self.assertEqual(actual, expected)
            self.assertEqual(decoded, expected)

    def test_every_small_matrix_matches_dense(self):
        for q in (2, 3):
            p = Profile(q, 1, 3, 2)
            for row in itertools.product(range(q), repeat=3):
                for cap, proof, batch in ((9, 256, 2), (5, 1, 4)):
                    kwargs = dict(candidate_limit=cap, proof_limit=proof, batch_size=batch)
                    dense = dense_search(p, [row], backend='python', **kwargs)
                    sparse = search(p, [row], backend='python-columns', **kwargs)
                    for key in ('domain', 'reason', 'domain_exhausted', 'all_proofs_returned', 'proofs'):
                        self.assertEqual(sparse[key], dense[key])
                    self.assertEqual(sparse['work']['accepted_seen'], dense['work']['accepted_seen'])

    def test_no_materialization_for_misses(self):
        p = Profile(17, 2, 2, 2)
        r = search(p, [[1, 2], [0, 1]], backend='python-columns')
        self.assertEqual(r['work']['vector_entries'], 0)
        self.assertEqual(r['work']['support_entries'], 12)
        self.assertEqual(r['work']['scheduled_column_reads'], 16)

    def test_tail_costs_and_exact_boundary(self):
        p = Profile(7, 1, 3, 2)
        r = search(p, [[0]*3], backend='python-columns', proof_limit=1, batch_size=7)
        self.assertEqual((r['work']['screened'], r['work']['accepted_seen'], r['work']['vector_entries']), (7, 7, 3))
        exact = search(p, [[0]*3], backend='python-columns', candidate_limit=9, proof_limit=9, batch_size=4096)
        self.assertTrue(exact['all_proofs_returned'])
        self.assertEqual(exact['reason'], 'proof-limit')

    def test_norm_one_and_single_dimension(self):
        p = Profile(7, 1, 3, 1)
        r = search(p, [[0]*3], backend='python-columns')
        self.assertEqual(r['domain'], 3)
        self.assertEqual(r['proofs'], [(1, 0, 0), (0, 1, 0), (0, 0, 1)])
        r = search(Profile(7, 1, 1, 1), [[1]], backend='python-columns', candidate_limit=1)
        self.assertEqual(r['reason'], 'domain-exhausted')

    def test_invalid_input_precedes_cuda_import(self):
        for kwargs in ({'batch_size': True}, {'batch_size': 4097}, {'proof_limit': 0},
                       {'candidate_limit': 16385}, {'backend': 'cpu'}):
            with self.assertRaises(ValueError):
                search(Profile(7, 1, 2, 2), [[1, 2]], **({'backend': 'cuda-columns'} | kwargs))
        with self.assertRaises(ValueError):
            search(Profile(7, 1, 2, 2), [[7, 0]], backend='cuda-columns')

    def test_materialization_and_output_tampering_refused(self):
        p = Profile(7, 1, 3, 2)
        dense = dense_search(p, [[0]*3], backend='python', proof_limit=1, batch_size=4)
        sparse = search(p, [[0]*3], backend='python-columns', proof_limit=1, batch_size=4)
        reconcile(dense, sparse)
        audit_ledger(p, sparse)
        sparse['work']['vector_entries'] = sparse['work']['screened']*p.m
        with self.assertRaisesRegex(RuntimeError, 'ledger'):
            audit_ledger(p, sparse)
        sparse['proofs'] = []
        with self.assertRaisesRegex(RuntimeError, 'proofs'):
            reconcile(dense, sparse)

    def test_schedule_keeps_legacy_and_large_width_domains_separate(self):
        planned = jobs()
        self.assertEqual(len(planned), 50)
        self.assertEqual(sum(j['group'] == 'legacy' for j in planned), 42)
        self.assertEqual(sum(j['group'] == 'large-chunk' for j in planned), 8)
        self.assertEqual(len({j['seed_hex'] for j in planned if j['seed_hex']}), 10)
        self.assertTrue(all(j['profile']['m'] >= 32 and j['fixture'] is None
                            for j in planned if j['group'] == 'large-chunk'))


if __name__ == '__main__':
    unittest.main()
