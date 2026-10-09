"""Frozen release-native comparisons and paid fresh/control refresh cohorts."""

import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from reference.native_coefficients import search_many
from reference.sis import Profile, encode_case, expand_matrix
from reference.small_coefficients import refresh, search
from scripts.consensus_evidence import begin_report, finish_report
from scripts.native_coefficient_checks import differential_coefficients
from scripts.small_coefficient_audits import native_verdicts

VERSION = 'native-small-coefficients-v1'
PROFILES = ((7, 1, 5, 8), (17, 2, 12, 12), (257, 2, 16, 12), (65521, 64, 16, 12))
SETTINGS = ((1, 1), (31, 3), (4096, 32), (20000, 256))
COMPARISON_SEEDS = (2026100917, 2026100918)
REFRESH_SEEDS = (2026100919, 2026100920, 2026100921)
REPETITIONS, STEPS = 3, 4


def build_engines():
    built = subprocess.run(['cargo', 'build', '--release', '--offline', '--locked', '--bin', 'sis-coeff',
                            '--bin', 'sis-verify', '--message-format=json'], cwd=ROOT,
                           capture_output=True, timeout=180, check=True)
    entries = [json.loads(line) for line in built.stdout.splitlines()]
    engines = {}
    for name in ('sis-coeff', 'sis-verify'):
        matches = [entry['executable'] for entry in entries if entry.get('reason') == 'compiler-artifact'
                   and entry.get('executable') and entry['target']['name'] == name
                   and 'bin' in entry['target']['kind']]
        if len(matches) != 1:
            raise RuntimeError('ambiguous current Cargo artifact: '+name)
        engines[name] = Path(matches[0])
    return engines


def matrix_at(profile, label_seed, cohort, step):
    # Controls use exactly the fresh step-zero instance, not a different label.
    label = '/'.join(map(str, (VERSION, 'fresh-matrix' if cohort == 'same-instance-control' else cohort,
                              profile.q, profile.n, profile.m, profile.b2, label_seed,
                              0 if cohort == 'same-instance-control' else step)))
    seed = hashlib.sha256(label.encode('ascii')).digest()
    return seed, expand_matrix(profile, seed)


def comparison_cases():
    cases, labels = [], []
    bases = []
    for values in PROFILES:
        p = Profile(*values)
        for label_seed in COMPARISON_SEEDS:
            seed, matrix = matrix_at(p, label_seed, 'comparison', 0)
            bases.append((p, matrix, dict(kind='seeded', seed_hex=seed.hex(), label_seed=label_seed)))
    bases.extend((p, matrix, dict(kind='fixture', fixture=name)) for name, p, matrix in (
        ('zero', Profile(7, 1, 5, 8), [[0]*5]),
        ('triple-only', Profile(17, 1, 3, 3), [[1, 3, 13]]),
        ('nonunit-only', Profile(17, 1, 2, 5), [[1, 2]]),
        ('scalar-copy', Profile(17, 1, 3, 8), [[1, 1, 3]]),
        ('singleton', Profile(17, 1, 1, 4), [[0]])))
    for p, matrix, label in bases:
        for bound in (1, 2):
            for cap, proofs in SETTINGS:
                cases.append((p, matrix, dict(bound=bound, candidate_limit=cap, proof_limit=proofs)))
                labels.append(dict(**label, profile=(p.q, p.n, p.m, p.b2)))
    return cases, labels


def timing_summary(values):
    if not values or any(type(x) is not int or x <= 0 for x in values):
        raise RuntimeError('nonpositive or missing timing sample')
    return dict(samples=len(values), minimum_ns=min(values), median_ns=statistics.median(values),
                maximum_ns=max(values))


def run(paths, state):
    engines = build_engines()
    fingerprints = {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in engines.items()}
    audit = differential_coefficients(engines['sis-coeff'])
    print('Independent differential and late-witness audits passed', flush=True)
    cases, labels = comparison_cases()
    native_checks, roundtrips = 0, []
    for repetition in range(REPETITIONS):
        state['current'] = dict(stage='comparison', repetition=repetition, unknown_work=True)
        reference_results, python_times = [], []
        for p, matrix, settings in cases:
            start = time.perf_counter_ns()
            result = search(p, matrix, **settings)
            python_times.append(time.perf_counter_ns()-start)
            reference_results.append(result)
        outputs, wall_ns = search_many(engines['sis-coeff'], cases)
        roundtrips.append(wall_ns)
        for index, ((p, matrix, settings), output, expected, python_ns) in enumerate(
                zip(cases, outputs, reference_results, python_times)):
            if output['result'] != expected:
                raise RuntimeError('timed native/reference mismatch')
            timing_summary([python_ns, output['elapsed_ns']])
            if repetition == 0:
                vectors = output['result']['proofs']
                native_verdicts(engines['sis-verify'], [encode_case(p, matrix, v) for v in vectors], [1]*len(vectors))
                native_checks += len(vectors)
            state['comparisons'].append(dict(case=index, repetition=repetition, label=labels[index],
                settings=settings, matrix=matrix, result=output['result'], python_ns=python_ns,
                native_ns=output['elapsed_ns']))
        state['current'] = None
        print(f'Comparison repetition {repetition+1}/{REPETITIONS} passed ({len(cases)} cases)', flush=True)
    for values in PROFILES:
        p = Profile(*values)
        for label_seed in REFRESH_SEEDS:
            for cohort in ('fresh-matrix', 'same-instance-control'):
                pools = {1: [], 2: []}
                for step in range(STEPS):
                    state['current'] = dict(stage='refresh', profile=values, label_seed=label_seed,
                                            cohort=cohort, step=step, unknown_work=True)
                    seed, matrix = matrix_at(p, label_seed, cohort, step)
                    batch = [(p, matrix, dict(bound=b, candidate_limit=4096, proof_limit=32)) for b in (1, 2)]
                    outputs, _ = search_many(engines['sis-coeff'], batch)
                    for bound, output in zip((1, 2), outputs):
                        acquisition = output['result']
                        previous = pools[bound]
                        transition = refresh(p, matrix, previous, acquisition['proofs'])
                        vectors = previous+acquisition['proofs']
                        verdicts = list(map(int, transition['carry_verdicts']))+[1]*len(acquisition['proofs'])
                        native_verdicts(engines['sis-verify'], [encode_case(p, matrix, v) for v in vectors], verdicts)
                        native_checks += len(vectors)
                        pools[bound] = transition['retained']
                        state['refresh'].append(dict(profile=values, label_seed=label_seed, cohort=cohort,
                            step=step, bound=bound, seed_hex=seed.hex(), matrix=matrix,
                            matrix_sha256=hashlib.sha256(json.dumps(matrix).encode('utf-8')).hexdigest(),
                            preparation=dict(matrix_entries_generated=p.n*p.m, seed_hashes=1),
                            acquisition=acquisition, transition=transition))
                    state['current'] = None
    groups = {}
    for record in state['refresh']:
        label = '/'.join(map(str, (record['profile'], record['cohort'], record['bound'])))
        group = groups.setdefault(label, dict(searches=0, acquired=0, carry_checks=0, carried=0,
            new_directions=0, retained=0, retained_directions=0, censored_searches=0))
        a, t = record['acquisition'], record['transition']
        for key, value in dict(searches=1, acquired=len(a['proofs']), carry_checks=t['work']['carry_checks'],
            carried=len(t['carried']), new_directions=t['new_directions'], retained=len(t['retained']),
            retained_directions=t['directions']['retained'], censored_searches=int(not a['domain_exhausted'])).items():
            group[key] += value
    timings = []
    for index, label in enumerate(labels):
        records = [r for r in state['comparisons'] if r['case'] == index]
        timings.append(dict(case=index, label=label, settings=cases[index][2],
                            python=timing_summary([r['python_ns'] for r in records]),
                            native=timing_summary([r['native_ns'] for r in records])))
    raw = dict(status='passed', version=VERSION, source_sha256=paths[2], binary_sha256=fingerprints,
               comparisons=state['comparisons'], refresh=state['refresh'], batch_roundtrip_ns=roundtrips)
    report = dict(version=VERSION, audit=audit, timed_comparisons=len(state['comparisons']),
        distinct_comparison_cases=len(cases), refresh_acquisitions=len(state['refresh']),
        independent_native_verdicts=native_checks, groups=groups, timings=timings,
        binary_sha256=fingerprints, batch_roundtrip=timing_summary(roundtrips),
        configuration=dict(profiles=PROFILES, comparison_seeds=COMPARISON_SEEDS, refresh_seeds=REFRESH_SEEDS,
            settings=SETTINGS, bounds=[1, 2], repetitions=REPETITIONS, steps=STEPS, refresh_candidate_cap=4096,
            refresh_proof_cap=32, pool_cap=32),
        scopes=dict(native='after frame read; validation/copy, templates, search and census; before response encoding',
                    python='validation, templates, search and result assembly',
                    roundtrip='one fresh process for 104 requests, pipe I/O and wait; encode/decode/audits excluded'),
        raw_artifact_sha256=hashlib.sha256((json.dumps(raw, indent=2)+'\n').encode('utf-8')).hexdigest(),
        limitations=['separate timing scopes; no mixed-scope ratio or portable winner',
            'host semantic audit re-runs Python search outside the roundtrip timing; adapter is not an acceleration claim',
            'tiny support<=3 family, not complete SIS; capped prefixes censor availability',
            'scalar copies and sequential pools are correlated; controls repeat fresh step zero',
            'refresh always pays acquisition; no adaptive saving or consensus pricing claim'])
    finish_report(paths, report, paths[2], raw=raw, executable=engines['sis-coeff'],
                  expected_executable_sha256=fingerprints['sis-coeff'], build_profile='release',
                  expected_artifacts={engines[name]: digest for name, digest in fingerprints.items()})


def main():
    paths = begin_report(VERSION)
    state = dict(comparisons=[], refresh=[], current=dict(stage='build-or-audit', unknown_work=True))
    try:
        run(paths, state)
    except Exception as error:
        failed = dict(status='failed', version=VERSION, detail=str(error), source_sha256=paths[2],
                      completed_comparisons=len(state['comparisons']), completed_refresh=len(state['refresh']),
                      in_progress_work=state['current'])
        paths[1].write_text(json.dumps(dict(**failed, incomplete_records=state), indent=2)+'\n',
                            encoding='utf-8', newline='\n')
        paths[0].write_text(json.dumps(failed, indent=2)+'\n', encoding='utf-8', newline='\n')
        raise


if __name__ == '__main__':
    main()
