"""Deterministic paid sparse acquisition plus independent CUDA-domain audits."""

import argparse
from collections import Counter
import hashlib
import itertools
from pathlib import Path
import random
import struct
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from reference.gpu_search import _cuda_candidates, candidates, search
from reference.sis import Profile, encode_case, expand_matrix, verify
from scripts.consensus_evidence import begin_report, finish_report

SEEDS = (2026100907, 2026100908)
ORDER_SEED = 2026100909
COMMON = ('generated', 'screened', 'vector_entries', 'matrix_grid_slots',
          'matrix_entries', 'batches', 'accepted_seen', 'returned')


def schedule():
    jobs = []
    for values in ((2, 1, 4, 2), (7, 1, 8, 2), (17, 2, 16, 2),
                   (257, 3, 32, 2), (65521, 4, 128, 2)):
        for seed in SEEDS:
            for cap, proofs, batch in ((16384, 256, 64), (16384, 256, 256), (13, 3, 7)):
                label = 'gpu-sparse-v1/'+ '-'.join(map(str, values))+'/'+str(seed)
                jobs.append({'label': label, 'profile': dict(zip(('q', 'n', 'm', 'b2'), values)),
                             'seed_hex': hashlib.sha256(label.encode()).hexdigest(),
                             'fixture': None, 'candidate_limit': cap, 'proof_limit': proofs, 'batch_size': batch})
    fixtures = (('zero', (7, 2, 3, 2)), ('identity', (17, 3, 3, 2)),
                ('zero', (2, 1, 4, 2)), ('zero', (7, 1, 4, 1)),
                ('one', (7, 1, 1, 1)), ('zero', (65521, 64, 128, 2)))
    for fixture, values in fixtures:
        for cap, proofs, batch in ((16384, 256, 64), (257, 1, 7)):
            jobs.append({'label': 'fixture/'+fixture+'/'+ '-'.join(map(str, values)),
                         'profile': dict(zip(('q', 'n', 'm', 'b2'), values)), 'seed_hex': None,
                         'fixture': fixture, 'candidate_limit': cap, 'proof_limit': proofs, 'batch_size': batch})
    random.Random(ORDER_SEED).shuffle(jobs)
    return jobs


def matrix_for(job):
    p = Profile(**job['profile'])
    if job['fixture'] is None:
        return expand_matrix(p, bytes.fromhex(job['seed_hex']))
    if job['fixture'] == 'zero':
        return tuple((0,)*p.m for _ in range(p.n))
    return tuple(tuple(int(i == j) for j in range(p.m)) for i in range(p.n))


def audit_domain(torch, profile, batch_size):
    """Outside paid search: check every GPU-generated ordinal against host order."""
    domain = profile.m if profile.b2 == 1 else profile.m**2
    positions = torch.arange(profile.m, dtype=torch.int64, device='cuda')
    starts = positions*(2*profile.m-positions-1)//2
    expected = candidates(profile)
    digest = hashlib.sha256()
    for offset in range(0, domain, batch_size):
        count = min(batch_size, domain-offset)
        ids = torch.arange(offset, offset+count, dtype=torch.int64, device='cuda')
        vectors = _cuda_candidates(torch, ids, profile.m, starts)
        actual = [tuple(v) for v in vectors.tolist()]
        if actual != list(itertools.islice(expected, count)):
            raise RuntimeError('CUDA candidate ordinal/domain disagreement')
        for v in actual:
            digest.update(struct.pack('<'+'i'*profile.m, *v))
        del ids, vectors
    return {'m': profile.m, 'b2': profile.b2, 'batch_size': batch_size,
            'candidates': domain, 'ordered_vectors_sha256': digest.hexdigest()}


def reconcile(cpu, gpu):
    for key in ('domain', 'reason', 'domain_exhausted', 'all_proofs_returned', 'proofs'):
        if cpu[key] != gpu[key]:
            raise RuntimeError('CPU/CUDA sparse '+key+' disagreement')
    if any(cpu['work'][k] != gpu['work'][k] for k in COMMON):
        raise RuntimeError('CPU/CUDA sparse ledger disagreement')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--native', type=Path, required=True)
    args = parser.parse_args()
    paths = begin_report('gpu-unit-sparse-search-v1')
    executable = args.native.resolve(strict=True)
    binary_hash = hashlib.sha256(executable.read_bytes()).hexdigest()
    import torch
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA required for sparse search survey')
    jobs = schedule()
    records, domains, packets = [], {}, []
    overall = {'python': Counter(), 'cuda': Counter()}
    reasons = {'python': Counter(), 'cuda': Counter()}
    timings = Counter()
    torch.cuda.reset_peak_memory_stats()
    for index, job in enumerate(jobs):
        p = Profile(**job['profile'])
        start = time.perf_counter_ns()
        matrix = matrix_for(job)
        generation_ns = time.perf_counter_ns()-start
        settings = {k: job[k] for k in ('candidate_limit', 'proof_limit', 'batch_size')}
        outputs = {}
        # Rotate execution order without ranking elapsed times.
        for backend in (('python', 'cuda') if index % 2 else ('cuda', 'python')):
            result = search(p, matrix, backend=backend, **settings)
            outputs[backend] = result
            overall[backend].update(result['work'])
            reasons[backend][result['reason']] += 1
            timings[backend] += result['elapsed_ns']
            for vector in result['proofs']:
                if not verify(p, matrix, vector):
                    raise RuntimeError('sparse search output fails independent host verifier')
                packets.append(encode_case(p, matrix, vector))
        reconcile(outputs['python'], outputs['cuda'])
        key = (p.m, p.b2, job['batch_size'])
        if key not in domains:
            domains[key] = audit_domain(torch, p, job['batch_size'])
        if p.m <= 4 and outputs['python']['all_proofs_returned']:
            independent = {v for v in itertools.product((-1, 0, 1), repeat=p.m)
                           if 1 <= sum(x*x for x in v) <= min(2, p.b2)
                           and next(x for x in v if x) > 0 and verify(p, matrix, v)}
            if set(outputs['cuda']['proofs']) != independent:
                raise RuntimeError('tiny complete accepted-set disagreement')
        records.append({'job': job, 'matrix': matrix, 'generation_ns': generation_ns, 'outputs': outputs})
        print(f'Sparse CUDA audit {index+1}/{len(jobs)}', flush=True)
    for offset in range(0, len(packets), 256):
        group = packets[offset:offset+256]
        wire = b''.join(struct.pack('<I', len(p))+p for p in group)
        result = subprocess.run([str(executable)], input=wire, capture_output=True, timeout=30, check=True)
        if result.stderr or result.stdout != b'\x01'*len(group):
            raise RuntimeError('independent native sparse proof disagreement')
    report = {'version': 'gpu-unit-sparse-search-v1', 'seeds': list(SEEDS), 'order_seed': ORDER_SEED,
              'scheduled_attempts': len(jobs)*2, 'completed_attempts': len(records)*2,
              'paired_cases': len(records), 'mismatches': 0,
              'seeded_cases': sum(r['job']['fixture'] is None for r in records),
              'fixture_cases': sum(r['job']['fixture'] is not None for r in records),
              'unique_seeded_challenges': len({r['job']['seed_hex'] for r in records if r['job']['seed_hex']}),
              'returned_occurrences_by_kind': {
                  kind: sum(len(r['outputs']['cuda']['proofs']) for r in records
                            if (r['job']['fixture'] is None) == (kind == 'seeded'))
                  for kind in ('seeded', 'fixture')},
              'configuration': {'candidate_max': 16384, 'proof_max': 256, 'batch_max': 256,
                                'domain': 'canonical support<=2, unit coefficients'},
              'work': {k: dict(v) for k, v in overall.items()},
              'reasons': {k: dict(v) for k, v in reasons.items()},
              'search_elapsed_ns': dict(timings),
              'matrix_generation_ns': sum(r['generation_ns'] for r in records),
              'native_returned_proof_checks': len(packets),
              'candidate_domain_audits': list(domains.values()),
              'audited_candidate_ordinals': sum(d['candidates'] for d in domains.values()),
              'gpu': {'name': torch.cuda.get_device_name(0), 'torch': torch.__version__,
                      'cuda_runtime': torch.version.cuda, 'capability': list(torch.cuda.get_device_capability(0)),
                      'max_tensor_allocated_bytes': torch.cuda.max_memory_allocated(),
                      'max_tensor_reserved_bytes': torch.cuda.max_memory_reserved()},
              'limitations': ['restricted sparse domain; incomplete for general SIS',
                              'matrix generation measured separately; audits outside paid search',
                              'matrix grid slots and explicit tensor bytes are logical metrics, not actual CPU ops/bus traffic',
                              'reference Python baseline, not optimized native CPU competition',
                              'no isolated elapsed/energy/chainwork/hardness ranking; failures invalidate full study']}
    finish_report(paths[:2], report, paths[2], executable=executable,
                  expected_executable_sha256=binary_hash, build_profile='release',
                  raw={'records': records, 'candidate_domain_audits': list(domains.values())})


if __name__ == '__main__':
    main()
