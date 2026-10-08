"""Runnable fixed-profile MGB1 example with paid native search; no wallets/payments."""

import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from reference.block import Block, commitment
from reference.chain import ChainPolicy, LabChain
from reference.grinding import score_digest
from reference.header import LabHeader
from reference.sis import Profile, verify
from scripts.native_driver import build_native, encode_request, run_requests
from scripts.sphere_survey import source_hashes


def run():
    output = ROOT / "docs/research/results/lab-chain-v1.json"
    output.write_text('{"status":"running-or-incomplete"}\n', encoding="utf-8")
    begin = time.perf_counter_ns()
    native = build_native(release=True)
    policy = ChainPolicy(hashlib.sha256(b"MagnetNetwork/demo-chain/v1").digest(), Profile(17, 2, 8, 8),
                         2**252, hashlib.sha256(b"MagnetNetwork/demo-anchor/v1").digest(), anchor_time=99)
    chain = LabChain(policy)
    records, searches, nodes, scores = [], 0, 0, 0
    for index in range(8):
        body = f"Magnet Network research event {index+1}".encode()
        recipient = hashlib.sha256(b"demo-recipient/not-an-asset-address").digest()
        payload = commitment(policy.target, recipient, body)
        solved = None
        for nonce in range(128):
            h = LabHeader(policy.network, chain.tip, payload, chain.height+1, 100+index, nonce, policy.profile)
            matrix = h.matrix()
            sample = run_requests(native, [encode_request(h.profile, matrix, "mitm-budgeted", nodes=100_000,
                                                        table=10_000, pairs=100_000, proofs=64)])[0]
            searches += 1
            nodes += sample["work"]["nodes"]
            if not all(verify(h.profile, matrix, x) for x in sample["proofs"]):
                raise RuntimeError("demo search returned invalid proof")
            for vector in sample["proofs"]:
                scores += 1
                if int.from_bytes(score_digest(h, vector), "big") < policy.target:
                    solved = Block(h, tuple(vector), policy.target, recipient, body)
                    break
            if solved is not None:
                break
        if solved is None:
            raise RuntimeError("demo nonce budget exhausted; no silent profile/target downgrade")
        if chain.append(solved.encode(), now=100+index) != "accepted":
            raise RuntimeError("demo block rejected")
        records.append({"height": chain.height, "id_hex": solved.identifier().hex(), "parent_hex": solved.header.parent.hex(),
                        "block_hex": solved.encode().hex(), "body_utf8": body.decode(), "nonce": nonce,
                        "cumulative_searches": searches, "cumulative_nodes": nodes, "cumulative_scores": scores})
    report = {"status": "passed", "profile": {"q": 17, "n": 2, "m": 8, "b2": 8}, "target": str(policy.target),
              "network_hex": policy.network.hex(), "anchor_hex": policy.anchor.hex(), "blocks": records,
              "elapsed_ns_including_build_startup_and_search": time.perf_counter_ns()-begin, "source_sha256": source_hashes(),
              "native_sha256": hashlib.sha256(native.read_bytes()).hexdigest(), "native_algorithm": "NAT1-mode3-mitm-budgeted",
              "nominal_weight": chain.nominal_weight(), "scope": "opaque events, no monetary state; fixed trusted laboratory anchor"}
    output.write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"blocks": len(records), "searches": searches, "nodes": nodes, "scores": scores,
                      "tip": chain.tip.hex(), "nominal_weight": chain.nominal_weight()}, indent=2))


if __name__ == "__main__":
    run()
