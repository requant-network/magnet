"""Bounded linear laboratory chain; no currencies, forks, retarget or networking."""

from dataclasses import dataclass

from reference.block import Block
from reference.header import ExpectedContext
from reference.sis import Profile

MAX_CHAIN = 4096


@dataclass(frozen=True)
class ChainPolicy:
    network: bytes
    profile: Profile
    target: int
    anchor: bytes
    anchor_height: int = 0
    anchor_time: int = 0
    future_seconds: int = 120

    def __post_init__(self):
        ExpectedContext(self.network, self.anchor, self.anchor_height, self.profile)
        # Fixed target/profile only; deliberately reject degenerate score targets.
        if type(self.target) is not int or not 1 <= self.target < 2**256:
            raise ValueError("chain target must be strictly between 0 and 2^256")
        if type(self.anchor_time) is not int or not 0 <= self.anchor_time < 2**64:
            raise ValueError("anchor time must be u64")
        if type(self.future_seconds) is not int or not 0 <= self.future_seconds <= 3600:
            raise ValueError("future tolerance outside laboratory bounds")
        if self.profile.q == 2:
            raise ValueError("degenerate q=2 profile is not chain-eligible")


class LabChain:
    def __init__(self, policy):
        if not isinstance(policy, ChainPolicy):
            raise ValueError("trusted chain policy required")
        self.policy = policy
        self._blocks = []

    @property
    def blocks(self):
        return tuple(self._blocks)

    @property
    def tip(self):
        return self._blocks[-1].identifier() if self._blocks else self.policy.anchor

    @property
    def height(self):
        return self.policy.anchor_height + len(self._blocks)

    def inspect(self, packet, *, now):
        if type(now) is not int or not 0 <= now < 2**64:
            raise ValueError("trusted clock must be u64 seconds")
        try:
            block = Block.decode(packet)
        except ValueError:
            return "malformed"
        h = block.header
        p = self.policy
        if h.network != p.network or h.profile != p.profile or block.target != p.target:
            return "wrong-policy"
        # This linear-chain API does not pretend to validate a competing branch.
        if h.parent != self.tip:
            return "unknown-or-nontip-parent"
        if self.height == 2**64-1 or h.height != self.height+1:
            return "wrong-height"
        times = [b.header.timestamp for b in self._blocks[-11:]] or [p.anchor_time]
        median = sorted(times)[len(times)//2]
        if h.timestamp <= median:
            return "past-time"
        if h.timestamp > min(2**64-1, now+p.future_seconds):
            return "defer-future-time"
        context = ExpectedContext(p.network, self.tip, self.height+1, p.profile)
        if not block.valid_proof(context):
            return "invalid-proof"
        if len(self._blocks) == MAX_CHAIN:
            return "storage-limit"
        return "accepted"

    def append(self, packet, *, now):
        status = self.inspect(packet, now=now)
        if status == "accepted":
            self._blocks.append(Block.decode(packet))
        return status

    def nominal_weight(self):
        """Fixed-policy simulator weight, NOT a priced SIS work or fork-choice claim."""
        return len(self._blocks)
