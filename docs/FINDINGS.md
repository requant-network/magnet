# Findings so far

Date: 2026-10-09. Primary question and ordering follow the working
`docs/CRITICAL-PATH.md`. These findings concern tested constructions,
not a general impossibility theorem for lattice-based PoW.

## Validity does not price work

Python and Rust independently verify SIS1 and laboratory header/block validity.
A valid short vector does not certify a particular number of operations, energy
cost or delivery of network service. The verifier is useful supporting machinery,
not the missing work-weight argument.

Legal sign/scalar/combination reuse and repeated score trials invalidate the
simple equivalence “one accepted vector or score attempt = one fresh SIS solve”.
See [reuse](research/solution-reuse-v1.md),
[header selection](research/practical-lll-and-grinding-v1.md) and
[paid fresh supply](research/precommitted-pool-supply-v1.md). These are concrete
counterexamples to those simple accounting assumptions; they do not reject all
possible constructions A or B.

## Logical meters and local timing remain descriptive

Equal-weight component budgets preserve paid preparation, acquisition and
retention, but their coefficients are an arbitrary experimental model.
See [component comparison](research/cooperative-acquisition-v1.md).
Fixed proof counts and normalized direction counts contain dependencies.

[Native small coefficients](research/native-small-coefficients-v1.md) distinguish
internal search from process roundtrip and host audit. The matched
[CPU/CUDA block](research/matched-coefficients-v1.md) is a bounded D5 pilot:
equal domain, caps, output and host timer. CPU has lower elapsed time in716/720
pairs and in every seeded group's median paired ratio. It shows no GPU advantage
for this family/fresh-session workload. It does not measure energy or memory
scaling and cannot resolve portable work.

## D2: explicit nominal weights, no selected consensus weight

[Critical path §8](CRITICAL-PATH.md)
fixes the trusted context, miner-controlled nonce and complete predicates.
Three candidate credits are distinguished: A-unit (one accepted header),
A-density (`q^n/N(m,B2)` for the complete canonical norm ball) and B-score
(`2^256/T` under random-oracle assumptions and an unlimited supply of fresh
eligible messages). None proves the price of acquiring an input. The density
reciprocal is not a measured or proven expected search cost; increasing nominal
credit does not prove increasing adversarial computation or energy.

MGH1 binds nonce into the matrix seed as well as the score. Changing nonce
therefore changes the challenge. This closes one particular score-only nonce
shortcut; multiple vectors from the same challenge remain a separate reuse risk.
No reported counter or local timer is installed as a trusted consensus weight.

## D3: paid screening signal, with insufficient successes

The frozen `d3-screening-v1` campaign compares plain sequential search,
single-header row0 probing, random batch4 selection and maximum-survivor batch4
selection. All generated/rejected headers, probes, search misses, dense
verification and score misses are charged. B keeps searching after a score miss.
The existing support<=3, coefficients ±1/±2 family is unchanged; this is neither
complete norm-ball search nor a secure SIS parameter set.

All 288 runs complete: four profiles, three labels, A/B, four policies and three
rotated timing repetitions. Only repetition0 contributes to the diagnostic.
The independent replay checks 1,150,494 candidate visits and 3,559 eligible proof
occurrences across 4,201 generated headers, including 1,858 rejected/unsearched
header occurrences. Native Rust reconciles 1,470 unique headers and 4,255 requests
including every eligible A/B proof and B score miss (deduplicated messages).
The other repetitions reproduce complete logical transcripts exactly.

Primary results below aggregate the three labelled streams. Success counts are
ordered plain / probe-control / random4 / screened4. Ratios use actual charged
units including overshoot; rounded figures here are descriptive. Exact fractions
and fingerprints are in the [compact evidence](research/results/d3-screening-v1.json).

| Profile `(q,n,m,B2)` | Construction | Successes | Screened/plain | Frozen diagnostic |
| --- | --- | --- | --- | --- |
| `(17,3,16,12)` | A | 4 / 4 / 4 / 11 | 2.750× | Insufficient successes |
| `(17,3,16,12)` | B | 2 / 2 / 2 / 3 | 1.500× | Insufficient successes |
| `(7,4,16,12)` | A | 15 / 15 / 8 / 16 | 1.067× | Not triggered |
| `(7,4,16,12)` | B | 4 / 4 / 1 / 5 | 1.250× | Insufficient successes |
| `(257,2,16,12)` | A | 1 / 1 / 1 / 0 | 0 | Insufficient successes |
| `(257,2,16,12)` | B | 0 / 0 / 0 / 0 | Undefined | Insufficient successes |

The first A profile shows about 2.75× against each control, but every control has
only four successes. The precommitted floor is five for each compared policy,
so **no declared kill criterion fires**. On the second A profile, screening is
about 2× random selection but only 1.067× the stronger sequential/probe controls;
all three controls must be beaten by strictly more than 2×. Five of six primary
comparisons lack the declared success floor. Neither result establishes that A
is safe or that B repairs it; the screening question remains open.

This is a reproducible signal, not a statistical confidence claim or a general
negative result for SIS-PoW. Do not tune this campaign retrospectively. The next
decision-bearing step is a separately precommitted replication on fresh common
streams, with adequate controls and budget, before declaring D3 resolved or
moving to D4. External cryptographic review remains outstanding. Ctrl+C/deadline/
audit failures preserve completed and unknown current work, suppress comparisons
and retain the frozen native identity. Publication reads back raw/config/report
bytes and rechecks contract/source/native hashes; a rejected publication is
retained locally rather than counted as successful evidence.

## Current conclusion

No deterministic monotone portable reuse-resistant weight is established.
Existing naive vector/score-count weights have counterexamples. A-vs-B remains
open under the critical path; implementation volume does not close it.
Continue with [open questions](OPEN-QUESTIONS.md), falsifying proposed weights
before choosing monetary rules or expanding hardware interfaces.
