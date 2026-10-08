"""Strict WAX1 experiment worker; reuse WXP1 validation and bounded campaign."""

import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from reference.adaptive_retention import FutureSupplyRetainer, MAX_DECISIONS
from reference.pool_campaign import run_pool_campaign
from scripts.portfolio_worker import decode as decode_portfolio
from scripts.window_worker import MAX_INPUT, publish
from solvers.portfolio import Portfolio


def decode(data):
    if type(data) is not bytes or len(data) > MAX_INPUT:
        raise ValueError('adaptive input bound/type')
    query = json.loads(data)
    fields = {'version', 'backend', 'policy', 'target', 'stages', 'capacity', 'combine', 'budget', 'seed',
              'retention', 'decisions'}
    if type(query) is not dict or set(query) != fields or query['version'] != 'WAX1':
        raise ValueError('adaptive fields/version')
    if (query['retention'] not in ('fifo', 'future-supply') or type(query['decisions']) is not int
            or not 1 <= query['decisions'] <= MAX_DECISIONS or type(query['capacity']) is not int
            or not 1 <= query['capacity'] <= 3):
        raise ValueError('adaptive retention bounds')
    normalized = {key: value for key, value in query.items() if key not in ('retention', 'decisions')}
    normalized['version'] = 'WXP1'
    _, stages, budget = decode_portfolio(json.dumps(normalized).encode())
    return query, stages, budget


def main():
    source, destination = map(Path, sys.argv[1:3])
    try:
        begin = time.perf_counter_ns()
        with source.open('rb') as stream:
            query, stages, budget = decode(stream.read(MAX_INPUT+1))
        solver = Portfolio(query['backend'], ROOT/'target/release/sis-search.exe', query['seed'])
        retain = FutureSupplyRetainer(int(query['target']), decisions=query['decisions']) if query['retention'] == 'future-supply' else None

        def snapshot(campaign, status):
            return {'status': status, 'campaign': campaign, 'backend': solver.metadata,
                    'setup_ns': solver.setup_ns, 'worker_elapsed_ns': time.perf_counter_ns()-begin,
                    'retention': retain.snapshot() if retain else None}

        def checkpoint(campaign):
            publish(destination.parent/f"checkpoint-{len(campaign['stages'])}.json", snapshot(campaign, 'checkpoint'))

        campaign = run_pool_campaign(stages, query['policy'], int(query['target']), solver,
                                     capacity=query['capacity'], combine=query['combine'], budget=budget,
                                     on_stage=checkpoint, retain=retain)
        publish(destination, snapshot(campaign, 'completed'))
    except MemoryError:
        publish(destination.parent/'error.json', {'status': 'memory-error'})
        raise SystemExit(77)
    except Exception as error:
        publish(destination.parent/'error.json', {'status': 'worker-error',
                                                'error_type': type(error).__name__, 'message': str(error)[:512]})
        raise SystemExit(78)


if __name__ == '__main__':
    main()
