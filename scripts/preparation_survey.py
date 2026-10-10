"""Precommitted minimal D4 integration. Local Windows Jobs; no speed/security claim."""

import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from reference.header import LabHeader
from reference.sis import Profile
from scripts.consensus_evidence import begin_report, finish_report
from scripts.lab_driver import build_lab
from scripts.preparation_audits import audit_campaign, audit_native, same
from scripts.screening_survey import verify_publication
from scripts.window_driver import run_window

NAME = 'd4-kernel-transfer-v1'
CONTRACT = ROOT/'docs/CRITICAL-PATH.md'
PROFILES = ((3, 1, 2, 2), (17, 2, 8, 8))
LABELS = (2026101031, 2026101032)
POLICIES = ('cold', 'kernel-cache')


def headers(profile, label):
    root = NAME+'/'+','.join(map(str, profile))+'/'+str(label)
    def digest(suffix):
        return hashlib.sha256((root+'/'+suffix).encode('ascii')).digest()
    return [LabHeader(digest('network'), digest('parent/'+str(i)), digest('payload'),
                      i+1, 20261010+i, i, Profile(*profile)) for i in range(8)]


def main():
    destination, raw_path, sources = begin_report(NAME)
    contract_hash = hashlib.sha256(CONTRACT.read_bytes()).hexdigest()
    config = dict(version=NAME, profiles=PROFILES, labels=LABELS, policies=POLICIES,
                  headers_per_worker=8, nodes=10000, reductions=8, search_cap=2000, cache_limit=8,
                  wall_ms=15000, memory_mib=192, deadline_seconds=180,
                  order='profile/label/rotated-policy', backend='lll75')
    config_hash = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
    completed, comparisons, current = [], [], None
    native_hash = None
    try:
        executable = build_lab()
        native_hash = hashlib.sha256(executable.read_bytes()).hexdigest()
        deadline = time.monotonic()+config['deadline_seconds']
        def check_deadline():
            if time.monotonic() >= deadline:
                raise RuntimeError('D4 global deadline; conclusions suppressed')
        python = ROOT/'artifacts/flint-env/Scripts/python.exe'
        for profile in PROFILES:
            for label_index, label in enumerate(LABELS):
                stream = headers(profile, label)
                group = {}
                order = POLICIES[label_index:]+POLICIES[:label_index]
                for policy in order:
                    check_deadline()
                    current = dict(profile=profile, label=label, policy=policy, execution='unknown-unfinished')
                    window = run_window(python, dict(version='WDP1', headers=[h.encode().hex() for h in stream], policy=policy),
                                        wall_ms=config['wall_ms'], memory_mib=config['memory_mib'], worker='preparation_worker.py')
                    current['window'] = window
                    record = window['snapshot'].get('campaign') if window['snapshot'] else None
                    entry = dict(profile=profile, label=label, policy=policy, window=window)
                    completed.append(entry)
                    if record is not None:
                        entry['replay_audit'] = audit_campaign(stream, record)
                        entry['native_audit'] = audit_native(executable, stream, record)
                    if window['outcome'] != 'completed':
                        raise RuntimeError('D4 censored/unclassified worker; unknown in-flight work retained')
                    if record is None or len(record['stages']) != 8 or record['reason'] != 'headers-exhausted':
                        raise RuntimeError('D4 incomplete declared integration stream')
                    group[policy] = entry
                    current = None
                    check_deadline()
                cold = group['cold']['window']['snapshot']['campaign']
                warm = group['kernel-cache']['window']['snapshot']['campaign']
                same([(s['header_hex'], s['proofs'], s['scores']) for s in cold['stages']],
                     [(s['header_hex'], s['proofs'], s['scores']) for s in warm['stages']])
                comparisons.append(dict(profile=profile, label=label, outputs_equal=True,
                                        cold_work=cold['work'], cache_work=warm['work'],
                                        different_matrix_hits=group['kernel-cache']['replay_audit']['different_matrix_hits']))
                print(f'{profile} label{label}: exact outputs agree, cache hits={warm["work"]["cache_hits"]}', flush=True)
        check_deadline()
        raw = dict(status='passed', config=config, config_sha256=config_hash, contract_sha256=contract_hash,
                   source_sha256=sources, executable_sha256=native_hash, completed=completed, comparisons=comparisons)
        report = dict(config=config, config_sha256=config_hash, contract_sha256=contract_hash,
                      planned_campaigns=8, completed_campaigns=len(completed), comparisons=comparisons,
                      campaigns=[dict(profile=e['profile'], label=e['label'], policy=e['policy'],
                                      outcome=e['window']['outcome'], resource=e['window']['resource'],
                                      replay_audit=e['replay_audit'], native_audit=e['native_audit']) for e in completed],
                      raw_sha256=hashlib.sha256((json.dumps(raw, indent=2)+'\n').encode()).hexdigest(),
                      scope='exact complete-kernel transfer only; general D4 and A/B viability remain open',
                      counter_scope='named components; fingerprint paid on hits, duplicated kernel construction on misses',
                      timer_scope='descriptive cold worker/Job observations, not matched hardware speed or energy')
        finish_report((destination, raw_path), report, sources, raw=raw, executable=executable,
                      expected_executable_sha256=native_hash, expected_artifacts={CONTRACT: contract_hash})
        verify_publication((destination, raw_path), report, executable, contract_hash)
    except (Exception, KeyboardInterrupt) as error:
        if current is not None and hasattr(error, 'window_evidence'):
            current['window'] = error.window_evidence
        failure = dict(status='failed-or-incomplete', error=str(error), config=config, config_sha256=config_hash,
                       contract_sha256=contract_hash, source_sha256=sources, executable_sha256=native_hash,
                       completed=completed, current=current, comparisons_suppressed=True)
        raw_path.write_text(json.dumps(failure, indent=2)+'\n', encoding='utf-8', newline='\n')
        destination.write_text(json.dumps(dict(status='failed-or-incomplete', error=str(error),
                                               completed_campaigns=len(completed), comparisons_suppressed=True), indent=2)+'\n',
                               encoding='utf-8', newline='\n')
        raise


if __name__ == '__main__':
    main()
