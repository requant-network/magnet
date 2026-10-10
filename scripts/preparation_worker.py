"""Bounded D4 integration worker; only launched by the Windows Job driver."""

import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from reference.header import LabHeader
from reference.preparation_campaign import POLICIES, run_preparation
from scripts.window_worker import MAX_INPUT, publish
from solvers.portfolio import Portfolio


def decode(data):
    if type(data) is not bytes or len(data) > MAX_INPUT:
        raise ValueError('D4 input bounds')
    value = json.loads(data)
    if (type(value) is not dict or set(value) != {'version', 'headers', 'policy'}
            or value['version'] != 'WDP1' or value['policy'] not in POLICIES
            or type(value['headers']) is not list or not 1 <= len(value['headers']) <= 8):
        raise ValueError('D4 protocol')
    headers = []
    for wire in value['headers']:
        if type(wire) is not str or len(wire) != 280 or any(c not in '0123456789abcdef' for c in wire):
            raise ValueError('D4 header encoding')
        h = LabHeader.decode(bytes.fromhex(wire))
        if h.profile.m > 8 or h.profile.n > 2:
            raise ValueError('D4 profile bound')
        headers.append(h)
    return headers, value['policy']


def main():
    source, destination = map(Path, sys.argv[1:3])
    try:
        begin = time.perf_counter_ns()
        with source.open('rb') as stream:
            headers, policy = decode(stream.read(MAX_INPUT+1))
        solver = Portfolio('lll75', None, 2026101033)
        def checkpoint(result):
            publish(destination.with_name(f"checkpoint-{len(result['stages'])}.json"),
                    dict(status='checkpoint', campaign=result, backend=solver.metadata))
        campaign = run_preparation(headers, policy, solver, on_stage=checkpoint)
        publish(destination, dict(status='completed', campaign=campaign, backend=solver.metadata,
                                  setup_ns=solver.setup_ns, worker_elapsed_ns=time.perf_counter_ns()-begin))
    except MemoryError:
        publish(destination.with_name('error.json'), {'status': 'memory-error'})
        raise SystemExit(77)
    except Exception as error:
        publish(destination.with_name('error.json'), dict(status='worker-error', error_type=type(error).__name__, message=str(error)[:512]))
        raise SystemExit(78)


if __name__ == '__main__':
    main()
