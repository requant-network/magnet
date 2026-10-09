"""Frozen D2/D3 falsification campaign. Local only; no consensus or GPU change."""

import hashlib
import json
from pathlib import Path
import sys
import time
from fractions import Fraction

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from reference.header import LabHeader
from reference.screening import POLICIES, campaign
from reference.sis import Profile
from scripts.consensus_evidence import begin_report, finish_report, source_hashes
from scripts.lab_driver import build_lab
from scripts.screening_audits import audit_campaign, audit_native

NAME = 'd3-screening-v1'
PROFILES = ((7, 1, 4, 8), (17, 3, 16, 12), (7, 4, 16, 12), (257, 2, 16, 12))
LABELS = (2026100926, 2026100927, 2026100928)
CAPS = dict(budget=100000, header_limit=256, candidate_limit=4096, probe_limit=64, target=2**254)
REPETITIONS = 3
DEADLINE_SECONDS = 120
CONTRACT = ROOT/'docs/CRITICAL-PATH.md'


def header(profile, label):
    text = NAME+'/'+('/'.join(map(str, profile)))+'/'+str(label)
    fields = [hashlib.sha256((text+'/'+suffix).encode('ascii')).digest() for suffix in ('network', 'parent', 'payload')]
    return LabHeader(*fields, 1, 20261009, 0, Profile(*profile))


def logical_hash(record):
    value = {k: v for k, v in record.items() if k != 'elapsed_ns'}
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def compare(group):
    totals = {policy: dict(successes=0, units=0) for policy in POLICIES}
    for entry in group:
        if entry['repetition'] == 0:
            dest = totals[entry['record']['policy']]
            dest['successes'] += entry['record']['successes']
            dest['units'] += entry['record']['work']['used']
    sufficient = all(t['successes'] >= 5 and t['units'] > 0 for t in totals.values())
    rates = {p: Fraction(t['successes'], t['units']) if t['units'] else Fraction(0) for p, t in totals.items()}
    ratios = {p: str(rates['screened4']/rates[p]) if rates[p] else None for p in POLICIES[:-1]}
    triggered = sufficient and all(rates['screened4'] > 2*rates[p] for p in POLICIES[:-1])
    return dict(outcome='triggered' if triggered else 'not-triggered' if sufficient else 'insufficient-successes',
                totals=totals, screened_vs_controls=ratios, repetitions_counted=1)


def summarize(entry):
    record = entry['record']
    return dict(profile=entry['profile'], construction=record['construction'], label=entry['label'],
                repetition=entry['repetition'], policy=record['policy'], elapsed_ns=record['elapsed_ns'],
                successes=record['successes'], eligible=record['eligible'], generated_headers=record['generated_headers'],
                reason=record['reason'], work=record['work'], logical_sha256=logical_hash(record))


def verify_publication(paths, report, executable, contract_hash):
    """Read back persisted bytes, then recheck the frozen inputs after writes."""
    raw_bytes = paths[1].read_bytes()
    persisted = json.loads(raw_bytes)
    if hashlib.sha256(raw_bytes).hexdigest() != report['raw_sha256']:
        raise RuntimeError('D3 persisted raw digest changed')
    config_hash = hashlib.sha256(json.dumps(persisted['config'], sort_keys=True).encode()).hexdigest()
    if config_hash != report['config_sha256'] or config_hash != persisted['config_sha256']:
        raise RuntimeError('D3 persisted config identity changed')
    if json.loads(paths[0].read_bytes()) != json.loads(json.dumps(report)):
        raise RuntimeError('D3 persisted compact report changed')
    if (source_hashes() != report['source_sha256']
            or hashlib.sha256(CONTRACT.read_bytes()).hexdigest() != contract_hash
            or hashlib.sha256(executable.read_bytes()).hexdigest() != report['executable_sha256']):
        raise RuntimeError('D3 frozen inputs changed after publication')


def main():
    destination, raw_path, sources = begin_report(NAME)
    contract_hash = hashlib.sha256(CONTRACT.read_bytes()).hexdigest()
    config = dict(version=NAME, profiles=PROFILES, labels=LABELS, caps=CAPS,
                  repetitions=REPETITIONS, policies=POLICIES, deadline_seconds=DEADLINE_SECONDS,
                  order='profile/construction/repetition/label/rotated-policy',
                  primary_profiles=PROFILES[1:])
    config_hash = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
    completed, findings, current, native_counts, replay_counts = [], [], None, [], []
    executable, native_hash = None, None
    try:
        executable = build_lab()
        native_hash = hashlib.sha256(executable.read_bytes()).hexdigest()
        deadline = time.monotonic()+DEADLINE_SECONDS

        def check_deadline():
            if time.monotonic() >= deadline:
                raise RuntimeError('D3 global study deadline, comparisons suppressed')

        stop = False
        for profile in PROFILES:
            for construction in ('A', 'B'):
                group = []
                signatures = {}
                for repetition in range(REPETITIONS):
                    for label_index, label in enumerate(LABELS):
                        shift = (label_index+repetition) % len(POLICIES)
                        order = POLICIES[shift:]+POLICIES[:shift]
                        base = header(profile, label)
                        for policy in order:
                            check_deadline()
                            current = dict(profile=profile, construction=construction, label=label,
                                repetition=repetition, policy=policy, trace=[], execution='unknown-unfinished')
                            record = campaign(base, policy, construction, **CAPS, deadline=deadline, trace=current['trace'])
                            entry = dict(profile=profile, label=label, repetition=repetition, record=record)
                            completed.append(entry)
                            group.append(entry)
                            current = None
                            digest = logical_hash(record)
                            key = (label, policy)
                            if repetition == 0:
                                signatures[key] = digest
                                replay_counts.append(audit_campaign(base, record, **CAPS))
                            elif signatures[key] != digest:
                                raise RuntimeError('D3 logical transcript changed across repetitions')
                            check_deadline()
                native_counts.append(audit_native(executable, [e['record'] for e in group if e['repetition'] == 0], CAPS['target']))
                check_deadline()
                comparison = compare(group)
                comparison.update(profile=profile, construction=construction,
                                  primary=profile != PROFILES[0], campaigns=len(group), audits_passed=True)
                findings.append(comparison)
                print(f'{profile} {construction}: {comparison["outcome"]}', flush=True)
                if comparison['primary'] and comparison['outcome'] == 'triggered':
                    stop = True
                    break
            if stop:
                break
        check_deadline()
        raw = dict(config=config, config_sha256=config_hash, contract_sha256=contract_hash,
                   source_sha256=sources, executable_sha256=native_hash, completed=completed,
                   findings=findings, native_audits=native_counts, replay_audits=replay_counts,
                   status='passed', stopped_on_primary_trigger=stop)
        raw_bytes = (json.dumps(raw, indent=2)+'\n').encode('utf-8')
        report = dict(config=config, config_sha256=config_hash, contract_sha256=contract_hash,
            planned_campaigns=288, completed_campaigns=len(completed), stopped_on_primary_trigger=stop,
            comparisons=findings, native_audits=native_counts, replay_audits=replay_counts,
            campaigns=[summarize(e) for e in completed], raw_sha256=hashlib.sha256(raw_bytes).hexdigest(),
            scope='toy sparse-family logical cost; no secure SIS profile or hardware/energy inference',
            counter_scope='named logical components, not every interpreter operation; trace storage and host audit excluded',
            timer_scope='cold campaign after bounded argument validation; setup/generation/probes/search/proof/trace included; audit/build excluded')
        finish_report((destination, raw_path), report, sources, raw=raw, executable=executable,
                      expected_executable_sha256=native_hash, expected_artifacts={CONTRACT: contract_hash})
        verify_publication((destination, raw_path), report, executable, contract_hash)
    except (Exception, KeyboardInterrupt) as error:
        failure = dict(status='failed-or-incomplete', error=str(error), config=config,
            config_sha256=config_hash, contract_sha256=contract_hash, source_sha256=sources,
            executable_sha256=native_hash,
            completed=completed, current=current, comparisons_suppressed=True,
            completed_audits=dict(native=native_counts, replay=replay_counts))
        raw_path.write_text(json.dumps(failure, indent=2)+'\n', encoding='utf-8', newline='\n')
        destination.write_text(json.dumps(dict(status='failed-or-incomplete', error=str(error),
            completed_campaigns=len(completed), comparisons_suppressed=True), indent=2)+'\n', encoding='utf-8', newline='\n')
        raise


if __name__ == '__main__':
    main()
