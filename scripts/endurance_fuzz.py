"""Local timed native/reference admission fuzzing; no remote compute or secrets."""

import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import random
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from reference.admission_wire import admission_request, decode_rules
from reference.header import LabHeader, encode_proof
from reference.header_rules import admit_proof
from reference.sis import Profile
from scripts.lab_driver import build_lab, exchange


def run(seconds, seed=2026100815):
    if type(seconds) is not int or not 1 <= seconds <= 7200:
        raise ValueError("fuzz duration must be 1..7200 seconds")
    output = ROOT / "docs/research/results/endurance-fuzz-v1.json"
    output.write_text('{"status":"running-or-incomplete"}\n', encoding="utf-8")
    executable = build_lab()
    paths = [Path(__file__), *sorted((ROOT / "reference").glob("*.py")),
             *sorted((ROOT / "crates/sis-verifier/src").glob("*.rs"))]
    hashes = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    fixture = json.loads((ROOT / "tests/vectors/admission-v1.json").read_text())
    original = bytes.fromhex(fixture["proof_hex"])
    rules = decode_rules(bytes.fromhex(fixture["rules_hex"]))
    header = LabHeader.decode(original[:140])
    rng = random.Random(seed)
    counts = dict.fromkeys(("mutation", "truncation", "extension", "random", "near-valid", "large-instance"), 0)
    elapsed_groups = {name: {"native_batch_ns": 0, "reference_ns": 0, "batches": 0} for name in counts}
    total, accepted, batches = 0, 0, 0
    begin = time.perf_counter()
    while time.perf_counter()-begin < seconds:
        name = tuple(counts)[batches % len(counts)]
        packets = []
        # Homogeneous batches permit honest timings by input family, including
        # process startup and transport in native_batch_ns (not isolated CPU).
        for _ in range(256):
            if name == "mutation":
                wire = bytearray(original)
                for _ in range(rng.randint(1, 4)):
                    wire[rng.randrange(len(wire))] ^= 1 << rng.randrange(8)
                packet = bytes(wire)
            elif name == "truncation":
                packet = original[:rng.randrange(len(original))]
            elif name == "extension":
                packet = original + rng.randbytes(rng.randint(1, 64))
            elif name == "random":
                packet = rng.randbytes(rng.randrange(700))
            elif name == "near-valid":
                h = replace(header, nonce=rng.getrandbits(64))
                packet = encode_proof(h, (0, 1, 0))
            else:
                h = replace(header, profile=Profile(65521, 64, 128, 65521**2-1), nonce=rng.getrandbits(64))
                packet = encode_proof(h, (1,) + (0,)*127)
            packets.append(packet)
        current = rules
        if name == "large-instance":
            current = replace(rules, context=replace(rules.context, profile=h.profile))
        start = time.perf_counter_ns()
        expected = [bytes([admit_proof(p, current)]) for p in packets]
        elapsed_groups[name]["reference_ns"] += time.perf_counter_ns()-start
        start = time.perf_counter_ns()
        actual = exchange(executable, [admission_request(current, p) for p in packets])
        elapsed_groups[name]["native_batch_ns"] += time.perf_counter_ns()-start
        if actual != expected:
            raise RuntimeError(f"endurance differential mismatch in batch {batches}, family {name}")
        total += len(packets)
        accepted += sum(value == b"\x01" for value in expected)
        counts[name] += len(packets)
        elapsed_groups[name]["batches"] += 1
        batches += 1
        if batches % 60 == 0:
            print(f"fuzz {time.perf_counter()-begin:.1f}s: {total} cases, zero mismatches", flush=True)
    report = {"status": "passed", "seed": seed, "requested_seconds": seconds,
              "elapsed_seconds": time.perf_counter()-begin, "cases": total, "accepted": accepted,
              "batches": batches, "groups": counts, "timings": elapsed_groups, "mismatches": 0,
              "source_sha256": hashes, "executable_sha256": hashlib.sha256(executable.read_bytes()).hexdigest(),
              "scope": "well-formed mode-6 framing, mutated proofs; timing includes process/IPC; not network fuzz"}
    report["source_unchanged"] = all(hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == value for p, value in hashes.items())
    output.write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("status", "cases", "elapsed_seconds", "source_unchanged")}), flush=True)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=int, default=3600)
    run(parser.parse_args().seconds)
