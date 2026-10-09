"""Shared deterministic evidence lifecycle for the explicitly invoked consensus studies."""

import hashlib
import json
from pathlib import Path
import platform
import subprocess

ROOT=Path(__file__).resolve().parents[1]


def source_hashes():
    paths=[ROOT/'Cargo.toml',ROOT/'Cargo.lock',ROOT/'benchmarks/flint-win.lock']
    for folder,pattern in (("reference","*.py"),("solvers","*.py"),("scripts","*.py"),("crates","*.rs"),("tests","*.py"),
                           ("tests/vectors","*.json"),("spec","*.md"),("cuda","*.cu")):
        paths.extend((ROOT/folder).rglob(pattern))
    return {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}


def begin_report(name):
    destination=ROOT/'docs/research/results'/f'{name}.json'
    raw=ROOT/'artifacts'/f'{name}.json'
    raw.parent.mkdir(exist_ok=True)
    for p in (destination,raw): p.write_text('{"status":"running-or-incomplete"}\n',encoding='utf-8',newline='\n')
    return destination,raw,source_hashes()


def finish_report(paths,report,manifest,*,raw=None,executable=None,
                  expected_executable_sha256=None,build_profile='debug',expected_artifacts=None):
    if manifest!=source_hashes(): raise RuntimeError("sources changed during consensus study")
    report.update(status='passed',source_sha256=manifest,source_unchanged=True,
                  python=platform.python_version(),platform=platform.platform(),
                  rustc=subprocess.check_output(['rustc','--version'],text=True,timeout=5).strip())
    if expected_executable_sha256 is not None and executable is None:
        raise ValueError('expected binary hash requires executable')
    if executable:
        fingerprint=hashlib.sha256(executable.read_bytes()).hexdigest()
        if expected_executable_sha256 is not None and fingerprint!=expected_executable_sha256:
            raise RuntimeError('native binary changed before evidence publication')
        report['executable_sha256']=fingerprint
        report['native_build_profile']=build_profile
    report['timing_scope']='deterministic correctness/hypothesis experiment, not isolated hardware performance'
    if manifest!=source_hashes(): raise RuntimeError('sources changed before evidence publication')
    for artifact, fingerprint in (expected_artifacts or {}).items():
        if hashlib.sha256(Path(artifact).read_bytes()).hexdigest()!=fingerprint:
            raise RuntimeError('experiment artifact changed before evidence publication')
    paths[1].write_text(json.dumps(raw if raw is not None else report,indent=2)+'\n',encoding='utf-8',newline='\n')
    paths[0].write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(f"Evidence saved: {paths[0].name}",flush=True)
