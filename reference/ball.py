"""Exact incremental enumeration of sign-canonical vectors inside the norm ball."""

from dataclasses import dataclass
import math

from reference.mitm import _SearchIterator
from reference.sis import Profile, _check_shape

MAX_PREFIX_NODES = 1_000_000


@dataclass
class BallWork:
    prefix_nodes: int = 0
    norm_terms: int = 0
    matrix_terms: int = 0
    row_reductions: int = 0
    leaves: int = 0
    emitted_proofs: int = 0


class BallSearch:
    def __init__(self, profile, matrix, *, node_limit=MAX_PREFIX_NODES, checkpoint=None):
        if not isinstance(profile, Profile):
            raise ValueError("expected Profile")
        _check_shape(profile, matrix, [0] * profile.m)
        if type(node_limit) is not int or not 1 <= node_limit <= MAX_PREFIX_NODES:
            raise ValueError("node limit outside laboratory budget")
        if checkpoint is not None and not callable(checkpoint):
            raise ValueError("checkpoint must be callable")
        self.profile = profile
        self.matrix = tuple(tuple(row) for row in matrix)
        self.node_limit, self.checkpoint = node_limit, checkpoint
        self.work = BallWork()
        self.reason = "not-started"

    def solutions(self):
        if self.reason != "not-started":
            raise ValueError("search can only be consumed once")
        self.reason = "running"
        return _SearchIterator(self, self._enumerate())

    def _walk(self, column, remaining, nonzero, residues, vector):
        if column == self.profile.m:
            self.work.leaves += 1
            if nonzero and not any(residues):
                self.work.emitted_proofs += 1
                yield tuple(vector)
            return
        radius = math.isqrt(remaining)
        # Before the first nonzero coordinate, only zero/positive values are canonical.
        for value in range(-radius if nonzero else 0, radius + 1):
            if self.checkpoint is not None:
                self.checkpoint()
            if self.work.prefix_nodes == self.node_limit:
                self.reason = "node-limit"
                return
            self.work.prefix_nodes += 1
            self.work.norm_terms += 1
            vector[column] = value
            next_residues = tuple((r + row[column] * value) % self.profile.q
                                  for r, row in zip(residues, self.matrix))
            self.work.matrix_terms += self.profile.n
            self.work.row_reductions += self.profile.n
            yield from self._walk(column + 1, remaining - value * value,
                                  nonzero or value != 0, next_residues, vector)
            if self.reason == "node-limit":
                return

    def _enumerate(self):
        try:
            yield from self._walk(0, self.profile.b2, False, (0,) * self.profile.n,
                                  [0] * self.profile.m)
            if self.reason == "running":
                self.reason = "domain-exhausted"
        finally:
            if self.reason == "running":
                self.reason = "interrupted"
