"""One local entry point: formatting, Rust/Python tests and differential corpus."""

import hashlib
import json
import os
from pathlib import Path
import platform
import random
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from reference.sis import MAX_PACKET, Profile, encode_case, verify_packet
from scripts.native_checks import differential_search
from scripts.binding_checks import differential_binding
from scripts.admission_checks import differential_admission
from scripts.block_checks import differential_blocks
from scripts.chain_checks import differential_chain


def run(command, capture_output=False):
    print("+ " + " ".join(command), flush=True)
    return subprocess.run(command, cwd=ROOT, check=True, timeout=180, capture_output=capture_output,
                          env={**os.environ, "CARGO_TARGET_DIR": str(ROOT / "target")})


def differential(executable):
    rng = random.Random(20261008)
    corpus = []
    for i in range(10_000):
        p = Profile(rng.choice([3, 7, 17, 257, 65521]), rng.randint(1, 4), rng.randint(2, 6), 2)
        matrix = [[rng.randrange(p.q) for _ in range(p.m)] for _ in range(p.n)]
        for row in matrix:
            row[1] = row[0]
        packet = encode_case(p, matrix, [1, -1] + [0] * (p.m - 2))
        if i % 4 == 1:
            data = bytearray(packet)
            data[rng.randrange(len(data))] ^= rng.randint(1, 255)
            packet = bytes(data)
        elif i % 4 == 2:
            packet = rng.randbytes(rng.randrange(200))
        elif i % 4 == 3:
            vector = [rng.randint(-3, 3) for _ in range(p.m)]
            packet = encode_case(p, matrix, vector)
        corpus.append(packet)

    # Extreme valid/invalid payloads exercise the integer and dimension limits.
    p = Profile(65521, 64, 128, 65521**2 - 1)
    matrix = [[0] * 128 for _ in range(64)]
    for first in [65520, 65521, -(2**31), 2**31 - 1]:
        corpus.append(encode_case(p, matrix, [first] + [0] * 127))
    fixture = json.loads((ROOT / "tests/vectors/manual.json").read_text(encoding="utf-8"))
    for case in fixture:
        corpus.append(encode_case(Profile(**case["profile"]), case["matrix"], case["vector"]))

    wire = b"".join(struct.pack("<I", len(packet)) + packet for packet in corpus)
    result = subprocess.run([str(executable)], input=wire, capture_output=True, timeout=60, check=True)
    expected = bytes(int(verify_packet(packet)) for packet in corpus)
    if result.stdout != expected:
        mismatch = next((i for i, pair in enumerate(zip(result.stdout, expected)) if pair[0] != pair[1]),
                        min(len(result.stdout), len(expected)))
        raise RuntimeError(f"Rust/Python mismatch at corpus index {mismatch}")
    if result.stderr:
        raise RuntimeError("unexpected verifier diagnostics")

    # Framing failures must exit, not allocate huge buffers or hang awaiting input.
    for wire in [b"\x01", struct.pack("<I", MAX_PACKET + 1), struct.pack("<I", 10) + b"abc"]:
        result = subprocess.run([str(executable)], input=wire, capture_output=True, timeout=5)
        if result.returncode == 0:
            raise RuntimeError("malformed framing unexpectedly accepted")
    valid = encode_case(Profile(7, 1, 2, 5), [[1, 2]], [2, -1])
    for wire, expected_output in [(b"", b""),
                                  (struct.pack("<II", 0, len(valid)) + valid, b"\x00\x01")]:
        result = subprocess.run([str(executable)], input=wire, capture_output=True, timeout=5, check=True)
        if result.stdout != expected_output:
            raise RuntimeError("empty input/frame handling differs from specification")
    print(f"Differential: {len(corpus)} cases, {sum(expected)} accepted, zero mismatches", flush=True)
    return {"seed": 20261008, "cases": len(corpus), "accepted": sum(expected), "mismatches": 0,
            "framing_rejections": 3, "empty_stream_checks": 2}


def main():
    destination = ROOT / "artifacts"
    destination.mkdir(exist_ok=True)
    report_path = destination / "local-checks.json"
    # A failed run must not leave a previous success looking like a fresh result.
    report_path.write_text('{"status": "running-or-incomplete"}\n', encoding="utf-8")
    run(["cargo", "fmt", "--check"])
    run(["cargo", "clippy", "--offline", "--locked", "--all-targets", "--", "-D", "warnings"])
    run(["cargo", "test", "--offline", "--locked"])
    run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"])
    build = run(["cargo", "build", "--offline", "--locked", "--message-format=json"], capture_output=True)
    sys.stderr.write(build.stderr.decode("utf-8"))
    artifacts = [json.loads(line) for line in build.stdout.splitlines()]
    executables = [item["executable"] for item in artifacts
                   if item.get("reason") == "compiler-artifact" and item.get("executable")
                   and item["target"]["name"] == "sis-verify" and "bin" in item["target"]["kind"]]
    if len(executables) != 1:
        raise RuntimeError("Cargo did not identify exactly one sis-verify executable")
    executable = Path(executables[0])
    search_paths = [item["executable"] for item in artifacts
                    if item.get("reason") == "compiler-artifact" and item.get("executable")
                    and item["target"]["name"] == "sis-search" and "bin" in item["target"]["kind"]]
    if len(search_paths) != 1:
        raise RuntimeError("Cargo did not identify exactly one sis-search executable")
    native = differential_search(Path(search_paths[0]))
    print(f"Native differential: {native}", flush=True)
    lab_paths = [item["executable"] for item in artifacts
                 if item.get("reason") == "compiler-artifact" and item.get("executable")
                 and item["target"]["name"] == "sis-lab" and "bin" in item["target"]["kind"]]
    if len(lab_paths) != 1:
        raise RuntimeError("Cargo did not identify exactly one sis-lab executable")
    binding = differential_binding(Path(lab_paths[0]))
    print(f"Binding differential: {binding}", flush=True)
    admission = differential_admission(Path(lab_paths[0]))
    print(f"Admission differential: {admission}", flush=True)
    blocks = differential_blocks(Path(lab_paths[0]))
    print(f"Block differential: {blocks}", flush=True)
    chain_paths = [item["executable"] for item in artifacts
                   if item.get("reason") == "compiler-artifact" and item.get("executable")
                   and item["target"]["name"] == "magnet-chain" and "bin" in item["target"]["kind"]]
    if len(chain_paths) != 1:
        raise RuntimeError("Cargo did not identify exactly one magnet-chain executable")
    chain = differential_chain(Path(chain_paths[0]))
    print(f"Full-chain differential: {chain}", flush=True)
    report = {"python": platform.python_version(), "platform": platform.platform(),
              "differential": differential(executable), "native_search": native,
              "header_binding": binding, "admission": admission, "blocks": blocks, "chain": chain, "status": "passed"}
    paths = [ROOT / "Cargo.toml", ROOT / "Cargo.lock", ROOT / "benchmarks/flint-win.lock"]
    for folder, pattern in [("reference", "*.py"), ("solvers", "*.py"), ("scripts", "*.py"), ("tests", "*.py"),
                            ("tests/vectors", "*.json"), ("crates", "*.rs"), ("spec", "*.md")]:
        paths.extend((ROOT / folder).rglob(pattern))
    report["source_sha256"] = {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                               for path in sorted(paths)}
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("Local checks passed. Report: artifacts/local-checks.json", flush=True)


if __name__ == "__main__":
    main()
