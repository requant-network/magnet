"""Durable bounded progress journal, outside measurements, for interrupted studies."""

import json
import os

VERSION = 'matched-coefficients-v1'
MAX_BYTES, MAX_EVENTS = 96*1024*1024, 5000


class Journal:
    def __init__(self, path, manifest):
        self.path = path
        with path.open('w', encoding='utf-8', newline='\n') as stream:
            stream.write(json.dumps(dict(kind='header', version=VERSION, source_sha256=manifest))+'\n')
            stream.flush()
            os.fsync(stream.fileno())

    def event(self, value):
        with self.path.open('a', encoding='utf-8', newline='\n') as stream:
            stream.write(json.dumps(value)+'\n')
            stream.flush()
            os.fsync(stream.fileno())


def recover(path, manifest):
    if path.stat().st_size > MAX_BYTES:
        raise RuntimeError('coefficient journal exceeds bound')
    lines = path.read_bytes().splitlines(keepends=True)
    if not lines or len(lines) > MAX_EVENTS:
        raise RuntimeError('coefficient journal event bound')
    header = json.loads(lines[0])
    if header != dict(kind='header', version=VERSION, source_sha256=manifest):
        raise RuntimeError('stale coefficient journal')
    records, by_key, current = [], {}, dict(stage='journal-start', unknown_work=True)
    for line in lines[1:]:
        if not line.endswith(b'\n'):
            # The interrupted final append is unknown work, not a completed event.
            current = dict(stage='journal-partial-append', unknown_work=True)
            break
        event = json.loads(line)
        kind = event['kind']
        if kind == 'pair':
            record = event['record']
            key = (record['case'], record['repetition'])
            if (key in by_key or type(key[0]) is not int or not 0 <= key[0] < 240
                    or type(key[1]) is not int or not 0 <= key[1] < 3 or record['outputs'] != {}):
                raise RuntimeError('invalid coefficient journal pair')
            records.append(record)
            by_key[key] = record
        elif kind == 'output':
            key = (event['case'], event['repetition'])
            backend = event['backend']
            if key not in by_key or backend not in ('native-cpu', 'fused-gpu') or backend in by_key[key]['outputs']:
                raise RuntimeError('invalid coefficient journal output')
            by_key[key]['outputs'][backend] = event['output']
            current = dict(stage='after-search-before-audit', case=key[0], repetition=key[1], backend=backend, unknown_work=True)
        elif kind == 'pending':
            current = event['current']
        elif kind == 'paired':
            current = dict(stage='after-pair', unknown_work=True)
        else:
            raise RuntimeError('unknown coefficient journal event')
    return records, current
