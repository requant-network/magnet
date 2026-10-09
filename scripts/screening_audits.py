"""Independent D3 prefix/ledger replay and native adjudication, outside timing."""

from dataclasses import replace
import hashlib
import itertools
import json
import math
import struct

from reference.admission_wire import scored_request
from reference.component_meter import MODEL_VERSION, ZERO_WEIGHT
from reference.grinding import SCORE_DOMAIN
from reference.header import DOMAIN, ExpectedContext, LabHeader
from scripts.lab_driver import exchange, matrix_bytes, request


class ReplayStop(Exception):
    pass


def audit_campaign(base, record, *, budget=100000, header_limit=256,
                   candidate_limit=4096, probe_limit=64, target=2**254):
    """Reconstruct without campaign, templates, screen, paid_verify or meter."""
    p = base.profile
    pattern_work = dict(template_visits=0, template_norm_terms=0)
    patterns = []
    for weight in range(1, min(3, p.m)+1):
        entries = []
        for first in (1, 2):
            for tail in itertools.product((1, -1, 2, -2), repeat=weight-1):
                values = (first,)+tail
                pattern_work['template_visits'] += 1
                pattern_work['template_norm_terms'] += weight
                if sum(x*x for x in values) <= p.b2:
                    entries.append(values)
        patterns.append((weight, entries))
    domain = sum(math.comb(p.m, w)*len(entries) for w, entries in patterns)
    ordered = []
    for weight, entries in patterns:
        for positions in itertools.combinations(range(p.m), weight):
            for values in entries:
                if len(ordered) < candidate_limit:
                    ordered.append((positions, values))
    prefix = ordered[:probe_limit] if record['policy'] != 'plain' else []
    phases, used, first_boundary = {}, 0, None
    trace, nonce_index, successes, eligible_count = [], 0, 0, 0
    stage, reason = 'setup', 'header-limit'

    def charge(phase, **counts):
        nonlocal used, first_boundary
        dest = phases.setdefault(phase, {})
        for key, count in counts.items():
            dest[key] = dest.get(key, 0)+count
            if phase+'.'+key not in ZERO_WEIGHT:
                used += count
        if used >= budget and first_boundary is None:
            first_boundary = dict(phase=phase, used=used)

    def boundary():
        if used >= budget:
            raise ReplayStop()

    def rows(matrix, positions, values):
        checks = 0
        for row in matrix:
            checks += 1
            if sum(row[i]*v for i, v in zip(positions, values)) % p.q:
                return False, checks*len(values), checks
        return True, checks*len(values), checks

    charge('setup', **pattern_work)
    charge('setup', prefix_generations=len(prefix))
    try:
        boundary()
        while nonce_index < header_limit:
            start = nonce_index
            length = min(4 if record['policy'].endswith('4') else 1, header_limit-start)
            batch = dict(start=start, headers=[], selected=None, search=None)
            trace.append(batch)
            for _ in range(length):
                stage = 'generation'
                h = replace(base, nonce=base.nonce+nonce_index)
                encoded = h.encode()
                # Matrix itself is independently checked through Rust below.
                actual = record['trace'][len(trace)-1]['headers'][len(batch['headers'])]
                item = dict(header_hex=encoded.hex(), seed_hex=hashlib.shake_256(DOMAIN+encoded).digest(32).hex(),
                            matrix=actual['matrix'], probe_flags=[], probe_complete=not bool(prefix))
                batch['headers'].append(item)
                nonce_index += 1
                charge('matrix', headers=1, seed_hashes=1, header_encodings=1,
                       seed_input_bytes=len(DOMAIN)+len(encoded), entries=p.n*p.m,
                       shake_output_bytes=2*(4*p.n*p.m+1024))
                boundary()
                stage = 'probe'
                for positions, values in prefix:
                    valid, terms, reductions = rows(item['matrix'][:1], positions, values)
                    item['probe_flags'].append(int(valid))
                    charge('probe', checks=1, matrix_terms=terms, row_reductions=reductions)
                    boundary()
                item['probe_complete'] = True
            stage = 'selection'
            if record['policy'] == 'random4':
                message = b'D3/random-selection\0'+base.encode()+start.to_bytes(8, 'little')
                selected = int.from_bytes(hashlib.sha256(message).digest()[:8], 'little') % length
                charge('selection', hashes=1, input_bytes=len(message))
            elif record['policy'] == 'screened4':
                scores = [sum(h['probe_flags']) for h in batch['headers']]
                selected = scores.index(max(scores))
                charge('selection', flag_reads=sum(len(h['probe_flags']) for h in batch['headers']), comparisons=length-1)
            else:
                selected = 0
            batch['selected'] = selected
            boundary()
            item = batch['headers'][selected]
            current = batch['search'] = dict(checked=0, eligible=[], hit=None, reason='running')
            for ordinal, (positions, values) in enumerate(ordered):
                stage = 'candidate'
                if ordinal < len(item['probe_flags']):
                    valid, terms, reductions = rows(item['matrix'][1:], positions, values) if item['probe_flags'][ordinal] else (False, 0, 0)
                    charge('search', cache_reads=1)
                else:
                    valid, terms, reductions = rows(item['matrix'], positions, values)
                current['checked'] += 1
                charge('search', generations=1, checks=1, matrix_terms=terms, row_reductions=reductions)
                if valid:
                    stage = 'proof-transaction'
                    vector = [0]*p.m
                    for i, value in zip(positions, values):
                        vector[i] = value
                    charge('output', vector_entries=p.m)
                    if vector[positions[0]] <= 0 or sum(x*x for x in vector) > p.b2:
                        raise RuntimeError('noncanonical acquired candidate')
                    if any(sum(a*x for a, x in zip(row, vector)) % p.q for row in item['matrix']):
                        raise RuntimeError('invalid dense acquired candidate')
                    charge('validation', shape_entries=p.n*p.m+p.m, sign_terms=positions[0]+1,
                           norm_terms=p.m, matrix_terms=p.n*p.m, row_reductions=p.n, checks=1)
                    packet = bytes.fromhex(item['header_hex'])+struct.pack(f'<{p.m}i', *vector)
                    charge('output', proof_bytes=len(packet), header_encodings=1)
                    digest = hashlib.sha256(SCORE_DOMAIN+packet).digest() if record['construction'] == 'B' else None
                    if digest is not None:
                        charge('score', hashes=1, input_bytes=len(SCORE_DOMAIN)+len(packet))
                    admitted = digest is None or int.from_bytes(digest, 'big') < target
                    current['eligible'].append(dict(ordinal=ordinal, vector=tuple(vector), proof_hex=packet.hex(),
                        digest_hex=None if digest is None else digest.hex(), admitted=admitted))
                    eligible_count += 1
                    if admitted:
                        current['hit'], current['reason'] = ordinal, 'hit'
                        successes += 1
                boundary()
                if current['hit'] is not None:
                    break
            if current['reason'] == 'running':
                current['reason'] = 'domain-exhausted' if current['checked'] == domain else 'candidate-limit'
    except ReplayStop:
        reason = 'component-budget'
    expected = dict(policy=record['policy'], construction=record['construction'], successes=successes,
        eligible=eligible_count, generated_headers=nonce_index, reason=reason, stopping_stage=stage, domain=domain,
        work=dict(model=MODEL_VERSION, zero_weight=list(ZERO_WEIGHT), limit=budget, used=used,
                  overshoot=max(0, used-budget), first_boundary=first_boundary,
                  post_boundary_units=0 if first_boundary is None else used-first_boundary['used'], phases=phases), trace=trace)
    actual = {k: v for k, v in record.items() if k != 'elapsed_ns'}
    if json.dumps(expected, sort_keys=True) != json.dumps(actual, sort_keys=True):
        differing = [k for k in expected if json.dumps(expected[k], sort_keys=True) != json.dumps(actual.get(k), sort_keys=True)]
        raise RuntimeError(f'D3 independent ledger/prefix mismatch: {differing}')
    return dict(headers=nonce_index, searched=sum(b['search']['checked'] for b in trace if b['search']), eligible=eligible_count)


def audit_native(executable, records, target):
    """Deduplicate messages, but count every generated/rejected occurrence."""
    headers, proofs = {}, {}
    occurrences, rejected, eligible = 0, 0, 0
    for record in records:
        for batch in record['trace']:
            for i, item in enumerate(batch['headers']):
                occurrences += 1
                rejected += int(batch['search'] is None or i != batch['selected'])
                wire = bytes.fromhex(item['header_hex'])
                response = bytes.fromhex(item['seed_hex'])+matrix_bytes(item['matrix'])
                if wire in headers and headers[wire] != response:
                    raise RuntimeError('inconsistent matrix replay')
                headers[wire] = response
            if batch['search']:
                for item in batch['search']['eligible']:
                    eligible += 1
                    packet = bytes.fromhex(item['proof_hex'])
                    h = LabHeader.decode(packet[:140])
                    context = ExpectedContext(h.network, h.parent, h.height, h.profile)
                    proofs[request(3, context.encode()+packet)] = b'\x01'
                    if record['construction'] == 'B':
                        proofs[scored_request(context, target, packet)] = bytes([item['admitted']])
    messages = [(request(2, h), expected) for h, expected in headers.items()]+list(proofs.items())
    for offset in range(0, len(messages), 512):
        chunk = messages[offset:offset+512]
        if exchange(executable, (m for m, _ in chunk)) != [expected for _, expected in chunk]:
            raise RuntimeError('D3 native derivation/proof/score mismatch')
    return dict(header_occurrences=occurrences, rejected_header_occurrences=rejected,
                unique_headers=len(headers), eligible_occurrences=eligible, native_requests=len(messages))
