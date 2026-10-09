"""Independent order/set checks, matched chunks and owner failure accounting."""
import ctypes as C
import itertools
import unittest
from unittest.mock import patch
from reference.matched_coefficients import Domain, Session, SearchFailure, reference_search, reconcile, search
from reference.sis import Profile, verify
from reference.small_coefficients import candidates, dense, templates

class FakeLibrary:
    def __init__(self, profile, matrix, bound, *, fail_batch=0, corrupt_batch=0, fail_close=False):
        self.lib = self
        self.profile, self.matrix = profile, matrix
        self.fail_batch, self.corrupt_batch, self.fail_close = fail_batch, corrupt_batch, fail_close
        self.batches, self.calls = 0, []
        self.family = list(candidates(profile.m, templates(profile, bound)[0]))
    def check(self, code):
        if code: raise RuntimeError('fake coefficient failure')
    def cc_open(self, backend, data, entries, n, m, q, b2, bound, width, output):
        self.calls.append(('open', backend))
        C.cast(output, C.POINTER(C.c_void_p))[0] = 1
        return 0
    def cc_batch(self, handle, offset, count, output, length):
        self.batches += 1
        self.calls.append(('batch', offset, count))
        for i, (positions, values) in enumerate(self.family[offset:offset+count]):
            output[i] = int(verify(self.profile, self.matrix, dense(self.profile.m, positions, values)))
        if self.batches == self.corrupt_batch: output[0] = 2
        return int(self.batches == self.fail_batch)
    def cc_close(self, handle):
        self.calls.append(('close',))
        return int(self.fail_close)

class MatchedCoefficientTests(unittest.TestCase):
    def test_full_unrank_order_across_norm_and_weight_boundaries(self):
        for m in (1, 2, 3, 5, 8, 16):
            for b2 in (1, 3, 5, 8, 12):
                for bound in (1, 2):
                    p = Profile(17, 1, m, b2)
                    d = Domain(p, bound)
                    self.assertEqual([d.at(i) for i in range(d.size)], list(candidates(m, templates(p, bound)[0])))
    def test_bad_ordinals(self):
        d = Domain(Profile(17, 1, 2, 5), 2)
        for ordinal in (-1, True, d.size, 1.0):
            with self.assertRaises(ValueError): d.at(ordinal)
    def test_small_box_sets_independent_of_templates(self):
        for q in (2, 3, 17):
            p = Profile(q, 1, 3, min(5, q*q-1))
            for matrix in ([[0, 0, 0]], [[1, q-1, 1]]):
                for bound in (1, 2):
                    expected = {v for v in itertools.product(range(-bound, bound+1), repeat=3)
                        if sum(x != 0 for x in v) <= 3 and verify(p, matrix, v)}
                    output = reference_search(p, matrix, bound=bound, batch_size=7)
                    self.assertEqual(set(output['proofs']), expected)
                    self.assertTrue(output['all_proofs_returned'])
    def test_both_backends_same_scope_and_census_with_fake_ffi(self):
        p, matrix = Profile(17, 2, 5, 12), [[1, 2, 3, 4, 5], [2, 4, 6, 8, 10]]
        for bound in (1, 2):
            for width in (1, 7, 4096):
                expected = reference_search(p, matrix, bound=bound, candidate_limit=31, proof_limit=3, batch_size=width)
                for backend in ('native-cpu', 'fused-gpu'):
                    actual = search(p, matrix, library=FakeLibrary(p, matrix, bound), backend=backend,
                                    bound=bound, candidate_limit=31, proof_limit=3, batch_size=width)
                    reconcile(expected, actual)
                    self.assertGreater(actual['elapsed_ns'], 0)
    def test_paid_tail_and_exact_exhaustion(self):
        p, matrix = Profile(17, 1, 2, 5), [[0, 0]]
        result = reference_search(p, matrix, bound=2, proof_limit=1, batch_size=4096)
        self.assertEqual(result['accepted_tail_discarded'], result['domain']-1)
        self.assertTrue(result['domain_exhausted'])
        self.assertFalse(result['all_proofs_returned'])
        self.assertEqual(result['reason'], 'proof-limit')
        result = reference_search(p, matrix, bound=2, candidate_limit=result['domain'], batch_size=7)
        self.assertTrue(result['all_proofs_returned'])
        self.assertFalse(result['candidate_cap_truncates_domain'])
    def test_invalid_input_before_ffi(self):
        p, matrix = Profile(17, 1, 2, 5), [[1, 2]]
        for settings in (dict(bound=True), dict(bound=3), dict(bound=2, batch_size=True),
                         dict(bound=2, candidate_limit=20001), dict(bound=2, proof_limit=0)):
            library = FakeLibrary(p, matrix, 2)
            with self.assertRaises(ValueError): search(p, matrix, library=library, backend='native-cpu', **settings)
            self.assertEqual(library.calls, [])
    def test_closed_or_wrapping_ranges_never_enter_ffi(self):
        p, matrix = Profile(17, 1, 2, 5), [[1, 2]]
        library = FakeLibrary(p, matrix, 2)
        with Session(library, p, matrix, 'native-cpu', 2, 7) as session:
            for args in ((-1, 1), (0, True), (session.domain, 1), (session.domain-1, 2), (0, 8)):
                with self.assertRaises(ValueError): session.mask(*args)
        with self.assertRaises(ValueError): session.mask(0, 1)
        self.assertEqual(library.calls, [('open', 0), ('close',)])
    def test_failed_second_chunk_keeps_validated_prefix(self):
        p, matrix = Profile(17, 1, 2, 5), [[0, 0]]
        library = FakeLibrary(p, matrix, 2, fail_batch=2)
        with self.assertRaises(SearchFailure) as ctx:
            search(p, matrix, library=library, backend='native-cpu', bound=2, batch_size=3)
        d = ctx.exception.diagnostic
        self.assertEqual((d['completed_screened'], d['validated_accepted']), (3, 3))
        self.assertTrue(d['in_flight_work_unknown'])
        self.assertEqual(library.calls[-1], ('close',))
    def test_corrupt_successful_chunk_charged_acceptance_unknown(self):
        p, matrix = Profile(17, 1, 2, 5), [[0, 0]]
        library = FakeLibrary(p, matrix, 2, corrupt_batch=2)
        with self.assertRaises(SearchFailure) as ctx:
            search(p, matrix, library=library, backend='native-cpu', bound=2, batch_size=3)
        d = ctx.exception.diagnostic
        self.assertEqual((d['completed_screened'], d['validated_screened']), (6, 3))
        self.assertIsNone(d['completed_accepted'])
        self.assertEqual(d['stage'], 'mask-validation')
    def test_materialization_failure_preserves_mask_charge(self):
        p, matrix = Profile(17, 1, 2, 5), [[0, 0]]
        library = FakeLibrary(p, matrix, 2)
        with patch('reference.matched_coefficients.dense', side_effect=RuntimeError('decode fail')):
            with self.assertRaises(SearchFailure) as ctx:
                search(p, matrix, library=library, backend='native-cpu', bound=2, batch_size=3)
        self.assertEqual(ctx.exception.diagnostic['completed_accepted'], 3)
        self.assertEqual(ctx.exception.diagnostic['completed_screened'], 3)
        self.assertEqual(library.calls[-1], ('close',))
    def test_successful_ffi_bytes_allocation_failure_is_paid(self):
        p, matrix = Profile(17, 1, 2, 5), [[0, 0]]
        library = FakeLibrary(p, matrix, 2)
        with patch('reference.matched_coefficients.bytes', side_effect=MemoryError('host bytes'), create=True):
            with self.assertRaises(SearchFailure) as ctx:
                search(p, matrix, library=library, backend='native-cpu', bound=2, batch_size=3)
        d = ctx.exception.diagnostic
        self.assertEqual((d['completed_screened'], d['validated_screened']), (3, 0))
        self.assertIsNone(d['completed_accepted'])
        self.assertFalse(d['in_flight_work_unknown'])
        self.assertEqual(library.calls[-1], ('close',))
    def test_hit_collection_failure_preserves_known_mask_acceptance(self):
        p, matrix = Profile(17, 1, 2, 5), [[0, 0]]
        library = FakeLibrary(p, matrix, 2)
        with patch('reference.matched_coefficients.enumerate', side_effect=MemoryError('host hits'), create=True):
            with self.assertRaises(SearchFailure) as ctx:
                search(p, matrix, library=library, backend='native-cpu', bound=2, batch_size=3)
        d = ctx.exception.diagnostic
        self.assertEqual((d['completed_screened'], d['validated_accepted']), (3, 3))
        self.assertEqual(d['completed_accepted'], 3)
        self.assertEqual(library.calls[-1], ('close',))
    def test_cleanup_cannot_hide_failure_or_produce_success(self):
        p, matrix = Profile(17, 1, 2, 5), [[0, 0]]
        for fail_batch in (0, 1):
            library = FakeLibrary(p, matrix, 2, fail_batch=fail_batch, fail_close=True)
            with self.assertRaises(SearchFailure) as ctx:
                search(p, matrix, library=library, backend='native-cpu', bound=2)
            d = ctx.exception.diagnostic
            self.assertEqual(d['stage'], 'mask-completion' if fail_batch else 'session-close')
            if fail_batch: self.assertTrue(d['cleanup_notes'])

if __name__ == '__main__': unittest.main()
