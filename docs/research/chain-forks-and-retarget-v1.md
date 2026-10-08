# Independent chain admission, forks and retarget research

Milestone 11вЂ“15, 2026-10-08/09. English is primary. This is an executable laboratory
and evidence report, not a production network or monetary launch.

| Item | Delivered | Boundary |
|---|---|---|
|11|Independent Rust MGB1 parser, commitments, IDs and complete fixed-policy linear engine|No native fork database or peer protocol|
|12|Three-node/two-miner delivery/partition simulator over real blocks; native replay of every retained branch|Finite reliable-retry model|
|13|Paid real-block FIFO-reuse experiments and explicit nominal-depth/ideal-score work distinctions|Portable adversarial SIS work remains unresolved|
|14|Fixed/window/per-block retarget hypotheses, capacity/reuse/time attacks|Synthetic arrivals; no dynamic targets in real MGB1 admission|
|15|Atomic canonical changes, full revalidation, detach/attach events and resource caps|Opaque body history only; no balances or monetary rollback|

[ADR 0012](../decisions/0012-fork-simulation-without-priced-work.md) records the
decisions and the still-open E3/E4 monetary safety gates.

## Independent native engine

Rust receives original MGB1 bytes and independently decodes and validates size,
version, target, profile, commitments, proof and ID. It supplies its own trusted
parent/height/time context to its existing independent SIS/score verifier. Python
never supplies parsed block fields or trusted acceptance decisions. Spec11's
proof-before-storage rejection precedence is deliberately preserved.

[The full-chain study](results/full-chain-v1.json) compares 6236 commands in main
and full-capacity histories, with zero mismatches. The main history appends 66
blocks and includes 2000 seeded malformed/near-valid inputs, inspection, replay,
future deferral/retry and upper-median behavior. A separate history legally
reaches 4096 blocks: an extra valid candidate returns storage-limit, an invalid
proof returns invalid-proof. Two additional chains exercise saturated u64 height/
clock; one maximum 1747-byte envelope exercises q=65521, n=64, m=128 admission.
Four malformed framing cases reject; empty stdin exits cleanly.

The local MCP1 adapter has a 135-byte trusted policy, 1756-byte frame cap,
8192-command cap and 43-byte state replies. Layouts: [spec 12](../../spec/12-native-chain-v1.md).
It is not an Internet protocol or public service.

## Real forks and canonical history

Fixture miners build real blocks on their current preferred tips. Each receiving
tree admits against that block's own ancestor branch under fixed profile 7/1/3/8
and target 2^255. Preference is strictly longer nominal depth; equal depth retains
the first chosen tip. This rule is not priced SIS cumulative work.

Before changing history, the entire proposed path is replayed through linear
admission. Failure preserves accepted nodes and canonical state. Successful
transitions expose detached IDs old-tip-first and attached IDs ancestor-first;
the opaque body sequence changes atomically. No rewards, balances or transaction
undo are claimed. A regression injects ancestor failure during revalidation.

[The delivery study](results/forks-v1.json) runs 16 scenarios: delays 0/1/10/60s,
with/without temporary partition until time 180 and two seeds. After healing,
known blocks are explicitly retried parent-first under the same bounded API.
All 16 have a unique longest branch and converge; 25 canonical reorgs occur.
624 native retained-branch replays cover 2985 block occurrences, zero mismatches.
Occurrences include repeated ancestors; they are not distinct mined blocks.

This does not guarantee convergence under permanent partition, arbitrary
Byzantine delivery or queue eviction without retries. Equal-depth tips can
remain different until a strictly longer branch arrives. Raw event traces and
block wires are retained under ignored artifacts/forks-v1.json.

## Concrete work-weight evidence

[Four paid campaigns](results/work-weight-v1.json) mine 64 real blocks, 16 per
campaign. Native mode 3 uses cumulative 250000 proposal/pair nodes, 4096 solver calls
and 256 nonces per block. FIFO capacity is 0 or 16; every carry is validated on the
current matrix. Acquisition is eager and all returned proofs are paid/checked
before selecting a winning score. Score inputs deduplicate per header. Score
bytes include the full domain plus proof; process startup, setup, other hashing,
elapsed time and energy are not priced by these descriptive counters. Every
resulting chain is replayed through complete independent Rust admission.

| Target | Pool | Blocks | Carried-vector hits | Fresh acquisitions | Native proposal/pair nodes | Scores |
|---|---:|---:|---:|---:|---:|---:|
|2^255|0|16|0|16|661|34|
|2^255|16|16|11|5|203|32|
|2^252|0|16|0|45|1863|240|
|2^252|16|16|4|53|2277|361|

This disproves a universal fresh-solver-call-per-block assumption. It is not a
paired performance ranking: different proofs change IDs and subsequent parents,
so policies traverse different challenges. The harder-target pool cohort even
uses more acquisitions here. No universal reuse advantage, free blocks or
high-dimensional speedup follows from these tiny examples.

2^256/T describes mean eligible-score trials only under the declared uniform-
independent input assumption. It does not price SIS preparation or eligible-input
supply. Nominal count under one fixed policy can inspect histories; neither it
nor inverse target times an arbitrary SIS constant is promoted to consensus work.
Safe variable-target/profile comparisons remain a research gate.

## Retarget hypotheses and negative results

[The separate model](results/difficulty-v1.json) runs 720 scenarios and 92160
candidate events: two seeds, three methods, desired intervals 30/60/120s, capacity
factors 0.1/0.5/1/2/10, hypothetical reuse-supply multipliers 1 or 4 and four timestamp
behaviors. Supply changes after 64 of 128 events. Methods are fixed, 16-accepted-
timestamp windows and per-accepted-candidate adjustment. Initial T=2^252,
bounds 2^232..2^255, exact ratio clamp1/4..4, integer floor then saturation.
Time admission uses upper median of last 11 and trusted now+120; rejects remain
recorded. Varying-target nominal trial sums use exact per-event floor/ceil bounds
to avoid exponentially growing rational common denominators.

Exponential eligible-input arrivals are an explicit hypothesis. There is no
actual SIS solving, transport or energy calibration. Dynamic targets are never
used to admit real MGB1 blocks.

For desired60s, capacity 1, reuse1, two honest seeds give post-shock means:
fixed 52.17/66.96s, window 58.42/69.28s, per-block 154.49/287.80s. Median+1 timestamps
raise window means to 279702/373655s and per-block to 54707741/70216963s. These are
simulated intervals, not observed waits on a running network. This past-time
strategy drives difficulty up and causes severe availability failures of these
particular hypotheses. No method or promised block interval is selected for
production. This alone does not prove a cheap inflated-work fork or general SIS
insecurity; both still require an adversarial work model.

## Resource probes

Caps:256 accepted nodes, 128 depth, 32 combined pending entries, 8 per trusted peer,
60s TTL and 16 submissions per label per local second. At most 16 trusted labels
exist. Malformed and duplicate packets count; rate rejection precedes decoding.
Orphans get bounded shape/policy checks before parents exist. Known future
entries retain original age. Drain takes at most 8 ready entries from a snapshot,
never recursively activates every descendant, and expires at age>=TTL.

Full replay permits up to 129 admission calls per submit and 1032 per drain, not
just eight proof verifications. Wire retention is at most 503136 bytes; interpreter
and object overhead are additional. Capacity halts further accepted storage;
pruning/persistence remains future work.

[The overload study](results/fork-resources-v1.json) submits 1024 malformed packets
at one local second:16 decode, 1008 reject at the rate gate, no proof admission.
Another 64 orphan submissions retain 32 entries, 39904 wire bytes, at most 8 per
label and no proof admission; all expire at 60s. Node-cap rejection precedes
expensive admission and preserves the preferred tip. Evidence checks remain
active under python -O; a negative test injects false rate outcomes and verifies
report refusal even with optimized Python.

Trusted finite labels are not Internet identities or Sybil protection. Counters
are not throughput, OS memory or deployment guarantees. See [spec 13](../../spec/13-fork-and-retarget-lab-v1.md).

## Reproduce locally

~~~sh
python scripts/check.py
python scripts/chain_survey.py
python scripts/fork_survey.py
python scripts/work_weight_study.py
python scripts/difficulty_survey.py
python scripts/resource_survey.py
~~~

Standard Python and offline locked Cargo, no new packages/GitHub Actions/paid CI
or cloud jobs. Studies invalidate reports before starting and refuse publication
after source changes. Compact reports retain configurations, seeds, source and
binary hashes. Raw traces are ignored. Experiments share a local host; no isolated
hardware speed claim is made. Earlier manifests remain historical snapshots.

Next: portable adversarial work, secure parameters and optimized/GPU baselines,
external cryptographic review, persistence/pruning, peer synchronization,
transactions/signatures/economics, wallet integration and separate-operator testnet.
