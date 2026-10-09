"""Explicit local nvcc build with frozen source/compiler/binary metadata."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--nvcc', type=Path, default=Path('/usr/local/cuda/bin/nvcc'))
    parser.add_argument('--arch', default='sm_75')
    parser.add_argument('--kernel', choices=('unit_sparse', 'matched_sparse'), default='unit_sparse')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if not re.fullmatch(r'sm_[0-9]{2,3}', args.arch):
        raise ValueError('expected explicit CUDA architecture')
    source = ROOT/'cuda'/f'{args.kernel}.cu'
    fingerprint = digest(source)
    compiler = args.nvcc.resolve(strict=True)
    compiler_hash = digest(compiler)
    output = (args.output or ROOT/'artifacts'/f'{args.kernel}.so').resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    metadata = output.with_suffix('.build.json')
    metadata.write_text('{"status":"running-or-incomplete"}\n')
    with tempfile.TemporaryDirectory(dir=output.parent) as directory:
        library = Path(directory)/f'{args.kernel}.so'
        command = [str(compiler), '-O3', '--shared', '--cudart=static', '-Xcompiler=-fPIC',
                   '-arch='+args.arch, str(source), '-o', str(library)]
        version = subprocess.check_output([str(compiler), '--version'], text=True, timeout=10).strip()
        begin = time.perf_counter_ns()
        subprocess.run(command, check=True, timeout=180)
        elapsed = time.perf_counter_ns()-begin
        if fingerprint != digest(source) or compiler_hash != digest(compiler):
            raise RuntimeError('CUDA build inputs changed')
        library_hash = digest(library)
        os.replace(library, output)
    metadata.write_text(json.dumps(dict(status='passed', compiler=version, compiler_sha256=compiler_hash,
                                        arguments=['-O3', '--shared', '--cudart=static', '-Xcompiler=-fPIC',
                                                   '-arch='+args.arch, source.relative_to(ROOT).as_posix()],
                                        build_elapsed_ns=elapsed, source_sha256=fingerprint,
                                        library_sha256=library_hash), indent=2)+'\n')
    print('Built fused CUDA research library and metadata', flush=True)


if __name__ == '__main__':
    main()
