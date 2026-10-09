"""Independent norm-ball oracle, prefix census, FFI lifecycle and failure evidence."""

import ctypes as C
import itertools
import unittest
from unittest.mock import patch

from reference.matched_sparse import Session, SearchFailure, search
from reference.sis import Profile, verify
from reference.sparse_domain import reference_search, support_at, supports, vector_for, weight_domains


class FakeLibrary:
    def __init__(self, fail_batch=0, fail_close=False):
        self.lib = self
        self.calls = []
        self.batches = 0
        self.fail_batch, self.fail_close = fail_batch, fail_close

    def check(self, code):
        if code:
            raise RuntimeError('fake matched error')

    def sp_open(self, backend, data, entries, n, m, q, b2, weight, width, output):
        self.calls.append(('open', backend))
        C.cast(output, C.POINTER(C.c_void_p))[0] = 1
        return 0

    def sp_batch(self, handle, offset, count, output, length):
        self.batches += 1
        self.calls.append(('batch', offset, count))
        for i in range(count):
            output[i] = 0
        return int(self.batches == self.fail_batch)

    def sp_close(self, handle):
        self.calls.append(('close',))
        return int(self.fail_close)


class MatchedSparseTests(unittest.TestCase):
    def test_full_order_decode_matches_combinations_at_all_boundaries(self):
        for m in range(1, 14):
            p = Profile(17, 1, m, 3)
            expected = list(supports(p, 3))
            self.assertEqual(len(expected), sum(weight_domains(p, 3).values()))
            self.assertEqual(expected, [support_at(m, ordinal) for ordinal in range(len(expected))])

    def test_bad_ordinals_reject_instead_of_looping_or_wrapping(self):
        for m, ordinal in ((0, 0), (129, 0), (True, 0), (1, 1), (3, 13), (3, -1), (3, True)):
            with self.assertRaises(ValueError):
                support_at(m, ordinal)

    def test_small_fields_match_independent_complete_norm_ball(self):
        for q in (2, 3):
            p = Profile(q, 1, 3, 3)
            for row in itertools.product(range(q), repeat=3):
                result = reference_search(p, [row], max_weight=3, batch_size=2)
                expected = {v for v in itertools.product((-1, 0, 1), repeat=3) if verify(p, [row], v)}
                self.assertEqual(set(result['proofs']), expected)
                self.assertTrue(result['all_proofs_returned'])

    def test_triples_discover_a_solution_absent_from_pair_domain(self):
        p, matrix = Profile(17, 1, 3, 3), [[1, 2, 3]]
        pair = reference_search(p, matrix, max_weight=2)
        triple = reference_search(p, matrix, max_weight=3)
        self.assertEqual(pair['proofs'], [])
        self.assertEqual(triple['proofs'], [(1, 1, -1)])
        self.assertEqual(triple['weights']['3']['accepted'], 1)

    def test_paid_tail_and_independent_search_output_censoring(self):
        p, matrix = Profile(7, 1, 3, 3), [[0]*3]
        result = reference_search(p, matrix, max_weight=3, candidate_limit=13, proof_limit=1, batch_size=13)
        self.assertEqual(result['checked_interval'], [0, 13])
        self.assertTrue(result['domain_exhausted'])
        self.assertEqual(result['accepted_tail_discarded'], 12)
        self.assertEqual([result['weights'][str(w)]['tested'] for w in (1, 2, 3)], [3, 6, 4])
        self.assertEqual(result['weights']['3']['discarded'], 4)
        result = reference_search(p, matrix, max_weight=3, candidate_limit=4, proof_limit=256, batch_size=3)
        self.assertEqual(result['checked_interval'], [0, 4])
        self.assertTrue(result['candidate_censored'])
        self.assertEqual(result['weights']['3']['tested'], 0)
        self.assertEqual(result['accepted_tail_discarded'], 0)

    def test_norm_and_dimension_degenerate_domains(self):
        for m in (1, 2, 3):
            for b2 in (1, 2, 3):
                p = Profile(7, 1, m, b2)
                result = reference_search(p, [[0]*m], max_weight=3, proof_limit=256)
                self.assertTrue(result['all_proofs_returned'])
                self.assertEqual(result['domain'], len(set(result['proofs'])))
                self.assertTrue(all(sum(x*x for x in v) <= b2 for v in result['proofs']))

    def test_invalid_input_precedes_ffi(self):
        p = Profile(7, 1, 3, 3)
        library = FakeLibrary()
        for settings in ({'max_weight': True}, {'max_weight': 4}, {'candidate_limit': 65537},
                         {'batch_size': 4097}, {'proof_limit': True}, {'backend': []}):
            kwargs = dict(library=library, backend='native-cpu', max_weight=3)
            kwargs.update(settings)
            with self.assertRaises(ValueError):
                search(p, [[0]*3], **kwargs)
        self.assertEqual(library.calls, [])

    def test_identical_host_wrapper_scope_and_ledger(self):
        p = Profile(7, 1, 3, 3)
        for backend in ('native-cpu', 'fused-gpu'):
            library = FakeLibrary()
            result = search(p, [[1, 2, 3]], library=library, backend=backend, max_weight=3, batch_size=2)
            self.assertEqual(result['work']['screened'], 13)
            self.assertEqual(result['work']['host_matrix_copy_bytes'], 24)
            self.assertEqual(result['logical_device_bytes'], 26 if backend == 'fused-gpu' else 0)
            self.assertEqual(library.calls[-1], ('close',))

    def test_second_chunk_failure_retains_paid_progress_and_closes(self):
        p, library = Profile(7, 1, 3, 3), FakeLibrary(fail_batch=2)
        with self.assertRaises(SearchFailure) as raised:
            search(p, [[1, 2, 3]], library=library, backend='fused-gpu', max_weight=3, batch_size=2)
        diagnostic = raised.exception.diagnostic
        self.assertEqual(diagnostic['completed_screened'], 2)
        self.assertEqual(diagnostic['completed_batches'], 1)
        self.assertEqual(diagnostic['stage'], 'mask-completion')
        self.assertGreater(diagnostic['elapsed_ns'], 0)
        self.assertEqual(library.calls[-1], ('close',))

    def test_output_decode_failure_keeps_completed_mask_charge(self):
        p, library = Profile(7, 1, 3, 3), FakeLibrary()
        def accepted(handle, offset, count, output, length):
            for i in range(count): output[i] = 1
            return 0
        library.sp_batch = accepted
        with patch('reference.matched_sparse.vector_for', side_effect=RuntimeError('decode failure')):
            with self.assertRaises(SearchFailure) as raised:
                search(p, [[0]*3], library=library, backend='native-cpu', max_weight=3, batch_size=2)
        self.assertEqual(raised.exception.diagnostic['completed_screened'], 2)
        self.assertEqual(raised.exception.diagnostic['completed_accepted'], 2)
        self.assertEqual(raised.exception.diagnostic['stage'], 'output-decode')

    def test_corrupt_successful_mask_keeps_completed_work_but_unknown_acceptance(self):
        p, library = Profile(7, 1, 3, 3), FakeLibrary()
        calls = 0
        def corrupt(handle, offset, count, output, length):
            nonlocal calls
            calls += 1
            for i in range(count): output[i] = 0
            if calls == 2: output[0] = 2
            return 0
        library.sp_batch = corrupt
        with self.assertRaises(SearchFailure) as raised:
            search(p, [[1, 2, 3]], library=library, backend='native-cpu', max_weight=3, batch_size=2)
        diagnostic = raised.exception.diagnostic
        self.assertEqual(diagnostic['completed_screened'], 4)
        self.assertEqual(diagnostic['completed_batches'], 2)
        self.assertEqual(diagnostic['validated_screened'], 2)
        self.assertIsNone(diagnostic['completed_accepted'])
        self.assertEqual(diagnostic['stage'], 'mask-validation')
        self.assertEqual(library.calls[-1], ('close',))

    def test_cleanup_failure_cannot_produce_success_or_hide_kernel_failure(self):
        p, library = Profile(7, 1, 1, 3), FakeLibrary(fail_close=True)
        with self.assertRaises(SearchFailure) as raised:
            search(p, [[1]], library=library, backend='native-cpu', max_weight=3)
        self.assertEqual(raised.exception.diagnostic['stage'], 'session-close')
        library = FakeLibrary(fail_batch=1, fail_close=True)
        with self.assertRaises(SearchFailure) as raised:
            search(p, [[1]], library=library, backend='fused-gpu', max_weight=3)
        self.assertEqual(len(raised.exception.diagnostic['cleanup_notes']), 1)

    def test_closed_and_out_of_domain_range_reject(self):
        library = FakeLibrary()
        with Session(library, Profile(7, 1, 3, 3), [[0]*3], 'native-cpu', 3, 2) as session:
            for offset, count in ((13, 1), (12, 2), (0, 3), (True, 1), (-1, 1)):
                with self.assertRaises(ValueError): session.mask(offset, count)
        with self.assertRaises(ValueError): session.mask(0, 1)


if __name__ == '__main__':
    unittest.main()
