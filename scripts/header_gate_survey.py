"""Frozen B-H candidate fork: public gate versus alleged SIS amplification."""

from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from reference.header import ExpectedContext, LabHeader
from reference.header_gate import DOMAIN, header_digest, renewal_costs
from reference.sis import Profile
from scripts.consensus_evidence import begin_report, finish_report
from scripts.lab_driver import build_lab, exchange, request
from scripts.preparation_audits import audit_campaign, audit_native, same
from scripts.screening_survey import verify_publication
from scripts.window_driver import run_window

NAME = 'd4-header-gate-v1'
CONTRACT = ROOT/'docs/CRITICAL-PATH.md'
PROFILES = ((3, 1, 2, 2), (17, 2, 8, 8))
LABELS = (2026101041, 2026101042, 2026101043, 2026101044)
POLICIES = ('solve-all', 'gate-first')
TARGET = 2**254


def headers(profile, label):
    root = NAME+'/'+','.join(map(str, profile))+'/'+str(label)
    fields = [hashlib.sha256((root+'/'+s).encode('ascii')).digest() for s in ('network', 'parent', 'payload')]
    base = LabHeader(*fields, 1, 20261010, 0, Profile(*profile))
    return [replace(base, nonce=i) for i in range(5)]


def gate_plan(stream, policy, target=TARGET):
    if (type(stream) not in (list, tuple) or not 1 <= len(stream) <= 5
            or any(not isinstance(h, LabHeader) for h in stream) or policy not in POLICIES
            or type(target) is not int or not 0 <= target <= 2**256):
        raise ValueError('B-H bounded plan')
    base = stream[0]
    context = ExpectedContext(base.network, base.parent, base.height, base.profile)
    if len({h.encode() for h in stream}) != len(stream) or any(not context.matches(h) for h in stream):
        raise ValueError('B-H context/distinctness')
    scores = []
    for h in stream:
        digest = header_digest(h)
        scores.append(dict(header_hex=h.encode().hex(), digest_hex=digest.hex(), passed=int.from_bytes(digest, 'big') < target))
    selected = [i for i, s in enumerate(scores) if s['passed']]
    attempted = list(range(len(stream))) if policy == 'solve-all' else selected
    return dict(policy=policy, scores=scores, attempted_indices=attempted,
                gate_work=dict(header_hashes=len(stream), score_bytes=sum(len(DOMAIN)+len(h.encode()) for h in stream),
                               selection_checks=len(stream)))


def compare_pair(control, attack, *, primary):
    same(control['plan']['scores'], attack['plan']['scores'])
    selected = [i for i, s in enumerate(control['plan']['scores']) if s['passed']]
    total = len(control['plan']['scores'])
    same(control['plan']['attempted_indices'], list(range(total)))
    same(attack['plan']['attempted_indices'], selected)
    def stages(entry):
        if not entry['plan']['attempted_indices']:
            if entry['window'] is not None:
                raise ValueError('B-H empty cohort must not launch worker')
            return {}
        window = entry['window']
        if window['outcome'] != 'completed':
            raise ValueError('B-H censored comparison')
        record = window['snapshot']['campaign']
        if record['reason'] != 'headers-exhausted' or len(record['stages']) != len(entry['plan']['attempted_indices']):
            raise ValueError('B-H incomplete declared attempts')
        return dict(zip(entry['plan']['attempted_indices'], record['stages'], strict=True))
    cold, filtered = stages(control), stages(attack)
    common = 0
    for i in selected:
        keys = ('header_hex', 'proofs', 'search_work', 'search_reason')
        same([cold[i][k] for k in keys], [filtered[i][k] for k in keys])
        common += len(cold[i]['proofs'])
    control_reductions = control['window']['snapshot']['campaign']['work']['reductions']
    attack_reductions = attack['window']['snapshot']['campaign']['work']['reductions'] if attack['window'] else 0
    # Both are cold; every attempted header, including bounded misses, is paid.
    same((control_reductions, attack_reductions), (total, len(selected)))
    avoided = total-len(selected)
    return dict(primary=primary, outcome='observed-bypass' if primary and common and avoided else 'structural-only',
                passing_headers=len(selected), rejected_headers=avoided, common_admitted_proofs=common,
                accepted_outputs_equal=True, control_reductions=control_reductions, gate_first_reductions=attack_reductions)


def main():
    destination, raw_path, sources = begin_report(NAME)
    contract_hash = hashlib.sha256(CONTRACT.read_bytes()).hexdigest()
    config = dict(version=NAME, profiles=PROFILES, labels=LABELS, policies=POLICIES, target=str(TARGET),
                  headers_per_batch=5, nodes=10000, reductions=8, search_cap=2000, proof_cap=1,
                  wall_ms=15000, memory_mib=192, deadline_seconds=270,
                  order='profile/label/rotated-policy', predicate='canonical SIS AND SHA256(D_H||header)<T')
    config_hash = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
    completed, comparisons, current = [], [], None
    native_hash = None
    try:
        executable = build_lab()
        native_hash = hashlib.sha256(executable.read_bytes()).hexdigest()
        deadline = time.monotonic()+config['deadline_seconds']
        def check_deadline():
            if time.monotonic() >= deadline:
                raise RuntimeError('B-H global deadline; conclusions suppressed')
        python = ROOT/'artifacts/flint-env/Scripts/python.exe'
        for profile in PROFILES:
            for label_index, label in enumerate(LABELS):
                stream, group = headers(profile, label), {}
                shift = label_index % 2
                for policy in POLICIES[shift:]+POLICIES[:shift]:
                    check_deadline()
                    current = dict(profile=profile, label=label, policy=policy, execution='unknown-unfinished')
                    plan = gate_plan(stream, policy)
                    current['plan'] = plan
                    actual = exchange(executable, [request(4, DOMAIN+h.encode()) for h in stream])
                    if actual != [bytes.fromhex(s['digest_hex']) for s in plan['scores']]:
                        raise ValueError('B-H independent header score mismatch')
                    current['native_gate_hashes'] = len(stream)
                    attempted = [stream[i] for i in plan['attempted_indices']]
                    window = None
                    if attempted:
                        window = run_window(python, dict(version='WDP1', headers=[h.encode().hex() for h in attempted], policy='cold'),
                                            wall_ms=config['wall_ms'], memory_mib=config['memory_mib'], worker='preparation_worker.py')
                    current['window'] = window
                    entry = dict(profile=profile, label=label, policy=policy, plan=plan, window=window, native_gate_hashes=len(stream))
                    completed.append(entry)
                    if window is not None:
                        record = window['snapshot'].get('campaign') if window['snapshot'] else None
                        if record is not None:
                            entry['replay_audit'] = audit_campaign(attempted, record)
                            entry['native_solver_audit'] = audit_native(executable, attempted, record)
                        if window['outcome'] != 'completed' or record is None:
                            raise RuntimeError('B-H unfinished attempt; unknown in-flight work retained')
                    group[policy] = entry
                    current = None
                    check_deadline()
                result = compare_pair(group['solve-all'], group['gate-first'], primary=profile == PROFILES[1])
                result.update(profile=profile, label=label)
                comparisons.append(result)
                print(f'{profile} label{label}: {result["outcome"]}, admitted={result["common_admitted_proofs"]}, skipped={result["rejected_headers"]}', flush=True)
        check_deadline()
        raw = dict(status='passed', config=config, config_sha256=config_hash, contract_sha256=contract_hash,
                   source_sha256=sources, executable_sha256=native_hash, completed=completed, comparisons=comparisons)
        model = []
        for c in (1, 10, 100):
            cold, filtered = renewal_costs(TARGET, 1, 1, c)
            model.append(dict(p='1/4', s='1', illustrative_G=1, illustrative_C=c,
                              solve_all=str(cold), gate_first=str(filtered), ratio=str(cold/filtered)))
        report = dict(config=config, config_sha256=config_hash, contract_sha256=contract_hash,
                      planned_batches=16, completed_batches=len(completed),
                      actual_workers=sum(e['window'] is not None for e in completed), comparisons=comparisons,
                      observed_primary_pairs=sum(e['outcome'] == 'observed-bypass' for e in comparisons),
                      conditional_model=model, raw_sha256=hashlib.sha256((json.dumps(raw, indent=2)+'\n').encode()).hexdigest(),
                      batches=[dict(profile=e['profile'], label=e['label'], policy=e['policy'],
                                    gate_work=e['plan']['gate_work'], attempted_indices=e['plan']['attempted_indices'],
                                    native_gate_hashes=e['native_gate_hashes'],
                                    worker_outcome=e['window']['outcome'] if e['window'] else 'empty-gate-skipped',
                                    resource=e['window']['resource'] if e['window'] else None,
                                    solver_work=e['window']['snapshot']['campaign']['work'] if e['window'] else None,
                                    replay_audit=e.get('replay_audit'), native_solver_audit=e.get('native_solver_audit')) for e in completed],
                      scope='new B-H-SIS acquisition-premise falsifier; neither general D4 closure nor target-monotonicity rejection',
                      counter_scope='named actual hashes/preparations; no calibrated work sum; auxiliary proof scores retained',
                      timer_scope='Job resources descriptive; host gate untimed; no speed/energy or time-to-first-block claim')
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
                                               completed_batches=len(completed), comparisons_suppressed=True), indent=2)+'\n',
                               encoding='utf-8', newline='\n')
        raise


if __name__ == '__main__':
    main()
