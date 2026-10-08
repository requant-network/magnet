"""Canonical local lab-rule/target transport; this is not a block serialization."""

import struct

from reference.grinding import _target
from reference.header import CONTEXT, ExpectedContext
from reference.header_rules import LabRules
from reference.sis import Profile


def target_bytes(target):
    _target(target)
    return target.to_bytes(33, "big")


def encode_rules(rules):
    if not isinstance(rules, LabRules):
        raise ValueError("trusted lab rules required")
    return (rules.context.encode() + target_bytes(rules.target)
            + struct.pack("<QQB", rules.earliest, rules.latest, len(rules.payloads)) + b"".join(rules.payloads))


def decode_rules(wire):
    if type(wire) is not bytes or not 170 <= len(wire) <= 394:
        raise ValueError("rules length/type")
    network, parent, height, q, n, m, b2 = CONTEXT.unpack(wire[:88])
    target = int.from_bytes(wire[88:121], "big")
    earliest, latest, count = struct.unpack("<QQB", wire[121:138])
    if not 1 <= count <= 8 or len(wire) != 138 + 32*count:
        raise ValueError("rules payload count/length")
    return LabRules(ExpectedContext(network, parent, height, Profile(q, n, m, b2)), target, earliest, latest,
                    tuple(wire[i:i+32] for i in range(138, len(wire), 32)))


def scored_request(context, target, packet):
    return b"MGL1\x05" + context.encode() + target_bytes(target) + packet


def admission_request(rules, packet):
    wire = encode_rules(rules)
    return b"MGL1\x06" + struct.pack("<H", len(wire)) + wire + packet
