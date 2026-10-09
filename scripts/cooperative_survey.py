"""Frozen five-task component-budget study; no hardware or chainwork benchmark."""

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from reference.component_meter import ComponentMeter, MODEL_VERSION, ZERO_WEIGHT
from reference.cooperative_campaign import POLICIES, step
from reference.cooperative_solvers import ALGORITHMS, Acquisition
from reference.sis import Profile, encode_case, expand_matrix
from scripts.consensus_evidence import begin_report, finish_report
from scripts.cooperative_audits import audit_record, oracle
from scripts.small_coefficient_audits import native_verdicts
from scripts.small_coefficient_survey import build_verifier

VERSION = 'cooperative-acquisition-v1'
LABEL_SEED = 2026100916
PROFILES = ((7, 1, 4, 8), (17, 2, 5, 8), (257, 2, 6, 12))
BUDGETS = (750, 5000, 50000)
COHORTS = ('fresh', 'control')
STEPS = 4


def label_for(profile, cohort, index):
    return '/'.join(map(str, (VERSION, LABEL_SEED, profile.q, profile.n, profile.m, profile.b2,
                              0 if cohort == 'control' else index)))


def summarize(records):
    groups = {}
    for r in records:
        label = '/'.join(map(str, (r['profile'], r['cohort'], r['algorithm'], r['policy'], r['budget'])))
        group = groups.setdefault(label, dict(steps=0, acquired=0, carry_checks=0, carry_hits=0,
            retained=0, directions=0, used=0, overshoot=0, post_boundary_units=0,
            budget_reached=0, proof_cap_hit=0, domain_exhausted=0, empty=0, reasons={}))
        for key, value in dict(steps=1, acquired=len(r['acquired']), carry_checks=len(r['carry']),
            carry_hits=sum(x['valid'] for x in r['carry']), retained=len(r['retained']),
            directions=len(r['retained_direction_multiplicities']), used=r['meter']['used'],
            overshoot=r['meter']['overshoot'], post_boundary_units=r['meter']['post_boundary_units'],
            budget_reached=int(r['budget_reached']), proof_cap_hit=int(r['proof_cap_hit']),
            domain_exhausted=int(r['domain_exhausted']), empty=int(not r['acquired'])).items():
            group[key] += value
        group['reasons'][r['reason']] = group['reasons'].get(r['reason'], 0)+1
    return groups


def frontiers(groups):
    result = []
    for profile in PROFILES:
        for algorithm in ALGORITHMS:
            for policy in POLICIES:
                for cohort in COHORTS:
                    samples = []
                    for budget in BUDGETS:
                        key = '/'.join(map(str, (profile, cohort, algorithm, policy, budget)))
                        group = groups[key]
                        samples.append(dict(budget=budget, used=group['used'], acquired=group['acquired'],
                                            retained_directions=group['directions'], empty_steps=group['empty'],
                                            exhausted_steps=group['domain_exhausted'],
                                            budget_reached_steps=group['budget_reached']))
                    result.append(dict(profile=profile, algorithm=algorithm, policy=policy, cohort=cohort,
                                       samples=samples))
    return result


def run(paths, records):
    verifier = build_verifier()
    fingerprint = hashlib.sha256(verifier.read_bytes()).hexdigest()
    complete, native_checks, oracle_cache = [], 0, {}
    # Independent full-domain audits are outside the cooperative campaign model.
    for values in PROFILES:
        p = Profile(*values)
        seed = hashlib.sha256(label_for(p, 'fresh', 0).encode('ascii')).digest()
        matrix = expand_matrix(p, seed)
        for algorithm in ALGORITHMS:
            expected = oracle(p, matrix, algorithm)
            meter = ComponentMeter(1000000)
            source = Acquisition(p, matrix, algorithm, meter)
            results = list(source.solutions())
            if source.reason != 'domain-exhausted' or set(results) != expected or len(results) != len(expected):
                raise RuntimeError('complete acquisition oracle mismatch')
            native_verdicts(verifier, [encode_case(p, matrix, v) for v in results], [1]*len(results))
            native_checks += len(results)
            complete.append(dict(profile=values, algorithm=algorithm, solutions=len(results), meter=meter.report()))
    for values in PROFILES:
        p = Profile(*values)
        for budget in BUDGETS:
            for algorithm in ALGORITHMS:
                for policy in POLICIES:
                    for cohort in COHORTS:
                        pool = []
                        for index in range(STEPS):
                            label = label_for(p, cohort, index)
                            seed = hashlib.sha256(label.encode('ascii')).digest()
                            output = step(p, seed, algorithm, policy, pool, budget=budget)
                            output.update(profile=values, cohort=cohort, step=index, budget=budget,
                                          label=label, seed_hex=seed.hex())
                            audit_record(p, output)
                            key = (values, label, algorithm)
                            if key not in oracle_cache:
                                oracle_cache[key] = oracle(p, output['matrix'], algorithm)
                            expected = oracle_cache[key]
                            if not set(output['acquired']) <= expected:
                                raise RuntimeError('capped acquisition outside oracle domain')
                            if output['domain_exhausted'] and set(output['acquired']) != expected:
                                raise RuntimeError('fabricated full-domain completion')
                            vectors = [x['vector'] for x in output['carry']]+output['acquired']
                            flags = [int(x['valid']) for x in output['carry']]+[1]*len(output['acquired'])
                            native_verdicts(verifier, [encode_case(p, output['matrix'], v) for v in vectors], flags)
                            native_checks += len(vectors)
                            records.append(output)
                            pool = output['retained']
    definition = dict(version=MODEL_VERSION, default_weight=1, zero_weight=ZERO_WEIGHT,
                      excluded_engine_counters=['table_buckets'])
    config = dict(profiles=PROFILES, budgets=BUDGETS, algorithms=ALGORITHMS, policies=POLICIES,
                  cohorts=COHORTS, steps=STEPS, label_seed=LABEL_SEED, pool_limit=8, proof_limit=64,
                  model=definition,
                  model_sha256=hashlib.sha256(json.dumps(definition, sort_keys=True).encode()).hexdigest())
    raw = dict(status='passed', version=VERSION, configuration=config, source_sha256=paths[2],
               verifier_sha256=fingerprint, complete_audits=complete, records=records)
    raw_digest = hashlib.sha256((json.dumps(raw, indent=2)+'\n').encode('utf-8')).hexdigest()
    groups = summarize(records)
    report = dict(version=VERSION, configuration=config, planned_steps=576, completed_steps=len(records),
                  complete_oracle_audits=len(complete), groups=groups, budget_frontiers=frontiers(groups),
                  independent_native_verdicts=native_checks, raw_artifact_sha256=raw_digest,
                  maximum_overshoot=max(r['meter']['overshoot'] for r in records),
                  limitations=['arbitrary equal-weight logical component model, not work pricing',
                    'cooperative limits with recorded excess; no hard resource isolation',
                    'different algorithm domains/orders and correlated pool observations',
                    'fixed continued acquisition after full retention; no adaptive saving claim',
                    'report-only/native/oracle bookkeeping outside the model; no hardware speed ratio'])
    finish_report(paths, report, paths[2], raw=raw, executable=verifier, expected_executable_sha256=fingerprint)


def main():
    paths, records = begin_report(VERSION), []
    try:
        run(paths, records)
    except Exception as error:
        failed = dict(status='failed', version=VERSION, detail=str(error), source_sha256=paths[2],
                      completed_steps=len(records), in_progress_work=None)
        paths[1].write_text(json.dumps(dict(**failed, incomplete_records=records), indent=2)+'\n', encoding='utf-8')
        paths[0].write_text(json.dumps(failed, indent=2)+'\n', encoding='utf-8')
        raise


if __name__ == '__main__':
    main()
