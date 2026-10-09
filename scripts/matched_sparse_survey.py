"""Matched per-search CPU/GPU scope, prefix census and independent proof audits."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import statistics
import struct
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from reference.matched_sparse import BACKENDS, Library, SearchFailure, search
from reference.native_columns import search_many
from reference.sis import Profile, encode_case
from reference.sparse_domain import reference_search, weight_domains
from scripts.consensus_evidence import begin_report, finish_report
from scripts.matched_sparse_audits import audit_boundaries, audit_domains, audit_ledger, reconcile
from scripts.matched_sparse_cases import ORDER_SEED, SEEDS, jobs, matrix_for
from scripts.native_fused_survey import validate_build_snapshot


def fingerprint(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def summarize(records):
    result = {}
    for record in records:
        label = record['job']['group']+'/weight'+str(record['job']['max_weight'])
        group = result.setdefault(label, {})
        for backend, output in record['outputs'].items():
            if type(output['elapsed_ns']) is not int or output['elapsed_ns'] <= 0:
                raise RuntimeError('nonpositive/invalid individual timing; refusing ratios')
            data = group.setdefault(backend, dict(attempts=0, elapsed_ns=0, repeat_elapsed_ns=[0, 0, 0],
                                                  work=Counter(), stops=Counter(), weights={}))
            data['attempts'] += 1
            data['elapsed_ns'] += output['elapsed_ns']
            data['repeat_elapsed_ns'][record['repetition']] += output['elapsed_ns']
            data['work'].update(output['work'])
            data['stops'][output['reason']] += 1
            for weight, census in output['weights'].items():
                data['weights'].setdefault(weight, Counter()).update(census)
    for label, group in result.items():
        cpu, gpu = group['native-cpu'], group['fused-gpu']
        cpu_samples, gpu_samples = cpu['repeat_elapsed_ns'], gpu['repeat_elapsed_ns']
        if min(cpu_samples+gpu_samples) <= 0:
            raise RuntimeError('nonpositive timing; refusing ratios')
        group['descriptive_cpu_over_gpu_ratios'] = [a/b for a, b in zip(cpu_samples, gpu_samples)]
        group['aggregate_cpu_over_gpu_ratio'] = cpu['elapsed_ns']/gpu['elapsed_ns']
        group['per_case_ratio_median'] = statistics.median(
            r['outputs']['native-cpu']['elapsed_ns']/r['outputs']['fused-gpu']['elapsed_ns']
            for r in records if r['job']['group']+'/weight'+str(r['job']['max_weight']) == label)
    return result


def failure_report(paths, error, records, manifest, begin):
    diagnostic = getattr(error, 'diagnostic', dict(stage='setup-or-audit', detail=str(error)))
    compact = dict(status='failed', version='matched-sparse-v1', source_sha256=manifest,
                   elapsed_ns=time.perf_counter_ns()-begin, failure=diagnostic,
                   completed_paired_records=None if records is None else sum(len(r['outputs']) == 2 for r in records),
                   timing_ratios_published=False)
    paths[1].write_text(json.dumps(dict(**compact, incomplete_records=records), indent=2)+'\n')
    paths[0].write_text(json.dumps(compact, indent=2)+'\n')


def run(args, paths, records):
    native, verifier, library_path, metadata_path, snapshot_path = [p.resolve(strict=True) for p in
        (args.native, args.verifier, args.library, args.build_metadata, args.build_sources)]
    frozen = {p: fingerprint(p) for p in (native, verifier, library_path, metadata_path)}
    snapshot = json.loads(snapshot_path.read_text())
    validate_build_snapshot(snapshot, paths[2], frozen)
    frozen[snapshot_path] = fingerprint(snapshot_path)
    metadata = json.loads(metadata_path.read_text())
    if (metadata['status'] != 'passed' or metadata['library_sha256'] != frozen[library_path]
            or metadata['source_sha256'] != fingerprint(ROOT/'cuda/matched_sparse.cu')):
        raise RuntimeError('matched library build metadata disagreement')
    begin = time.perf_counter_ns()
    library = Library(library_path)
    setup = dict(library_load_ns=time.perf_counter_ns()-begin)
    p = Profile(7, 1, 3, 3)
    for backend in BACKENDS:
        begin = time.perf_counter_ns()
        probe = search(p, [[0]*3], library=library, backend=backend, max_weight=3, batch_size=7)
        if len(probe['proofs']) != 13:
            raise RuntimeError('matched first probe disagreement')
        setup[backend+'_first_probe_ns'] = time.perf_counter_ns()-begin
    library.check(library.lib.sp_sync())
    begin = time.perf_counter_ns()
    boundary = audit_boundaries(library)
    boundary_ns = time.perf_counter_ns()-begin
    begin = time.perf_counter_ns()
    domains = audit_domains(library)
    domain_ns = time.perf_counter_ns()-begin
    prepared, references, generation_ns, reference_ns = [], [], 0, 0
    pending = jobs()
    for job in pending:
        p = Profile(**job['profile'])
        begin = time.perf_counter_ns()
        matrix = matrix_for(job)
        generation_ns += time.perf_counter_ns()-begin
        settings = {k: job[k] for k in ('max_weight', 'candidate_limit', 'proof_limit', 'batch_size')}
        prepared.append((p, matrix, settings))
        begin = time.perf_counter_ns()
        references.append(reference_search(p, matrix, **settings))
        reference_ns += time.perf_counter_ns()-begin
    packets = []
    for repetition in range(3):
        for index, (job, (p, matrix, settings), expected) in enumerate(zip(pending, prepared, references)):
            record = dict(repetition=repetition, job=job, matrix=matrix, outputs={})
            records.append(record)
            order = list(BACKENDS)
            if (index+repetition) % 2: order.reverse()
            record['backend_order'] = order
            for backend in order:
                output = search(p, matrix, library=library, backend=backend, **settings)
                record['outputs'][backend] = output
                audit_ledger(p, settings, output)
                reconcile(expected, output)
                packets.extend(encode_case(p, matrix, v) for v in output['proofs'])
        print(f'Matched CPU/GPU repetition {repetition+1}/3 complete', flush=True)
    begin = time.perf_counter_ns()
    pair_requests, pair_expected = [], []
    for (p, matrix, settings), expected in zip(prepared, references):
        if weight_domains(p, settings['max_weight'])[3] == 0:
            native_settings = {k: settings[k] for k in ('candidate_limit', 'proof_limit', 'batch_size')}
            native_settings['candidate_limit'] = min(16384, native_settings['candidate_limit'])
            pair_requests.append((p, matrix, native_settings))
            pair_expected.append(expected)
    native_outputs, pair_wall = search_many(native, pair_requests)
    for expected, actual in zip(pair_expected, native_outputs):
        for key in ('domain', 'reason', 'domain_exhausted', 'all_proofs_returned', 'proofs'):
            if expected[key] != actual[key]: raise RuntimeError('matched Rust pair-domain disagreement')
        for key in ('screened', 'generated', 'batches', 'accepted_seen', 'returned', 'vector_entries'):
            if expected['work'][key] != actual['work'][key]: raise RuntimeError('matched Rust pair-work disagreement')
    for offset in range(0, len(packets), 256):
        group = packets[offset:offset+256]
        wire = b''.join(struct.pack('<I', len(p))+p for p in group)
        result = subprocess.run([str(verifier)], input=wire, capture_output=True, timeout=30, check=True)
        if result.stderr or result.stdout != b'\x01'*len(group): raise RuntimeError('matched native proof audit failure')
    native_audit_ns = time.perf_counter_ns()-begin
    report = dict(version='matched-sparse-v1', cases=len(prepared), repetitions=3, completed_attempts=6*len(prepared),
                  unique_seeded_challenges=len({j['seed_hex'] for j in pending if j['seed_hex']}), mismatches=0,
                  configuration=dict(order_seed=ORDER_SEED, seeds=list(SEEDS), candidate_max=65536,
                                     proof_max=256, chunk_max=4096, weights=[2, 3]), groups=summarize(records),
                  setup=setup, matrix_generation_ns=generation_ns, reference_audit_ns=reference_ns,
                  boundary_audits=boundary, boundary_audit_ns=boundary_ns, domain_audits=domains, domain_audit_ns=domain_ns,
                  audited_domain_ordinals_per_backend=sum(d['candidates_per_backend'] for d in domains),
                  native_pair_cases=len(pair_requests), native_pair_adapter_wall_ns=pair_wall,
                  independent_native_proof_checks=len(packets), native_audit_ns=native_audit_ns,
                  compiler_build=metadata, binaries_sha256={p.name: v for p, v in frozen.items()},
                  gpu=dict(cuda_runtime=library.runtime_version,
                          device_and_driver=subprocess.check_output(['nvidia-smi', '--query-gpu=name,driver_version',
                                                                    '--format=csv,noheader'], text=True).strip()),
                  timing_scope_description='same Python/FFI validation, owned session, copy, paid masks, output and close',
                  limitations=['scalar C++ CPU baseline, not best CPU/SIMD/parallel implementation',
                               'singletons/pairs/triples ±1 domain; not general SIS at larger B2',
                               'biased capped prefixes; separately censored search/output, no population yield inference',
                               'q2 signs may share acceptance events; repeats are not independent challenges',
                               'shared C++ sum/unrank helpers require independent Python/Rust audits',
                               'cold probes/audits/compiler excluded and recorded; every measured session is fresh',
                               'resident/concurrent workloads and clocks not isolated; no energy/chainwork/security calibration'])
    raw = dict(status='passed', version='matched-sparse-v1', source_sha256=paths[2],
               binaries_sha256=report['binaries_sha256'], configuration=report['configuration'],
               records=records, references=references, domain_audits=domains)
    report['raw_artifact_sha256'] = hashlib.sha256((json.dumps(raw, indent=2)+'\n').encode()).hexdigest()
    finish_report(paths[:2], report, paths[2], executable=native, expected_executable_sha256=frozen[native],
                  build_profile='release', expected_artifacts=frozen,
                  raw=raw)


def main():
    parser = argparse.ArgumentParser()
    for name in ('native', 'verifier', 'library', 'build-metadata', 'build-sources'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    begin = time.perf_counter_ns()
    paths = begin_report('matched-sparse-v1')
    records = []
    try:
        run(args, paths, records)
    except Exception as error:
        failure_report(paths, error, records, paths[2], begin)
        raise


if __name__ == '__main__':
    main()
