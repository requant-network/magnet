"""Bounded local adapter client; select the executable from this Cargo build."""

import json
import os
from pathlib import Path
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[1]
MAX_REQUEST = 2057
MAX_RESPONSE = 67584


def build_lab():
    result = subprocess.run(["cargo", "build", "--offline", "--locked", "--bin", "sis-lab",
                             "--message-format=json"], cwd=ROOT, capture_output=True,
                            check=True, timeout=180,
                            env={**os.environ, "CARGO_TARGET_DIR": str(ROOT / "target")})
    paths = [item["executable"] for line in result.stdout.splitlines()
             if (item := json.loads(line)).get("reason") == "compiler-artifact"
             and item.get("executable") and item["target"]["name"] == "sis-lab"
             and "bin" in item["target"]["kind"]]
    if len(paths) != 1:
        raise RuntimeError("Cargo did not identify exactly one sis-lab executable")
    return Path(paths[0])


def exchange(executable, requests):
    requests = tuple(requests)
    if any(type(request) is not bytes or len(request) > MAX_REQUEST for request in requests):
        raise ValueError("request length/type")
    wire = b"".join(struct.pack("<I", len(request)) + request for request in requests)
    result = subprocess.run([str(executable)], input=wire, capture_output=True, check=True, timeout=60)
    if result.stderr:
        raise RuntimeError("unexpected lab diagnostics")
    responses, cursor = [], 0
    for _ in requests:
        if cursor + 4 > len(result.stdout):
            raise RuntimeError("missing response length")
        length, = struct.unpack_from("<I", result.stdout, cursor)
        cursor += 4
        if length > MAX_RESPONSE or cursor + length > len(result.stdout):
            raise RuntimeError("invalid response length")
        responses.append(result.stdout[cursor:cursor + length])
        cursor += length
    if cursor != len(result.stdout):
        raise RuntimeError("trailing lab response")
    return responses


def matrix_bytes(matrix):
    flat = [value for row in matrix for value in row]
    return struct.pack(f"<{len(flat)}I", *flat)


def request(mode, payload):
    return b"MGL1" + bytes([mode]) + payload
