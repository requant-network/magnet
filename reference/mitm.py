"""Exact bounded meet-in-the-middle baseline for the existing SIS predicate."""

from dataclasses import asdict, dataclass
import hashlib
import itertools
import math

from reference.sis import Profile, _check_shape, expand_matrix
from reference.strategies import _score_message

MAX_HALF_BOX = 100_000
MAX_TABLE_ENTRIES = 100_000
MAX_JOIN_PAIRS = 1_000_000


@dataclass
class MitmWork:
    left_proposals: int = 0
    right_proposals: int = 0
    norm_terms: int = 0
    sign_terms: int = 0
    matrix_terms: int = 0
    row_reductions: int = 0
    table_entries: int = 0
    table_buckets: int = 0
    lookups: int = 0
    join_pairs: int = 0
    emitted_proofs: int = 0


class _SearchIterator:
    """Record explicit closure even when the generator has not started."""

    def __init__(self, search, iterator):
        self.search, self.iterator = search, iterator

    def __iter__(self):
        return self

    def __next__(self):
        return next(self.iterator)

    def close(self):
        self.iterator.close()
        if self.search.reason == "running":
            self.search.reason = "interrupted"


class MitmSearch:
    """One-shot search; an interrupted/capped run is not a nonexistence proof."""

    def __init__(self, profile, matrix, *, table_limit=MAX_TABLE_ENTRIES, pair_limit=MAX_JOIN_PAIRS):
        if not isinstance(profile, Profile):
            raise ValueError("expected Profile")
        _check_shape(profile, matrix, [0] * profile.m)
        for value, maximum in ((table_limit, MAX_TABLE_ENTRIES), (pair_limit, MAX_JOIN_PAIRS)):
            if type(value) is not int or not 1 <= value <= maximum:
                raise ValueError("limit outside laboratory budget")
        self.split = profile.m // 2
        self.radius = math.isqrt(profile.b2)
        if any((2 * self.radius + 1)**width > MAX_HALF_BOX
               for width in (self.split, profile.m - self.split)):
            raise ValueError("half box exceeds laboratory budget")
        self.profile = profile
        self.matrix = tuple(tuple(row) for row in matrix)
        self.table_limit, self.pair_limit = table_limit, pair_limit
        self.work = MitmWork()
        self.reason = "not-started"

    def _sign(self, vector):
        for value in vector:
            self.work.sign_terms += 1
            if value:
                return 1 if value > 0 else -1
        return 0

    def _halves(self, start, stop):
        width = stop - start
        for vector in itertools.product(range(-self.radius, self.radius + 1), repeat=width):
            if start == 0 and stop == self.split:
                self.work.left_proposals += 1
            else:
                self.work.right_proposals += 1
            self.work.norm_terms += width
            norm = sum(v * v for v in vector)
            if norm > self.profile.b2:
                continue
            # Negative left halves can never form a sign-canonical whole vector.
            if start == 0 and stop == self.split and self._sign(vector) < 0:
                continue
            syndrome = tuple(sum(row[start + i] * v for i, v in enumerate(vector)) % self.profile.q
                             for row in self.matrix)
            self.work.matrix_terms += self.profile.n * width
            self.work.row_reductions += self.profile.n
            yield vector, norm, syndrome

    def solutions(self):
        if self.reason != "not-started":
            raise ValueError("search can only be consumed once")
        self.reason = "running"
        return _SearchIterator(self, self._enumerate())

    def _enumerate(self):
        table = {}
        try:
            for left, norm, syndrome in self._halves(0, self.split):
                if self.work.table_entries == self.table_limit:
                    self.reason = "table-limit"
                    return
                table.setdefault(syndrome, []).append((left, norm))
                self.work.table_entries += 1
                self.work.table_buckets = len(table)
            for right, norm, syndrome in self._halves(self.split, self.profile.m):
                self.work.lookups += 1
                opposite = tuple(-s % self.profile.q for s in syndrome)
                for left, left_norm in table.get(opposite, ()):
                    if self.work.join_pairs == self.pair_limit:
                        self.reason = "pair-limit"
                        return
                    self.work.join_pairs += 1
                    if not 0 < norm + left_norm <= self.profile.b2:
                        continue
                    vector = left + right
                    if self._sign(vector) <= 0:
                        continue
                    self.work.emitted_proofs += 1
                    yield vector
            self.reason = "domain-exhausted"
        finally:
            if self.reason == "running":
                self.reason = "interrupted"


def run_mitm(profile, seed, *, target=2**252, table_limit=MAX_TABLE_ENTRIES, pair_limit=MAX_JOIN_PAIRS):
    """Generate, preprocess, search and score; reuse the existing lab score format."""
    if not isinstance(profile, Profile) or type(seed) is not bytes or len(seed) != 32:
        raise ValueError("expected Profile and exactly 32 seed bytes")
    if type(target) is not int or not 0 <= target <= 2**256:
        raise ValueError("invalid score target")
    matrix = expand_matrix(profile, seed)
    search = MitmSearch(profile, matrix, table_limit=table_limit, pair_limit=pair_limit)
    proofs = []
    score_bytes = 0
    reason = None
    iterator = search.solutions()
    try:
        for vector in iterator:
            message = _score_message(profile, seed, vector)
            score_bytes += len(message)
            proofs.append(vector)
            if int.from_bytes(hashlib.sha256(message).digest(), "big") < target:
                reason = "score-hit"
                break
    finally:
        iterator.close()
    work = {**asdict(search.work), "matrix_expansions": 1,
            "shake_output_bytes": 2 * (4 * profile.n * profile.m + 1024),
            "score_hashes": len(proofs), "score_input_bytes": score_bytes}
    return {"reason": reason or search.reason, "work": work, "proofs": proofs}
