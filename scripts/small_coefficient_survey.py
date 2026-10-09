"""Frozen small-coefficient cohorts and fixed paid matrix-refresh campaigns."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from reference.sis import Profile, encode_case, expand_matrix, verify
from reference.small_coefficients import candidates, dense, direction, refresh, search, templates
from scripts.consensus_evidence import begin_report, finish_report
from scripts.small_coefficient_audits import max_shape_audits, native_verdicts, tiny_audits

VERSION = 'small-coefficient-v1'
PROFILES = ((7, 1, 5, 8), (17, 2, 12, 12), (257, 2, 16, 12), (65521, 3, 16, 12))
STEPS = 6
LABEL_SEED = 2026100915


def build_verifier():
    built = subprocess.run(['cargo', 'build', '--offline', '--locked', '--bin', 'sis-verify',
                            '--message-format=json'], cwd=ROOT, capture_output=True, timeout=180, check=True)
    entries = [json.loads(line) for line in built.stdout.splitlines()]
    selected = [item['executable'] for item in entries if item.get('reason') == 'compiler-artifact'
                and item.get('executable') and item['target']['name'] == 'sis-verify'
                and 'bin' in item['target']['kind']]
    if len(selected) != 1:
        raise RuntimeError('ambiguous current verifier artifact')
    return Path(selected[0])


def matrix_at(profile, cohort, step):
    label = '/'.join(map(str, (VERSION, LABEL_SEED, profile.q, profile.n, profile.m, profile.b2,
                              0 if cohort == 'same-instance-control' else step)))
    seed = hashlib.sha256(label.encode('ascii')).digest()
    return seed, expand_matrix(profile, seed)


def tested_vectors(profile, bound, count):
    import itertools
    patterns, _ = templates(profile, bound)
    return [dense(profile.m, pos, values) for pos, values in
            itertools.islice(candidates(profile.m, patterns), count)]


def run(paths, records):
    verifier = build_verifier()
    fingerprint = hashlib.sha256(verifier.read_bytes()).hexdigest()
    audits = tiny_audits(verifier)
    maximum = max_shape_audits(verifier)
    native_checks = audits['native_candidate_verdicts']+maximum['native_candidate_verdicts']
    complete_cases = []
    for values in PROFILES:
        profile = Profile(*values)
        for cohort in ('fresh-matrix', 'same-instance-control'):
            pools = {1: [], 2: []}
            for step in range(STEPS):
                seed, matrix = matrix_at(profile, cohort, step)
                outputs = {}
                for bound in (1, 2):
                    acquisition = search(profile, matrix, bound=bound, candidate_limit=4096, proof_limit=32)
                    previous = pools[bound]
                    transition = refresh(profile, matrix, previous, acquisition['proofs'])
                    vectors = previous+acquisition['proofs']
                    expected = [int(x) for x in transition['carry_verdicts']]+[1]*len(acquisition['proofs'])
                    native_verdicts(verifier, [encode_case(profile, matrix, v) for v in vectors], expected)
                    native_checks += len(vectors)
                    pools[bound] = transition['retained']
                    outputs[str(bound)] = dict(acquisition=acquisition, transition=transition)
                tested = {b: set(tested_vectors(profile, b, outputs[str(b)]['acquisition']['work']['screened']))
                          for b in (1, 2)}
                shared = tested[1] & tested[2]
                shared_hits = sum(verify(profile, matrix, v) for v in shared)
                record = dict(profile=values, cohort=cohort, step=step, seed_hex=seed.hex(),
                              matrix=matrix, matrix_sha256=hashlib.sha256(json.dumps(matrix).encode()).hexdigest(),
                              preparation=dict(matrix_entries_generated=profile.n*profile.m, seed_hashes=1),
                              outputs=outputs,
                              prefix_intersection=dict(candidates=len(shared), accepted=shared_hits,
                                                       bound1_only=len(tested[1]-shared), bound2_only=len(tested[2]-shared)))
                records.append(record)
                # Only this tiny profile supplies a full cross-family availability comparison.
                if profile.m == 5 and cohort == 'fresh-matrix':
                    complete = {b: search(profile, matrix, bound=b, proof_limit=256) for b in (1, 2)}
                    if not all(result['domain_exhausted'] for result in complete.values()):
                        raise RuntimeError('complete cohort censored')
                    one, two = [set(complete[b]['proofs']) for b in (1, 2)]
                    if not one <= two:
                        raise RuntimeError('complete unit family missing from bound2')
                    vectors = list(one | two)
                    native_verdicts(verifier, [encode_case(profile, matrix, v) for v in vectors], [1]*len(vectors))
                    native_checks += len(vectors)
                    complete_cases.append(dict(step=step, outputs={str(b): complete[b] for b in (1, 2)},
                        additional_vectors=len(two-one), additional_directions=len({direction(v) for v in two})-
                            len({direction(v) for v in one})))
    groups = {}
    for record in records:
        label = str(record['profile'])+'/'+record['cohort']
        group = groups.setdefault(label, {})
        for bound, output in record['outputs'].items():
            a, t = output['acquisition'], output['transition']
            total = group.setdefault(bound, dict(searches=0, screened=0, acquired=0, carry_checks=0,
                carried=0, new_directions=0, retained=0, retained_directions=0, censored_searches=0))
            for key, value in dict(searches=1, screened=a['work']['screened'], acquired=len(a['proofs']),
                carry_checks=t['work']['carry_checks'], carried=len(t['carried']),
                new_directions=t['new_directions'], retained=len(t['retained']),
                retained_directions=t['directions']['retained'], censored_searches=int(not a['domain_exhausted'])).items():
                total[key] += value
    raw = dict(status='passed', version=VERSION, source_sha256=paths[2], verifier_sha256=fingerprint,
               records=records, complete_cases=complete_cases)
    raw_bytes = (json.dumps(raw, indent=2)+'\n').encode('utf-8')
    report = dict(version=VERSION, records=len(records), acquisition_searches=2*len(records),
        configuration=dict(profiles=PROFILES, steps=STEPS, label_seed=LABEL_SEED, candidate_limit=4096,
                           proof_limit=32, pool_limit=32, cohorts=['fresh-matrix', 'same-instance-control']),
        groups=groups, tiny_audits=audits, maximum_shape_audit=maximum,
        independent_native_verdicts=native_checks,
        complete_cohort=dict(cases=len(complete_cases), additional_vectors=sum(x['additional_vectors'] for x in complete_cases),
                             additional_directions=sum(x['additional_directions'] for x in complete_cases)),
        fresh_matrix_digests=len({r['matrix_sha256'] for r in records if r['cohort'] == 'fresh-matrix'}),
        raw_artifact_sha256=hashlib.sha256(raw_bytes).hexdigest(),
        limitations=['fixed refresh pays acquisition every step; no adaptive saving claim',
                     'scalar copies share kernel direction and modular events',
                     'capped coefficient families have different biased prefixes',
                     'same-instance controls and sequential pool observations are correlated',
                     'operation counts, not calibrated consensus work or isolated timings'])
    finish_report(paths, report, paths[2], raw=raw, executable=verifier, expected_executable_sha256=fingerprint)


def main():
    paths = begin_report(VERSION)
    records = []
    try:
        run(paths, records)
    except Exception as error:
        failed = dict(status='failed', version=VERSION, stage='build-audit-or-campaign', detail=str(error),
                      source_sha256=paths[2], completed_records=len(records), in_progress_work=None)
        paths[1].write_text(json.dumps(dict(**failed, incomplete_records=records), indent=2)+'\n', encoding='utf-8')
        paths[0].write_text(json.dumps(failed, indent=2)+'\n', encoding='utf-8')
        raise


if __name__ == '__main__':
    main()
