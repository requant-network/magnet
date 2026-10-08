from dataclasses import replace
import hashlib
import unittest
from unittest.mock import patch

from reference.block import Block, PREFIX, MAX_BODY, commitment
from reference.chain import ChainPolicy, LabChain
from reference.grinding import score_digest
from reference.header import LabHeader
from reference.search import exhaustive_solutions
from reference.sis import Profile


class BlockChainTests(unittest.TestCase):
    def setUp(self):
        self.policy = ChainPolicy(bytes(32), Profile(7, 1, 3, 8), 2**255, bytes([1])*32, anchor_time=99)
        self.chain = LabChain(self.policy)

    def mine(self, timestamp=100, body=b"event", recipient=bytes(32)):
        p = self.policy
        payload = commitment(p.target, recipient, body)
        for nonce in range(1000):
            h = LabHeader(p.network, self.chain.tip, payload, self.chain.height+1, timestamp, nonce, p.profile)
            for x in exhaustive_solutions(p.profile, h.matrix()):
                if int.from_bytes(score_digest(h, x), "big") < p.target:
                    return Block(h, tuple(x), p.target, recipient, body)
        self.fail("deterministic tiny mining fixture exhausted")

    def test_roundtrip_link_and_replay(self):
        first = self.mine()
        self.assertEqual(Block.decode(first.encode()), first)
        self.assertEqual(self.chain.append(first.encode(), now=100), "accepted")
        self.assertEqual(self.chain.append(first.encode(), now=100), "unknown-or-nontip-parent")
        second = self.mine(timestamp=101)
        self.assertEqual(second.header.parent, first.identifier())
        self.assertEqual(self.chain.append(second.encode(), now=101), "accepted")
        self.assertEqual(self.chain.height, 2)
        self.assertEqual(self.chain.nominal_weight(), 2)
        self.assertEqual(len(self.chain.blocks), 2)

    def test_descriptor_commitment_and_bounded_canonical_wire(self):
        block = self.mine(body=bytes(MAX_BODY))
        packet = block.encode()
        for wire in (b"", packet[:-1], packet+b"x", b"MGB2"+packet[4:]):
            with self.assertRaises(ValueError):
                Block.decode(wire)
        for index in (4, 37, PREFIX.size):
            wire = bytearray(packet)
            wire[index] ^= 1
            with self.assertRaises(ValueError):
                Block.decode(bytes(wire))
        with self.assertRaises(ValueError):
            replace(block, body=b"changed")
        with self.assertRaises(ValueError):
            commitment(self.policy.target, bytes(32), bytes(MAX_BODY+1))
        self.assertNotEqual(commitment(1, bytes(32), b"a"), commitment(2, bytes(32), b"a"))
        self.assertNotEqual(commitment(1, bytes(32), b"a"), commitment(1, bytes([1])*32, b"a"))

    def test_reject_header_surface_before_matrix_and_preserve_state(self):
        block = self.mine()
        variants = [(replace(block, header=replace(block.header, height=2)), "wrong-height"),
                    (replace(block, header=replace(block.header, network=bytes([9])*32)), "wrong-policy"),
                    (replace(block, header=replace(block.header, timestamp=99)), "past-time"),
                    (replace(block, header=replace(block.header, timestamp=221)), "defer-future-time")]
        with patch.object(LabHeader, "matrix", side_effect=AssertionError("early rejection must not expand")):
            for other, status in variants:
                self.assertEqual(self.chain.append(other.encode(), now=100), status)
        self.assertEqual(self.chain.blocks, ())
        self.assertEqual(self.chain.append(replace(block, vector=(0, 0, 0)).encode(), now=100), "invalid-proof")

    def test_future_block_can_be_retried_without_remining(self):
        block = self.mine(timestamp=500)
        self.assertEqual(self.chain.append(block.encode(), now=100), "defer-future-time")
        self.assertEqual(self.chain.append(block.encode(), now=380), "accepted")

    def test_median_window_and_trusted_clock(self):
        for stamp in range(100, 112):
            self.assertEqual(self.chain.append(self.mine(timestamp=stamp).encode(), now=200), "accepted")
        block = self.mine(timestamp=107)  # Above median 106, below previous 111.
        self.assertEqual(self.chain.append(block.encode(), now=200), "accepted")
        with self.assertRaises(ValueError):
            self.chain.inspect(block.encode(), now=True)

    def test_policy_and_overflow(self):
        for value in (0, 2**256, True):
            with self.assertRaises(ValueError):
                replace(self.policy, target=value)
        with self.assertRaises(ValueError):
            replace(self.policy, profile=Profile(2, 1, 3, 1))
        self.assertEqual(len(hashlib.sha256(b"test").digest()), len(self.mine().identifier()))
