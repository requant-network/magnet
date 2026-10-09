"""Host GPU-adapter safety tests; actual CUDA is tested by the explicit survey."""

import unittest

from reference.gpu_verify import MAX_BATCH, MAX_INPUT_BYTES, prepare
from reference.sis import Profile, encode_case, verify_packet
from scripts.gpu_verify_survey import corpus


class HostGpuAdmissionTests(unittest.TestCase):
    def test_norm_and_sign_before_device(self):
        p = Profile(65521, 1, 4, 65521**2-1)
        matrix = [[0]*4]
        vectors = ([65520, 0, 0, 0], [65521, 0, 0, 0], [0]*4,
                   [-1, 0, 0, 0], [2**31-1]*4, [-(2**31)]*4)
        groups = prepare([encode_case(p, matrix, v) for v in vectors])
        self.assertEqual([c[0] for cs in groups.values() for c in cs], [0])

    def test_malformed_packets_are_false_candidates(self):
        p = Profile(7, 1, 2, 5)
        good = encode_case(p, [[1, 2]], [2, -1])
        packets = [good[:-1], good+b'x', b'', bytearray(good), None, good]
        self.assertEqual(prepare(packets)[(7, 1, 2)][0][0], 5)

    def test_batch_bounds(self):
        for bad in ([], (), [b'']*(MAX_BATCH+1), iter([b'']), b''):
            with self.assertRaises(ValueError):
                prepare(bad)
        self.assertEqual(prepare([b'']*MAX_BATCH), {})

    def test_input_byte_budget_is_not_silently_ignored(self):
        with self.assertRaisesRegex(ValueError, 'input byte budget'):
            prepare([b'x'*(MAX_INPUT_BYTES+1)])

    def test_frozen_corpus_reaches_device_both_verdicts(self):
        packets = corpus()
        eligible = []
        for offset in range(0, len(packets), MAX_BATCH):
            groups = prepare(packets[offset:offset+MAX_BATCH])
            eligible.extend(offset+c[0] for cases in groups.values() for c in cases)
        accepted = sum(verify_packet(packets[i]) for i in eligible)
        self.assertEqual((len(packets), len(eligible), accepted), (731, 470, 228))
        self.assertEqual(len(eligible)-accepted, 242)

    def test_grouping_keeps_original_positions_and_wrap_cases(self):
        packets = [encode_case(Profile(7, 1, 2, 5), [[1, 2]], [2, -1]),
                   encode_case(Profile(2, 1, 1, 1), [[0]], [1]),
                   encode_case(Profile(7, 1, 2, 5), [[6, 1]], [1, 1])]
        groups = prepare(packets)
        self.assertEqual([c[0] for c in groups[(7, 1, 2)]], [0, 2])
        self.assertEqual(groups[(2, 1, 1)][0][0], 1)

    def test_noncanonical_matrix_and_profile_rejected(self):
        packet = bytearray(encode_case(Profile(7, 1, 2, 5), [[1, 2]], [2, -1]))
        packet[20:24] = (7).to_bytes(4, 'little')
        self.assertEqual(prepare([bytes(packet)]), {})
        packet[4:8] = (4).to_bytes(4, 'little')
        self.assertEqual(prepare([bytes(packet)]), {})

    def test_full_width_admitted_coordinate_bound(self):
        p = Profile(65521, 64, 128, 65521**2-1)
        packet = encode_case(p, [[65520]*128]*64, [65520]+[0]*127)
        self.assertEqual(len(prepare([packet]*MAX_BATCH)[(65521, 64, 128)]), MAX_BATCH)
        self.assertLess(128*65520**2, 2**63)


if __name__ == '__main__':
    unittest.main()
