"""Bounded local LRU of verified complete candidate pools, keyed by exact instances."""

from collections import OrderedDict

from reference.sis import Profile, _check_shape, verify


def instance_key(profile, matrix):
    if not isinstance(profile, Profile) or profile.m > 16:
        raise ValueError("cache profile bound")
    _check_shape(profile, matrix, [0]*profile.m)
    return (profile, tuple(tuple(row) for row in matrix))


class CandidateCache:
    def __init__(self, capacity=32, proof_limit=256):
        if (type(capacity) is not int or not 1 <= capacity <= 32
                or type(proof_limit) is not int or not 1 <= proof_limit <= 256):
            raise ValueError("cache capacity/proof bound")
        self.capacity, self.proof_limit = capacity, proof_limit
        self._entries = OrderedDict()

    def __len__(self):
        return len(self._entries)

    def get(self, profile, matrix):
        key = instance_key(profile, matrix)
        if key not in self._entries:
            return None  # An empty tuple is a cached complete empty domain.
        self._entries.move_to_end(key)
        return self._entries[key]

    def store(self, profile, matrix, sphere):
        key = instance_key(profile, matrix)
        proofs = sphere["proofs"]
        if (sphere["reason"] != "domain-exhausted" or type(proofs) not in (list, tuple)
                or len(proofs) > self.proof_limit):
            raise ValueError("cache requires a complete bounded pool")
        if any(not verify(profile, matrix, v) for v in proofs):
            raise ValueError("cache contains invalid SIS vector")
        pool = tuple(sorted(tuple(v) for v in proofs))
        if len(set(pool)) != len(pool):
            raise ValueError("duplicate cached vector")
        self._entries[key] = pool
        self._entries.move_to_end(key)
        evicted = len(self._entries) > self.capacity
        if evicted:
            self._entries.popitem(last=False)
        return int(evicted)
