"""Canonical research headers and context-bound proofs; no consensus rules."""

from dataclasses import dataclass
import hashlib
import struct

from reference.sis import Profile, expand_matrix, verify

HEADER = struct.Struct("<4s32s32s32sQQQIHHQ")
CONTEXT = struct.Struct("<32s32sQIHHQ")
MAGIC = b"MGH1"
DOMAIN = b"MagnetNetwork/SIS-LAB/header-seed/v1\0"
MAX_PROOF = HEADER.size + 4 * 128


def _validate_fields(network, parent, height, profile):
    if any(type(value) is not bytes or len(value) != 32 for value in (network, parent)):
        raise ValueError("network and parent must be 32-byte strings")
    if type(height) is not int or not 0 <= height < 2**64:
        raise ValueError("height must be a u64 integer")
    if not isinstance(profile, Profile):
        raise ValueError("expected Profile")


@dataclass(frozen=True)
class LabHeader:
    network: bytes
    parent: bytes
    payload: bytes
    height: int
    timestamp: int
    nonce: int
    profile: Profile

    def __post_init__(self):
        _validate_fields(self.network, self.parent, self.height, self.profile)
        if type(self.payload) is not bytes or len(self.payload) != 32:
            raise ValueError("payload commitment must be 32 bytes")
        for value in (self.timestamp, self.nonce):
            if type(value) is not int or not 0 <= value < 2**64:
                raise ValueError("timestamp and nonce must be u64 integers")

    def encode(self):
        p = self.profile
        return HEADER.pack(MAGIC, self.network, self.parent, self.payload,
                           self.height, self.timestamp, self.nonce, p.q, p.n, p.m, p.b2)

    @classmethod
    def decode(cls, data):
        if type(data) is not bytes or len(data) != HEADER.size:
            raise ValueError("header length/type")
        magic, network, parent, payload, height, timestamp, nonce, q, n, m, b2 = HEADER.unpack(data)
        if magic != MAGIC:
            raise ValueError("header version")
        return cls(network, parent, payload, height, timestamp, nonce, Profile(q, n, m, b2))

    def seed(self):
        return hashlib.shake_256(DOMAIN + self.encode()).digest(32)

    def matrix(self):
        return expand_matrix(self.profile, self.seed())


@dataclass(frozen=True)
class ExpectedContext:
    """Trusted caller policy, supplied separately from an untrusted proof."""

    network: bytes
    parent: bytes
    height: int
    profile: Profile

    def __post_init__(self):
        _validate_fields(self.network, self.parent, self.height, self.profile)

    def encode(self):
        p = self.profile
        return CONTEXT.pack(self.network, self.parent, self.height, p.q, p.n, p.m, p.b2)

    def matches(self, header):
        return (self.network, self.parent, self.height, self.profile) == (
            header.network, header.parent, header.height, header.profile)


def encode_proof(header, vector):
    if not isinstance(header, LabHeader) or type(vector) not in (tuple, list):
        raise ValueError("header/vector type")
    if len(vector) != header.profile.m or any(
            type(x) is not int or not -(2**31) <= x < 2**31 for x in vector):
        raise ValueError("vector shape/coordinate")
    return header.encode() + struct.pack(f"<{len(vector)}i", *vector)


def verify_proof(packet, expected):
    """Derive A internally; never accept a miner-supplied matrix or policy."""
    if not isinstance(expected, ExpectedContext):
        raise ValueError("trusted expected context is required")
    if type(packet) is not bytes or not HEADER.size <= len(packet) <= MAX_PROOF:
        return False
    try:
        header = LabHeader.decode(packet[:HEADER.size])
        if not expected.matches(header) or len(packet) != HEADER.size + 4 * header.profile.m:
            return False
        vector = struct.unpack(f"<{header.profile.m}i", packet[HEADER.size:])
        first = next((x for x in vector if x), 0)
        if first <= 0 or sum(x * x for x in vector) > header.profile.b2:
            return False
        return verify(header.profile, header.matrix(), vector)
    except ValueError:
        return False
