"""Bounded real-block fork laboratory. Longest depth is nominal, not SIS chainwork."""

from dataclasses import dataclass
from collections import Counter

from reference.block import Block, MAX_BLOCK
from reference.chain import ChainPolicy, LabChain


@dataclass(frozen=True)
class ForkLimits:
    nodes: int = 256
    depth: int = 128
    queued: int = 32
    per_peer: int = 8
    ttl: int = 60
    drain: int = 8
    submissions: int = 16  # per trusted peer label, per trusted local second

    def __post_init__(self):
        for value, maximum in ((self.nodes, 256), (self.depth, 128), (self.queued, 32),
                               (self.per_peer, 8), (self.ttl, 60), (self.drain, 8), (self.submissions,16)):
            if type(value) is not int or not 1 <= value <= maximum:
                raise ValueError("fork limit outside laboratory envelope")


@dataclass(frozen=True)
class Transition:
    status: str
    detached: tuple = ()  # old tip toward common ancestor
    attached: tuple = ()  # common ancestor toward new tip
    admission_calls: int = 0


@dataclass(frozen=True)
class Pending:
    block: Block
    peer: str
    enqueued: int


class ForkTree:
    def __init__(self, policy, *, peers=("local",), limits=ForkLimits()):
        if not isinstance(policy, ChainPolicy) or not isinstance(limits, ForkLimits):
            raise ValueError("trusted policy/limits required")
        if type(peers) is not tuple or not 1 <= len(peers) <= 16 or any(
                type(p) is not str or not p.isascii() or not 1 <= len(p) <= 32 for p in peers) or len(set(peers)) != len(peers):
            raise ValueError("fixed trusted peer labels required")
        self._policy, self._limits, self._peers = policy, limits, peers
        self._nodes, self._pending = {}, {}
        self._canonical, self._clock = (), 0
        self._rates = {}

    @property
    def policy(self):
        return self._policy

    @property
    def limits(self):
        return self._limits

    @property
    def peers(self):
        return self._peers

    @property
    def canonical(self):
        return self._canonical

    @property
    def tip(self):
        return self._canonical[-1] if self._canonical else self.policy.anchor

    @property
    def node_count(self):
        return len(self._nodes)

    @property
    def queued_count(self):
        return len(self._pending)

    @property
    def retained_wire_bytes(self):
        return sum(len(b.encode()) for b in self._nodes.values()) + sum(len(p.block.encode()) for p in self._pending.values())

    def canonical_bodies(self):
        return tuple(self._nodes[key].body for key in self._canonical)

    def path(self, tip):
        if type(tip) is not bytes or len(tip)!=32:
            raise ValueError("validated tip must be 32 bytes")
        if tip == self.policy.anchor:
            return ()
        if tip not in self._nodes:
            raise ValueError("unknown validated tip")
        reverse = []
        while tip != self.policy.anchor:
            reverse.append(tip)
            if len(reverse) > self.limits.depth:
                raise RuntimeError("corrupt ancestry/depth")
            tip = self._nodes[tip].header.parent
        return tuple(reversed(reverse))

    def _tick(self, now):
        if type(now) is not int or not self._clock <= now < 2**64:
            raise ValueError("trusted local clock must be monotone u64")
        if now != self._clock:
            self._rates.clear()
        self._clock = now
        for key, pending in tuple(self._pending.items()):
            if now - pending.enqueued >= self.limits.ttl:
                del self._pending[key]

    def _queue(self, block, peer, now, status, calls=0):
        if len(self._pending) == self.limits.queued:
            return Transition("queue-limit",admission_calls=calls)
        if sum(p.peer == peer for p in self._pending.values()) >= self.limits.per_peer:
            return Transition("peer-queue-limit",admission_calls=calls)
        self._pending[block.identifier()] = Pending(block, peer, now)
        return Transition(status,admission_calls=calls)

    def _admit(self, block, now):
        if len(self._nodes) == self.limits.nodes:
            return Transition("node-limit")
        parent_path = self.path(block.header.parent)
        if len(parent_path) == self.limits.depth:
            return Transition("depth-limit")
        # Ancestors in _nodes have already passed admission under the immutable
        # fixed policy. This private reconstruction is never exposed to callers.
        chain = LabChain(self.policy)
        chain._blocks = [self._nodes[key] for key in parent_path]
        status = chain.append(block.encode(), now=now)
        if status != "accepted":
            return Transition(status, admission_calls=1)
        key = block.identifier()
        if key == self.policy.anchor:
            return Transition("anchor-id-collision", admission_calls=1)
        proposal = parent_path + (key,)
        if len(proposal) <= len(self._canonical):
            self._nodes[key] = block
            return Transition("accepted-side", admission_calls=1)
        # Fully replay before any canonical/node mutation. At most depth+1
        # admission calls for one submission; drain multiplies this by <=8.
        replay = LabChain(self.policy)
        for item in proposal:
            candidate = block if item == key else self._nodes[item]
            if replay.append(candidate.encode(), now=now) != "accepted":
                return Transition("revalidation-failed", admission_calls=1+len(replay.blocks)+1)
        common = 0
        while common < min(len(proposal), len(self._canonical)) and proposal[common] == self._canonical[common]:
            common += 1
        detached = tuple(reversed(self._canonical[common:]))
        attached = proposal[common:]
        self._nodes[key] = block
        self._canonical = proposal
        return Transition("accepted-reorg" if detached else "accepted-main", detached, attached, 1+len(proposal))

    def submit(self, packet, *, peer, now):
        if type(peer) is not str or peer not in self.peers:
            raise ValueError("untrusted peer label")
        self._tick(now)
        used=self._rates.get(peer,0)
        if used==self.limits.submissions:
            return Transition("submission-rate-limit")
        self._rates[peer]=used+1
        try:
            block = Block.decode(packet)
        except ValueError:
            return Transition("malformed")
        p, h = self.policy, block.header
        if h.network != p.network or h.profile != p.profile or block.target != p.target:
            return Transition("wrong-policy")
        key = block.identifier()
        if key in self._nodes or key in self._pending:
            return Transition("duplicate")
        if not p.anchor_height < h.height <= min(2**64-1, p.anchor_height+self.limits.depth):
            return Transition("wrong-height")
        if h.parent != p.anchor and h.parent not in self._nodes:
            return self._queue(block, peer, now, "queued-orphan")
        result = self._admit(block, now)
        if result.status == "defer-future-time":
            return self._queue(block, peer, now, "queued-future",result.admission_calls)
        return result

    def drain(self, *, now, budget=None):
        self._tick(now)
        budget = self.limits.drain if budget is None else budget
        if type(budget) is not int or not 1 <= budget <= self.limits.drain:
            raise ValueError("drain budget outside configured cap")
        results = []
        # Fixed snapshot: a parent accepted in this drain makes its child ready
        # only on the next call. No unbounded recursive descendant activation.
        ready = [key for key, p in self._pending.items()
                 if (p.block.header.parent == self.policy.anchor or p.block.header.parent in self._nodes)
                 and p.block.header.timestamp <= min(2**64-1, now+self.policy.future_seconds)]
        for key in ready[:budget]:
            pending = self._pending.pop(key)
            result = self._admit(pending.block, now)
            if result.status == "defer-future-time":
                self._pending[key] = pending  # never renew original TTL
            results.append(result)
        return tuple(results)

    def queue_peers(self):
        return dict(Counter(p.peer for p in self._pending.values()))


MAX_RETAINED_WIRE = (256+32)*MAX_BLOCK  # object/interpreter overhead is additional
