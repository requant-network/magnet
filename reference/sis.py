"""Exact, bounded SIS verification and deterministic lab instances (spec/01)."""

from dataclasses import dataclass
import hashlib
import math
import struct

MAX_N = 64
MAX_M = 128
MAX_Q = 65521
HEADER = struct.Struct("<4sIHHQ")
MAGIC = b"SIS1"
DOMAIN = b"MagnetNetwork/SIS-LAB/matrix/v1\x00"
MAX_PACKET = HEADER.size + 4 * MAX_N * MAX_M + 4 * MAX_M


@dataclass(frozen=True)
class Profile:
    q: int
    n: int
    m: int
    b2: int

    def __post_init__(self):
        if any(type(v) is not int for v in (self.q, self.n, self.m, self.b2)):
            raise ValueError("profile fields must be integers, not booleans")
        if not 2 <= self.q <= MAX_Q:
            raise ValueError("q out of laboratory range")
        if any(self.q % d == 0 for d in range(2, math.isqrt(self.q) + 1)):
            raise ValueError("q must be prime")
        if not (1 <= self.n <= MAX_N and 1 <= self.m <= MAX_M):
            raise ValueError("dimensions out of laboratory range")
        if not 1 <= self.b2 < self.q * self.q:
            raise ValueError("require 1 <= B2 < q^2")


def _check_shape(profile, matrix, vector):
    if not isinstance(profile, Profile):
        raise ValueError("expected Profile")
    if type(matrix) not in (list, tuple) or len(matrix) != profile.n:
        raise ValueError("wrong matrix height")
    for row in matrix:
        if type(row) not in (list, tuple) or len(row) != profile.m:
            raise ValueError("wrong matrix width")
        if any(type(a) is not int or not 0 <= a < profile.q for a in row):
            raise ValueError("matrix entries must be canonical residues")
    if type(vector) not in (list, tuple) or len(vector) != profile.m:
        raise ValueError("wrong vector length")
    if any(type(x) is not int or not -(2**31) <= x < 2**31 for x in vector):
        raise ValueError("coordinates must be signed 32-bit integers")


def verify(profile, matrix, vector):
    """Return False for malformed data, noncanonical signs or invalid SIS."""
    try:
        _check_shape(profile, matrix, vector)
    except ValueError:
        return False
    first = next((x for x in vector if x != 0), 0)
    if first <= 0 or sum(x * x for x in vector) > profile.b2:
        return False
    return all(sum(a * x for a, x in zip(row, vector)) % profile.q == 0
               for row in matrix)


def encode_case(profile, matrix, vector):
    """Encode a well-shaped lab case, including mathematically invalid vectors."""
    _check_shape(profile, matrix, vector)
    head = HEADER.pack(MAGIC, profile.q, profile.n, profile.m, profile.b2)
    entries = [a for row in matrix for a in row]
    return (head + struct.pack(f"<{len(entries)}I", *entries)
            + struct.pack(f"<{profile.m}i", *vector))


def decode_case(packet):
    if type(packet) is not bytes or not HEADER.size <= len(packet) <= MAX_PACKET:
        raise ValueError("invalid packet size or type")
    magic, q, n, m, b2 = HEADER.unpack_from(packet)
    if magic != MAGIC:
        raise ValueError("unknown packet format")
    profile = Profile(q, n, m, b2)
    expected = HEADER.size + 4 * n * m + 4 * m
    if len(packet) != expected:
        raise ValueError("truncated packet or trailing bytes")
    entries = struct.unpack_from(f"<{n * m}I", packet, HEADER.size)
    matrix = tuple(tuple(entries[i * m:(i + 1) * m]) for i in range(n))
    vector = struct.unpack_from(f"<{m}i", packet, HEADER.size + 4 * n * m)
    _check_shape(profile, matrix, vector)
    return profile, matrix, vector


def verify_packet(packet):
    try:
        return verify(*decode_case(packet))
    except ValueError:
        return False


def expand_matrix(profile, seed):
    """Generate a bounded SHAKE256 instance. seed is public, never a key."""
    if not isinstance(profile, Profile) or type(seed) is not bytes or len(seed) != 32:
        raise ValueError("expected Profile and exactly 32 seed bytes")
    params = struct.pack("<IHHQ", profile.q, profile.n, profile.m, profile.b2)
    count = profile.n * profile.m
    max_draws = 4 * count + 1024
    stream = hashlib.shake_256(DOMAIN + params + seed).digest(2 * max_draws)
    cutoff = 65536 - (65536 % profile.q)
    entries = []
    for (word,) in struct.iter_unpack("<H", stream):
        if word < cutoff:
            entries.append(word % profile.q)
            if len(entries) == count:
                return tuple(tuple(entries[i * profile.m:(i + 1) * profile.m])
                             for i in range(profile.n))
    raise ValueError("matrix sampling budget exhausted")
