"""Independent Python/native bounded sparse differential and malformed framing."""

import random
import itertools
import struct
import subprocess

from reference.column_search import search
from reference.native_columns import encode_request, search_many
from reference.sis import Profile


def differential_columns(executable):
    rng = random.Random(2026100911)
    requests = []
    for _ in range(300):
        p = Profile(rng.choice([2, 3, 7, 257, 65521]), rng.randint(1, 8), rng.randint(1, 20), rng.choice([1, 2, 3]))
        matrix = [[rng.randrange(p.q) for _ in range(p.m)] for _ in range(p.n)]
        if rng.randrange(3) == 0:
            matrix = [[0]*p.m for _ in range(p.n)]
        settings = dict(candidate_limit=rng.choice([1, 3, p.m, p.m*p.m, 16384]),
                        proof_limit=rng.choice([1, 3, 256]), batch_size=rng.choice([1, 7, 256, 4096]))
        requests.append((p, matrix, settings))
    for b2 in (1, 2, 65521**2-1):
        requests.append((Profile(65521, 64, 128, b2), [[0]*128 for _ in range(64)],
                         dict(candidate_limit=16384, proof_limit=256, batch_size=4096)))
    for q in (2, 3):
        p = Profile(q, 1, 3, 2)
        for row in itertools.product(range(q), repeat=3):
            for cap, proofs, width in ((9, 256, 2), (5, 1, 4)):
                requests.append((p, [row], dict(candidate_limit=cap, proof_limit=proofs, batch_size=width)))
    checked = 0
    for offset in range(0, len(requests), 128):
        group = requests[offset:offset+128]
        outputs, _ = search_many(executable, group)
        for (p, matrix, settings), native in zip(group, outputs):
            expected = search(p, matrix, backend='python-columns', **settings)
            for key in ('domain', 'reason', 'domain_exhausted', 'all_proofs_returned', 'proofs'):
                if native[key] != expected[key]:
                    raise RuntimeError('native columns differ: '+key)
            for key, value in expected['work'].items():
                if native['work'][key] != value:
                    raise RuntimeError('native columns ledger differs: '+key)
            checked += native['work']['screened']
    packet = encode_request(Profile(7, 1, 2, 2), [[0, 0]])
    bad = [b'\x01', struct.pack('<I', 32801), struct.pack('<I', 31)+b'x'*31,
           struct.pack('<I', len(packet))+packet[:-1]]
    mutations = []
    for pos, size, value in [(0, 1, 0), (4, 4, 4), (8, 2, 0), (10, 2, 129), (12, 8, 0),
                             (20, 4, 0), (24, 4, 0), (28, 4, 0), (32, 4, 7)]:
        changed = bytearray(packet)
        changed[pos:pos+size] = value.to_bytes(size, 'little')
        mutations.append(bytes(changed))
    mutations.append(packet+b'x')
    bad.extend(struct.pack('<I', len(p))+p for p in mutations)
    for wire in bad:
        result = subprocess.run([str(executable)], input=wire, capture_output=True, timeout=5)
        if result.returncode == 0:
            raise RuntimeError('native columns accepted malformed framing/request')
    empty = subprocess.run([str(executable)], input=b'', capture_output=True, timeout=5, check=True)
    if empty.stdout or empty.stderr:
        raise RuntimeError('native columns empty stream')
    return dict(seed=2026100911, cases=len(requests), screened=checked, malformed_rejections=len(bad), mismatches=0)
