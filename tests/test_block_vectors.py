from dataclasses import replace
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from reference.block import Block, MAX_BLOCK, MAX_BODY, commitment
from reference.chain import ChainPolicy, LabChain
from reference.grinding import score_digest
from reference.header import LabHeader
from reference.sis import Profile


class BlockVectorTests(unittest.TestCase):
    def setUp(self):
        self.fixture = json.loads((Path(__file__).parent / "vectors/block-v1.json").read_text())
        self.block = Block.decode(bytes.fromhex(self.fixture["block_hex"]))
        h = self.block.header
        self.policy = ChainPolicy(h.network, h.profile, self.block.target, bytes.fromhex(self.fixture["anchor_hex"]), anchor_time=99)

    def test_frozen_encoding_commitment_score_identifier_and_admission(self):
        f, b = self.fixture, self.block
        self.assertEqual(b.encode().hex(), f["block_hex"])
        self.assertEqual(b.identifier().hex(), f["id_hex"])
        self.assertEqual(b.header.encode().hex(), f["header_hex"])
        self.assertEqual(b.header.payload.hex(), f["payload_hex"])
        self.assertEqual(score_digest(b.header, b.vector).hex(), f["score_hex"])
        self.assertEqual(b.vector, tuple(f["vector"]))
        self.assertEqual(LabChain(self.policy).append(b.encode(), now=f["now"]), "accepted")

    def test_maximum_body_and_proof_shape_canonical_length(self):
        body = bytes(MAX_BODY)
        h = replace(self.block.header, profile=Profile(65521, 64, 128, 65521**2-1),
                    payload=commitment(self.block.target, self.block.recipient, body))
        largest = Block(h, (1,)+(0,)*127, self.block.target, self.block.recipient, body)
        self.assertEqual(len(largest.encode()), MAX_BLOCK)
        self.assertEqual(Block.decode(largest.encode()), largest)
        with self.assertRaises(ValueError):
            Block.decode(largest.encode()+b"x")
        self.assertEqual(LabChain(self.policy).inspect(largest.encode(), now=100), "wrong-policy")

    def test_height_overflow_and_saturated_future_bound_before_expansion(self):
        policy = replace(self.policy, anchor_height=2**64-1)
        h = replace(self.block.header, height=0)
        with patch.object(LabHeader, "matrix", side_effect=AssertionError("height must reject before expansion")):
            self.assertEqual(LabChain(policy).inspect(replace(self.block, header=h).encode(), now=100), "wrong-height")
        h = replace(self.block.header, timestamp=2**64-1)
        # At a saturated trusted clock the candidate proceeds to proof admission,
        # rather than wrapping the future bound to a small integer.
        with patch.object(Block, "valid_proof", return_value=False):
            self.assertEqual(LabChain(self.policy).inspect(replace(self.block, header=h).encode(), now=2**64-1), "invalid-proof")

    def test_storage_limit_preserves_history_on_rejection(self):
        with patch("reference.chain.MAX_CHAIN", 0):
            chain = LabChain(self.policy)
            self.assertEqual(chain.append(self.block.encode(), now=100), "storage-limit")
            self.assertEqual(chain.blocks, ())
            self.assertEqual(chain.tip, self.policy.anchor)

    def test_zero_score_wrong_target_and_q2_do_not_become_policy(self):
        payload = commitment(0, self.block.recipient, self.block.body)
        zero = replace(self.block, target=0, header=replace(self.block.header, payload=payload))
        with patch.object(LabHeader, "matrix", side_effect=AssertionError("target policy must reject first")):
            self.assertEqual(LabChain(self.policy).inspect(zero.encode(), now=100), "wrong-policy")
        with self.assertRaises(ValueError):
            replace(self.policy, target=0)
        with self.assertRaises(ValueError):
            replace(self.policy, profile=Profile(2, 1, 3, 1))
