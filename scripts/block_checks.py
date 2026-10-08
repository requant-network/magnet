"""MGB1 commitment/hash and proof interoperability against the existing Rust core.

The MGB1 parser and chain state remain Python-only. Rust independently computes
the hashing preimages and verifies bound proofs; this is not a second chain engine.
"""

from dataclasses import replace
import hashlib
import random
import struct

from reference.admission_wire import admission_request, target_bytes
from reference.block import BODY_DOMAIN, COMMIT_DOMAIN, ID_DOMAIN, MAGIC, Block, commitment
from reference.chain import LabChain, ChainPolicy
from reference.grinding import score_digest
from reference.header import ExpectedContext, LabHeader
from reference.header_rules import LabRules
from reference.search import exhaustive_solutions
from reference.sis import Profile
from scripts.lab_driver import exchange, request


def differential_blocks(executable):
    rng = random.Random(2026100817)
    inputs, expected, mined = [], [], 0
    policy = ChainPolicy(bytes([7])*32, Profile(7, 1, 3, 8), 2**255, bytes([3])*32, anchor_time=99)
    chain = LabChain(policy)
    for index in range(64):
        body = rng.randbytes((0, 1, 55, 56, 64, 127, 1024)[index % 7])
        recipient = rng.randbytes(32)
        body_preimage = BODY_DOMAIN + struct.pack("<H", len(body)) + body
        body_root = hashlib.sha256(body_preimage).digest()
        commit_preimage = COMMIT_DOMAIN + MAGIC + target_bytes(policy.target) + recipient + body_root
        payload = commitment(policy.target, recipient, body)
        for nonce in range(1000):
            header = LabHeader(policy.network, chain.tip, payload, chain.height+1, 100+index, nonce, policy.profile)
            vectors = exhaustive_solutions(policy.profile, header.matrix())
            vector = next((tuple(x) for x in vectors if int.from_bytes(score_digest(header, x), "big") < policy.target), None)
            if vector is not None:
                break
        else:
            raise RuntimeError("block fixture search cap")
        block = Block(header, vector, policy.target, recipient, body)
        context = ExpectedContext(policy.network, chain.tip, chain.height+1, policy.profile)
        rules = LabRules(context, policy.target, 100+index, 100+index, (payload,))
        for preimage, digest in ((body_preimage, body_root), (commit_preimage, payload),
                                 (ID_DOMAIN+block.encode(), block.identifier())):
            inputs.append(request(4, preimage))
            expected.append(digest)
        inputs.append(admission_request(rules, block.proof()))
        expected.append(b"\x01")
        # Changing a committed field while keeping the old proof changes A/score;
        # verify using independently trusted original payload policy, no chance-based assertion.
        changed = replace(header, payload=commitment(policy.target, recipient, body+b"x")) if len(body) < 1024 else replace(header, payload=bytes(32))
        forged = replace(block, header=changed, body=body+b"x") if len(body) < 1024 else None
        if forged is not None:
            inputs.append(admission_request(rules, forged.proof()))
            expected.append(b"\x00")
        if chain.append(block.encode(), now=100+index) != "accepted":
            raise RuntimeError("mined block did not append")
        mined += 1
    responses = exchange(executable, inputs)
    if responses != expected:
        raise RuntimeError("block hash/admission differential mismatch")
    return {"seed": 2026100817, "blocks": mined, "requests": len(inputs), "mismatches": 0,
            "scope": "Rust hash/admission; Python MGB1 parser and linear-chain state"}
