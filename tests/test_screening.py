"""Attack-control and interrupted-transaction regressions for D3."""

import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from reference.header import LabHeader
from reference.screening import POLICIES, DeadlineStop, campaign
from reference.sis import Profile
from scripts.screening_audits import audit_campaign
from scripts.screening_survey import LABELS, PROFILES, compare, header, logical_hash, main, verify_publication


class ScreeningTests(unittest.TestCase):
    def setUp(self):
        self.base = header((7, 1, 4, 8), 2026100926)
        self.caps = dict(budget=100000, header_limit=8, candidate_limit=100, probe_limit=16, target=2**254)

    def test_replication_headers_are_fresh_and_historical_defaults_are_stable(self):
        from scripts.screening_replication import LABELS as fresh_labels, NAME, PROFILES as fresh_profiles
        profile = fresh_profiles[0]
        fresh = {header(profile, label, namespace=NAME).encode() for label in fresh_labels}
        original = {header(profile, label).encode() for label in LABELS}
        self.assertEqual(len(fresh), 24)
        self.assertTrue(fresh.isdisjoint(original))
        self.assertEqual(hashlib.sha256(header(profile, 2026100926).encode()).hexdigest(),
                         'c3b4118c4c58977d73beee9a5612d7f1c88c1c4b55f46be074e4078cd1bb66a3')
        for label in fresh_labels:
            self.assertNotEqual(header(profile, label).encode(), header(profile, label, namespace=NAME).encode())

    def test_custom_schedule_keeps_config_counts_and_native_failure_is_not_a_pass(self):
        from scripts.consensus_evidence import source_hashes
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = (root/'compact.json', root/'raw.json')
            contract, binary = root/'contract.md', root/'lab.exe'
            contract.write_bytes(b'frozen')
            binary.write_bytes(b'fixture')
            options = dict(name='fresh-test', profiles=((7, 1, 4, 8),), labels=(1, 2),
                           repetitions=2, deadline_seconds=30, primary_profiles=((7, 1, 4, 8),))
            with patch('scripts.screening_survey.begin_report', return_value=(*paths, source_hashes())) as begin, \
                    patch('scripts.screening_survey.CONTRACT', contract), \
                    patch('scripts.screening_survey.CAPS', self.caps), \
                    patch('scripts.screening_survey.build_lab', return_value=binary), \
                    patch('scripts.screening_survey.audit_native', return_value={'fixture': True}):
                main(**options)
                begin.assert_called_once_with('fresh-test')
            saved = json.loads(paths[1].read_text())
            compact = json.loads(paths[0].read_text())
            self.assertEqual(compact['planned_campaigns'], 32)
            self.assertEqual(compact['completed_campaigns'], 32)
            self.assertTrue(all(c['primary'] for c in compact['comparisons']))
            self.assertEqual(saved['config']['primary_profiles'], [[7, 1, 4, 8]])
            for entry in saved['completed']:
                base = header(entry['profile'], entry['label'], namespace='fresh-test')
                audit_campaign(base, entry['record'], **self.caps)
            with patch('scripts.screening_survey.begin_report', return_value=(*paths, source_hashes())), \
                    patch('scripts.screening_survey.CONTRACT', contract), \
                    patch('scripts.screening_survey.CAPS', self.caps), \
                    patch('scripts.screening_survey.build_lab', return_value=binary), \
                    patch('scripts.screening_survey.audit_native', side_effect=RuntimeError('native mismatch')):
                with self.assertRaisesRegex(RuntimeError, 'native mismatch'):
                    main(**options)
            self.assertTrue(json.loads(paths[1].read_text())['comparisons_suppressed'])
            self.assertEqual(json.loads(paths[0].read_text())['status'], 'failed-or-incomplete')

    def test_all_policies_and_constructions_replay(self):
        for policy in POLICIES:
            for construction in ('A', 'B'):
                with self.subTest(policy=policy, construction=construction):
                    record = campaign(self.base, policy, construction, **self.caps)
                    audit_campaign(self.base, record, **self.caps)
                    audit_campaign(self.base, json.loads(json.dumps(record)), **self.caps)
                    self.assertEqual(logical_hash(record), logical_hash(campaign(self.base, policy, construction, **self.caps)))

    def test_b_continues_past_score_misses(self):
        record = campaign(self.base, 'plain', 'B', **{**self.caps, 'target': 1})
        self.assertEqual(record['successes'], 0)
        self.assertGreater(record['eligible'], 8)
        self.assertTrue(any(len(b['search']['eligible']) > 1 for b in record['trace']))
        audit_campaign(self.base, record, **{**self.caps, 'target': 1})

    def test_batch_probes_rejected_headers_and_selects_earliest_tie(self):
        for policy in ('random4', 'screened4'):
            record = campaign(self.base, policy, 'A', **self.caps)
            self.assertEqual(record['work']['phases']['probe']['checks'], 8*16)
            for batch in record['trace']:
                self.assertEqual(len(batch['headers']), 4)
                self.assertTrue(all(len(h['probe_flags']) == 16 for h in batch['headers']))
                if policy == 'screened4':
                    scores = [sum(h['probe_flags']) for h in batch['headers']]
                    self.assertEqual(batch['selected'], scores.index(max(scores)))

    def test_false_cached_rows_do_not_charge_remaining_rows(self):
        base = header((17, 3, 16, 12), 2026100926)
        caps = {**self.caps, 'header_limit': 1, 'candidate_limit': 16}
        record = campaign(base, 'probe-control', 'A', **caps)
        audit_campaign(base, record, **caps)
        flags = record['trace'][0]['headers'][0]['probe_flags']
        self.assertGreater(flags.count(0), 0)
        self.assertEqual(record['work']['phases']['search']['cache_reads'], record['trace'][0]['search']['checked'])

    def test_every_small_budget_stops_at_audited_transaction(self):
        for budget in (1, 130, 500, 750, 1000, 1800, 3500):
            for policy in POLICIES:
                caps = {**self.caps, 'budget': budget}
                record = campaign(self.base, policy, 'B', **caps)
                audit_campaign(self.base, record, **caps)

    def test_proof_hit_commits_before_budget_check(self):
        caps = {**self.caps, 'header_limit': 1, 'target': 2**256}
        first = campaign(self.base, 'plain', 'B', **caps)
        self.assertEqual(first['successes'], 1)
        stopped = campaign(self.base, 'plain', 'B', **{**caps, 'budget': first['work']['used']-1})
        self.assertEqual(stopped['successes'], 1)
        self.assertEqual(stopped['reason'], 'component-budget')
        self.assertEqual(stopped['stopping_stage'], 'proof-transaction')
        audit_campaign(self.base, stopped, **{**caps, 'budget': first['work']['used']-1})

    def test_ledger_and_proxy_tampering_rejected(self):
        record = campaign(self.base, 'screened4', 'B', **self.caps)
        for field in ('ledger', 'flag', 'selection', 'proof'):
            bad = copy.deepcopy(record)
            if field == 'ledger':
                bad['work']['used'] -= 1
            elif field == 'flag':
                bad['trace'][0]['headers'][0]['probe_flags'][0] ^= 1
            elif field == 'selection':
                bad['trace'][0]['selected'] = (bad['trace'][0]['selected']+1) % 4
            else:
                b = next(b for b in bad['trace'] if b['search']['eligible'])
                b['search']['eligible'][0]['proof_hex'] = '00'
            with self.assertRaises(RuntimeError):
                audit_campaign(self.base, bad, **self.caps)

    def test_deadline_keeps_owned_partial_trace_and_raises(self):
        trace = []
        with patch('reference.screening.time.monotonic', side_effect=[0, 0, 2]):
            with self.assertRaises(DeadlineStop):
                campaign(self.base, 'screened4', 'B', **self.caps, deadline=1, trace=trace)
        self.assertEqual(len(trace[0]['headers']), 1)
        self.assertEqual(len(trace[0]['headers'][0]['probe_flags']), 1)

    def test_invalid_caps_fail_before_matrix_derivation(self):
        with patch('reference.screening.expand_matrix', side_effect=AssertionError('unexpected generation')):
            for keyword, value in (('budget', True), ('header_limit', 257), ('candidate_limit', 4097), ('probe_limit', 65), ('target', 0), ('deadline', float('nan'))):
                with self.assertRaises(ValueError):
                    campaign(self.base, 'plain', 'A', **{**self.caps, keyword: value})
            too_late = LabHeader(self.base.network, self.base.parent, self.base.payload, 1, 1, 2**64-1, Profile(7, 1, 4, 8))
            with self.assertRaises(ValueError):
                campaign(too_late, 'plain', 'A', **self.caps)

    def test_diagnostic_strict_threshold_and_repetition_exclusion(self):
        def group(screened, repeats=1000):
            return [dict(repetition=r, record=dict(policy=p, successes=(screened if p == 'screened4' else 5) if r == 0 else repeats,
                work=dict(used=100))) for r in (0, 1, 2) for p in POLICIES]
        self.assertEqual(compare(group(10))['outcome'], 'not-triggered')
        self.assertEqual(compare(group(11))['outcome'], 'triggered')
        self.assertEqual(compare(group(4))['outcome'], 'insufficient-successes')
        self.assertEqual(compare(group(11)), compare(group(11, 0)))

    def test_build_failure_invalidates_previous_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = (root/'compact.json', root/'raw.json')
            contract = root/'contract.md'
            contract.write_text('frozen', encoding='utf-8')
            for path in paths:
                path.write_text('{"status":"passed"}', encoding='utf-8')
            with patch('scripts.screening_survey.begin_report', return_value=(*paths, {})), \
                    patch('scripts.screening_survey.CONTRACT', contract), \
                    patch('scripts.screening_survey.build_lab', side_effect=RuntimeError('build failure')):
                with self.assertRaises(RuntimeError):
                    main()
            for path in paths:
                self.assertEqual(json.loads(path.read_text())['status'], 'failed-or-incomplete')
            self.assertIsNone(json.loads(paths[1].read_text())['executable_sha256'])

    def test_keyboard_interrupt_retains_unknown_trace_and_native_digest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = (root/'compact.json', root/'raw.json')
            contract, binary = root/'contract.md', root/'lab.exe'
            contract.write_bytes(b'frozen')
            binary.write_bytes(b'native')

            def interrupt(*args, **kwargs):
                kwargs['trace'].append({'partially_completed': True})
                raise KeyboardInterrupt()

            with patch('scripts.screening_survey.begin_report', return_value=(*paths, {})), \
                    patch('scripts.screening_survey.CONTRACT', contract), \
                    patch('scripts.screening_survey.build_lab', return_value=binary), \
                    patch('scripts.screening_survey.campaign', side_effect=interrupt):
                with self.assertRaises(KeyboardInterrupt):
                    main()
            saved = json.loads(paths[1].read_text())
            self.assertTrue(saved['comparisons_suppressed'])
            self.assertEqual(saved['current']['execution'], 'unknown-unfinished')
            self.assertEqual(saved['current']['trace'], [{'partially_completed': True}])
            self.assertEqual(saved['executable_sha256'], hashlib.sha256(b'native').hexdigest())

    def test_publication_rejects_changed_raw_and_frozen_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = (root/'compact.json', root/'raw.json')
            contract, binary = root/'contract.md', root/'lab.exe'
            contract.write_bytes(b'frozen')
            binary.write_bytes(b'native')
            config = {'labels': LABELS, 'profiles': PROFILES, 'policies': POLICIES, 'primary_profiles': PROFILES[1:]}
            config_hash = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
            raw_bytes = json.dumps(dict(config=config, config_sha256=config_hash)).encode()
            report = dict(config=config, config_sha256=config_hash, raw_sha256=hashlib.sha256(raw_bytes).hexdigest(),
                source_sha256={}, executable_sha256=hashlib.sha256(b'native').hexdigest())
            paths[1].write_bytes(raw_bytes)
            paths[0].write_text(json.dumps(report), encoding='utf-8')
            contract_hash = hashlib.sha256(b'frozen').hexdigest()
            with patch('scripts.screening_survey.CONTRACT', contract), patch('scripts.screening_survey.source_hashes', return_value={}):
                verify_publication(paths, report, binary, contract_hash)
                paths[1].write_bytes(raw_bytes+b' ')
                with self.assertRaisesRegex(RuntimeError, 'raw digest'):
                    verify_publication(paths, report, binary, contract_hash)
                paths[1].write_bytes(raw_bytes)
                binary.write_bytes(b'changed')
                with self.assertRaisesRegex(RuntimeError, 'frozen inputs'):
                    verify_publication(paths, report, binary, contract_hash)


if __name__ == '__main__':
    unittest.main()
