"""Recipient/FIFO/ledger replay plus independent native validity, outside timing."""

from dataclasses import asdict
import hashlib
import json

from reference.admission_wire import scored_request
from reference.grinding import SCORE_DOMAIN
from reference.header import ExpectedContext, encode_proof
from reference.sis import verify
from scripts.lab_driver import exchange, matrix_bytes, request
from solvers.lattice import LatticeWork, Reduction, kernel_basis
from solvers.lattice_audit import audit_certificate
from solvers.sphere import enumerate_kernel


def same(left, right):
    if json.dumps(left, sort_keys=True) != json.dumps(right, sort_keys=True):
        raise ValueError('D4 replay mismatch')


def audit_campaign(headers, record, *, nodes=10000, reductions=8, cache_limit=8, search_cap=2000):
    policy = record['policy']
    if policy not in ('cold', 'kernel-cache') or not 1 <= len(record['stages']) <= len(headers):
        raise ValueError('D4 replay policy/stages')
    work = dict(headers=0, matrix_entries=0, fingerprint_calls=0, reductions=0,
                search_nodes=0, cache_hits=0, cache_evictions=0, verification_checks=0,
                score_hashes=0, score_bytes=0)
    cache, different = {}, 0
    for i, stage in enumerate(record['stages']):
        if work['search_nodes'] >= nodes:
            raise ValueError('D4 generation after node stop')
        h = headers[i]
        matrix = h.matrix()
        same((stage['index'], stage['header_hex'], stage['matrix']), (i, h.encode().hex(), matrix))
        work['headers'] += 1
        work['matrix_entries'] += h.profile.n*h.profile.m
        counter = LatticeWork()
        initial, rank = kernel_basis(h.profile, matrix, counter)
        key = (h.profile, rank, initial)
        hit = cache.get(key) if policy == 'kernel-cache' else None
        if policy == 'kernel-cache':
            same(stage['fingerprint_work'], asdict(counter))
            work['fingerprint_calls'] += 1
        else:
            same(stage['fingerprint_work'], None)
        if stage['certificate'] is None:
            if hit or work['reductions'] != reductions or i != len(record['stages'])-1:
                raise ValueError('D4 unexplained unfinished preparation')
            same((stage['reused_from'], stage['proofs'], stage['scores'], stage['search_reason'], stage['search_work'],
                  stage['preparation_work'], stage['preparation_timers']),
                 (None, [], [], 'not-started', {'nodes': 0}, None, None))
            break
        c = stage['certificate']
        if set(c) != {'initial_basis', 'basis', 'transform', 'rank', 'reason'}:
            raise ValueError('D4 certificate fields')
        red = Reduction(*(tuple(map(tuple, c[name])) for name in ('initial_basis', 'basis', 'transform')),
                        c['rank'], c['reason'], LatticeWork())
        audit_certificate(h.profile, matrix, red)
        same((red.initial_basis, red.rank), (initial, rank))
        if hit:
            donor, donor_certificate, donor_matrix = hit
            same((stage['reused_from'], c), (donor, donor_certificate))
            same((stage['preparation_work'], stage['preparation_timers']), (None, None))
            work['cache_hits'] += 1
            different += matrix != donor_matrix
        else:
            if work['reductions'] == reductions:
                raise ValueError('D4 reduction budget overshoot')
            same(stage['reused_from'], None)
            same(stage['preparation_work'], {'bkz_nodes': 0})
            if type(stage['preparation_timers']) is not dict:
                raise ValueError('D4 missing preparation timers')
            work['reductions'] += 1
            if policy == 'kernel-cache':
                if len(cache) == cache_limit:
                    del cache[next(iter(cache))]
                    work['cache_evictions'] += 1
                cache[key] = (h.encode().hex(), c, matrix)
        sample = enumerate_kernel(h.profile, matrix, red, node_limit=min(search_cap, nodes-work['search_nodes']), proof_limit=1)
        same((stage['proofs'], stage['search_work'], stage['search_reason']),
             (sample['proofs'], sample['work'], sample['reason']))
        work['search_nodes'] += sample['work']['nodes']
        scores = []
        for vector in stage['proofs']:
            if not verify(h.profile, matrix, vector):
                raise ValueError('D4 recipient proof')
            message = SCORE_DOMAIN+encode_proof(h, vector)
            scores.append(dict(proof_hex=encode_proof(h, vector).hex(), digest_hex=hashlib.sha256(message).hexdigest()))
            work['verification_checks'] += 1
            work['score_hashes'] += 1
            work['score_bytes'] += len(message)
        same(stage['scores'], scores)
    same(record['work'], work)
    reason = ('reduction-limit' if record['stages'][-1]['certificate'] is None else
              'headers-exhausted' if len(record['stages']) == len(headers) else
              'node-limit' if work['search_nodes'] >= nodes else 'checkpoint')
    if 'elapsed_ns' in record:
        if reason == 'checkpoint':
            raise ValueError('D4 unexplained completed prefix')
        same(record['reason'], reason)
    return dict(stages=len(record['stages']), proofs=work['verification_checks'],
                different_matrix_hits=different, counter_scope='named components; no portable cost weights')


def audit_native(executable, headers, record):
    messages, expected = [], []
    for h, stage in zip(headers, record['stages']):
        messages.append(request(2, h.encode()))
        expected.append(h.seed()+matrix_bytes(h.matrix()))
        context = ExpectedContext(h.network, h.parent, h.height, h.profile)
        for score in stage['scores']:
            packet = bytes.fromhex(score['proof_hex'])
            messages.extend((request(3, context.encode()+packet), scored_request(context, 2**254, packet)))
            expected.extend((b'\x01', bytes([int(int(score['digest_hex'], 16) < 2**254)])))
    if exchange(executable, messages) != expected:
        raise ValueError('D4 independent native validity/score mismatch')
    return dict(messages=len(messages), generated_headers=len(record['stages']),
                independent_scope='header derivation, proof validity and score threshold; not search completeness')
