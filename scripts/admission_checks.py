"""Deterministic SHA-256/score/admission differential and malformed local requests."""

from dataclasses import replace
import hashlib
import json
from pathlib import Path
import random
import struct
import subprocess

from reference.admission_wire import admission_request, decode_rules, encode_rules, scored_request
from reference.grinding import score_digest, verify_scored_proof
from reference.header import ExpectedContext, LabHeader, encode_proof
from reference.header_rules import LabRules, admit_proof
from reference.search import exhaustive_solutions
from reference.sis import Profile
from scripts.lab_driver import exchange, request


def differential_admission(executable):
    rng = random.Random(2026100809)
    requests, expected, counts = [], [], {}

    def add(group, wire, response):
        counts[group] = counts.get(group, 0)+1
        requests.append(wire)
        expected.append(response)

    for length in (0, 1, 55, 56, 63, 64, 65, 119, 120, 127, 128, 129, 2047, 2048):
        for _ in range(4):
            message = rng.randbytes(length)
            add("sha256_padding", request(4, message), hashlib.sha256(message).digest())
    for _ in range(512):
        message = rng.randbytes(rng.randrange(2049))
        add("sha256_random", request(4, message), hashlib.sha256(message).digest())

    fixture = json.loads((Path(__file__).resolve().parents[1] / "tests/vectors/admission-v1.json").read_text())
    frozen_packet = bytes.fromhex(fixture["proof_hex"])
    frozen_rules = decode_rules(bytes.fromhex(fixture["rules_hex"]))
    for case in fixture["targets"]:
        rules = replace(frozen_rules, target=int(case["target"]))
        add("frozen_admission", admission_request(rules, frozen_packet), bytes([case["accepted"]]))

    for i in range(512):
        profile = Profile((7, 17, 257)[i % 3], 1, 3, 8)
        h = LabHeader(rng.randbytes(32), rng.randbytes(32), rng.randbytes(32), i, 100, rng.getrandbits(64), profile)
        context = ExpectedContext(h.network, h.parent, h.height, profile)
        proofs = list(exhaustive_solutions(profile, h.matrix()))
        vector = proofs[0] if proofs else (1, 0, 0)
        packet = encode_proof(h, vector)
        digest = int.from_bytes(score_digest(h, vector), "big")
        for target in (0, 1, 2**255, 2**256, digest, digest+1):
            add("strict_score", scored_request(context, target, packet), bytes([verify_scored_proof(packet, context, target)]))
        rules = LabRules(context, 2**256, 99, 101, (h.payload,))
        changed = bytearray(packet)
        changed[rng.randrange(len(changed))] ^= 1 << rng.randrange(8)
        for other in (packet, b"", packet[:-1], packet+b"x", bytes(changed),
                      encode_proof(replace(h, nonce=h.nonce ^ 1), vector),
                      encode_proof(replace(h, timestamp=102), vector),
                      encode_proof(replace(h, timestamp=99), vector),
                      encode_proof(replace(h, payload=bytes(32)), vector),
                      encode_proof(h, tuple(-x for x in vector))):
            add("proof_admission", admission_request(rules, other), bytes([admit_proof(other, rules)]))
        for other in (replace(rules, target=0), replace(rules, latest=99, earliest=99),
                      replace(rules, context=replace(context, parent=bytes(32))),
                      replace(rules, payloads=tuple(bytes([k])*32 for k in range(8)))):
            add("trusted_surface", admission_request(other, packet), bytes([admit_proof(packet, other)]))
    for index, (actual, wanted) in enumerate(zip(exchange(executable, requests), expected, strict=True)):
        if actual != wanted:
            raise RuntimeError(f"admission differential mismatch at {index}")

    wire = encode_rules(frozen_rules)
    malformed_rules = (wire[:-1], wire+b"x", wire[:88]+b"\x02"+wire[89:],
                       wire[:137]+b"\x00"+wire[138:], wire[:137]+b"\x09"+wire[138:],
                       wire[:137]+b"\x02"+wire[138:]*2, wire[:121]+struct.pack("<QQ", 102, 101)+wire[137:])
    bad = [request(4, bytes(2049)), request(5, b""),
           scored_request(frozen_rules.context, 0, b"")[:93]+b"\x02"+bytes(32),
           request(6, b""), request(6, b"\xff\xff"), request(6, b"\x00\x00")]
    bad += [request(6, struct.pack("<H", len(r))+r+frozen_packet) for r in malformed_rules]
    for data in bad:
        result = subprocess.run([str(executable)], input=struct.pack("<I", len(data))+data,
                                capture_output=True, timeout=5)
        if result.returncode == 0 or not result.stderr or result.stdout:
            raise RuntimeError("malformed admission request did not fail cleanly")
    return {"seed": 2026100809, "cases": len(requests), "groups": counts,
            "mismatches": 0, "malformed_request_rejections": len(bad)}
