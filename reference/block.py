"""MGB1 experimental blocks: bounded opaque body, committed descriptor and SIS proof."""

from dataclasses import dataclass
import hashlib
import struct

from reference.admission_wire import target_bytes
from reference.grinding import _target, verify_scored_proof
from reference.header import HEADER, MAX_PROOF, LabHeader, encode_proof

MAGIC = b"MGB1"
BODY_DOMAIN = b"MagnetNetwork/block-body/v1\0"
COMMIT_DOMAIN = b"MagnetNetwork/block-commit/v1\0"
ID_DOMAIN = b"MagnetNetwork/block-id/v1\0"
MAX_BODY = 1024
PREFIX = struct.Struct("<4s33s32sH")
MAX_BLOCK = PREFIX.size + MAX_BODY + MAX_PROOF


def _body(body):
    if type(body) is not bytes or len(body) > MAX_BODY:
        raise ValueError("body must be opaque bytes of at most 1024 bytes")


def commitment(target, recipient, body):
    _target(target)
    if type(recipient) is not bytes or len(recipient) != 32:
        raise ValueError("recipient commitment must be 32 bytes")
    _body(body)
    root = hashlib.sha256(BODY_DOMAIN + struct.pack("<H", len(body)) + body).digest()
    return hashlib.sha256(COMMIT_DOMAIN + MAGIC + target_bytes(target) + recipient + root).digest()


@dataclass(frozen=True)
class Block:
    header: LabHeader
    vector: tuple
    target: int
    recipient: bytes
    body: bytes

    def __post_init__(self):
        if not isinstance(self.header, LabHeader) or type(self.vector) is not tuple:
            raise ValueError("invalid block header/vector")
        # Serialization shape validation does not imply mathematical validity.
        encode_proof(self.header, self.vector)
        expected = commitment(self.target, self.recipient, self.body)
        if self.header.payload != expected:
            raise ValueError("descriptor/body commitment does not match header")

    def encode(self):
        return PREFIX.pack(MAGIC, target_bytes(self.target), self.recipient, len(self.body)) + self.body + self.proof()

    def proof(self):
        return encode_proof(self.header, self.vector)

    def identifier(self):
        return hashlib.sha256(ID_DOMAIN + self.encode()).digest()

    @classmethod
    def decode(cls, packet):
        if type(packet) is not bytes or not PREFIX.size + HEADER.size <= len(packet) <= MAX_BLOCK:
            raise ValueError("block bounds/type")
        magic, target_wire, recipient, size = PREFIX.unpack_from(packet)
        if magic != MAGIC or size > MAX_BODY:
            raise ValueError("block version/body limit")
        target = int.from_bytes(target_wire, "big")
        _target(target)
        offset = PREFIX.size + size
        if offset + HEADER.size > len(packet):
            raise ValueError("truncated body/header")
        header = LabHeader.decode(packet[offset:offset+HEADER.size])
        if len(packet) != offset + HEADER.size + 4*header.profile.m:
            raise ValueError("proof/trailing data length")
        vector = struct.unpack_from(f"<{header.profile.m}i", packet, offset+HEADER.size)
        return cls(header, vector, target, recipient, packet[PREFIX.size:offset])

    def valid_proof(self, context):
        return self.target != 0 and verify_scored_proof(self.proof(), context, self.target)
