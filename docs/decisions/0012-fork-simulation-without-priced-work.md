# ADR 0012 — Exercise forks while keeping priced SIS work unresolved

Status: accepted laboratory interfaces; production chainwork/retarget gate open.

## Decisions

Implement a complete independent Rust MGB1 linear engine with unchanged fixed
policy and rejection precedence. Compare every local state transition to Python,
including legal full-capacity histories. The Rust engine independently interprets
wire bytes rather than accepting Python-parsed block descriptions.

Exercise real fixed-policy fork histories with nominal depth only, retain first
equal-depth tip and fully revalidate before canonical switching. Return explicit
detach/attach events and atomically replace opaque body histories. No rewards,
transactions or monetary rollback are implied. Queue/call/byte/rate caps bound
the simulator; they are not a production networking or Sybil defense claim.

Explore target control in a separate explicit score-input arrival model. Compare
fixed/window/per-block responses to capacity, reuse-supply and timestamp shocks.
Dynamic targets are not quietly installed in real MGB1 admission. Choosing ASERT,
WTEMA or inverse-target cumulative work by familiarity would not close E3.

## What the work study can establish

Real tiny blocks mined by paid native mode3 under fixed target are replayed by
both complete engines. FIFO reuse campaigns charge matrix derivation, carried
proof checks, score computations, fresh acquisition and native proposal/pair
work. They can exhibit a block obtained from a previously paid vector, invalidating
the universal claim that every accepted block requires a fresh solver call.
They do not show free blocks, bounded adversarial speedup or portable joule cost.

Inverse target counts expected eligible-score attempts under a declared ideal
hash-input assumption. Multiple proofs, sparse screening, context selection and
preparation sharing change eligible-input supply. Positive toy evidence and
synthetic attacks justify further work research; they do not alone prove every
possible SIS-PoW unsafe or establish a safe cumulative-work rule.

## Gates that stay open

High-dimensional optimized/GPU attack competition, portable adversarial work
argument, parameter/activation comparability and external cryptographic review.
Only after these can a production fork-choice/retarget design be selected. The
current E4 simulator is an executable testing tool with explicitly hypothetical
work inputs, not an assertion that E3/E4 monetary safety gates have passed.

Node persistence/pruning, real peer synchronization, transactions/state/signatures,
economic issuance rules, wallet/MagnetGate integration and separate-operator
testnet remain subsequent work. See [spec12](../../spec/12-native-chain-v1.md)
and [spec13](../../spec/13-fork-and-retarget-lab-v1.md).
