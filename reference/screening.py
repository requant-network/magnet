"""D3 paid nonce selection using existing spec21 predicates; no new solver."""

from dataclasses import replace
import hashlib
import itertools
import math
import time

from reference.component_meter import ComponentMeter, ComponentStop
from reference.cooperative_campaign import paid_verify
from reference.grinding import SCORE_DOMAIN
from reference.header import DOMAIN, LabHeader, encode_proof
from reference.sis import expand_matrix
from reference.small_coefficients import candidates, dense, screen, templates

POLICIES = ('plain', 'probe-control', 'random4', 'screened4')
CONSTRUCTIONS = ('A', 'B')
RANDOM_DOMAIN = b'D3/random-selection\0'


class DeadlineStop(RuntimeError):
    pass


def campaign(base, policy, construction, *, budget=100000, header_limit=256,
             candidate_limit=4096, probe_limit=64, target=2**254, deadline=None, trace=None):
    if (not isinstance(base, LabHeader) or base.profile.m > 16 or base.profile.n > 4
            or base.profile.b2 > 12 or type(policy) is not str or policy not in POLICIES
            or type(construction) is not str or construction not in CONSTRUCTIONS):
        raise ValueError('D3 profile/policy/construction outside range')
    for value, maximum in ((budget, 1000000), (header_limit, 256), (candidate_limit, 4096), (probe_limit, 64)):
        if type(value) is not int or not 1 <= value <= maximum:
            raise ValueError('D3 cap outside range')
    if type(target) is not int or not 1 <= target <= 2**256 or base.nonce+header_limit > 2**64:
        raise ValueError('D3 target/nonce bound')
    if deadline is not None and (type(deadline) not in (int, float) or not math.isfinite(deadline)):
        raise ValueError('D3 deadline type')
    if trace is not None and (type(trace) is not list or trace):
        raise ValueError('D3 trace must be an empty owned list')
    trace = [] if trace is None else trace
    begin = time.perf_counter_ns()
    p, meter = base.profile, ComponentMeter(budget)
    patterns, work = templates(p, 2)
    meter.add('setup', **work)
    domain = sum(math.comb(p.m, w)*len(values) for w, values in patterns.items())
    prefix = tuple(itertools.islice(candidates(p.m, patterns), min(probe_limit, candidate_limit))) if policy != 'plain' else ()
    meter.add('setup', prefix_generations=len(prefix))
    stage, successes, eligible_count, nonce_index = 'setup', 0, 0, 0
    reason = 'header-limit'

    def checkpoint():
        meter.check()
        if deadline is not None and time.monotonic() >= deadline:
            raise DeadlineStop('D3 study deadline')

    try:
        checkpoint()
        while nonce_index < header_limit:
            batch_start = nonce_index
            length = min(4 if policy.endswith('4') else 1, header_limit-nonce_index)
            batch = dict(start=batch_start, headers=[], selected=None, search=None)
            trace.append(batch)
            for _ in range(length):
                stage = 'generation'
                h = replace(base, nonce=base.nonce+nonce_index)
                encoded = h.encode()
                seed = hashlib.shake_256(DOMAIN+encoded).digest(32)
                matrix = expand_matrix(p, seed)
                item = dict(header_hex=encoded.hex(), seed_hex=seed.hex(), matrix=matrix,
                            probe_flags=[], probe_complete=not bool(prefix))
                batch['headers'].append(item)
                nonce_index += 1
                meter.add('matrix', headers=1, seed_hashes=1, header_encodings=1,
                          seed_input_bytes=len(DOMAIN)+len(encoded), entries=p.n*p.m,
                          shake_output_bytes=2*(4*p.n*p.m+1024))
                checkpoint()
                stage = 'probe'
                for positions, values in prefix:
                    valid, terms, rows = screen(matrix[:1], positions, values, p.q)
                    item['probe_flags'].append(int(valid))
                    meter.add('probe', checks=1, matrix_terms=terms, row_reductions=rows)
                    checkpoint()
                item['probe_complete'] = True
            stage = 'selection'
            if policy == 'random4':
                message = RANDOM_DOMAIN+base.encode()+batch_start.to_bytes(8, 'little')
                selected = int.from_bytes(hashlib.sha256(message).digest()[:8], 'little') % length
                meter.add('selection', hashes=1, input_bytes=len(message))
            elif policy == 'screened4':
                scores = [sum(item['probe_flags']) for item in batch['headers']]
                selected = max(range(length), key=lambda i: (scores[i], -i))
                meter.add('selection', flag_reads=sum(len(item['probe_flags']) for item in batch['headers']), comparisons=length-1)
            else:
                selected = 0
            batch['selected'] = selected
            checkpoint()
            item = batch['headers'][selected]
            h, matrix = LabHeader.decode(bytes.fromhex(item['header_hex'])), item['matrix']
            current = batch['search'] = dict(checked=0, eligible=[], hit=None, reason='running')
            for ordinal, (positions, values) in enumerate(itertools.islice(candidates(p.m, patterns), candidate_limit)):
                stage = 'candidate'
                if ordinal < len(item['probe_flags']):
                    cached = item['probe_flags'][ordinal]
                    valid, terms, rows = screen(matrix[1:], positions, values, p.q) if cached else (False, 0, 0)
                    meter.add('search', cache_reads=1)
                else:
                    valid, terms, rows = screen(matrix, positions, values, p.q)
                current['checked'] += 1
                meter.add('search', generations=1, checks=1, matrix_terms=terms, row_reductions=rows)
                if valid:
                    stage = 'proof-transaction'
                    vector = dense(p.m, positions, values)
                    meter.add('output', vector_entries=p.m)
                    if not paid_verify(p, matrix, vector, meter, 'validation'):
                        raise RuntimeError('D3 acquired vector invalid')
                    packet = encode_proof(h, vector)
                    meter.add('output', proof_bytes=len(packet), header_encodings=1)
                    digest = hashlib.sha256(SCORE_DOMAIN+packet).digest() if construction == 'B' else None
                    if digest is not None:
                        meter.add('score', hashes=1, input_bytes=len(SCORE_DOMAIN)+len(packet))
                    admitted = construction == 'A' or int.from_bytes(digest, 'big') < target
                    current['eligible'].append(dict(ordinal=ordinal, vector=vector, proof_hex=packet.hex(),
                        digest_hex=None if digest is None else digest.hex(), admitted=admitted))
                    eligible_count += 1
                    if admitted:
                        current['hit'] = ordinal
                        current['reason'] = 'hit'
                        successes += 1
                checkpoint()
                if current['hit'] is not None:
                    break
            if current['reason'] == 'running':
                current['reason'] = 'domain-exhausted' if current['checked'] == domain else 'candidate-limit'
    except ComponentStop:
        reason = 'component-budget'
    logical = dict(policy=policy, construction=construction, successes=successes, eligible=eligible_count,
        generated_headers=nonce_index, reason=reason, stopping_stage=stage, domain=domain,
        work=meter.report(), trace=trace)
    return dict(**logical, elapsed_ns=time.perf_counter_ns()-begin)
