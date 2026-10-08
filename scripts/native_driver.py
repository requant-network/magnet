"""Strict bounded client for the local native search laboratory protocol."""
import json
import os
from pathlib import Path
import struct
import subprocess

from reference.sis import encode_case

ROOT = Path(__file__).resolve().parents[1]
REQUEST = struct.Struct("<4sB3xQIQII")
RESPONSE = struct.Struct("<4sB3xH2xIIQ10Q")
ALGORITHMS = {"ball": 1, "mitm": 2}
STOPS = ("domain-exhausted", "node-limit", "table-limit", "pair-limit", "proof-limit", "half-box-limit")
WORK_NAMES = ("nodes", "left", "right", "norm_terms", "matrix_terms", "row_reductions",
              "leaves", "table_entries", "pairs", "proofs")
MAX_RESPONSE = RESPONSE.size + 9 * 8 + 100_000 * 128 * 4


def build_native(*, release=False):
    command = ["cargo", "build", "--offline", "--locked", "--bin", "sis-search", "--message-format=json"]
    if release:
        command.append("--release")
    result = subprocess.run(command, cwd=ROOT, capture_output=True, timeout=180, check=True,
                            env={**os.environ, "CARGO_TARGET_DIR": str(ROOT / "target")})
    items = [json.loads(line) for line in result.stdout.splitlines()]
    paths = [item["executable"] for item in items if item.get("reason") == "compiler-artifact"
             and item.get("executable") and item["target"]["name"] == "sis-search"]
    if len(paths) != 1:
        raise RuntimeError("Cargo did not identify exactly one native search executable")
    return Path(paths[0])


def encode_request(profile, matrix, algorithm, *, nodes=50_000_000, table=1_000_000,
                   pairs=10_000_000, proofs=100_000, repeats=1):
    if algorithm not in ALGORITHMS:
        raise ValueError("unknown native search algorithm")
    for value, maximum in ((nodes, 50_000_000), (table, 1_000_000), (pairs, 10_000_000),
                           (proofs, 100_000), (repeats, 9)):
        if type(value) is not int or not 1 <= value <= maximum:
            raise ValueError("limit outside native laboratory budget")
    return REQUEST.pack(b"NAT1", ALGORITHMS[algorithm], nodes, table, pairs, proofs, repeats) + \
        encode_case(profile, matrix, [0] * profile.m)


def decode_response(body):
    if len(body) < RESPONSE.size or len(body) > MAX_RESPONSE:
        raise ValueError("invalid response length")
    magic, stop, width, count, repeats, capacity, *words = RESPONSE.unpack_from(body)
    if magic != b"NSR1" or body[5:8] != bytes(3) or body[10:12] != bytes(2):
        raise ValueError("invalid response header")
    if stop >= len(STOPS) or not 1 <= width <= 128 or count > 100_000 or not 1 <= repeats <= 9:
        raise ValueError("response bounds exceeded")
    expected = RESPONSE.size + repeats * 8 + count * width * 4
    if len(body) != expected or words[-1] != count:
        raise ValueError("inconsistent response payload")
    times = struct.unpack_from(f"<{repeats}Q", body, RESPONSE.size)
    offset = RESPONSE.size + repeats * 8
    vectors = [struct.unpack_from(f"<{width}i", body, offset + i * width * 4) for i in range(count)]
    return {"stop": STOPS[stop], "width": width, "owned_capacity_bytes": capacity,
            "work": dict(zip(WORK_NAMES, words)), "elapsed_ns": list(times), "proofs": vectors}


def run_requests(executable, requests, *, timeout=180):
    requests = tuple(requests)
    wire = b"".join(struct.pack("<I", len(body)) + body for body in requests)
    result = subprocess.run([str(executable)], input=wire, capture_output=True, check=True, timeout=timeout)
    if result.stderr:
        raise RuntimeError("unexpected native search diagnostics")
    offset, responses = 0, []
    for _ in requests:
        if len(result.stdout) - offset < 4:
            raise ValueError("missing response frame")
        size = struct.unpack_from("<I", result.stdout, offset)[0]
        offset += 4
        if size > MAX_RESPONSE or len(result.stdout) - offset < size:
            raise ValueError("invalid response frame")
        responses.append(decode_response(result.stdout[offset:offset + size]))
        offset += size
    if offset != len(result.stdout):
        raise ValueError("unexpected trailing response bytes")
    return responses
