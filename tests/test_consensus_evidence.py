import hashlib
import subprocess
import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from reference.forks import Transition
from scripts.resource_survey import probes
from scripts import consensus_evidence


class ConsensusEvidenceTests(unittest.TestCase):
    def test_binary_changed_during_metadata_collection_refuses_publication(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            binary = root/'native'
            binary.write_bytes(b'original')
            fingerprint = hashlib.sha256(binary.read_bytes()).hexdigest()
            paths = (root/'compact.json', root/'raw.json')
            for p in paths:
                p.write_text('{"status":"running-or-incomplete"}')
            def metadata(*args, **kwargs):
                binary.write_bytes(b'replacement')
                return 'rustc test'
            with patch.object(consensus_evidence, 'source_hashes', return_value={}), \
                    patch.object(consensus_evidence.subprocess, 'check_output', side_effect=metadata):
                with self.assertRaisesRegex(RuntimeError, 'binary changed'):
                    consensus_evidence.finish_report(paths, {}, {}, executable=binary,
                        expected_executable_sha256=fingerprint, build_profile='release')
            for p in paths:
                self.assertIn('running-or-incomplete', p.read_text())

    def test_source_freeze_covers_solver_implementations_and_optional_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ('Cargo.toml', 'Cargo.lock', 'benchmarks/flint-win.lock', 'solvers/portfolio.py'):
                path = root/name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('initial')
            with patch.object(consensus_evidence, 'ROOT', root):
                before = consensus_evidence.source_hashes()
                self.assertIn('solvers/portfolio.py', before)
                self.assertIn('benchmarks/flint-win.lock', before)
                (root/'solvers/portfolio.py').write_text('changed')
                self.assertNotEqual(before, consensus_evidence.source_hashes())

    def test_resource_probe_refuses_false_rate_evidence(self):
        with patch('scripts.resource_survey.ForkTree.submit',return_value=Transition('malformed')):
            with self.assertRaisesRegex(RuntimeError,'rate accounting'): probes()

    def test_optimized_python_keeps_resource_evidence_gates(self):
        code="from unittest.mock import patch\nfrom reference.forks import Transition\nfrom scripts.resource_survey import probes\nwith patch('scripts.resource_survey.ForkTree.submit',return_value=Transition('malformed')):\n probes()\n"
        r=subprocess.run([sys.executable,'-O','-c',code],capture_output=True,timeout=10)
        self.assertNotEqual(r.returncode,0)
        self.assertIn(b'RuntimeError: malformed decoding/rate accounting',r.stderr)


if __name__=='__main__': unittest.main()
