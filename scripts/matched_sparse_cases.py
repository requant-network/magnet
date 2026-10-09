"""Fixed seeded workloads; families share the same matrix and labelled caps."""

import hashlib
import random

from reference.sis import Profile, expand_matrix

ORDER_SEED = 2026100912
SEEDS = (2026100913, 2026100914)


def jobs():
    result = []
    for values in ((2, 1, 8, 3), (17, 2, 16, 3), (257, 3, 32, 3),
                   (65521, 4, 64, 3), (65521, 64, 128, 3)):
        for seed in SEEDS:
            label = 'matched-sparse-v1/'+'-'.join(map(str, values))+'/'+str(seed)
            for weight in (2, 3):
                for cap, proofs, width, group in ((65536, 256, 64, 'small-chunk'),
                                                  (65536, 256, 4096, 'large-chunk'),
                                                  (31, 3, 7, 'capped-prefix')):
                    result.append(dict(label=label, profile=dict(zip(('q', 'n', 'm', 'b2'), values)),
                                       seed_hex=hashlib.sha256(label.encode()).hexdigest(), fixture=None,
                                       max_weight=weight, candidate_limit=cap, proof_limit=proofs,
                                       batch_size=width, group=group))
    fixtures = (('zero', (7, 1, 3, 3)), ('triple-only', (17, 1, 3, 3)),
                ('identity', (17, 3, 3, 3)), ('zero', (7, 1, 8, 1)),
                ('one', (7, 1, 1, 3)), ('zero', (65521, 64, 128, 65521**2-1)))
    for fixture, values in fixtures:
        for weight in (2, 3):
            for cap, proofs, width in ((65536, 256, 4096), (13, 1, 7)):
                result.append(dict(label='fixture/'+fixture+'/'+'-'.join(map(str, values)),
                                   profile=dict(zip(('q', 'n', 'm', 'b2'), values)), seed_hex=None,
                                   fixture=fixture, max_weight=weight, candidate_limit=cap,
                                   proof_limit=proofs, batch_size=width, group='fixtures'))
    random.Random(ORDER_SEED).shuffle(result)
    return result


def matrix_for(job):
    p = Profile(**job['profile'])
    if job['fixture'] is None:
        return expand_matrix(p, bytes.fromhex(job['seed_hex']))
    if job['fixture'] == 'zero':
        return tuple((0,)*p.m for _ in range(p.n))
    if job['fixture'] == 'triple-only':
        return ((1, 2, 3),)
    return tuple(tuple(int(i == j) for j in range(p.m)) for i in range(p.n))
