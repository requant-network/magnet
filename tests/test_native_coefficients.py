"""Strict framing, semantic reconciliation and bounded child-process pipes."""

import struct
import subprocess
import sys
import unittest
from unittest.mock import patch

from reference.native_coefficients import (HEADER, MAX_BATCH, MAX_RESPONSE, PATTERN, WORK,
    decode_response, encode_request, exchange, search_many)
from reference.sis import Profile
from reference.small_coefficients import search


def packet(result, width=2):
    reasons = {'proof-limit': 1, 'candidate-limit': 2, 'domain-exhausted': 3}
    parts = [HEADER.pack(b'SCR1', reasons[result['reason']], result['domain_exhausted'], 0,
                         width, len(result['coefficients']), len(result['proofs']), result['domain'], 1),
             struct.pack('<13Q', *(result['work'][k] for k in WORK))]
    for w in range(1, 4):
        group = result['weights'].get(str(w), dict(domain=0, tested=0, accepted=0))
        parts.append(struct.pack('<3Q', *(group[k] for k in ('domain', 'tested', 'accepted'))))
    for key, group in result['coefficients'].items():
        values = list(map(int, key.split(',')))
        parts.append(PATTERN.pack(len(values), *(values+[0]*(3-len(values))),
                                 *(group[k] for k in ('domain', 'tested', 'accepted'))))
    for v in result['proofs']:
        parts.append(struct.pack('<'+'i'*width, *v))
    return b''.join(parts)


class NativeCoefficientTests(unittest.TestCase):
    def setUp(self):
        self.p, self.matrix = Profile(17, 1, 2, 5), [[1, 2]]
        self.settings = dict(bound=2)
        self.result = search(self.p, self.matrix, **self.settings)
        self.wire = packet(self.result)

    def test_reference_packet_roundtrip(self):
        self.assertEqual(decode_response(self.wire, self.p, self.matrix, **self.settings)['result'], self.result)

    def test_strict_types_and_caps_before_process(self):
        for key, value in (('bound', True), ('candidate_limit', 0), ('proof_limit', 257)):
            with patch('reference.native_coefficients.exchange') as launch:
                with self.assertRaises(ValueError):
                    search_many('unused', [(self.p, self.matrix, {**self.settings, key: value})])
                launch.assert_not_called()

    def test_bounded_generator_consumption(self):
        visits = []
        def cases():
            for i in range(MAX_BATCH+100):
                visits.append(i)
                yield self.p, self.matrix, self.settings
        with self.assertRaises(ValueError):
            search_many('unused', cases())
        self.assertEqual(len(visits), MAX_BATCH+1)

    def test_header_length_reserved_and_timer_rejections(self):
        for offset, change in ((0, b'BAD!'), (4, b'\x04'), (5, b'\x02'), (6, b'\x01'),
                               (8, b'\x03'), (10, b'\xff'), (20, b'\0'*8)):
            damaged = self.wire[:offset]+change+self.wire[offset+len(change):]
            with self.subTest(offset=offset), self.assertRaises(RuntimeError):
                decode_response(damaged, self.p, self.matrix, **self.settings)
        for damaged in (self.wire[:-1], self.wire+b'\0', b'0'*(MAX_RESPONSE+1)):
            with self.assertRaises(RuntimeError):
                decode_response(damaged, self.p, self.matrix, **self.settings)

    def test_census_pattern_and_proof_corruption(self):
        for offset in (28, 132, 204, len(self.wire)-1):
            damaged = bytearray(self.wire)
            damaged[offset] ^= 1
            with self.subTest(offset=offset), self.assertRaises(RuntimeError):
                decode_response(bytes(damaged), self.p, self.matrix, **self.settings)

    def test_valid_later_proof_cannot_hide_earlier_acceptance(self):
        p, matrix = Profile(17, 1, 2, 5), [[0, 0]]
        result = search(p, matrix, bound=2)
        result['proofs'].pop(0)
        with self.assertRaises(RuntimeError):
            decode_response(packet(result), p, matrix, bound=2)

    def test_transport_missing_trailing_and_extra_frames(self):
        framed = struct.pack('<I', len(self.wire))+self.wire
        for data in (b'', framed[:-1], framed+b'\0', framed+framed, struct.pack('<I', MAX_RESPONSE+1)):
            with patch('reference.native_coefficients.exchange', return_value=data):
                with self.assertRaises(RuntimeError):
                    search_many('unused', [(self.p, self.matrix, self.settings)])

    def test_bounded_stdout_and_stderr(self):
        for program, limit in ((b"import sys; sys.stdout.write('x'*100000)\n", 10),
                               (b"import sys; sys.stderr.write('x'*100000)\n", 10),
                               (b"import sys; sys.stderr.write('diagnostic')\n", 10)):
            with self.assertRaises(RuntimeError):
                exchange(sys.executable, program, limit, timeout=5)

    def test_child_exit_and_timeout(self):
        with self.assertRaises(RuntimeError):
            exchange(sys.executable, b'raise SystemExit(3)\n', 0, timeout=5)
        with self.assertRaises(subprocess.TimeoutExpired):
            exchange(sys.executable, b'import time; time.sleep(10)\n', 0, timeout=.1)

    def test_transport_argument_bounds(self):
        for value in (-1, True, MAX_BATCH*(MAX_RESPONSE+4)+1):
            with self.assertRaises(ValueError):
                exchange('unused', b'', value)
        for value in (0, True, 61, float('nan')):
            with self.assertRaises(ValueError):
                exchange('unused', b'', 0, timeout=value)


if __name__ == '__main__':
    unittest.main()
