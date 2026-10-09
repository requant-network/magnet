"""Transport corruption, validation-before-FFI and session lifecycle gates."""

import ctypes as C
import struct
import unittest
from unittest.mock import patch

from reference.fused_search import Session, search
from reference.native_columns import RESPONSE, decode_response, encode_request, search_many
from reference.sis import Profile
from scripts.native_fused_survey import validate_build_snapshot


class FakeLibrary:
    def __init__(self, fail_batch=False, fail_close=False):
        self.lib = self
        self.calls = []
        self.fail_batch, self.fail_close = fail_batch, fail_close

    def check(self, code):
        if code:
            raise RuntimeError('fake CUDA error')

    def mg_open(self, data, entries, n, m, q, norm_one, width, output):
        self.calls.append('open')
        C.cast(output, C.POINTER(C.c_void_p))[0] = 1
        return 0

    def mg_batch(self, handle, offset, count, result, length):
        self.calls.append('batch')
        for i in range(count):
            result[i] = 1
        return int(self.fail_batch)

    def mg_close(self, handle):
        self.calls.append('close')
        return int(self.fail_close)


class NativeFusedTests(unittest.TestCase):
    def setUp(self):
        self.p = Profile(7, 1, 3, 2)
        self.matrix = [[0, 0, 0]]
        self.settings = dict(candidate_limit=9, proof_limit=1, batch_size=9)

    def packet(self):
        return RESPONSE.pack(b'CSR1', 1, 1, 0, 0, 3, 0, 1, 9, 50, 9, 1, 9, 9) + struct.pack('<3i', 1, 0, 0)

    def test_wire_has_exact_max_shape_allowance(self):
        p = Profile(65521, 64, 128, 65521**2-1)
        self.assertEqual(len(encode_request(p, [[0]*128 for _ in range(64)])), 32800)
        self.assertEqual(RESPONSE.size, 60)

    def test_transport_rejects_corrupt_fields(self):
        valid = self.packet()
        self.assertEqual(decode_response(valid, self.p, self.matrix, **self.settings)['proofs'], [(1, 0, 0)])
        for offset, value in [(0, 0), (4, 2), (5, 0), (6, 1), (7, 1), (8, 4), (10, 1),
                              (12, 2), (16, 8), (28, 8), (36, 2), (44, 10), (52, 8), (60, 0)]:
            packet = bytearray(valid)
            packet[offset] = value
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                decode_response(bytes(packet), self.p, self.matrix, **self.settings)
        for packet in (valid[:-1], valid+b'x'):
            with self.assertRaises(ValueError):
                decode_response(packet, self.p, self.matrix, **self.settings)

    def test_invalid_caps_do_not_start_native_process(self):
        with patch('reference.native_columns.subprocess.run') as run:
            for value in (True, 0, 16385, '1'):
                with self.assertRaises(ValueError):
                    search_many('unused', [(self.p, self.matrix, dict(candidate_limit=value))])
            run.assert_not_called()

    def test_response_cannot_emit_unscreened_or_out_of_order_proofs(self):
        packet = RESPONSE.pack(b'CSR1', 1, 0, 0, 0, 3, 0, 1, 9, 50, 1, 1, 1, 1)
        with self.assertRaisesRegex(ValueError, 'charged prefix/order'):
            decode_response(packet+struct.pack('<3i', 0, 0, 1), self.p, self.matrix,
                            candidate_limit=1, proof_limit=1, batch_size=1)
        packet = RESPONSE.pack(b'CSR1', 1, 1, 0, 0, 3, 0, 2, 9, 50, 9, 1, 9, 9)
        with self.assertRaisesRegex(ValueError, 'charged prefix/order'):
            decode_response(packet+struct.pack('<6i', 0, 1, 0, 1, 0, 0), self.p, self.matrix,
                            candidate_limit=9, proof_limit=2, batch_size=9)

    def test_accepted_candidates_require_all_rows_in_native_counter(self):
        p = Profile(7, 2, 3, 2)
        packet = RESPONSE.pack(b'CSR1', 1, 1, 0, 0, 3, 0, 1, 9, 50, 9, 1, 9, 9)
        with self.assertRaisesRegex(ValueError, 'header/counters'):
            decode_response(packet+struct.pack('<3i', 1, 0, 0), p, [[0]*3]*2, **self.settings)

    def test_prebuild_snapshot_survives_child_launch_boundary(self):
        from pathlib import Path
        binaries = {Path('sis-column'): 'native', Path('kernel.so'): 'library'}
        manifest = {'source.rs': 'old'}
        snapshot = dict(source_sha256=manifest, binaries_sha256={'sis-column': 'native', 'kernel.so': 'library'})
        validate_build_snapshot(snapshot, manifest, binaries)
        with self.assertRaisesRegex(RuntimeError, 'pre-build snapshot'):
            validate_build_snapshot(snapshot, {'source.rs': 'new'}, binaries)
        with self.assertRaisesRegex(RuntimeError, 'build snapshot'):
            validate_build_snapshot(snapshot, manifest, {Path('sis-column'): 'replacement'})

    def test_invalid_input_does_not_enter_ffi(self):
        for matrix, settings in [([[True, 0, 0]], {}), ([[7, 0, 0]], {}),
                                 ([[0]], {}), (self.matrix, {'batch_size': 4097}),
                                 (self.matrix, {'candidate_limit': True})]:
            library = FakeLibrary()
            with self.assertRaises(ValueError):
                search(self.p, matrix, library=library, **settings)
            self.assertEqual(library.calls, [])

    def test_whole_mask_paid_before_proof_cap_and_cleanup(self):
        library = FakeLibrary()
        result = search(self.p, self.matrix, library=library, **self.settings)
        self.assertEqual(result['proofs'], [(1, 0, 0)])
        self.assertEqual(result['work']['accepted_seen'], 9)
        self.assertEqual(result['work']['explicit_d2h_bytes'], 9)
        self.assertEqual(result['work']['vector_entries'], 3)
        self.assertTrue(result['domain_exhausted'])
        self.assertFalse(result['all_proofs_returned'])
        self.assertEqual(library.calls, ['open', 'batch', 'close'])

    def test_failed_kernel_still_closes_and_no_fallback(self):
        library = FakeLibrary(fail_batch=True)
        with self.assertRaises(RuntimeError):
            search(self.p, self.matrix, library=library, **self.settings)
        self.assertEqual(library.calls, ['open', 'batch', 'close'])

    def test_cleanup_failure_is_not_reported_as_success(self):
        library = FakeLibrary(fail_close=True)
        with self.assertRaises(RuntimeError):
            search(self.p, self.matrix, library=library, **self.settings)
        library = FakeLibrary(fail_batch=True, fail_close=True)
        with self.assertRaises(RuntimeError) as raised:
            search(self.p, self.matrix, library=library, **self.settings)
        self.assertEqual(len(raised.exception.__notes__), 1)

    def test_closed_or_wrapping_ranges_do_not_enter_ffi(self):
        library = FakeLibrary()
        with Session(library, self.p, self.matrix, 9) as session:
            for offset, count in [(True, 1), (2**32, 1), (-1, 1), (8, 2), (0, 0), (0, 10)]:
                with self.assertRaises(ValueError):
                    session.mask(offset, count)
        with self.assertRaises(ValueError):
            session.mask(0, 1)
        self.assertEqual(library.calls, ['open', 'close'])


if __name__ == '__main__':
    unittest.main()
