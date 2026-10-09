"""Exact native/fused comparison with separate engine and adapter timing scopes."""

import argparse
import ctypes as C
from collections import Counter
import hashlib
import itertools
from pathlib import Path
import struct
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from reference.column_search import search as columns, supports, vector_for
from reference.fused_search import Library, Session, search as fused
from reference.native_columns import search_many
from reference.sis import Profile, encode_case, verify
from scripts.column_search_survey import jobs, reconcile
from scripts.consensus_evidence import begin_report, finish_report
from scripts.gpu_search_survey import matrix_for

BACKENDS = ('python-columns', 'rust-columns', 'cuda-columns', 'cuda-fused')


def fingerprint(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_build_snapshot(snapshot, manifest, binaries):
    if snapshot.get('source_sha256') != manifest:
        raise RuntimeError('sources differ from pre-build snapshot')
    if snapshot.get('binaries_sha256') != {path.name: value for path, value in binaries.items()}:
        raise RuntimeError('binaries differ from build snapshot')


def audit_ledger(profile, result):
    w, backend = result['work'], result['backend']
    checked, returned = w['screened'], len(result['proofs'])
    gpu = backend.startswith('cuda')
    expected = dict(generated=checked, matrix_entries=profile.n*profile.m,
                    matrix_grid_slots=checked*profile.n*profile.m, vector_entries=returned*profile.m,
                    returned=returned, support_entries=3*checked, scheduled_column_reads=2*checked*profile.n,
                    host_prefix_entries=profile.m if gpu else 0,
                    device_prefix_entries=profile.m if backend == 'cuda-columns' else 0,
                    column_table_entries=0 if gpu else profile.n*profile.m,
                    explicit_h2d_bytes=8*profile.n*profile.m if gpu else 0,
                    explicit_d2h_bytes=checked if gpu else 0)
    if any(w[k] != value for k, value in expected.items()):
        raise RuntimeError('native/fused ledger mismatch')
    if backend == 'rust-columns' and not checked <= w['actual_row_checks'] <= checked*profile.n:
        raise RuntimeError('native row-check count')
    if backend == 'cuda-fused' and (w['kernel_launches'] != w['batches'] or
            result['logical_owned_device_bytes'] != 8*profile.n*profile.m+result['chunk_width']):
        raise RuntimeError('fused ownership/launch ledger')


def audit_domain(library, profile, matrix, width):
    expected, digest = supports(profile), hashlib.sha256()
    domain = profile.m if profile.b2 == 1 else profile.m**2
    with Session(library, profile, matrix, width) as session:
        for offset in range(0, domain, width):
            count = min(width, domain-offset)
            triples = session.audit(offset, count)
            if triples != list(itertools.islice(expected, count)):
                raise RuntimeError('fused support order mismatch')
            for s in triples:
                digest.update(struct.pack('<'+'i'*profile.m, *vector_for(profile.m, s)))
    return dict(m=profile.m, b2=profile.b2, batch_size=width, candidates=domain,
                ordered_vectors_sha256=digest.hexdigest())


def audit_boundaries(library):
    """Real C ABI rejection and full masks, outside measurement timers."""
    data, handle = (C.c_int64*1)(0), C.c_void_p()
    cases = [(0, 1, 7, 0, 1, 1), (65, 1, 7, 0, 1, 1), (1, 129, 7, 0, 1, 1),
             (1, 1, 4, 0, 1, 1), (1, 1, 7, 2, 1, 1), (1, 1, 7, 0, 4097, 1),
             (1, 1, 7, 0, 1, 2)]
    for n, m, q, norm_one, width, entries in cases:
        handle.value = 123
        code = library.lib.mg_open(data, entries, n, m, q, norm_one, width, C.byref(handle))
        if code != -1 or handle.value:
            raise RuntimeError('C ABI invalid open parameters accepted')
    for residue in (-1, 7):
        data[0] = residue
        if library.lib.mg_open(data, 1, 1, 1, 7, 0, 1, C.byref(handle)) != -1 or handle.value:
            raise RuntimeError('C ABI invalid matrix accepted')
    p = Profile(7, 1, 1, 1)
    rejects = len(cases)+2
    with Session(library, p, [[0]], 1) as session:
        out = (C.c_uint8*2)()
        for offset, count, length in ((-1, 1, 1), (1, 1, 1), (0, 2, 2), (0, 1, 2), (0, 0, 0)):
            if library.lib.mg_batch(session.handle, offset, count, out, length) != -1:
                raise RuntimeError('C ABI invalid batch accepted')
            rejects += 1
    masks, ordinals = 0, 0
    probes = []
    for q in (2, 3):
        for b2 in (1, 2):
            for row in itertools.product(range(q), repeat=3):
                probes.append((Profile(q, 1, 3, b2), [row], 2))
    # Maximum modulus/dimensions, mixed identical/opposite columns; includes
    # negative residuals, max residues and accepted late pair ordinals.
    p = Profile(65521, 64, 128, 65521**2-1)
    matrix = [[(i % 8)*9360 % p.q for i in range(p.m)] for _ in range(p.n)]
    probes.append((p, matrix, 4096))
    for p, matrix, width in probes:
        expected = supports(p)
        with Session(library, p, matrix, width) as session:
            for offset in range(0, session.domain, width):
                count = min(width, session.domain-offset)
                triples = list(itertools.islice(expected, count))
                wanted = bytes(int(all((row[a]+sign*row[b]) % p.q == 0 for row in matrix))
                               for a, b, sign in triples)
                if session.mask(offset, count) != wanted:
                    raise RuntimeError('fused full boundary mask differs from exact host columns')
                masks += 1
                ordinals += count
    return dict(ffi_rejections=rejects, full_mask_cases=len(probes), masks=masks, ordinals=ordinals)


def summarize(records):
    groups = {}
    for record in records:
        for backend, result in record['outputs'].items():
            group = groups.setdefault(record['job']['group'], {})
            data = group.setdefault(backend, dict(attempts=0, elapsed_ns=0, work=Counter(), stops=Counter()))
            data['attempts'] += 1
            data['elapsed_ns'] += result['elapsed_ns']
            data['work'].update(result['work'])
            data['stops'][result['reason']] += 1
            if backend == 'cuda-fused':
                data['max_logical_owned_device_bytes'] = max(data.get('max_logical_owned_device_bytes', 0),
                                                           result['logical_owned_device_bytes'])
    return groups


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--native', type=Path, required=True, help='release sis-column')
    parser.add_argument('--verifier', type=Path, required=True, help='release sis-verify')
    parser.add_argument('--library', type=Path, required=True, help='locally compiled ABI v1 library')
    parser.add_argument('--build-metadata', type=Path, required=True)
    parser.add_argument('--build-sources', type=Path, required=True, help='pre-build source/binary snapshot')
    args = parser.parse_args()
    paths = begin_report('native-fused-column-v1')
    native, verifier, so, metadata_path = [p.resolve(strict=True) for p in
                                          (args.native, args.verifier, args.library, args.build_metadata)]
    frozen = {p: fingerprint(p) for p in (native, verifier, so, metadata_path)}
    import json
    snapshot_path = args.build_sources.resolve(strict=True)
    snapshot = json.loads(snapshot_path.read_text())
    validate_build_snapshot(snapshot, paths[2], frozen)
    frozen[snapshot_path] = fingerprint(snapshot_path)
    metadata = json.loads(metadata_path.read_text())
    if (metadata['source_sha256'] != fingerprint(ROOT/'cuda/unit_sparse.cu') or
            metadata['library_sha256'] != frozen[so]):
        raise RuntimeError('fused compiler metadata mismatch')
    cold_begin = time.perf_counter_ns()
    library = Library(so)
    p = Profile(7, 1, 1, 1)
    # Paid separately; session allocation/H2D/D2H/cleanup initialize the runtime.
    cold_probe = fused(p, [[0]], library=library, candidate_limit=1, proof_limit=1, batch_size=1)
    library_setup_ns = time.perf_counter_ns()-cold_begin
    if cold_probe['proofs'] != [(1,)]:
        raise RuntimeError('fused initial runtime probe')
    torch_begin = time.perf_counter_ns()
    import torch
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA required for native/fused survey')
    torch_probe = columns(p, [[0]], backend='cuda-columns', candidate_limit=1, proof_limit=1, batch_size=1)
    torch_setup_ns = time.perf_counter_ns()-torch_begin
    if torch_probe['proofs'] != [(1,)]:
        raise RuntimeError('torch initial runtime probe')
    audit_begin = time.perf_counter_ns()
    boundary_audits = audit_boundaries(library)
    audit_ns = dict(boundary=time.perf_counter_ns()-audit_begin, domain=0, host_returned_proofs=0)
    pending = jobs()
    prepared, generation_ns = [], 0
    for job in pending:
        begin = time.perf_counter_ns()
        matrix = matrix_for(job)
        generation_ns += time.perf_counter_ns()-begin
        prepared.append((Profile(**job['profile']), matrix,
                         {k: job[k] for k in ('candidate_limit', 'proof_limit', 'batch_size')}))
    records, packets, domains, bulk = [], [], {}, []
    for repeat in range(3):
        # Native bulk has one process per repetition; record its full wall scope.
        # Position relative to GPU work changes each repetition, not interleaved per-case.
        native_outputs = None
        if repeat != 1:
            native_outputs, wall = search_many(native, prepared)
            bulk.append(dict(repetition=repeat, requests=len(prepared), adapter_wall_ns=wall))
        for index, (job, (p, matrix, settings)) in enumerate(zip(pending, prepared)):
            shift = (index+repeat) % 3
            order = ('python-columns', 'cuda-columns', 'cuda-fused')
            order = order[shift:]+order[:shift]
            outputs = {}
            for backend in order:
                result = (fused(p, matrix, library=library, **settings) if backend == 'cuda-fused' else
                          columns(p, matrix, backend=backend, **settings))
                result['chunk_width'] = settings['batch_size']
                audit_ledger(p, result)
                outputs[backend] = result
            records.append(dict(repetition=repeat, job=job, matrix=matrix, outputs=outputs))
        if native_outputs is None:
            native_outputs, wall = search_many(native, prepared)
            bulk.append(dict(repetition=repeat, requests=len(prepared), adapter_wall_ns=wall))
        for index, result in enumerate(native_outputs):
            record = records[repeat*len(prepared)+index]
            p, matrix, settings = prepared[index]
            result['chunk_width'] = settings['batch_size']
            audit_ledger(p, result)
            record['outputs']['rust-columns'] = result
            for output in record['outputs'].values():
                reconcile(result, output)
                audit_begin = time.perf_counter_ns()
                for vector in output['proofs']:
                    if not verify(p, matrix, vector):
                        raise RuntimeError('native/fused host proof failure')
                    packets.append(encode_case(p, matrix, vector))
                audit_ns['host_returned_proofs'] += time.perf_counter_ns()-audit_begin
            key = (p.m, p.b2, settings['batch_size'])
            if key not in domains:
                audit_begin = time.perf_counter_ns()
                domains[key] = audit_domain(library, p, matrix, settings['batch_size'])
                audit_ns['domain'] += time.perf_counter_ns()-audit_begin
        print(f'Native/fused repetition {repeat+1}/3 complete', flush=True)
    audit_begin = time.perf_counter_ns()
    for offset in range(0, len(packets), 256):
        group = packets[offset:offset+256]
        wire = b''.join(struct.pack('<I', len(packet))+packet for packet in group)
        result = subprocess.run([str(verifier)], input=wire, capture_output=True, timeout=30, check=True)
        if result.stderr or result.stdout != b'\x01'*len(group):
            raise RuntimeError('independent native proof verifier failure')
    audit_ns['native_returned_proofs'] = time.perf_counter_ns()-audit_begin
    report = dict(version='native-fused-column-v1', cases=len(prepared), repetitions=3,
                  completed_attempts=len(records)*4, groups=summarize(records), mismatches=0,
                  configuration=dict(order_seed=2026100910, candidate_max=16384, proof_max=256,
                                     chunk_max=4096, matrix_regenerated_once=True),
                  unique_seeded_challenges=len({j['seed_hex'] for j in pending if j['seed_hex']}),
                  matrix_generation_ns=generation_ns, native_bulk=bulk,
                  cold_setup=dict(fused_library_and_first_probe_ns=library_setup_ns,
                                  torch_import_and_first_probe_ns=torch_setup_ns),
                  native_returned_proof_checks=len(packets), domain_audits=list(domains.values()),
                  boundary_audits=boundary_audits,
                  audit_elapsed_ns=audit_ns,
                  audited_candidate_ordinals=sum(d['candidates'] for d in domains.values()),
                  gpu=dict(name=torch.cuda.get_device_name(0), torch=torch.__version__,
                           torch_cuda_runtime=torch.version.cuda, fused_cuda_runtime=library.runtime_version,
                           capability=list(torch.cuda.get_device_capability(0))),
                  binaries_sha256={p.name: value for p, value in frozen.items()}, fused_build=metadata,
                  measurement_scopes=dict(rust='parse/validate/transpose/search engine only',
                                          native_bulk='one process/repetition plus encode/pipe/decode/host proof checks',
                                          python='validate/transpose/search/output',
                                          torch='validate/matrix and prefix setup/transfer/search/readback/output/cleanup',
                                          fused='validate/session setup/matrix transfer/search/readback/output/cleanup'),
                  limitations=['restricted unit-sparse domain, not general SIS or block mining',
                               'no session reuse: every GPU search pays matrix transfer/allocation/cleanup',
                               'native engine excludes transport; no unqualified cross-scope speedup',
                               'native order is bulk before/between GPU repetitions; not per-case interleaving',
                               'compiler/setup/domain/verifier costs outside search timers and recorded separately',
                               'concurrent resident workloads possible; no isolated speed/energy/chainwork claim',
                               'logical device ownership excludes runtime overhead; reads are scheduled upper bounds'])
    finish_report(paths[:2], report, paths[2], executable=native,
                  expected_executable_sha256=frozen[native], build_profile='release', expected_artifacts=frozen,
                  raw=dict(records=records, native_bulk=bulk, domain_audits=list(domains.values())))


if __name__ == '__main__':
    main()
