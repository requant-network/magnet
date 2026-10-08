"""Replay bounded adaptive campaigns and independently audit original MGH1 bytes."""

import json

from reference.adaptive_retention import FutureSupplyRetainer
from reference.admission_wire import admission_request, scored_request
from reference.grinding import SCORE_DOMAIN, score_digest
from reference.header import ExpectedContext, LabHeader, encode_proof
from reference.header_rules import LabRules
from reference.pool_campaign import run_pool_campaign
from reference.sis import verify
from scripts.lab_driver import exchange, matrix_bytes, request


class _TranscriptSolver:
    def __init__(self, instances):
        self.queue = [instance for instance in instances if 'acquired' in instance]
        self.cursor = 0

    def acquire(self, profile, matrix, nodes, proofs):
        if self.cursor >= len(self.queue):
            raise RuntimeError('unrecorded replay acquisition')
        instance = self.queue[self.cursor]
        header = LabHeader.decode(bytes.fromhex(instance['header_hex']))
        if header.profile != profile or header.matrix() != matrix:
            raise RuntimeError('acquisition transcript context disagreement')
        self.cursor += 1
        return instance['acquired']


def audit_snapshot(snapshot, stages, lab, *, query, budget):
    empty = {'visited_headers': 0, 'native_requests': 0, 'scores_checked': 0, 'hit_occurrences': 0,
             'selection_decisions': 0, 'replayed': False}
    if snapshot is None or snapshot.get('status') == 'memory-error':
        return empty
    if snapshot.get('status') not in ('completed', 'checkpoint'):
        raise RuntimeError('unexpected adaptive snapshot')
    actual = snapshot['campaign']
    completed_stages = len(actual['stages'])
    if not 1 <= completed_stages <= len(stages) or snapshot['status'] == 'completed' and completed_stages != len(stages):
        raise RuntimeError('adaptive stage coverage')
    solver = _TranscriptSolver(actual['instances'])
    retain = FutureSupplyRetainer(int(query['target']), decisions=query['decisions']) if query['retention'] == 'future-supply' else None
    replay = run_pool_campaign(stages[:completed_stages], query['policy'], int(query['target']), solver,
                               capacity=query['capacity'], combine=query['combine'], budget=budget, retain=retain)
    expected = json.loads(json.dumps(actual))
    expected.pop('elapsed_ns', None)
    replay.pop('elapsed_ns', None)
    if 'pool' not in expected:
        replay.pop('pool')
    if solver.cursor != len(solver.queue) or json.loads(json.dumps(replay)) != expected:
        raise RuntimeError('adaptive campaign transcript disagreement')
    retention = retain.snapshot() if retain else None
    if json.loads(json.dumps(snapshot['retention'])) != json.loads(json.dumps(retention)):
        raise RuntimeError('adaptive retention decision disagreement')
    work = actual['work']
    if (work['search_nodes'] > budget.nodes or work['acquisitions'] > budget.acquisitions
            or work['pool_checks']+work['combination_checks'] > budget.checks or work['score_hashes'] > budget.scores):
        raise RuntimeError('adaptive component cap violation')
    commands, replies = [], []
    for instance in actual['instances']:
        h = stages[instance['stage']][instance['index']]
        if instance['header_hex'] != h.encode().hex():
            raise RuntimeError('header outside declared adaptive surface')
        matrix = h.matrix()
        context = ExpectedContext(h.network, h.parent, h.height, h.profile)
        commands.append(request(2, h.encode()))
        replies.append(h.seed()+matrix_bytes(matrix))
        acquired = instance.get('acquired')
        if acquired is not None:
            native = acquired['work'].get('native')
            backend = query['backend']
            if backend == 'mitm':
                if (native is None or native['nodes'] != native['left']+native['right']+native['pairs']
                        or acquired['work']['nodes'] != native['nodes']):
                    raise RuntimeError('native mode3 accounting identity')
            elif backend == 'sparse-first':
                if acquired['work']['nodes'] != acquired['work']['sparse_checks']:
                    raise RuntimeError('sparse accounting identity')
            elif acquired['work']['nodes'] != acquired['work']['search']['nodes']+acquired['work']['bkz_nodes']:
                raise RuntimeError('lattice accounting identity')
        vectors = tuple(instance['pool_before'])+tuple(instance['valid_carried'])+tuple(
            acquired['proofs'] if acquired is not None else ())
        for vector in dict.fromkeys(map(tuple, vectors)):
            commands.append(scored_request(context, 2**256, encode_proof(h, vector)))
            replies.append(bytes([verify(h.profile, matrix, vector)]))
    scored = set()
    for score in actual['scores']:
        h = stages[score['stage']][score['index']]
        vector = tuple(score['vector'])
        identity = h.encode(), vector
        if identity in scored:
            raise RuntimeError('duplicate adaptive score input')
        scored.add(identity)
        packet = encode_proof(h, vector)
        context = ExpectedContext(h.network, h.parent, h.height, h.profile)
        if not verify(h.profile, h.matrix(), vector) or score_digest(h, vector).hex() != score['digest']:
            raise RuntimeError('adaptive score validity/digest disagreement')
        commands += [request(4, SCORE_DOMAIN+packet), scored_request(context, int(query['target']), packet)]
        replies += [bytes.fromhex(score['digest']), bytes([int(score['digest'], 16) < int(query['target'])])]
    for stage in actual['stages']:
        hit = stage['hit']
        if hit is None:
            continue
        headers = stages[stage['index']]
        base = headers[0]
        context = ExpectedContext(base.network, base.parent, base.height, base.profile)
        rules = LabRules(context, int(query['target']), min(h.timestamp for h in headers),
                         max(h.timestamp for h in headers), tuple(dict.fromkeys(h.payload for h in headers)))
        commands.append(admission_request(rules, bytes.fromhex(hit['proof_hex'])))
        replies.append(b'\x01')
    for offset in range(0, len(commands), 1024):
        if exchange(lab, commands[offset:offset+1024]) != replies[offset:offset+1024]:
            raise RuntimeError('independent adaptive generation/validity/score disagreement')
    return {'visited_headers': len(actual['instances']), 'native_requests': len(commands),
            'scores_checked': len(actual['scores']), 'hit_occurrences': sum(s['hit'] is not None for s in actual['stages']),
            'selection_decisions': len(retain.records) if retain else 0, 'replayed': True}
