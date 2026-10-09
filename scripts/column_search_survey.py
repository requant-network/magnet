"""Dense/column equivalence and bounded large-chunk research measurements."""

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
from reference.column_search import device_supports, search as column_search, supports, vector_for
from reference.gpu_search import candidates, search as dense_search
from reference.sis import Profile, encode_case, verify
from scripts.consensus_evidence import begin_report, finish_report
from scripts.gpu_search_survey import matrix_for, schedule

ORDER_SEED = 2026100910
COMMON = ('generated', 'screened', 'matrix_grid_slots', 'matrix_entries', 'batches', 'accepted_seen', 'returned')
BACKENDS = ('python', 'cuda', 'python-columns', 'cuda-columns')


def jobs():
    result = [dict(j, group='legacy') for j in schedule()]
    for j in schedule():
        if j['fixture'] is None and j['profile']['m'] >= 32 and j['batch_size'] == 256:
            for batch in (1024, 4096):
                result.append(dict(j, group='large-chunk', batch_size=batch))
    random.Random(ORDER_SEED).shuffle(result)
    return result


def reconcile(a, b):
    for key in ('domain', 'reason', 'domain_exhausted', 'all_proofs_returned', 'proofs'):
        if a[key] != b[key]:
            raise RuntimeError('optimized column '+key+' disagreement')
    if any(a['work'][k] != b['work'][k] for k in COMMON):
        raise RuntimeError('optimized column common ledger disagreement')


def audit_ledger(profile, result):
    w, backend = result['work'], result['backend']
    count, returned, batches = w['screened'], len(result['proofs']), w['batches']
    expected = {'generated': count, 'matrix_grid_slots': count*profile.n*profile.m,
                'matrix_entries': profile.n*profile.m, 'returned': returned}
    if backend in ('python', 'cuda'):
        expected.update(vector_entries=count*profile.m, support_prefix_entries=profile.m if backend == 'cuda' else 0,
                        explicit_h2d_bytes=profile.n*profile.m*8 if backend == 'cuda' else 0,
                        explicit_d2h_bytes=16*batches+8*profile.m*returned if backend == 'cuda' else 0)
    elif backend in ('python-columns', 'cuda-columns'):
        cuda = backend == 'cuda-columns'
        expected.update(vector_entries=returned*profile.m, support_entries=3*count,
                        scheduled_column_reads=2*count*profile.n,
                        host_prefix_entries=profile.m if cuda else 0, device_prefix_entries=profile.m if cuda else 0,
                        column_table_entries=0 if cuda else profile.n*profile.m,
                        explicit_h2d_bytes=profile.n*profile.m*8 if cuda else 0,
                        explicit_d2h_bytes=count if cuda else 0)
    else:
        raise RuntimeError('unrecognized ledger backend')
    if any(w[k] != value for k, value in expected.items()):
        raise RuntimeError('optimized column materialization/transfer ledger disagreement')


def audit_domain(torch, profile, batch_size):
    domain = profile.m if profile.b2 == 1 else profile.m**2
    positions = torch.arange(profile.m, dtype=torch.int64, device='cuda')
    starts = positions*(2*profile.m-positions-1)//2
    host, vectors, digest = supports(profile), candidates(profile), hashlib.sha256()
    for offset in range(0, domain, batch_size):
        count = min(batch_size, domain-offset)
        first, second, sign = device_supports(torch, offset, count, profile.m, starts)
        actual = [tuple(s) for s in torch.stack((first, second, sign), dim=1).cpu().tolist()]
        if actual != list(itertools.islice(host, count)):
            raise RuntimeError('optimized CUDA support ordering disagreement')
        decoded = [vector_for(profile.m, s) for s in actual]
        if decoded != list(itertools.islice(vectors, count)):
            raise RuntimeError('optimized CUDA vector ordering disagreement')
        for vector in decoded:
            digest.update(struct.pack('<'+'i'*profile.m, *vector))
        del first, second, sign
    return {'m': profile.m, 'b2': profile.b2, 'batch_size': batch_size,
            'candidates': domain, 'ordered_vectors_sha256': digest.hexdigest()}


def summarize(records):
    groups = {}
    for record in records:
        group = record['job']['group']
        destination = groups.setdefault(group, {})
        for backend, result in record['outputs'].items():
            data = destination.setdefault(backend, {'attempts': 0, 'work': Counter(), 'stops': Counter(),
                                                   'elapsed_ns': 0, 'peak_allocated_bytes': 0})
            data['attempts'] += 1
            data['work'].update(result['work'])
            data['stops'][result['reason']] += 1
            data['elapsed_ns'] += result['elapsed_ns']
            data['peak_allocated_bytes'] = max(data['peak_allocated_bytes'], result.get('gpu_peak_allocated_bytes', 0))
    return groups


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--native', type=Path, required=True)
    args = parser.parse_args()
    paths = begin_report('gpu-column-search-v1')
    executable = args.native.resolve(strict=True)
    binary_hash = hashlib.sha256(executable.read_bytes()).hexdigest()
    import torch
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA required for column search survey')
    records, domains, packets = [], {}, []
    pending = jobs()
    for index, job in enumerate(pending):
        p = Profile(**job['profile'])
        start = time.perf_counter_ns()
        matrix = matrix_for(job)
        generation_ns = time.perf_counter_ns()-start
        settings = {k: job[k] for k in ('candidate_limit', 'proof_limit', 'batch_size')}
        backends = BACKENDS if job['group'] == 'legacy' else BACKENDS[2:]
        order = backends[index % len(backends):]+backends[:index % len(backends)]
        outputs = {}
        for backend in order:
            if backend.startswith('cuda'):
                torch.cuda.reset_peak_memory_stats()
            function = dense_search if backend in ('python', 'cuda') else column_search
            result = function(p, matrix, backend=backend, **settings)
            if backend.startswith('cuda'):
                result['gpu_peak_allocated_bytes'] = torch.cuda.max_memory_allocated()
            audit_ledger(p, result)
            outputs[backend] = result
            for vector in result['proofs']:
                if not verify(p, matrix, vector):
                    raise RuntimeError('optimized output fails host verifier')
                packets.append(encode_case(p, matrix, vector))
        reference = next(iter(outputs.values()))
        for result in outputs.values():
            reconcile(reference, result)
        key = (p.m, p.b2, job['batch_size'])
        if key not in domains:
            domains[key] = audit_domain(torch, p, job['batch_size'])
        records.append({'job': job, 'matrix': matrix, 'generation_ns': generation_ns, 'outputs': outputs})
        print(f'Column search audit {index+1}/{len(pending)}', flush=True)
    for offset in range(0, len(packets), 256):
        group = packets[offset:offset+256]
        wire = b''.join(struct.pack('<I', len(p))+p for p in group)
        native = subprocess.run([str(executable)], input=wire, capture_output=True, timeout=30, check=True)
        if native.stderr or native.stdout != b'\x01'*len(group):
            raise RuntimeError('native optimized proof audit disagreement')
    report = {'version': 'gpu-column-search-v1', 'order_seed': ORDER_SEED,
              'configuration': {'candidate_max': 16384, 'proof_max': 256, 'column_batch_max': 4096,
                                'legacy_seed_labels': [2026100907, 2026100908], 'large_widths': [1024, 4096]},
              'cases': len(records), 'completed_attempts': sum(len(r['outputs']) for r in records),
              'groups': summarize(records), 'mismatches': 0,
              'unique_seeded_challenges': len({r['job']['seed_hex'] for r in records if r['job']['seed_hex']}),
              'matrix_generation_ns': sum(r['generation_ns'] for r in records),
              'native_returned_proof_checks': len(packets), 'domain_audits': list(domains.values()),
              'audited_candidate_ordinals': sum(d['candidates'] for d in domains.values()),
              'gpu': {'name': torch.cuda.get_device_name(0), 'torch': torch.__version__,
                      'cuda_runtime': torch.version.cuda, 'capability': list(torch.cuda.get_device_capability(0))},
              'limitations': ['same restricted unit-sparse domain, not block mining or general SIS completeness',
                              'different materialization/transfer counters checked by backend',
                              'matrix generation and native/domain audits outside search timers',
                              'reference Python/column baselines, not optimized native CPU competition',
                              'mixed cold/setup and concurrent GPU work possible; no isolated speed/energy/chainwork claim']}
    finish_report(paths[:2], report, paths[2], executable=executable,
                  expected_executable_sha256=binary_hash, build_profile='release',
                  raw={'records': records, 'domain_audits': list(domains.values())})


if __name__ == '__main__':
    main()
