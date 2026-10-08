"""Bounded MCP1 local native chain adapter. No network or untrusted executable path."""

import json
from itertools import islice
import os
from pathlib import Path
import struct
import subprocess

from reference.block import MAX_BLOCK
from reference.chain import ChainPolicy
from reference.admission_wire import target_bytes

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = struct.Struct("<BQ32sH")
STATUSES = ("accepted", "malformed", "wrong-policy", "unknown-or-nontip-parent", "wrong-height",
            "past-time", "defer-future-time", "invalid-proof", "storage-limit")


def build_chain():
    result = subprocess.run(["cargo", "build", "--offline", "--locked", "--bin", "magnet-chain", "--message-format=json"],
                            cwd=ROOT, check=True, capture_output=True, timeout=180,
                            env={**os.environ, "CARGO_TARGET_DIR": str(ROOT / "target")})
    items = [json.loads(line) for line in result.stdout.splitlines()]
    paths = [r["executable"] for r in items if r.get("reason") == "compiler-artifact" and r.get("executable")
             and r["target"]["name"] == "magnet-chain" and "bin" in r["target"]["kind"]]
    if len(paths) != 1:
        raise RuntimeError("Cargo did not identify exactly one chain executable")
    return Path(paths[0])


def encode_policy(policy):
    if not isinstance(policy, ChainPolicy):
        raise ValueError("trusted policy required")
    p = policy.profile
    return b"MCP1" + policy.network + struct.pack("<IHHQ", p.q,p.n,p.m,p.b2) + target_bytes(policy.target) + \
        policy.anchor + struct.pack("<QQH",policy.anchor_height,policy.anchor_time,policy.future_seconds)


def command(packet=b"", *, now=0, append=True):
    if type(packet) is not bytes or len(packet) > MAX_BLOCK or type(now) is not int or not 0 <= now < 2**64 or type(append) is not bool:
        raise ValueError("chain command bounds/type")
    return bytes([1 if append else 2]) + struct.pack("<Q",now) + packet


def exchange_chain(executable, policy, commands):
    commands = tuple(islice(commands,8193))
    if len(commands) > 8192 or any(type(c) is not bytes or len(c) > 9+MAX_BLOCK for c in commands):
        raise ValueError("chain command stream bounds")
    frames = (encode_policy(policy),) + commands
    wire = b"".join(struct.pack("<I",len(f))+f for f in frames)
    result = subprocess.run([str(executable)],input=wire,check=True,capture_output=True,timeout=60)
    if result.stderr or len(result.stdout) != len(frames)*SNAPSHOT.size:
        raise RuntimeError("chain response framing/diagnostics")
    records = []
    for offset in range(0,len(result.stdout),SNAPSHOT.size):
        status,height,tip,count = SNAPSHOT.unpack_from(result.stdout,offset)
        if status >= len(STATUSES) or count > 4096:
            raise RuntimeError("chain response bounds")
        records.append({"status":STATUSES[status],"height":height,"tip":tip.hex(),"count":count})
    return records
