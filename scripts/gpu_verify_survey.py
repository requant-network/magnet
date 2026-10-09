"""Explicit local CUDA/Python/Rust correctness corpus; no mining speed claim."""

import argparse
import hashlib
import json
from pathlib import Path
import random
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from reference.gpu_verify import MAX_BATCH, prepare, verify_batch
from reference.sis import MAX_PACKET, Profile, encode_case, verify_packet
from scripts.consensus_evidence import begin_report, finish_report

SEED = 2026100906


def corpus():
    rng = random.Random(SEED)
    packets = []
    for q, n, m in ((2, 1, 2), (3, 2, 3), (7, 1, 3), (17, 2, 8),
                    (257, 3, 14), (65521, 64, 128)):
        p = Profile(q, n, m, q*q-1)
        for _ in range(32):
            matrix = [[rng.randrange(q) for _ in range(m)] for _ in range(n)]
            for row in matrix:
                row[1] = row[0]
            packets.extend((encode_case(p, matrix, [1, -1]+[0]*(m-2)),
                            encode_case(p, matrix, [1]+[0]*(m-1)),
                            encode_case(p, matrix, [rng.randint(-3, 3) for _ in range(m)])))
    p = Profile(65521, 64, 128, 65521**2-1)
    for a in (0, 1, 65520):
        for vector in ([65520]+[0]*127, [65521]+[0]*127, [0]*128,
                       [-1]+[0]*127, [2**31-1]*128, [-(2**31)]*128,
                       [1, -1]+[0]*126):
            packets.append(encode_case(p, [[a]*128]*64, vector))
    good = encode_case(Profile(7, 1, 2, 5), [[1, 2]], [2, -1])
    packets.extend((b'', good[:-1], good+b'x', b'x'*(MAX_PACKET+1)))
    bad_residue = bytearray(good)
    bad_residue[20:24] = (7).to_bytes(4, 'little')
    bad_profile = bytearray(good)
    bad_profile[4:8] = (4).to_bytes(4, 'little')
    packets.extend((bytes(bad_residue), bytes(bad_profile)))
    for _ in range(128):
        data = bytearray(good)
        data[rng.randrange(len(data))] ^= rng.randint(1, 255)
        packets.append(bytes(data))
    rng.shuffle(packets)
    return packets


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--native', type=Path, required=True)
    args = parser.parse_args()
    paths = begin_report('gpu-verification-v1')
    executable = args.native.resolve(strict=True)
    binary_hash = hashlib.sha256(executable.read_bytes()).hexdigest()
    import torch
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA required for this explicit survey')
    packets = corpus()
    expected = [verify_packet(p) for p in packets]
    # Oversize frames are invalid transport, checked separately without killing the corpus.
    normal = [(i, p) for i, p in enumerate(packets) if len(p) <= MAX_PACKET]
    wire = b''.join(struct.pack('<I', len(p))+p for _, p in normal)
    result = subprocess.run([str(executable)], input=wire, capture_output=True, timeout=60, check=True)
    if result.stderr or result.stdout != bytes(expected[i] for i, _ in normal):
        raise RuntimeError('independent Rust/Python corpus disagreement')
    malformed = subprocess.run([str(executable)], input=struct.pack('<I', MAX_PACKET+1),
                               capture_output=True, timeout=5)
    if malformed.returncode == 0:
        raise RuntimeError('native oversized frame accepted')
    torch.cuda.reset_peak_memory_stats()
    observed = []
    eligible = []
    for offset in range(0, len(packets), MAX_BATCH):
        batch = packets[offset:offset+MAX_BATCH]
        groups = prepare(batch)
        eligible.extend(offset+c[0] for cases in groups.values() for c in cases)
        observed.extend(verify_batch(batch))
    torch.cuda.synchronize()
    if observed != expected:
        raise RuntimeError('CUDA/Python/Rust verdict disagreement')
    if not any(expected[i] for i in eligible) or not any(not expected[i] for i in eligible):
        raise RuntimeError('corpus must exercise GPU acceptance and modular rejection')
    if hashlib.sha256(executable.read_bytes()).hexdigest() != binary_hash:
        raise RuntimeError('native binary changed during GPU experiment')
    framed = b''.join(struct.pack('<I', len(p))+p for p in packets)
    driver = subprocess.check_output(['nvidia-smi', '--query-gpu=driver_version,name,memory.total',
                                     '--format=csv,noheader'], text=True, timeout=10).strip()
    report = {
        'version': 'gpu-verification-v1', 'seed': SEED, 'cases': len(packets),
        'accepted': sum(expected), 'rejected': len(packets)-sum(expected),
        'native_case_comparisons': len(normal), 'native_oversized_frame_rejections': 1,
        'pipeline_case_comparisons': len(observed), 'cuda_case_comparisons': len(eligible),
        'host_rejected_cases': len(packets)-len(eligible),
        'cuda_accepted': sum(expected[i] for i in eligible),
        'cuda_modularly_rejected': sum(not expected[i] for i in eligible), 'mismatches': 0,
        'corpus_framed_sha256': hashlib.sha256(framed).hexdigest(),
        'native_verifier_sha256': binary_hash,
        'gpu': {'name': torch.cuda.get_device_name(0),
                'capability': list(torch.cuda.get_device_capability(0)),
                'torch': torch.__version__, 'cuda_runtime': torch.version.cuda,
                'driver_inventory': driver,
                'max_tensor_allocated_bytes': torch.cuda.max_memory_allocated(),
                'max_tensor_reserved_bytes': torch.cuda.max_memory_reserved()},
        'limitations': ['supplied-matrix verification only; no paid search, score kernel or MGH1 admission',
                        'host prechecks and GPU modular products; not all verification runs on GPU',
                        'logical tensor caps exclude context/allocator overhead; no external memory ceiling',
                        'no time, energy, hashrate, GPU advantage or hardware-isolation claim'],
    }
    finish_report(paths[:2], report, paths[2], executable=executable,
                  expected_executable_sha256=binary_hash, build_profile='release',
                  raw={'packets_hex': [p.hex() for p in packets], 'expected': expected,
                       'observed': observed, 'cuda_eligible_indices': sorted(eligible)})


if __name__ == '__main__':
    main()
