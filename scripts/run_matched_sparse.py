"""Reproducible local matched builds; no services, dependencies or paid compute."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.consensus_evidence import begin_report, source_hashes
from scripts.matched_sparse_survey import failure_report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--nvcc', type=Path, default=Path('/usr/local/cuda/bin/nvcc'))
    parser.add_argument('--arch', default='sm_75')
    args = parser.parse_args()
    paths = begin_report('matched-sparse-v1')
    begin = time.perf_counter_ns()
    try:
        build = subprocess.run(['cargo', 'build', '--release', '--offline', '--locked',
                                '--bin', 'sis-column', '--bin', 'sis-verify', '--message-format=json'],
                               cwd=ROOT, capture_output=True, timeout=180, check=True)
        sys.stderr.write(build.stderr.decode())
        entries = [json.loads(line) for line in build.stdout.splitlines()]
        executables = {}
        for name in ('sis-column', 'sis-verify'):
            selected = [entry['executable'] for entry in entries
                        if entry.get('reason') == 'compiler-artifact' and entry.get('executable')
                        and entry['target']['name'] == name and 'bin' in entry['target']['kind']]
            if len(selected) != 1: raise RuntimeError('ambiguous Cargo executable: '+name)
            executables[name] = selected[0]
        native_hashes = {Path(path).name: hashlib.sha256(Path(path).read_bytes()).hexdigest()
                         for path in executables.values()}
        subprocess.run([sys.executable, str(ROOT/'scripts/build_fused.py'), '--nvcc', str(args.nvcc),
                        '--arch', args.arch, '--kernel', 'matched_sparse'], cwd=ROOT, timeout=240, check=True)
        if paths[2] != source_hashes(): raise RuntimeError('sources changed during matched builds')
        if any(hashlib.sha256(Path(path).read_bytes()).hexdigest() != native_hashes[Path(path).name]
               for path in executables.values()):
            raise RuntimeError('native binary changed during CUDA build')
        snapshot = ROOT/'artifacts/matched-build-sources.json'
        cuda_artifacts = [ROOT/'artifacts/matched_sparse.so', ROOT/'artifacts/matched_sparse.build.json']
        snapshot.write_text(json.dumps(dict(source_sha256=paths[2],
            binaries_sha256={**native_hashes, **{p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                                for p in cuda_artifacts}}), indent=2)+'\n')
    except Exception as error:
        failure_report(paths, error, [], paths[2], begin)
        raise
    try:
        subprocess.run([sys.executable, str(ROOT/'scripts/matched_sparse_survey.py'),
                        '--native', executables['sis-column'], '--verifier', executables['sis-verify'],
                        '--library', str(ROOT/'artifacts/matched_sparse.so'),
                        '--build-metadata', str(ROOT/'artifacts/matched_sparse.build.json'),
                        '--build-sources', str(snapshot)], cwd=ROOT, timeout=180, check=True)
    except Exception as error:
        # Preserve child diagnostics if it reached its own failure handler. A
        # timed-out/killed child has unknown progress, not zero successful work.
        if json.loads(paths[0].read_text()).get('status') != 'failed':
            failure_report(paths, error, None, paths[2], begin)
        raise


if __name__ == '__main__':
    main()
