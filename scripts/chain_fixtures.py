"""Deterministic bounded tiny mining for admission/simulator fixtures, not performance."""

from reference.block import Block, commitment
from reference.grinding import score_digest
from reference.header import LabHeader
from reference.search import exhaustive_solutions


def mine(policy, *, parent=None, height=None, timestamp=100, body=b"event", recipient=bytes(32), nonce_start=0):
    parent=policy.anchor if parent is None else parent
    height=policy.anchor_height+1 if height is None else height
    payload=commitment(policy.target,recipient,body)
    for nonce in range(nonce_start,min(2**64,nonce_start+4096)):
        h=LabHeader(policy.network,parent,payload,height,timestamp,nonce,policy.profile)
        for vector in exhaustive_solutions(policy.profile,h.matrix()):
            if int.from_bytes(score_digest(h,vector),"big") < policy.target:
                return Block(h,tuple(vector),policy.target,recipient,body)
    raise RuntimeError("fixture mining cap exhausted")
