"""Owned streaming adapters sharing cooperative component accounting."""

from dataclasses import asdict
import math

from reference.ball import BallSearch
from reference.mitm import MitmSearch
from reference.small_coefficients import candidates, dense, screen, templates

ALGORITHMS = ('sparse1', 'sparse2', 'ball', 'mitm')


class Acquisition:
    def __init__(self, profile, matrix, algorithm, meter):
        self.profile, self.matrix, self.algorithm, self.meter = profile, matrix, algorithm, meter
        self.reason, self.work, self.engine, self.iterator = 'not-started', {}, None, None
        if algorithm not in ALGORITHMS:
            raise ValueError('unknown acquisition algorithm')

    def sync(self):
        counts = asdict(self.engine.work) if self.engine else self.work
        counts = {k: v for k, v in counts.items() if k != 'table_buckets'}
        self.meter.sync('solver', counts)

    def checkpoint(self):
        self.sync()
        self.meter.check()

    def solutions(self):
        if self.reason != 'not-started':
            raise ValueError('one-shot acquisition')
        self.reason = 'running'
        try:
            self.meter.check()
            if self.algorithm.startswith('sparse'):
                patterns, setup = templates(self.profile, int(self.algorithm[-1]))
                self.meter.add('solver_setup', **setup)
                self.meter.check()
                self.work = dict(generated=0, screened=0, matrix_terms=0, row_reductions=0,
                                 emitted_proofs=0, vector_entries=0)
                domain = sum(math.comb(self.profile.m, w)*len(p) for w, p in patterns.items())
                for positions, values in candidates(self.profile.m, patterns):
                    self.checkpoint()
                    valid, terms, rows = screen(self.matrix, positions, values, self.profile.q)
                    self.work['generated'] += 1
                    self.work['screened'] += 1
                    self.work['matrix_terms'] += terms
                    self.work['row_reductions'] += rows
                    if self.work['screened'] == domain:
                        self.reason = 'domain-exhausted'
                    if valid:
                        vector = dense(self.profile.m, positions, values)
                        self.work['emitted_proofs'] += 1
                        self.work['vector_entries'] += self.profile.m
                        yield vector
                    self.checkpoint()
                self.reason = 'domain-exhausted'
            else:
                engine = BallSearch if self.algorithm == 'ball' else MitmSearch
                self.engine = engine(self.profile, self.matrix, checkpoint=self.checkpoint)
                self.meter.add('solver_setup', shape_entries=self.profile.n*self.profile.m+self.profile.m)
                self.meter.check()
                self.iterator = self.engine.solutions()
                yield from self.iterator
                self.reason = self.engine.reason
        finally:
            if self.iterator is not None:
                self.iterator.close()
            self.sync()
            if self.reason == 'running':
                self.reason = 'interrupted'
