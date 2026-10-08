"""Paired adaptive retention/solver campaigns in externally bounded CPU workers."""

import argparse
from collections import Counter
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from reference.header import LabHeader
from reference.pool_campaign import PoolBudget, joint_headers
from reference.sis import Profile
from scripts.adaptive_audit import audit_snapshot
from scripts.consensus_evidence import begin_report, finish_report
from scripts.lab_driver import build_lab
from scripts.native_driver import build_native
from scripts.portfolio_survey import summarize as summarize_campaigns
from scripts.window_driver import run_window
from solvers.portfolio import BACKENDS

SEEDS = (2026100903, 2026100904)
ORDER_SEED = 2026100905
PROFILES = (Profile(7, 1, 3, 8), Profile(17, 2, 8, 8), Profile(257, 3, 14, 12))
CONFIGS = (('restart-all', 'fifo'), ('pool-all', 'fifo'), ('pool-fallback', 'fifo'), ('pool-fallback', 'future-supply'))
WINDOWS = (500, 4000)
TARGET = 2**252
BUDGET = PoolBudget(nodes=100_000, acquisitions=24, checks=8192, scores=4096, proofs=6)


def stages_for(profile, seed):
    label = f'adaptive-v1/{profile.q}-{profile.n}-{profile.m}-{profile.b2}/{seed}'
    def digest(field):
        return hashlib.sha256((label+'/'+field).encode('ascii')).digest()
    stages = tuple(joint_headers(LabHeader(digest('network'), digest(f'parent/{i}'), digest(f'payload/{i}'),
                                            i+1, 100+i*16, 0, profile), nonces=4, times=2, payloads=2)
                   for i in range(3))
    return label, stages


def summarize(records):
    result = summarize_campaigns(records)
    complete = [r for r in records if r['window']['logical_work_known']]
    selectors = [r['window']['snapshot']['retention'] for r in complete if r['window']['snapshot']['retention'] is not None]
    result['completed_retention'] = {name: sum(s[name] for s in selectors)
                                    for name in ('decisions', 'evaluations', 'rank_arithmetic_units', 'fifo_fallbacks')}
    result['checkpoint_hit_occurrences'] = sum(r['audit']['hit_occurrences'] for r in records if not r['window']['logical_work_known'])
    result['all_attempt_retention_work_known'] = len(complete) == len(records)
    return result


def paired_retention(records):
    pairs = {}
    for record in records:
        if record['policy'] != 'pool-fallback':
            continue
        key = record['label'], record['backend'], record['wall_ms']
        pairs.setdefault(key, {})[record['retention']] = record
    if any(set(pair) != {'fifo', 'future-supply'} for pair in pairs.values()):
        raise RuntimeError('unpaired retention schedule')
    complete = [pair for pair in pairs.values() if all(r['window']['logical_work_known'] for r in pair.values())]
    deltas = Counter()
    for pair in complete:
        hits = {name: sum(s['hit'] is not None for s in r['window']['snapshot']['campaign']['stages'])
                for name, r in pair.items()}
        delta = hits['future-supply']-hits['fifo']
        deltas['more-hits' if delta > 0 else 'fewer-hits' if delta < 0 else 'equal-hits'] += 1
    return {'scheduled_pairs': len(pairs), 'both_completed_pairs': len(complete),
            'censored_or_incomplete_pairs': len(pairs)-len(complete),
            'completed_pair_outcomes': dict(deltas),
            'scope': 'conditional paired stage-hit counts; not wall-time, energy or economic ranking'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--python', required=True, type=Path)
    args = parser.parse_args()
    paths = begin_report('adaptive-retention-v1')
    lab, native = build_lab(), build_native(release=True)
    cases = [(profile, seed, backend, policy, retention, wall_ms) for profile in PROFILES for seed in SEEDS
             for backend in BACKENDS for policy, retention in CONFIGS for wall_ms in WINDOWS]
    random.Random(ORDER_SEED).shuffle(cases)
    records = []
    for i, (profile, seed, backend, policy, retention, wall_ms) in enumerate(cases):
        label, stages = stages_for(profile, seed)
        query = {'version': 'WAX1', 'backend': backend, 'policy': policy, 'target': str(TARGET),
                 'stages': [[h.encode().hex() for h in stage] for stage in stages], 'seed': seed,
                 'capacity': 3, 'combine': False, 'budget': asdict(BUDGET), 'retention': retention, 'decisions': 64}
        window = run_window(args.python.resolve(), query, wall_ms=wall_ms, memory_mib=128, worker='adaptive_worker.py')
        audit = audit_snapshot(window['snapshot'], stages, lab, query=query, budget=BUDGET)
        records.append({'label': label, 'seed': seed, 'backend': backend, 'policy': policy,
                        'retention': retention, 'wall_ms': wall_ms, 'window': window, 'audit': audit})
        if i % 8 == 0:
            print(f"Adaptive {i+1}/{len(cases)} {backend}/{retention}: {window['outcome']}", flush=True)
    groups = {}
    for record in records:
        key = f"{record['label'].split('/')[1]}/{record['backend']}/{record['policy']}/{record['retention']}/{record['wall_ms']}ms"
        groups.setdefault(key, []).append(record)
    report = {'version': 'adaptive-retention-v1', 'seeds': SEEDS, 'order_seed': ORDER_SEED,
              'configuration': {'profiles': [asdict(p) for p in PROFILES], 'backends': BACKENDS,
                                'configs': CONFIGS, 'windows_ms': WINDOWS, 'memory_mib': 128,
                                'target': str(TARGET), 'budget': asdict(BUDGET), 'capacity': 3,
                                'combine': False, 'selection_decisions': 64, 'stages': 3, 'headers_per_stage': 16},
              'scheduled_attempts': len(cases), 'unique_scheduled_headers': len(PROFILES)*len(SEEDS)*3*16,
              'repeated_header_schedule_scope': 'same challenges across backend/policy/windows; not distinct block counts',
              'overall': summarize(records), 'groups': {key: summarize(value) for key, value in sorted(groups.items())},
              'paired_retention': paired_retention(records),
              'audits': {name: sum(r['audit'][name] for r in records) for name in
                         ('visited_headers', 'native_requests', 'scores_checked', 'hit_occurrences', 'selection_decisions')},
              'mismatches': 0, 'native_search_release_sha256': hashlib.sha256(native.read_bytes()).hexdigest(),
              'limitations': ['future-supply ranking uses explicit iid matrix/conditional iid score hypotheses',
                              'current observed matrix never receives a precommitted-pool probability',
                              'selection decisions and backend setup/reduction are inside measured Job time/commit',
                              'node kinds differ across backend; no universal work weight or elapsed/energy ranking',
                              'partial checkpoints audited separately; censored unconditional work remains unknown',
                              'paired completed outcomes are conditional, not a general adaptive speedup',
                              'dimensions <=14, finite sieve/one-tour BKZ, no optimized GPU or production hardness',
                              'native/model/transcript re-audits outside workers; they supply no mining inputs',
              'no production chainwork, dynamic admission targets or monetary protocol selected']}
    observed = [r['window']['snapshot']['backend'].get('flint') for r in records
                if r['window']['snapshot'] is not None and 'backend' in r['window']['snapshot']]
    flint = [metadata for metadata in observed if metadata is not None]
    if not flint or any(metadata != flint[0] for metadata in flint):
        raise RuntimeError('optional backend metadata missing/changed')
    report['observed_flint_backend'] = flint[0]
    finish_report(paths, report, paths[2], raw={'records': records}, executable=lab)


if __name__ == '__main__':
    main()
