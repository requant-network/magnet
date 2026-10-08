# Bounded real-block forks and separate retarget hypotheses

No production work function is defined here. Real MGB1 fork simulations retain
the exact fixed network/profile/target of spec 11. Synthetic dynamic-target
experiments are separate, never used to admit MGB1 blocks or compare real forks.

## Real-block tree

Trusted policy, immutable limits and 1..16 fixed ASCII peer labels (1..32 chars).
Accepted blocks are immutable; private verified ancestry is used to validate each
candidate against its own branch. Rejection preserves validated nodes and
canonical state; normal trusted-clock ticks can expire pending entries.

Maximum 256 validated nodes, 128 depth, 32 combined orphan/future entries, 8 pending
per peer, 60-second TTL, 8 drain attempts. Limits can only be tightened. Clock is
trusted monotone u64 seconds. At most 16 submissions per label per local second;
malformed and duplicate submissions count and rate rejection precedes decoding.
Finite trusted labels are not a Sybil-resistant Internet admission mechanism.

Canonical decode and fixed policy/height bounds precede queueing. Unknown-parent
blocks receive only bounded shape/policy checks until their parent is accepted.
Known-parent future blocks can queue after an early time rejection. Combined
queue bounds apply to both. IDs deduplicate queues and accepted nodes. Duplicates
do not refresh enqueue time; internal transitions preserve original TTL.
Entries expire at now-enqueued>=TTL. No automatic recursive descendant processing.

Drain takes a snapshot of ready entries (known parent, future bound satisfied)
and processes at most its explicit budget. Children newly made ready wait for
the next call. Invalid ready blocks leave the queue. Capacity rejects before
proof expansion in this fork API; this deliberately differs from the spec 11
linear API's final storage check and is not advertised as identical precedence.

Preferred history is a strictly longer validated path under identical policy.
Equal depth retains the first chosen tip. This is nominal depth, not priced SIS
chainwork. Before a change, the complete proposed path is independently replayed
through Python linear admission. Only successful replay commits both new node
and canonical path. Returned transitions expose detached IDs in old-tip order
and attached IDs in ancestor-to-new-tip order; canonical opaque body sequence is
replaced atomically. No balances/rewards or transaction undo is claimed.

At most 129 linear admission evaluations per submit, 1032 per drain (8*129), not
eight proof evaluations. Returned admission_calls include early failures and
replays; they are descriptive call counts, not elapsed work. Wire retention is
at most(256+32)*1747=503136 bytes; Python/interpreter/object overhead is additional.
This hard cap halts new validation at capacity; pruning/persistence is future work.

## Delivery model

Three local node objects, two adaptive fixture miners, deterministic ordered
event delivery with jitter, delays 0/1/10/60seconds and temporary partition until
time 180. Every mining event uses its miner's current preferred tip. Post-heal
reconciliation explicitly retries every known block in parent-first order under
the same admission/queue controls. Each retained branch is separately replayed
by native Rust. Unique longer tips must converge; equal-depth histories need not.
This is neither independent operators nor an eventual-delivery guarantee under
adversarial permanent partitions or queue eviction without retries.

## Synthetic score-input model

Methods: fixed, 16-accepted-timestamp window, per accepted candidate. Initial
T=2^252, range 2^232..2^255. Adjustment uses exact rational observed_span/
expected_span, clamps 1/4..4, floors integer multiplication, then saturates bounds.
Zero observed span selects the 1/4 clamp. Negative consecutive timestamp movement
also supplies zero observed span. Times must exceed upper median of last 11 and
be at most trusted now+120; rejected candidates consume arrivals and are recorded.

For desired intervals 30/60/120s, exponential waiting-rate hypothesis is
(input_supply/desired_interval)*(T/initial_T). Supply changes after 64 of 128 events
by 0.1/0.5/1/2/10 and a declared reuse multiplier of 1 or 4. Timestamp cohorts are honest,
future edge, median+1, alternating edges. Two seeds supply common random draws
across methods/cohorts. No SIS solving, transport, energy or profile changes are
represented. This distribution is a declared hypothesis, not measured calibration.

2^256/T is an exact rational expected eligible-score count only under the
uniform-independent input assumption. For rounded varying targets its cumulative
nominal sum is bracketed by summing exact per-event floors and ceilings, avoiding
unbounded common-denominator growth. These bounds are not a consensus weight.
No retarget/fork method or promised 30/60/120s block interval is selected here.
