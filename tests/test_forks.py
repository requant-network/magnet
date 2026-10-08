from dataclasses import replace
import unittest
from unittest.mock import patch

from reference.block import Block
from reference.chain import ChainPolicy
from reference.forks import ForkLimits, ForkTree, MAX_RETAINED_WIRE
from reference.header import LabHeader
from reference.sis import Profile
from scripts.chain_fixtures import mine


class ForkTests(unittest.TestCase):
    def setUp(self):
        self.policy=ChainPolicy(bytes(32),Profile(7,1,3,8),2**255,bytes([1])*32,anchor_time=99)
        self.tree=ForkTree(self.policy,peers=("a","b"))
        self.a=mine(self.policy,body=b"a")
        self.b=mine(self.policy,body=b"b")
        self.b2=mine(self.policy,parent=self.b.identifier(),height=2,timestamp=101,body=b"b2")

    def put(self,block,peer="a",now=100):
        return self.tree.submit(block.encode(),peer=peer,now=now)

    def test_equal_depth_then_atomic_reorg_and_duplicate(self):
        self.assertEqual(self.put(self.a).status,"accepted-main")
        self.assertEqual(self.put(self.b,"b").status,"accepted-side")
        self.assertEqual(self.tree.tip,self.a.identifier())
        result=self.put(self.b2,"b",101)
        self.assertEqual(result.status,"accepted-reorg")
        self.assertEqual(result.detached,(self.a.identifier(),))
        self.assertEqual(result.attached,(self.b.identifier(),self.b2.identifier()))
        self.assertEqual(self.tree.canonical_bodies(),(b"b",b"b2"))
        self.assertEqual(result.admission_calls,3)
        self.assertEqual(self.put(self.b2,"b",101).status,"duplicate")
        self.assertEqual(self.tree.node_count,3)
        self.assertEqual(self.tree.path(self.b2.identifier()),self.tree.canonical)

    def test_reverse_delivery_explicit_bounded_drain(self):
        b3=mine(self.policy,parent=self.b2.identifier(),height=3,timestamp=102,body=b"b3")
        self.assertEqual(self.put(b3,"b").status,"queued-orphan")
        self.assertEqual(self.put(self.b2,"b").status,"queued-orphan")
        self.assertEqual(self.put(self.b,"b").status,"accepted-main")
        self.assertEqual(self.tree.queued_count,2)
        results=self.tree.drain(now=102,budget=1)
        self.assertEqual(len(results),1)
        self.assertEqual(self.tree.queued_count,1)
        self.assertEqual(len(self.tree.drain(now=102)),1)
        self.assertEqual(self.tree.canonical_bodies(),(b"b",b"b2",b"b3"))

    def test_ttl_duplicate_and_orphan_promotion_never_refresh(self):
        self.tree=ForkTree(self.policy,peers=("a","b"),limits=ForkLimits(ttl=10))
        future=mine(self.policy,parent=self.b.identifier(),height=2,timestamp=240,body=b"future")
        self.assertEqual(self.put(future,"b",100).status,"queued-orphan")
        self.assertEqual(self.put(future,"b",108).status,"duplicate")
        self.assertEqual(self.put(self.b,"b",108).status,"accepted-main")
        self.assertEqual(self.tree.drain(now=109),())
        self.assertEqual(self.tree.queued_count,1)
        self.assertEqual(self.tree.drain(now=110),())
        self.assertEqual(self.tree.queued_count,0)

    def test_future_retry_and_invalid_queued_proof(self):
        future=mine(self.policy,timestamp=230,body=b"future")
        queued=self.put(future,now=100)
        self.assertEqual(queued.status,"queued-future")
        self.assertEqual(queued.admission_calls,1)
        self.assertEqual(self.tree.drain(now=109),())
        self.assertEqual(self.tree.drain(now=110)[0].status,"accepted-main")
        self.assertEqual(self.tree.tip,future.identifier())
        other=replace(self.b2,vector=(0,0,0))
        self.assertEqual(self.put(other,now=110).status,"queued-orphan")
        self.assertEqual(self.put(self.b,now=110).status,"accepted-side")
        self.assertEqual(self.tree.drain(now=110)[0].status,"invalid-proof")
        self.assertEqual(self.tree.queued_count,0)

    def test_capacity_and_header_rejections_precede_expensive_proof(self):
        self.tree=ForkTree(self.policy,peers=("a","b"),limits=ForkLimits(nodes=1,queued=2,per_peer=1))
        self.assertEqual(self.put(self.a).status,"accepted-main")
        with patch.object(Block,"valid_proof",side_effect=AssertionError("proof work forbidden")):
            self.assertEqual(self.put(self.b).status,"node-limit")
            self.assertEqual(self.put(self.b2).status,"queued-orphan")
            other=replace(self.b2,header=replace(self.b2.header,nonce=self.b2.header.nonce+1))
            self.assertEqual(self.put(other).status,"peer-queue-limit")
            self.assertEqual(self.put(other,"b").status,"queued-orphan")
            self.assertEqual(self.put(replace(other,header=replace(other.header,nonce=other.header.nonce+1)),"b").status,"queue-limit")
        self.assertLessEqual(self.tree.retained_wire_bytes,MAX_RETAINED_WIRE)
        self.assertEqual(self.tree.queue_peers(),{"a":1,"b":1})
        self.assertEqual(self.tree.node_count,1)

    def test_replay_failure_preserves_nodes_canonical_and_bodies(self):
        self.put(self.a); self.put(self.b,"b")
        original=Block.valid_proof
        def fail_ancestor(block,context):
            return False if block.identifier()==self.b.identifier() else original(block,context)
        with patch.object(Block,"valid_proof",fail_ancestor):
            self.assertEqual(self.put(self.b2,"b",101).status,"revalidation-failed")
        self.assertEqual(self.tree.tip,self.a.identifier())
        self.assertEqual(self.tree.node_count,2)
        self.assertEqual(self.tree.canonical_bodies(),(b"a",))

    def test_invalid_limits_clocks_inputs_and_immutable_views(self):
        for field in ("nodes","depth","queued","per_peer","ttl","drain","submissions"):
            with self.assertRaises(ValueError): replace(ForkLimits(),**{field:True})
        with self.assertRaises(ValueError): ForkTree(self.policy,peers=("a","a"))
        with self.assertRaises(ValueError): ForkLimits(ttl=61)
        with self.assertRaises(AttributeError): self.tree.policy=self.policy
        with self.assertRaises(ValueError): self.put(self.a,"stranger")
        self.put(self.a,now=101)
        for now in (True,100,2**64):
            with self.assertRaises(ValueError): self.tree.drain(now=now)
        for budget in (True,0,9):
            with self.assertRaises(ValueError): self.tree.drain(now=101,budget=budget)
        self.assertIsInstance(self.tree.canonical,tuple)
        self.assertEqual(self.tree.submit(b"bad",peer="a",now=101).status,"malformed")

    def test_future_queue_rejection_retains_admission_cost(self):
        self.tree=ForkTree(self.policy,peers=("a","b"),limits=ForkLimits(queued=1,per_peer=1))
        first=mine(self.policy,timestamp=221,body=b"future one")
        other=mine(self.policy,timestamp=221,body=b"future two")
        self.assertEqual(self.put(first).admission_calls,1)
        r=self.put(other)
        self.assertEqual(r.status,"queue-limit")
        self.assertEqual(r.admission_calls,1)

    def test_rate_limit_charges_malformed_duplicate_and_peer_isolation(self):
        self.tree=ForkTree(self.policy,peers=("a","b"),limits=ForkLimits(submissions=2))
        self.assertEqual(self.tree.submit(b"bad",peer="a",now=100).status,"malformed")
        self.assertEqual(self.put(self.a).status,"accepted-main")
        with patch.object(Block,"decode",side_effect=AssertionError("rate rejection before decode")):
            self.assertEqual(self.put(self.b).status,"submission-rate-limit")
        self.assertEqual(self.put(self.b,"b").status,"accepted-side")
        self.assertEqual(self.put(self.a,now=101).status,"duplicate")

    def test_branch_time_is_ancestor_local(self):
        self.put(self.a,now=100)
        future=mine(self.policy,timestamp=210,body=b"other branch")
        self.assertEqual(self.put(future,"b",100).status,"accepted-side")
        self.assertEqual(self.put(self.b2,"b",101).status,"queued-orphan")
        self.assertEqual(self.put(self.b,"b",101).status,"accepted-side")
        self.assertEqual(self.tree.drain(now=101)[0].status,"accepted-reorg")


if __name__=="__main__": unittest.main()
