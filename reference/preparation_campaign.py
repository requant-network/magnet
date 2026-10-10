"""Small D4 full-kernel transfer integration; no calibrated work or speed claim."""

from dataclasses import asdict, replace
import hashlib
import time

from reference.header import LabHeader, encode_proof
from reference.grinding import SCORE_DOMAIN
from reference.sis import verify
from solvers.lattice import LatticeWork, kernel_basis
from solvers.lattice_audit import audit_certificate

POLICIES = ('cold', 'kernel-cache')


def run_preparation(headers, policy, solver, *, nodes=10000, reductions=8,
                    cache_limit=8, search_cap=2000, on_stage=None):
    if (type(headers) not in (list, tuple) or not 1 <= len(headers) <= 8
            or any(not isinstance(h, LabHeader) or h.profile.m > 8 or h.profile.n > 2 for h in headers)
            or policy not in POLICIES or solver.backend != 'lll75'
            or on_stage is not None and not callable(on_stage)):
        raise ValueError('D4 headers/policy/backend/callback')
    base = headers[0]
    if any((h.network, h.profile) != (base.network, base.profile) for h in headers):
        raise ValueError('D4 network/profile mismatch')
    if len({h.encode() for h in headers}) != len(headers):
        raise ValueError('D4 receiving headers must be distinct')
    for value, maximum in ((nodes, 100000), (reductions, 8), (cache_limit, 8), (search_cap, 2000)):
        if type(value) is not int or not 1 <= value <= maximum:
            raise ValueError('D4 budget bounds')
    start = time.perf_counter_ns()
    work = dict(headers=0, matrix_entries=0, fingerprint_calls=0, reductions=0,
                search_nodes=0, cache_hits=0, cache_evictions=0, verification_checks=0,
                score_hashes=0, score_bytes=0)
    result = dict(policy=policy, stages=[], work=work, reason='headers-exhausted')
    cache = {}
    for index, header in enumerate(headers):
        if work['search_nodes'] >= nodes:
            result['reason'] = 'node-limit'
            break
        stage_start = time.perf_counter_ns()
        matrix = header.matrix()
        work['headers'] += 1
        work['matrix_entries'] += header.profile.n*header.profile.m
        stage = dict(index=index, header_hex=header.encode().hex(), matrix=matrix,
                     reused_from=None, certificate=None, fingerprint_work=None,
                     preparation_work=None, preparation_timers=None,
                     proofs=(), scores=[], search_reason='not-started', search_work={'nodes': 0}, elapsed_ns=0)
        result['stages'].append(stage)
        prepared, donor, key, fingerprint_work = None, None, None, None
        if policy == 'kernel-cache':
            counter = LatticeWork()
            initial, rank = kernel_basis(header.profile, matrix, counter)
            fingerprint_work = asdict(counter)
            stage['fingerprint_work'] = fingerprint_work
            work['fingerprint_calls'] += 1
            key = (header.profile, rank, initial)
            if key in cache:
                prepared, donor = cache[key]
                prepared = replace(prepared, matrix=tuple(map(tuple, matrix)))
                # Membership alone is insufficient: audit recipient index/rank too.
                audit_certificate(header.profile, matrix, prepared.reduction)
                work['cache_hits'] += 1
                stage['reused_from'] = donor
        if prepared is None:
            if work['reductions'] == reductions:
                result['reason'] = 'reduction-limit'
                stage['elapsed_ns'] = time.perf_counter_ns()-stage_start
                break
            work['reductions'] += 1
            prepared = solver.prepare(header.profile, matrix, min(search_cap, nodes-work['search_nodes']))
            stage['preparation_work'] = prepared.work
            stage['preparation_timers'] = prepared.timers
            if policy == 'kernel-cache':
                if prepared.reduction.initial_basis != initial or prepared.reduction.rank != rank:
                    raise RuntimeError('D4 fingerprint/preparation mismatch')
                if len(cache) == cache_limit:
                    del cache[next(iter(cache))]
                    work['cache_evictions'] += 1
                cache[key] = (prepared, header.encode().hex())
        sample = solver.search_prepared(prepared, min(search_cap, nodes-work['search_nodes']), 1, seed=index)
        work['search_nodes'] += sample['work']['nodes']
        proofs = tuple(map(tuple, sample['proofs']))
        if len(proofs) > 1 or not all(verify(header.profile, matrix, v) for v in proofs):
            raise RuntimeError('D4 search emitted invalid proof')
        work['verification_checks'] += len(proofs)
        scores = []
        for vector in proofs:
            packet = encode_proof(header, vector)
            message = SCORE_DOMAIN+packet
            work['score_hashes'] += 1
            work['score_bytes'] += len(message)
            scores.append(dict(proof_hex=packet.hex(), digest_hex=hashlib.sha256(message).hexdigest()))
        certificate = asdict(prepared.reduction)
        certificate.pop('work')
        stage.update(certificate=certificate, proofs=proofs, scores=scores,
                     search_reason=sample['reason'], search_work=sample['work'],
                     elapsed_ns=time.perf_counter_ns()-stage_start)
        if on_stage is not None:
            on_stage(result)
    result['elapsed_ns'] = time.perf_counter_ns()-start
    return result
