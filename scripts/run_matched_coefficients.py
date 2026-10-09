"""Explicit local release/CUDA builds with pre-build source/artifact freezing."""

import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.consensus_evidence import begin_report, source_hashes
from scripts.matched_coefficient_survey import VERSION, failure_report, fingerprint
from scripts.coefficient_journal import Journal, recover


def interrupted_failure(paths, error):
    try:
        records, current = recover(paths[1].with_suffix('.progress.jsonl'), paths[2])
    except (OSError, ValueError, KeyError, RuntimeError) as journal_error:
        records, current = None, dict(stage='child-interrupted', journal_detail=str(journal_error), unknown_work=True)
    failure_report(paths, error, records, paths[2], current)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--nvcc', type=Path, default=Path('/usr/local/cuda/bin/nvcc'))
    parser.add_argument('--arch', default='sm_75')
    args = parser.parse_args()
    paths = begin_report(VERSION)
    # Clear same-source prior progress before builds/child launch, not only in child.
    Journal(paths[1].with_suffix('.progress.jsonl'), paths[2])
    try:
        build = subprocess.run(['cargo', 'build', '--release', '--offline', '--locked', '--bin', 'sis-coeff',
                                '--bin', 'sis-verify', '--message-format=json'], cwd=ROOT,
                               capture_output=True, timeout=180, check=True)
        entries = [json.loads(line) for line in build.stdout.splitlines()]
        engines = {}
        for name in ('sis-coeff', 'sis-verify'):
            selected = [e['executable'] for e in entries if e.get('reason') == 'compiler-artifact'
                        and e.get('executable') and e['target']['name'] == name and 'bin' in e['target']['kind']]
            if len(selected) != 1:
                raise RuntimeError('ambiguous release coefficient artifact: '+name)
            engines[name] = Path(selected[0])
        hashes = {path: fingerprint(path) for path in engines.values()}
        subprocess.run([sys.executable, str(ROOT/'scripts/build_fused.py'), '--nvcc', str(args.nvcc),
                        '--arch', args.arch, '--kernel', 'matched_coefficients'], cwd=ROOT, timeout=240, check=True)
        if paths[2] != source_hashes() or any(fingerprint(p) != h for p, h in hashes.items()):
            raise RuntimeError('coefficient build inputs/artifacts changed')
        library = ROOT/'artifacts/matched_coefficients.so'
        metadata = ROOT/'artifacts/matched_coefficients.build.json'
        snapshot = ROOT/'artifacts/matched-coefficients-build-sources.json'
        snapshot.write_text(json.dumps(dict(source_sha256=paths[2], binaries_sha256={
            **{p.name: h for p, h in hashes.items()}, library.name: fingerprint(library), metadata.name: fingerprint(metadata)}),
            indent=2)+'\n', encoding='utf-8', newline='\n')
    except Exception as error:
        failure_report(paths, error, [], paths[2], dict(stage='build', unknown_work=True))
        raise
    try:
        subprocess.run([sys.executable, str(ROOT/'scripts/matched_coefficient_survey.py'),
            '--native', str(engines['sis-coeff']), '--verifier', str(engines['sis-verify']), '--library', str(library),
            '--build-metadata', str(metadata), '--build-sources', str(snapshot)], cwd=ROOT, timeout=240, check=True)
    except Exception as error:
        if json.loads(paths[0].read_text()).get('status') != 'failed':
            interrupted_failure(paths, error)
        raise


if __name__ == '__main__':
    main()
