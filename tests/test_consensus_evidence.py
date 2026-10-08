import subprocess
import sys
import unittest
from unittest.mock import patch

from reference.forks import Transition
from scripts.resource_survey import probes


class ConsensusEvidenceTests(unittest.TestCase):
    def test_resource_probe_refuses_false_rate_evidence(self):
        with patch('scripts.resource_survey.ForkTree.submit',return_value=Transition('malformed')):
            with self.assertRaisesRegex(RuntimeError,'rate accounting'): probes()

    def test_optimized_python_keeps_resource_evidence_gates(self):
        code="from unittest.mock import patch\nfrom reference.forks import Transition\nfrom scripts.resource_survey import probes\nwith patch('scripts.resource_survey.ForkTree.submit',return_value=Transition('malformed')):\n probes()\n"
        r=subprocess.run([sys.executable,'-O','-c',code],capture_output=True,timeout=10)
        self.assertNotEqual(r.returncode,0)
        self.assertIn(b'RuntimeError: malformed decoding/rate accounting',r.stderr)


if __name__=='__main__': unittest.main()
