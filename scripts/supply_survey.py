"""Exact pool correlations and separate paid, fresh-header correctness cohorts."""

from dataclasses import replace
from fractions import Fraction
import hashlib
from itertools import product
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from reference.admission_wire import scored_request
from reference.grinding import SCORE_DOMAIN, score_digest
from reference.header import ExpectedContext, LabHeader, encode_proof
from reference.sis import Profile, verify
from reference.supply_model import independent_hit_shortcut, pool_law, score_hit_probability, validate_pool
from scripts.consensus_evidence import begin_report, finish_report
from scripts.lab_driver import build_lab, exchange, matrix_bytes, request
from scripts.native_driver import WORK_NAMES, build_native, encode_request, run_requests

SEEDS = (2026100901, 2026100902)
TARGETS = (0, 2**252, 2**255, 2**256)
PROFILES = (Profile(7, 1, 3, 8), Profile(17, 2, 8, 8), Profile(257, 3, 14, 12))
HEADERS = 256


def ratio(value):
    return {'numerator': value.numerator, 'denominator': value.denominator}


def digest(label):
    return hashlib.sha256(label.encode('ascii')).digest()


def exact_case(profile, pool):
    pool = validate_pool(profile, pool)
    cells = profile.n*profile.m
    if profile.q**cells > 100_000:
        raise ValueError('complete matrix space cap')
    observed = [0]*(len(pool)+1)
    for flat in product(range(profile.q), repeat=cells):
        matrix = tuple(flat[i*profile.m:(i+1)*profile.m] for i in range(profile.n))
        observed[sum(verify(profile, matrix, vector) for vector in pool)] += 1
    law = pool_law(profile, pool)
    if tuple(Fraction(c, profile.q**cells) for c in observed) != law.histogram:
        raise RuntimeError('exact matrix distribution disagreement')
    return {'profile': [profile.q, profile.n, profile.m, profile.b2], 'pool': pool,
            'matrices': profile.q**cells, 'histogram_counts': observed,
            'exact_histogram': [ratio(p) for p in law.histogram],
            'rank_arithmetic_units': law.rank_arithmetic_units, 'mismatches': 0}


def acquire_pool(executable, lab, profile, label):
    work = dict(headers=0, matrix_entries=0, validation_checks=0)
    native_work = dict.fromkeys(WORK_NAMES, 0)
    records = []
    audits = 0
    for nonce in range(16):
        header = LabHeader(digest(label+'/network'), digest(label+'/setup-parent'),
                           digest(label+'/setup-payload'), 1, 100, nonce, profile)
        matrix = header.matrix()
        work['headers'] += 1
        work['matrix_entries'] += profile.n*profile.m
        response, = run_requests(executable, [encode_request(profile, matrix, 'mitm-budgeted',
                                   nodes=250_000, table=10_000, pairs=250_000, proofs=6)], timeout=30)
        for name in native_work:
            native_work[name] += response['work'][name]
        work['validation_checks'] += len(response['proofs'])
        if len(set(response['proofs'])) != len(response['proofs']) or any(
                not verify(profile, matrix, vector) for vector in response['proofs']):
            raise RuntimeError('invalid setup acquisition')
        context = ExpectedContext(header.network, header.parent, header.height, profile)
        commands = [request(2, header.encode())] + [scored_request(
            context, 2**256, encode_proof(header, vector)) for vector in response['proofs']]
        expected = [header.seed()+matrix_bytes(matrix)] + [b'\x01']*len(response['proofs'])
        if exchange(lab, commands) != expected:
            raise RuntimeError('independent setup generation/validity disagreement')
        audits += len(commands)
        records.append({'header_hex': header.encode().hex(), 'stop': response['stop'],
                        'native_work': response['work'], 'proofs': response['proofs']})
        if response['proofs']:
            return tuple(response['proofs']), {'work': work, 'native_work': native_work,
                                              'kind': 'paid-native-acquisition', 'status': 'pool-acquired',
                                              'native_audit_requests': audits, 'records': records}
    return (), {'work': work, 'native_work': native_work, 'kind': 'paid-native-acquisition',
                'status': 'nonce-cap-no-vector', 'native_audit_requests': audits, 'records': records}


def fresh_headers(profile, label, axis):
    base = LabHeader(digest(label+'/network'), digest(label+'/'+axis+'/fresh-parent'),
                     digest(label+'/'+axis+'/fresh-payload'), 2, 200, 0, profile)
    if axis == 'nonce':
        return tuple(replace(base, nonce=i) for i in range(HEADERS))
    if axis == 'parent':
        return tuple(replace(base, parent=digest(label+'/parent/'+str(i)), height=2+i) for i in range(HEADERS))
    if axis == 'payload':
        return tuple(replace(base, payload=digest(label+'/payload/'+str(i))) for i in range(HEADERS))
    raise ValueError('unknown fresh axis')


def measure_headers(executable, profile, pool, headers, *, targets=TARGETS):
    pool = validate_pool(profile, pool)
    law = pool_law(profile, pool)
    for target in targets:
        score_hit_probability(law.histogram, target)
    if type(headers) not in (list, tuple) or not 1 <= len(headers) <= HEADERS or any(
            not isinstance(h, LabHeader) or h.profile != profile for h in headers):
        raise ValueError('fresh header cohort bound/type')
    if len({h.encode() for h in headers}) != len(headers):
        raise ValueError('duplicate header occurrence')
    counts = [0]*(len(pool)+1)
    wins = [0]*len(targets)
    work = dict(headers=0, matrix_entries=0, vector_checks=0, scores=0, score_bytes=0)
    raw, matrices, transcript = [], set(), hashlib.sha256()
    commands, expected = [], []
    audits = 0

    def flush():
        nonlocal audits
        if exchange(executable, commands) != expected:
            raise RuntimeError('independent generation/validity/score disagreement')
        audits += len(commands)
        commands.clear()
        expected.clear()

    for index, header in enumerate(headers):
        matrix = header.matrix()
        fingerprint = hashlib.sha256(matrix_bytes(matrix)).hexdigest()
        matrices.add(fingerprint)
        transcript.update(header.encode())
        work['headers'] += 1
        work['matrix_entries'] += profile.n*profile.m
        commands.append(request(2, header.encode()))
        expected.append(header.seed()+matrix_bytes(matrix))
        context = ExpectedContext(header.network, header.parent, header.height, profile)
        valid, scores, hits = [], [], [False]*len(targets)
        for vector in pool:
            packet = encode_proof(header, vector)
            accepted = verify(profile, matrix, vector)
            work['vector_checks'] += 1
            commands.append(scored_request(context, 2**256, packet))
            expected.append(bytes([accepted]))
            if not accepted:
                continue
            valid.append(vector)
            score = score_digest(header, vector)
            work['scores'] += 1
            work['score_bytes'] += len(SCORE_DOMAIN)+len(packet)
            commands.append(request(4, SCORE_DOMAIN+packet))
            expected.append(score)
            for i, target in enumerate(targets):
                hit = int.from_bytes(score, 'big') < target
                hits[i] |= hit
                commands.append(scored_request(context, target, packet))
                expected.append(bytes([hit]))
            scores.append(score.hex())
        counts[len(valid)] += 1
        wins = [w+int(h) for w, h in zip(wins, hits)]
        raw.append({'header_hex': header.encode().hex(), 'matrix_sha256': fingerprint,
                    'valid_vectors': valid, 'digests': scores, 'hits': hits})
        if (index+1) % 32 == 0:
            flush()
    if commands:
        flush()
    return {'headers': len(headers), 'unique_headers': len(headers), 'unique_matrices': len(matrices),
            'header_transcript_sha256': transcript.hexdigest(), 'pool_size': len(pool),
            'pool': pool, 'valid_count_histogram': counts, 'work': work,
            'native_audit_requests': audits, 'mismatches': 0,
            'law': {'histogram': [ratio(p) for p in law.histogram], 'subset_ranks': law.subset_ranks,
                    'rank_arithmetic_units': law.rank_arithmetic_units},
            'targets': [{'target': str(t), 'observed_header_hits': w,
                         'conditional_iid_model_probability': ratio(score_hit_probability(law.histogram, t)),
                         'independent_vector_shortcut': ratio(independent_hit_shortcut(profile, len(pool), t))}
                        for t, w in zip(targets, wins)]}, raw


def main():
    paths = begin_report('precommitted-supply-v1')
    lab, native = build_lab(), build_native(release=True)
    exact = []
    for q, n in ((2, 1), (3, 1), (3, 2), (5, 1), (5, 2), (7, 1)):
        p = Profile(q, n, 2, min(q*q-1, 8))
        pools = [((1, 0),), ((1, 0), (0, 1)), ((1, 0), (0, 1), (1, 1))]
        if q > 2:
            pools += [((1, 0), (2, 0)), ((1, -1), (1, 1))]
        exact.extend(exact_case(p, pool) for pool in pools)
    setups, cohorts, raw = [], [], []
    for profile in PROFILES:
        for seed in SEEDS:
            for kind in (('acquired', 'proportional', 'triangle') if profile == PROFILES[0] else ('acquired',)):
                label = f'supply-v1/{profile.q}/{profile.n}/{profile.m}/{seed}/{kind}'
                if kind == 'acquired':
                    pool, setup = acquire_pool(native, lab, profile, label)
                else:
                    pool = ((1, 0, 0), (2, 0, 0)) if kind == 'proportional' else ((1, 0, 0), (0, 1, 0), (1, 1, 0))
                    setup = {'kind': 'preselected-diagnostic-no-solver', 'records': [],
                             'status': 'pool-preselected', 'native_audit_requests': 0,
                             'work': dict(headers=0, matrix_entries=0, validation_checks=len(pool)),
                             'native_work': dict.fromkeys(WORK_NAMES, 0)}
                    validate_pool(profile, pool)
                setups.append({'label': label, 'pool': pool, **setup})
                print(f"Setup {label}: {setup['status']}; {len(pool)} vectors", flush=True)
                if not pool:
                    continue  # Preserve failed setup; do not invent an exact law for a nonexistent pool.
                for axis in ('nonce', 'parent', 'payload'):
                    measured, trace = measure_headers(lab, profile, pool, fresh_headers(profile, label, axis))
                    measured.update(setup_label=label, axis=axis,
                                    profile=[profile.q, profile.n, profile.m, profile.b2])
                    cohorts.append(measured)
                    raw.append({'setup_label': label, 'axis': axis, 'headers': trace})
    unique = {h['header_hex'] for cohort in raw for h in cohort['headers']}
    total = sum(c['headers'] for c in cohorts)
    if len(unique) != total:
        raise RuntimeError('fresh cohort overlap')
    report = {'version': 'precommitted-supply-v1', 'seeds': SEEDS,
              'configuration': {'headers_per_cohort': HEADERS, 'pool_cap': 6, 'setup_nonce_cap': 16,
                                'native_nodes_per_setup_attempt': 250_000, 'native_table_cap': 10_000,
                                'native_pairs_per_setup_attempt': 250_000, 'targets': [str(t) for t in TARGETS]},
              'exact_cases': exact, 'enumerated_matrices': sum(e['matrices'] for e in exact),
              'setups': [{k: v for k, v in s.items() if k != 'records'} for s in setups],
              'cohorts': cohorts, 'fresh_headers': total, 'global_unique_headers': len(unique),
              'planned_cohorts': 3*len(setups), 'completed_cohorts': len(cohorts),
              'skipped_cohorts_after_failed_setup': 3*sum(not s['pool'] for s in setups),
              'native_audit_requests': sum(c['native_audit_requests'] for c in cohorts)+sum(s['native_audit_requests'] for s in setups),
              'mismatches': 0, 'native_search_release_sha256': hashlib.sha256(native.read_bytes()).hexdigest(),
              'limitations': ['iid uniform matrices and conditional iid scores are explicit hypotheses',
                              'exact enumeration audits the model; finite real-header frequencies do not prove uniformity',
                              'pools held fixed after setup; no adaptive pool, free acquisition or global hardness claim',
                              'all setup attempts/returns paid once per pool, then shared by three fresh cohorts',
                              'failed capped setups retained; dependent cohorts explicitly skipped, no zero-cost successful denominator',
                              'full pool scanned/scored even after a hit; this is a correctness survey, not optimized mining',
                              'native generation/acceptance/scoring audits are outside paid scan component counts',
                              'MGH1 headers are real encodings, not MGB1 accepted chains or accepted block counts',
                              'exact model, process startup, host time and energy are not priced by scan counters',
                              'no production chainwork, retarget or high-dimensional parameters selected']}
    finish_report(paths, report, paths[2], raw={'setups': setups, 'cohorts': raw}, executable=lab)


if __name__ == '__main__':
    main()
