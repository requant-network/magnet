"""Frozen paired owned-session CPU/CUDA comparisons; full independent audits."""

import argparse
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from reference.matched_coefficients import BACKENDS, Library, SearchFailure, reference_search, reconcile, search
from reference.native_coefficients import search_many
from reference.sis import Profile, encode_case, expand_matrix
from scripts.consensus_evidence import begin_report, finish_report
from scripts.coefficient_journal import Journal
from scripts.matched_coefficient_audits import audit_boundaries, audit_domains, audit_ledger, audit_masks
from scripts.native_coefficient_checks import late_fixture
from scripts.native_coefficient_survey import comparison_cases
from scripts.native_fused_survey import validate_build_snapshot
from scripts.small_coefficient_audits import native_verdicts

VERSION = 'matched-coefficients-v1'
PROFILES = ((7, 1, 5, 8), (17, 2, 12, 12), (257, 2, 16, 12), (65521, 64, 16, 12))
SEEDS = (2026100923, 2026100924, 2026100925)


def fingerprint(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fixtures():
    cases, labels = comparison_cases()
    result, seen = [], set()
    for (p, matrix, _), label in zip(cases, labels):
        name = label.get('fixture')
        if name and name not in seen:
            result.append((name, p, matrix))
            seen.add(name)
    result.append(('late-witness', *late_fixture()))
    return result


def jobs():
    result = []
    for values in PROFILES:
        p = Profile(*values)
        for label in SEEDS:
            seed = hashlib.sha256('/'.join(map(str, (VERSION, *values, label))).encode('ascii')).digest()
            matrix = expand_matrix(p, seed)
            for bound in (1, 2):
                for width in (31, 256, 4096):
                    for cap in (4096, 20000):
                        result.append((p, matrix, dict(bound=bound, batch_size=width, candidate_limit=cap, proof_limit=32),
                                       dict(kind='seeded', label_seed=label, seed_hex=seed.hex(), profile=values)))
    for name, p, matrix in fixtures():
        for bound in (1, 2):
            for width in (7, 4096):
                for cap in (4096, 20000):
                    for proofs in (1, 256):
                        result.append((p, matrix, dict(bound=bound, batch_size=width, candidate_limit=cap, proof_limit=proofs),
                                       dict(kind='fixture', fixture=name, profile=(p.q, p.n, p.m, p.b2))))
    return result


def summarize(records):
    groups = {}
    for record in records:
        if set(record['outputs']) != set(BACKENDS):
            raise RuntimeError('cannot summarize partial CPU/GPU pair')
        cpu, gpu = (record['outputs'][k]['elapsed_ns'] for k in BACKENDS)
        if type(cpu) is not int or type(gpu) is not int or min(cpu, gpu) <= 0:
            raise RuntimeError('nonpositive individual paired sample')
        label = '/'.join(map(str, (record['label']['kind'], record['label'].get('fixture', record['label']['profile']),
                                  record['settings']['bound'], record['settings']['batch_size'])))
        group = groups.setdefault(label, dict(pairs=0, cpu_ns=[], gpu_ns=[], paired_cpu_over_gpu=[],
            screened=0, returned=0, discarded=0, empty_pairs=0, incomplete_domain_pairs=0,
            candidate_stops=0, proof_stops=0))
        for key, value in (('cpu_ns', cpu), ('gpu_ns', gpu), ('paired_cpu_over_gpu', cpu/gpu)):
            group[key].append(value)
        output = record['outputs']['native-cpu']
        for key, value in dict(pairs=1, screened=output['work']['screened'], returned=len(output['proofs']),
            discarded=output['accepted_tail_discarded'], empty_pairs=int(not output['proofs']),
            incomplete_domain_pairs=int(not output['domain_exhausted']),
            candidate_stops=int(output['reason'] == 'candidate-limit'), proof_stops=int(output['reason'] == 'proof-limit')).items():
            group[key] += value
    for group in groups.values():
        for field in ('cpu_ns', 'gpu_ns', 'paired_cpu_over_gpu'):
            values = group.pop(field)
            group[field] = dict(minimum=min(values), median=statistics.median(values), maximum=max(values))
    return groups


def failure_report(paths, error, records, manifest, current):
    report = dict(status='failed', version=VERSION, source_sha256=manifest, detail=str(error),
        completed_paired_records=None if records is None else sum(len(r['outputs']) == 2 for r in records),
        in_progress_work=current, native_diagnostic=getattr(error, 'diagnostic', None), timing_ratios_published=False)
    paths[1].write_text(json.dumps(dict(**report, incomplete_records=records), indent=2)+'\n', encoding='utf-8', newline='\n')
    paths[0].write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8', newline='\n')


def run(args, paths, records, state):
    journal = Journal(paths[1].with_suffix('.progress.jsonl'), paths[2])
    native, verifier, library_path, metadata_path, snapshot_path = [p.resolve(strict=True) for p in
        (args.native, args.verifier, args.library, args.build_metadata, args.build_sources)]
    frozen = {p: fingerprint(p) for p in (native, verifier, library_path, metadata_path)}
    validate_build_snapshot(json.loads(snapshot_path.read_text()), paths[2], frozen)
    frozen[snapshot_path] = fingerprint(snapshot_path)
    metadata = json.loads(metadata_path.read_text())
    if (metadata['status'] != 'passed' or metadata['library_sha256'] != frozen[library_path]
            or metadata['source_sha256'] != fingerprint(ROOT/'cuda/matched_coefficients.cu')):
        raise RuntimeError('coefficient library build metadata mismatch')
    begin = time.perf_counter_ns()
    library = Library(library_path)
    setup = dict(library_load_ns=time.perf_counter_ns()-begin)
    for backend in BACKENDS:
        begin = time.perf_counter_ns()
        p = Profile(17, 1, 2, 5)
        actual = search(p, [[1, 2]], library=library, backend=backend, bound=2, batch_size=7)
        reconcile(reference_search(p, [[1, 2]], bound=2, batch_size=7), actual)
        setup[backend+'_first_probe_ns'] = time.perf_counter_ns()-begin
    library.check(library.lib.cc_sync())
    begin = time.perf_counter_ns()
    boundary = audit_boundaries(library)
    domains = audit_domains(library)
    masks = audit_masks(library, verifier, fixtures())
    setup['complete_audit_ns'] = time.perf_counter_ns()-begin
    print('Complete native coefficient order/mask/boundary audits passed', flush=True)
    begin = time.perf_counter_ns()
    prepared = jobs()
    setup['matrix_preparation_ns'] = time.perf_counter_ns()-begin
    begin = time.perf_counter_ns()
    references = [reference_search(p, matrix, **settings) for p, matrix, settings, _ in prepared]
    setup['reference_audit_ns'] = time.perf_counter_ns()-begin
    native_checks, prefix_records = 0, []
    for repetition in range(3):
        for index, ((p, matrix, settings, label), expected) in enumerate(zip(prepared, references)):
            record = dict(case=index, repetition=repetition, label=label, settings=settings, outputs={})
            records.append(record)
            order = list(BACKENDS)
            if (index+repetition) % 2:
                order.reverse()
            record['backend_order'] = order
            journal.event(dict(kind='pair', record=record))
            for backend in order:
                state['current'] = dict(stage='search', case=index, repetition=repetition, backend=backend, unknown_work=True)
                journal.event(dict(kind='pending', current=state['current']))
                actual = search(p, matrix, library=library, backend=backend, **settings)
                record['outputs'][backend] = actual
                journal.event(dict(kind='output', case=index, repetition=repetition, backend=backend, output=actual))
                reconcile(expected, actual)
                if actual['elapsed_ns'] <= 0:
                    raise RuntimeError('nonpositive coefficient sample')
                if repetition == 0:
                    state['current'] = dict(stage='independent-ledger-proof-audit', case=index, backend=backend, unknown_work=True)
                    audit_ledger(p, matrix, settings, actual)
                    vectors = actual['proofs']
                    native_verdicts(verifier, [encode_case(p, matrix, v) for v in vectors], [1]*len(vectors))
                    native_checks += len(vectors)
            state['current'] = None
            journal.event(dict(kind='paired'))
        print(f'Matched coefficient CPU/GPU repetition {repetition+1}/3 passed', flush=True)
    state['current'] = dict(stage='independent-rust-prefix', unknown_work=True)
    journal.event(dict(kind='pending', current=state['current']))
    sequential, _ = search_many(native, [(p, matrix, {k: settings[k] for k in ('bound', 'candidate_limit', 'proof_limit')})
                                         for p, matrix, settings, _ in prepared])
    for index, (sequential_output, expected) in enumerate(zip(sequential, references)):
        result = sequential_output['result']
        if result['proofs'] != expected['proofs'] or result['work']['screened'] > expected['work']['screened']:
            raise RuntimeError('independent sequential Rust prefix mismatch')
        prefix_records.append(dict(case=index, sequential_checked=result['work']['screened'],
            chunk_checked=expected['work']['screened'], extra_paid_candidates=expected['work']['screened']-result['work']['screened']))
    state['current'] = dict(stage='evidence-publication', unknown_work=True)
    journal.event(dict(kind='pending', current=state['current']))
    report = dict(version=VERSION, paired_cases=len(prepared), repetitions=3, completed_attempts=2*len(records),
        unique_seeded_matrices=len({label['seed_hex'] for _, _, _, label in prepared if label['kind'] == 'seeded'}),
        configuration=dict(profiles=PROFILES, seeds=SEEDS, widths=[31, 256, 4096], caps=[4096, 20000],
                           seeded_proof_cap=32, fixture_widths=[7, 4096], fixture_proof_caps=[1, 256], bounds=[1, 2]),
        groups=summarize(records), setup=setup, boundary_audit=boundary, domain_audit=domains, mask_audit=masks,
        independent_native_returned_verdicts=native_checks, independent_rust_prefix_cases=len(prefix_records),
        extra_paid_chunk_candidates=sum(r['extra_paid_candidates'] for r in prefix_records),
        compiler_build=metadata, binaries_sha256={p.name: v for p, v in frozen.items()}, mismatches=0,
        gpu=dict(cuda_runtime=library.runtime_version, device_and_driver=subprocess.check_output(
            ['nvidia-smi', '--query-gpu=name,driver_version', '--format=csv,noheader'], text=True, timeout=10).strip()),
        timing_scope_description='same validation/domain/ctypes, fresh owned session/copies, chunk masks, host output/census and close; audits outside',
        limitations=['scalar C++ CPU baseline, not best SIMD/multicore CPU', 'shared C++ decoding/screen helpers audited independently',
            'local tiny support<=3 family; noisy unisolated clocks/workloads; no portable hardware or energy claim',
            'capped biased prefixes, scalar-copy dependencies and repeated seeds; no population yield or consensus pricing',
            'complete masks are paid, including accepted/discarded output tails; sequential Rust has a different work prefix'])
    raw = dict(status='passed', version=VERSION, source_sha256=paths[2], binaries_sha256=report['binaries_sha256'],
        configuration=report['configuration'], records=records, references=references,
        cases=[dict(label=label, settings=settings, matrix=matrix) for _, matrix, settings, label in prepared],
        sequential_prefix_audits=prefix_records)
    report['raw_artifact_sha256'] = hashlib.sha256((json.dumps(raw, indent=2)+'\n').encode('utf-8')).hexdigest()
    finish_report(paths[:2], report, paths[2], raw=raw, executable=native,
                  expected_executable_sha256=frozen[native], build_profile='release', expected_artifacts=frozen)
    state['current'] = None


def main():
    parser = argparse.ArgumentParser()
    for name in ('native', 'verifier', 'library', 'build-metadata', 'build-sources'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    paths = begin_report(VERSION)
    records, state = [], dict(current=dict(stage='setup-or-audit', unknown_work=True))
    try:
        run(args, paths, records, state)
    except Exception as error:
        failure_report(paths, error, records, paths[2], state['current'])
        raise


if __name__ == '__main__':
    main()
