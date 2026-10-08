"""Shared deterministic evidence lifecycle for the explicitly invoked consensus studies."""

import hashlib
import json
from pathlib import Path
import platform
import subprocess

ROOT=Path(__file__).resolve().parents[1]


def source_hashes():
    paths=[ROOT/'Cargo.toml',ROOT/'Cargo.lock']
    for folder,pattern in (("reference","*.py"),("scripts","*.py"),("crates","*.rs"),("tests","*.py"),
                           ("tests/vectors","*.json"),("spec","*.md")):
        paths.extend((ROOT/folder).rglob(pattern))
    return {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}


def begin_report(name):
    destination=ROOT/'docs/research/results'/f'{name}.json'
    raw=ROOT/'artifacts'/f'{name}.json'
    raw.parent.mkdir(exist_ok=True)
    for p in (destination,raw): p.write_text('{"status":"running-or-incomplete"}\n',encoding='utf-8',newline='\n')
    return destination,raw,source_hashes()


def finish_report(paths,report,manifest,*,raw=None,executable=None):
    if manifest!=source_hashes(): raise RuntimeError("sources changed during consensus study")
    report.update(status='passed',source_sha256=manifest,source_unchanged=True,
                  python=platform.python_version(),platform=platform.platform(),
                  rustc=subprocess.check_output(['rustc','--version'],text=True,timeout=5).strip())
    if executable:
        report['executable_sha256']=hashlib.sha256(executable.read_bytes()).hexdigest()
        report['native_build_profile']='debug'
    report['timing_scope']='deterministic correctness/hypothesis experiment, not isolated hardware performance'
    paths[1].write_text(json.dumps(raw if raw is not None else report,indent=2)+'\n',encoding='utf-8',newline='\n')
    paths[0].write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(f"Evidence saved: {paths[0].name}",flush=True)
