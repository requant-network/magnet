"""Exact rejection-path timing batches; IPC/startup are disclosed, no throughput claim."""

from dataclasses import replace
import hashlib
import json
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from reference.admission_wire import admission_request, decode_rules
from reference.grinding import score_digest
from reference.header import LabHeader, encode_proof
from reference.header_rules import admit_proof
from reference.sis import Profile
from scripts.lab_driver import build_lab, exchange
from scripts.sphere_survey import source_hashes


def run():
    output = ROOT / "docs/research/results/rejection-cost-v1.json"
    output.write_text('{"status":"running-or-incomplete"}\n', encoding="utf-8")
    executable = build_lab(target_dir=ROOT / "artifacts/admission-current")
    fixture = json.loads((ROOT / "tests/vectors/admission-v1.json").read_text())
    packet = bytes.fromhex(fixture["proof_hex"])
    rules = decode_rules(bytes.fromhex(fixture["rules_hex"]))
    h = LabHeader.decode(packet[:140])
    digest = int.from_bytes(score_digest(h, (0, 1, 0)), "big")
    score_rules = replace(rules, target=digest)
    large = replace(h, profile=Profile(65521, 64, 128, 65521**2-1))
    large_rules = replace(rules, context=replace(rules.context, profile=large.profile))
    groups = {"malformed-length": (packet[:-1], rules), "valid-SIS-strict-score-reject": (packet, score_rules),
              "maximum-shape-residual-reject": (encode_proof(large, (1,)+(0,)*127), large_rules)}
    records = {}
    count, repeats = 256, 5
    for name, (proof, policy) in groups.items():
        if admit_proof(proof, policy):
            raise RuntimeError("rejection fixture unexpectedly accepted")
        native_times, reference_times = [], []
        wires = [admission_request(policy, proof)]*count
        for _ in range(repeats):
            start = time.perf_counter_ns()
            expected = [bytes([admit_proof(proof, policy)]) for _ in range(count)]
            reference_times.append(time.perf_counter_ns()-start)
            start = time.perf_counter_ns()
            actual = exchange(executable, wires)
            native_times.append(time.perf_counter_ns()-start)
            if actual != expected or any(x != b"\x00" for x in actual):
                raise RuntimeError("rejection differential mismatch")
        records[name] = {"count_per_batch": count, "batches": repeats, "native_batch_ns": native_times,
                         "reference_batch_ns": reference_times, "median_native_ns_per_packet_with_startup_IPC": statistics.median(native_times)/count,
                         "median_reference_ns_per_packet": statistics.median(reference_times)/count, "accepted": 0}
    report = {"status": "passed", "source_sha256": source_hashes(), "records": records,
              "native_build_profile": "debug", "executable_sha256": hashlib.sha256(executable.read_bytes()).hexdigest(),
              "limitations": ["five fixed repeated batches; OS cache/load shared", "native includes process startup and transport",
                              "controlled fixtures, not network DoS capacity", "same host as concurrent endurance fuzzer"]}
    output.write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(records, indent=2))


if __name__ == "__main__":
    run()
