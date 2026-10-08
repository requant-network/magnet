# ADR 0005 — Header binding is necessary but does not price work

Status: accepted research boundary; no production consensus selected.

## Evidence

Python and Rust independently derive the same lab instances from a canonical
header. The bound proof interface accepts no supplied A and requires a trusted
external network/parent/height/profile context. All 1024 sampled nonce headers
agree across generators, complete Python enumeration and native MITM.

The smallest toy profile has matrix collisions and accepted cross-header vectors.
Another profile has no accepted vector in all 256 sampled instances. See the
[binding report](../research/header-binding-v1.md) for denominators and costs.

## Decision

Keep header binding as a separate tested interface from supplied-matrix SIS1.
Never derive expected policy from a miner's proof. Binding establishes which
instance is checked; it does not establish its intrinsic cost or availability.
Do not adopt a chainwork formula, target or monetary network using these results.

Nonce, payload and timestamp grinding remain measurable adversarial strategies.
Prior solution reuse, sparse screening and lattice-probe findings still apply;
this milestone does not supersede ADRs 0002–0004. Toy collisions do not establish
a practical attack at larger parameters, and misses do not certify secure cost.

## Next gates

Compare a practical optimized lattice solver with complete native search on
feasible profiles, including preprocessing and failed acquisition. Study explicit
candidate work models under nonce/payload/timestamp grinding, availability and
reuse. Specify block validity and deterministic resource bounds before any
difficulty/retarget/fork-choice selection. Independent cryptographic review is
required before deployment claims.
