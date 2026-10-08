# Exact LLL baseline: availability, certificates and a missed solution

Date: 2026-10-08. This is a bounded supplied-matrix SIS-LAB-v1 experiment.
It does not select PoW difficulty, accumulated chainwork or security parameters.

## Implementation

The [specification](../../spec/03-lattice-reduction-v1.md) describes a full integer
kernel basis from modular RREF, including noninitial pivots and deficient rank.
Pivot rows q*e_p and free-column lifts span {x in Z^m: A*x=0 mod q}; membership
plus determinant/index q^rank establishes equality with the complete lattice.

An exact-rational LLL reference reduces that basis, keeping B=U*B0. The independent
audit checks kernel membership, index, unimodularity, transformation equality and
reducedness using integer determinants and a different Gram-matrix recurrence.
The classical delta=3/4, eta=1/2 conditions and transformation contract are
documented in [Magma's reference](https://magma.maths.usyd.edu.au/magma/handbook/text/335).
This implementation uses Python fractions rather than a practical floating-point
LLL library. It is a mathematical baseline, not an optimized LLL/BKZ miner.

The finite probe checks reduced rows and small two-row combinations, normalizes
sign and verifies accepted vectors. A reduction cap leaves an equivalent
certified basis but does not claim LLL completion. Probe exhaustion only means
this candidate family is exhausted; no nonexistence conclusion follows.

## Reproduce and evidence

```sh
python scripts/check.py
python scripts/lattice_survey.py
```

The suite uses standard libraries only and the existing offline locked native
release MITM oracle. All computation is local, with no GitHub Actions or remote
compute. The run used Python 3.12.10 and the previously verified native Rust
search executable on Windows/AMD64. [The committed summary](results/lattice-survey-v1.json)
records source/configuration/test hashes, platform and executable identity.

`artifacts/lattice-survey-v1.json` holds per-instance seeds, complete basis/U
certificates, statuses, counters, timing, candidate vectors, oracle counts and
sorted oracle proof-set hashes. The compact local companion removes records.
Both outputs are marked incomplete before building, so failures cannot leave
stale successful reports. The committed summary is a snapshot of this run.
For historical native-v1 results, use their recorded source snapshot rather
than assuming current fingerprints must match an earlier experiment.

## Sampling and comparison boundary

There are 1000 cheap matrices and 100 larger matrices, satisfying the plan's
initial sampling scale. Each group has two batches: 500 cheap instances per
batch, or 8/9 per batch on larger profiles. Seeds are SHA256 of ASCII
`magnet-sis-lattice-v1/q/n/m/B2/batch/index`. The first three indices in each
larger batch instead use `magnet-sis-native-v1`; these reproduce all 36 inputs
from the preceding native CPU study. The existing SHAKE generator expands A.

Reduction and probing happen before the independent certificate audit and
exhaustive native MITM comparison. Neither an oracle solution nor its minimum
norm guides the reduction. Every oracle output is independently verified in
Python; lattice candidates must belong to the full oracle set when enumeration
completes. Candidate and oracle proof counts are distinct, since the probe does
not enumerate every vector inside the norm ball.

Availability, successful probes and misses use **completed-oracle instances**
as their denominator. Capped oracles remain recorded but are excluded from
those totals. Reduction status is retained separately even if a capped reduction
has a successful probe. In this run all 1100 reductions finish, all probes finish
and all native oracle domains exhaust; no observed result is censored by a cap.
Tests explicitly exercise partial certificates and capped-oracle aggregation.

## Availability and candidate discovery

| q, n, m, B2 | Instances | Have a solution | Basis rows succeed | Pairs rescue a row miss | Probe misses an existing solution |
|---|---:|---:|---:|---:|---:|
| 17, 2, 4, 8 | 1000 | 398 | 398 | 0 | 0 |
| 17, 2, 6, 16 | 16 | 16 | 16 | 0 | 0 |
| 17, 2, 8, 8 | 16 | 16 | 16 | 0 | 0 |
| 257, 3, 10, 8 | 16 | 0 | 0 | 0 | 0 |
| 257, 3, 12, 12 | 16 | 0 | 0 | 0 | 0 |
| 257, 3, 14, 12 | 18 | 10 | 8 | 1 | 1 |
| 17, 2, 12, 12 | 18 | 18 | 18 | 0 | 0 |

458 matrices admit an accepted vector; 642 have none in the complete norm domain.
The probe finds at least one vector on 457 of those 458 solvable instances.
This conditional observed count is not a universal success probability or a
cryptographic guarantee. The 602 empty cheap instances and 32 empty larger
instances at q=257,n=3,m=10/12 are established by complete enumeration, not LLL
failure. Another eight m=14 instances are also empty in the bounded domain.

The oracle emits 158825 vectors across all distinct instances; the finite probe
emits 3918, including pair-derived vectors. Counts are once per instance, not
independent units of work. On q=17,n=2,m=12,B2=12 alone, the oracle has 157049
vectors while the probe has 2738. A good ability to find one proof does not imply
ability to enumerate the complete accepted set, or an honest per-proof price.

## A reproducible counterexample

For q=257,n=3,m=14,B2=12 and seed
`43c60398fab2489b5fc93a7e1df30c2026fc4765db11d2235892608622d47432`,
the full native oracle has exactly one accepted vector:

```text
(1, 0, 1, -2, -1, -1, 0, -1, 0, 0, 1, -1, 0, 1)
```

Its squared norm is 12. The independently certified LLL-reduced full kernel
basis has no accepted row, and the finite row/pair probe's minimum proposed
nonzero squared norm is 16. Thus it emits nothing although a valid solution
exists. The [frozen fixture](../../tests/vectors/lattice-miss-v1.json) retains
the seed, accepted vector and reduced basis. A fast regression verifies the
vector and full-basis certificate without invoking the exhaustive oracle.

This rejects the inference "LLL-reduced basis plus this empty probe means the
SIS instance has no solution." It does not show that every LLL implementation,
basis order, parameter, larger combination search or BKZ run must miss it.

## Timing and resource limits

Each instance is measured once, in a reused Python process. Reduction timing
includes RREF construction and exact LLL, on a pre-expanded matrix. Probe timing
includes row/pair construction, sign/norm checks, SIS verification and
deduplication. SHAKE expansion, certificate audit and oracle comparison are
outside both timers. The native oracle records its solver-only internal timer.

These are different runtimes and search goals: a finite heuristic probe versus
complete enumeration. No elapsed-time speed ranking, mining rate or intrinsic
hardness estimate is claimed. Exact rational recomputation is intentionally
transparent and can be much slower than optimized reduction. Host scheduling
and frequency are uncontrolled; single-pass times do not support tail latency
or confidence claims. Raw times and descriptive medians remain in the summary.

The reference caps dimension at 16 and outer steps/size reductions at 10000.
Integer/fraction checks permit up to 4096 bits, after forming each checked value.
Temporary arithmetic can exceed that allowance. Observed bit maxima are not
allocated memory, process RSS or hard byte/time budgets. No memory/energy,
ARM, GPU or ASIC measurement is made here. All certificates remain auditable
after a cap, including a cap after a committed swap.

## Research consequence and next gate

[ADR 0004](../decisions/0004-lattice-probes.md) requires treating LLL/probe misses
as inconclusive and keeping certificate validity separate from solution discovery.
Both exact enumeration and a competing lattice family now have local baselines.
This adds evidence about the toy construction but does not close the broader
CPU/attack gate: practical fplll/BKZ/sieving, larger security-scale distributions,
preprocessing/reuse and independent cryptographic review remain absent.

Next establish an independently tested header-to-instance design and generation
path, alongside a pinned practical reduction comparison. Define the input to
network PoW before choosing difficulty, accumulated chainwork or retarget rules.
Neither a short SIS vector nor a reduced basis proves delivery of MagnetGate
network service or a particular amount of computation.
