"""New B-H fork: exact model, matched caps, nonvacuous evidence and failure paths."""

from copy import deepcopy
from dataclasses import replace
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from reference.header_gate import header_digest, passes, renewal_costs
from reference.preparation_campaign import run_preparation
from scripts import header_gate_survey as survey
from tests.test_kernel_reuse import ExactSolver


class HeaderGateTests(unittest.TestCase):
    def test_strict_gate_boundaries_and_nonce_binding(self):
        h = survey.headers((3, 1, 2, 2), survey.LABELS[0])[0]
        digest = int.from_bytes(header_digest(h), 'big')
        self.assertFalse(passes(h, 0))
        self.assertFalse(passes(h, digest))
        self.assertTrue(passes(h, digest+1))
        self.assertTrue(passes(h, 2**256))
        self.assertNotEqual(header_digest(h), header_digest(replace(h, nonce=h.nonce+1)))
        for target in (-1, True, 2**256+1):
            with self.assertRaises(ValueError):
                passes(h, target)

    def test_renewal_costs_and_nonfinite_cases(self):
        for success in (1, Fraction(1, 3)):
            for c in (0, 1, 10, 100):
                cold, gate = renewal_costs(2**254, success, 1, c)
                self.assertEqual(cold, Fraction(4*(1+c))/success)
                self.assertEqual(gate, Fraction(4+c)/success)
                if c >= 1:
                    self.assertGreaterEqual(cold/gate, Fraction(8, 5))
                self.assertEqual(*renewal_costs(2**256, success, 1, c))
        # Equal illustrative costs at p1/4 give an exact ratio of 8/5.
        self.assertEqual(renewal_costs(2**254, 1, 1, 1), (8, 5))
        for args in ((0, 1, 1, 1), (2**254, 0, 1, 1), (2**254, True, 1, 1),
                     (2**254, Fraction(1, 2**257), 1, 1), (2**254, 1, 0, 1)):
            with self.assertRaises(ValueError):
                renewal_costs(*args)

    def pair(self, target=None, *, no_proofs=False):
        stream = survey.headers((3, 1, 2, 2), survey.LABELS[0])
        if target is None:
            # Unit-test fixture guarantees both passing and rejected cases.
            # The frozen integration target and schedule remain unchanged.
            target = sorted(int.from_bytes(header_digest(h), 'big') for h in stream)[2]+1
        entries = []
        for policy in survey.POLICIES:
            plan = survey.gate_plan(stream, policy, target)
            attempted = [stream[i] for i in plan['attempted_indices']]
            window = None
            if attempted:
                record = run_preparation(attempted, 'cold', ExactSolver())
                if no_proofs:
                    for stage in record['stages']:
                        stage['proofs'] = ()
                window = dict(outcome='completed', snapshot={'campaign': record})
            entries.append(dict(plan=plan, window=window))
        return entries

    def test_renewal_law_matches_complete_cycle_costs_with_correlated_success_cost(self):
        # Four equally likely gate outcomes; three equally likely SIS outcomes.
        # Success costs8, failure costs2, so s1/3 and mean C4 despite correlation.
        successful, control_cost, gate_cost = 0, 0, 0
        for gate_outcome in range(4):
            for sis_outcome in range(3):
                passed, solved = gate_outcome == 0, sis_outcome == 0
                c = 8 if solved else 2
                successful += passed and solved
                control_cost += 1+c
                gate_cost += 1+(c if passed else 0)
        # Renewal equation E[total]=E[cycle cost]/P(cycle success).
        self.assertEqual((Fraction(control_cost, successful), Fraction(gate_cost, successful)),
                         renewal_costs(2**254, Fraction(1, 3), 1, 4))

    def test_selected_outputs_match_and_empty_is_never_a_success(self):
        pair = self.pair()
        result = survey.compare_pair(*pair, primary=True)
        self.assertGreater(result['common_admitted_proofs'], 0)
        self.assertGreater(result['rejected_headers'], 0)
        self.assertEqual(result['outcome'], 'observed-bypass')
        self.assertEqual(survey.compare_pair(*self.pair(0), primary=True)['outcome'], 'structural-only')
        self.assertEqual(survey.compare_pair(*self.pair(2**256), primary=True)['outcome'], 'structural-only')
        self.assertEqual(survey.compare_pair(*self.pair(no_proofs=True), primary=True)['outcome'], 'structural-only')
        bad = deepcopy(pair)
        bad[1]['window']['snapshot']['campaign']['stages'][0]['search_work']['nodes'] += 1
        with self.assertRaises(ValueError):
            survey.compare_pair(*bad, primary=True)

    def test_caps_context_and_namespace_are_frozen(self):
        stream = survey.headers((17, 2, 8, 8), survey.LABELS[0])
        self.assertEqual(len(stream)*2000, 10000)
        for bad in (stream+[replace(stream[0], nonce=10)], [stream[0]]*2,
                    [stream[0], replace(stream[1], parent=bytes(32))]):
            with self.assertRaises(ValueError):
                survey.gate_plan(bad, 'gate-first')
        from scripts.preparation_survey import headers as old_headers
        self.assertTrue({h.encode() for h in stream}.isdisjoint(h.encode() for h in old_headers((17, 2, 8, 8), 2026101031)))

    def test_failed_build_and_interrupted_worker_keep_frozen_failure_evidence(self):
        for interrupt in (False, True):
            with tempfile.TemporaryDirectory() as directory:
                dest, raw, contract, binary = [Path(directory)/s for s in ('report.json', 'raw.json', 'contract.md', 'lab.exe')]
                dest.write_text('{"status":"passed"}')
                raw.write_text('{"status":"passed"}')
                contract.write_bytes(b'contract')
                binary.write_bytes(b'binary')
                error = KeyboardInterrupt() if interrupt else RuntimeError('build failure')
                error.window_evidence = dict(resource=None, snapshot={'paid_prefix': 1}, artifact_directory='artifacts/window-owned')
                def native(executable, messages):
                    return [hashlib.sha256(message[5:]).digest() for message in messages]
                with patch.object(survey, 'begin_report', return_value=(dest, raw, {})), \
                        patch.object(survey, 'CONTRACT', contract), \
                        patch.object(survey, 'build_lab', return_value=binary if interrupt else None,
                                     side_effect=None if interrupt else error), \
                        patch.object(survey, 'exchange', side_effect=native), \
                        patch.object(survey, 'run_window', side_effect=error):
                    with self.assertRaises(KeyboardInterrupt if interrupt else RuntimeError):
                        survey.main()
                value = json.loads(raw.read_bytes())
                self.assertTrue(value['comparisons_suppressed'])
                self.assertEqual(json.loads(dest.read_bytes())['status'], 'failed-or-incomplete')
                if interrupt:
                    self.assertEqual(value['current']['window'], error.window_evidence)
                    self.assertEqual(value['executable_sha256'], hashlib.sha256(binary.read_bytes()).hexdigest())
                else:
                    self.assertIsNone(value['executable_sha256'])


if __name__ == '__main__':
    unittest.main()
