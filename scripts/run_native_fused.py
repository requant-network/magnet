"""Invalidate evidence before builds; run only on an explicitly selected local CUDA host."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.consensus_evidence import begin_report, source_hashes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--nvcc', type=Path, default=Path('/usr/local/cuda/bin/nvcc'))
    parser.add_argument('--arch', default='sm_75')
    args = parser.parse_args()
    frozen = begin_report('native-fused-column-v1')[2]
    build = subprocess.run(['cargo', 'build', '--release', '--offline', '--locked',
                            '--bin', 'sis-column', '--bin', 'sis-verify', '--message-format=json'],
                           cwd=ROOT, capture_output=True, timeout=180, check=True)
    sys.stderr.write(build.stderr.decode())
    entries = [json.loads(line) for line in build.stdout.splitlines()]
    executables = {}
    for name in ('sis-column', 'sis-verify'):
        candidates = [entry['executable'] for entry in entries
                      if entry.get('reason') == 'compiler-artifact' and entry.get('executable')
                      and entry['target']['name'] == name and 'bin' in entry['target']['kind']]
        if len(candidates) != 1:
            raise RuntimeError('missing or ambiguous Cargo executable: '+name)
        executables[name] = candidates[0]
    subprocess.run([sys.executable, str(ROOT/'scripts/build_fused.py'), '--nvcc', str(args.nvcc),
                    '--arch', args.arch], cwd=ROOT, timeout=240, check=True)
    if frozen != source_hashes():
        raise RuntimeError('sources changed during native/fused builds')
    snapshot = ROOT/'artifacts/native-fused-build-sources.json'
    binary_paths = [Path(executables[name]) for name in ('sis-column', 'sis-verify')]
    binary_paths.extend([ROOT/'artifacts/unit_sparse.so', ROOT/'artifacts/unit_sparse.build.json'])
    snapshot.write_text(json.dumps(dict(source_sha256=frozen,
                                       binaries_sha256={path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                                                        for path in binary_paths}), indent=2)+'\n')
    subprocess.run([sys.executable, str(ROOT/'scripts/native_fused_survey.py'),
                    '--native', executables['sis-column'], '--verifier', executables['sis-verify'],
                    '--library', str(ROOT/'artifacts/unit_sparse.so'),
                    '--build-metadata', str(ROOT/'artifacts/unit_sparse.build.json'),
                    '--build-sources', str(snapshot)],
                   cwd=ROOT, timeout=180, check=True)


if __name__ == '__main__':
    main()
