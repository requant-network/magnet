"""Deterministic cross-language XOF, generation, binding and rejection corpus."""

from dataclasses import replace
import hashlib
import json
from pathlib import Path
import random
import struct
import subprocess

from reference.header import ExpectedContext, HEADER, LabHeader, encode_proof, verify_proof
from reference.search import exhaustive_solutions
from reference.sis import Profile, expand_matrix
from scripts.lab_driver import MAX_REQUEST, exchange, matrix_bytes, request


def differential_binding(executable):
    rng = random.Random(2026100808)
    requests, expected, counts = [], [], {}

    def add(group, command, response):
        counts[group] = counts.get(group, 0) + 1
        requests.append(command)
        expected.append(response)

    # Absorb and squeeze boundaries, exact multiples, partial lanes, both bounds.
    for input_length in [0, 1, 7, 8, 135, 136, 137, 271, 272, 273, 2048]:
        data = rng.randbytes(input_length)
        for length in [0, 1, 31, 32, 135, 136, 137, 272, 273, 67584]:
            add("shake", request(0, struct.pack("<I", length) + data),
                hashlib.shake_256(data).digest(length))
    for _ in range(64):
        data, length = rng.randbytes(rng.randrange(2049)), rng.randrange(2049)
        add("shake", request(0, struct.pack("<I", length) + data), hashlib.shake_256(data).digest(length))

    for i in range(200):
        q = [2, 3, 7, 17, 257, 32771, 65521][i % 7]
        n, m = (64, 128) if i % 40 == 0 else (rng.randint(1, 8), rng.randint(1, 16))
        p = Profile(q, n, m, rng.choice([1, q*q - 1]))
        seed = rng.randbytes(32)
        add("matrix", request(1, struct.pack("<IHHQ", p.q, p.n, p.m, p.b2) + seed),
            matrix_bytes(expand_matrix(p, seed)))

    def generate(header):
        add("header_generation", request(2, header.encode()), header.seed() + matrix_bytes(header.matrix()))

    def verify(header, packet, context=None):
        context = context or ExpectedContext(header.network, header.parent, header.height, header.profile)
        add("proof", request(3, context.encode() + packet), bytes([verify_proof(packet, context)]))

    fixture = json.loads((Path(__file__).resolve().parents[1] / "tests/vectors/header-v1.json").read_text())
    frozen = LabHeader.decode(bytes.fromhex(fixture["header_hex"]))
    add("frozen_header", request(2, frozen.encode()),
        bytes.fromhex(fixture["seed_hex"]) + matrix_bytes(fixture["matrix"]))
    context = ExpectedContext(frozen.network, frozen.parent, frozen.height, frozen.profile)
    add("frozen_proof", request(3, context.encode() + bytes.fromhex(fixture["proof_hex"])), b"\x01")

    for i in range(100):
        header = LabHeader(rng.randbytes(32), rng.randbytes(32), rng.randbytes(32),
                           rng.getrandbits(64), rng.getrandbits(64), i, Profile(7, 1, 3, 8))
        generate(header)
        solutions = list(exhaustive_solutions(header.profile, header.matrix()))
        vector = solutions[0] if solutions else (1, 0, 0)
        packet = encode_proof(header, vector)
        verify(header, packet)
        verify(header, encode_proof(header, (0, 0, 0)))
        verify(header, encode_proof(header, (-2**31, 2**31 - 1, 0)))
        verify(header, packet + b"\0")
        verify(header, packet[:-1])
        verify(header, b"MGH2" + packet[4:])
        changed = bytearray(packet)
        changed[rng.randrange(HEADER.size)] ^= 1
        verify(header, bytes(changed))
        verify(header, encode_proof(replace(header, nonce=i + 1), vector))
        context = ExpectedContext(header.network, header.parent, header.height, header.profile)
        for replacement in [replace(context, network=bytes(32)), replace(context, parent=bytes(32)),
                            replace(context, height=context.height ^ 1),
                            replace(context, profile=Profile(7, 1, 3, 9))]:
            verify(header, packet, replacement)
        verify(header, rng.randbytes(rng.randrange(653)))

    base = LabHeader(bytes(32), bytes(range(32)), b"P" * 32, 0, 0, 0, Profile(32771, 3, 8, 5))
    for header in [base, replace(base, network=b"N" * 32), replace(base, parent=b"Q" * 32),
                   replace(base, payload=b"R" * 32), replace(base, height=2**64 - 1),
                   replace(base, timestamp=2**64 - 1), replace(base, nonce=2**64 - 1),
                   replace(base, profile=Profile(65521, 64, 128, 65521**2 - 1)),
                   replace(base, profile=Profile(2, 1, 1, 1))]:
        generate(header)
        verify(header, encode_proof(header, (1,) + (0,) * (header.profile.m - 1)))
    # Every truncation, oversized proof and a canonical existing SIS1 supplied-A packet.
    for end in range(HEADER.size):
        verify(base, base.encode()[:end])
    verify(base, b"\0" * 653)
    verify(base, b"SIS1" + b"\0" * 160)

    actual = exchange(executable, requests)
    for index, (left, right) in enumerate(zip(actual, expected, strict=True)):
        if left != right:
            raise RuntimeError(f"binding differential mismatch at {index}")

    invalid = [b"", b"MGL2\x00", b"MGL1\x04", request(0, b"\0" * 3),
               request(0, struct.pack("<I", 67585)), request(1, b"\0" * 48),
               request(1, b"\0" * 47), request(1, b"\0" * 49),
               request(2, base.encode()[:-1]), request(2, base.encode() + b"\0"),
               request(2, b"MGH2" + base.encode()[4:]), request(3, b"\0" * 88)]
    for fields in [(1, 1, 1, 1), (4, 1, 1, 1), (65537, 1, 1, 1),
                   (7, 0, 1, 1), (7, 65, 1, 1), (7, 1, 0, 1), (7, 1, 129, 1),
                   (7, 1, 1, 0), (7, 1, 1, 49), (7, 1, 1, 2**64 - 1)]:
        invalid.append(request(1, struct.pack("<IHHQ", *fields) + bytes(32)))
    wires = [struct.pack("<I", len(data)) + data for data in invalid]
    wires.extend([b"\x01", struct.pack("<I", MAX_REQUEST + 1), struct.pack("<I", 10) + b"abc"])
    for wire in wires:
        result = subprocess.run([str(executable)], input=wire, capture_output=True, timeout=5)
        if result.returncode == 0 or not result.stderr or result.stdout:
            raise RuntimeError("invalid lab request/framing did not fail cleanly")
    if exchange(executable, []) != []:
        raise RuntimeError("empty stream handling")
    return {"seed": 2026100808, "cases": len(requests), "groups": counts, "mismatches": 0,
            "malformed_request_rejections": len(wires), "empty_stream_checks": 1}
