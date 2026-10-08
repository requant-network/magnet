"""Trusted laboratory admission constraints; no chain, payload body or retarget."""

from dataclasses import dataclass

from reference.grinding import _target, verify_scored_proof
from reference.header import ExpectedContext, HEADER, LabHeader, MAX_PROOF


@dataclass(frozen=True)
class LabRules:
    context: ExpectedContext
    target: int
    earliest: int
    latest: int
    payloads: tuple

    def __post_init__(self):
        if not isinstance(self.context, ExpectedContext):
            raise ValueError("trusted context required")
        _target(self.target)
        if (type(self.earliest) is not int or type(self.latest) is not int
                or not 0 <= self.earliest <= self.latest < 2**64):
            raise ValueError("invalid trusted timestamp interval")
        if (type(self.payloads) is not tuple or not 1 <= len(self.payloads) <= 8
                or any(type(p) is not bytes or len(p) != 32 for p in self.payloads)
                or len(set(self.payloads)) != len(self.payloads)):
            raise ValueError("invalid trusted payload commitments")

    def permits(self, header):
        return (isinstance(header, LabHeader) and self.context.matches(header)
                and self.earliest <= header.timestamp <= self.latest and header.payload in self.payloads)


def admit_proof(packet, rules):
    if not isinstance(rules, LabRules):
        raise ValueError("trusted lab rules required")
    if type(packet) is not bytes or not HEADER.size <= len(packet) <= MAX_PROOF:
        return False
    try:
        header = LabHeader.decode(packet[:HEADER.size])
    except ValueError:
        return False
    # Reject invalid header surface and zero targets before expensive instance derivation.
    return (rules.target != 0 and rules.permits(header)
            and verify_scored_proof(packet, rules.context, rules.target))
