# ADR 0010 — Independently verify acceptance and charge persistent acquisition

Status: accepted laboratory interfaces and accounting constraints; no work model
or consensus target selected.

## Decision

Implement the unchanged SHA-256 score, strict external 0..2^256 threshold and
LabRules admission independently in Rust. Preserve canonical MGH1 and existing
instance generation. Use a bounded 33-byte big-endian target and exact-length
trusted-rule transport only in local adapters. Run frozen vectors, padding and
structured mutation differentials in the ordinary local gate. This closes an
implementation gap; it does not transform a lab predicate into network consensus
or certify handwritten cryptography.

Evaluate persistent cross-context vectors with paid acquisition. Fix network/
profile, permit controlled parent/height transitions, and retain one vector across
stages. Compare restart-first, carry-first and explicit carry-fallback under one
campaign-wide logical budget and one external process window. Do not inject
oracle-selected initial vectors or reset budgets after each changed parent.
Invalid carries do not score; valid carries use current-header hashes. Fallback
is charged for both its carry-check expansion and the existing helper's fresh
expansion. This wrapper is transparent rather than an optimized-miner claim.

Use multiple salted cohorts, same-input repeats and a recorded global shuffled
order. Keep failed completed campaigns in logical totals and interrupted ones
censored. Completed-only ratios cannot select work pricing when interrupted
costs are unknown. Tiny-q collisions and cheap vector reuse must stay explicit.
See [native interfaces](../../spec/09-native-score-and-admission-v1.md),
[campaign interfaces](../../spec/10-persistent-campaigns-v1.md) and
[evidence](../research/native-admission-and-campaigns-v1.md).

## Next gate

Broaden exact/native/BKZ/sieve solver and vector-pool competition, separate steady
campaign execution from cold startup while retaining initial costs, and measure
permitted timestamp/payload grinding and adversarial preprocessing. The current
experiment persists one vector; it is not a search over the best adversarial
pool or all solver families. SIS availability and multiplicity remain variable.

Specify deterministic profile/target derivation, real parent/body/time validity,
upgrades and independently checked encodings before retarget/fork-choice rules.
Do not use benchmark seconds, score multiplicity or self-reported operations as
chain weight. External cryptographic review remains a separate gate. MagnetGate,
wallets, transfers and a monetary testnet remain outside this milestone.
