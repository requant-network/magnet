# Findings so far

Date: 2026-10-10. Primary question and ordering follow the working
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
decision-bearing step at that milestone was a separately precommitted replication
on fresh common streams, reported below. External cryptographic review remains
outstanding. Ctrl+C/deadline/
audit failures preserve completed and unknown current work, suppress comparisons
and retain the frozen native identity. Publication reads back raw/config/report
bytes and rechecks contract/source/native hashes; a rejected publication is
retained locally rather than counted as successful evidence.

## D3 replication: the selected signal did not reproduce

The prospective [section9 protocol](CRITICAL-PATH.md) and implementation were
committed at `c932176` before execution. On the selected `(17,3,16,12)` profile,
24 fresh common streams replace the original three; no historical outcomes are
pooled. All576 campaigns complete, including three deterministic timing repeats.
Only repetition0 contributes to the exact diagnostic. The solver, proxy,
per-stream budget and >2x threshold are unchanged.

| Construction | Successes: plain / probe / random4 / screened4 | Screened/plain | Screened/random4 | Frozen diagnostic |
| --- | --- | --- | --- | --- |
| A | 73 / 73 / 61 / 70 | 0.959x | 1.148x | Not triggered |
| B | 26 / 26 / 15 / 20 | 0.769x | 1.333x | Not triggered |

Both groups now exceed the floor of5 successes for every policy. Ratios account
for actual charged units and overshoot; the table rounds exact fractions from
the [compact evidence](research/results/d3-screening-replication-v1.json).
The original 2.75x A observation does not reproduce in this fresh cohort. This
does not establish statistical equivalence, a secure SIS work function or the
absence of other screening attacks. The profile was selected because of that
earlier signal, so this is a targeted replication, not a population estimate.

Independent Python replay reconciles3,009,712 candidate visits,2,474 generated
header occurrences and603 eligible proof occurrences. Native Rust checks1,581
deduplicated header/proof/admission requests;1,467 rejected/unsearched header
occurrences stay paid. All timing repetitions reproduce full logical transcripts.
Sources, contract, config, native executable and persisted raw/compact bytes are
fingerprinted and checked. Total cold campaign time is38.29 seconds, descriptive
only. Raw transcripts are local under `artifacts/`; compact evidence is tracked.
The local gate passes345 Python tests,23 Rust tests and all differential corpora.
Source review covers preserved v1 headers/defaults, fresh namespaces, schedule
counts, explicit primary classification and failed-audit comparison suppression.

The next decisive experiment is a precommitted D4 first/subsequent acquisition
comparison under shared budgets. Do not rerun D3 with tuned proxies until a
distinct, explicitly justified falsifier changes the decision. CPPminer offline
integration and exact INT8 Tensor Core decomposition are [parked D5 options](research/gpu-readiness-v1.md),
not implemented miner support or evidence of GPU advantage. No GPU/miner/server,
consensus, wallet or GitHub Actions configuration changed in this batch.

## D4: exact complete-kernel transfer has a narrow conditional bound

The prospective [section10 protocol](CRITICAL-PATH.md) and implementation were
committed at `da6bda9` before execution. This tests full paid preparation transfer
to fresh MGH1 challenges, rather than repeating a cold-LLL donor-vector comparison.
Distinct matrices can define the same modular-kernel lattice, so the cache uses
the complete canonical RREF kernel, profile and rank. Recipient membership alone
is insufficient: the independent certificate audit also checks rank/index and
the exact transformation. A lower-rank receiver can accept old basis vectors
without the old basis spanning its complete kernel.

For a fixed rank-r donor rowspace and fresh independent uniform n-by-m matrix,
all donor-kernel vectors transfer with probability `q^[-n(m-r)]`; equal kernels
have probability `product(i=0..r-1, q^n-q^i)/q^(n*m)`. These laws are exhaustively
checked over all6,642 donor/receiver pairs for q3,m2,n1/n2, including rank0.
For a cache adapted to past observations, capacity C and H fresh opportunities,
the union bound is `min(1,C*H*q^[-n(m-min(n,m))])`. At `(17,2,8,8)`, C8,H256,
this is `2048/17^12`, approximately3.515e-12. The bound conditions on each new
matrix being uniform and independent given history; it does not establish that
SHAKE-generated or adaptively selected headers satisfy that assumption.
A fixed legal nonzero donor vector alone has acceptance probability q^-n,
identical to a free fixed candidate such as e1. Beating cold LLL would therefore
not establish valuable preprocessing of that candidate.

All8 externally bounded integration workers complete: two profiles, two fresh
labels, cold and kernel-cache, eight distinct headers each. Calibration q3 has
4 and3 cache hits, two involving different matrix bytes. Primary `(17,2,8,8)`
has0 hits across16 cached receiving headers. All four paired proof/score
transcripts agree. Across both policies,64 generated headers and64 returned
proof occurrences produce192 independent Rust header/validity/score requests.
Replay reconciles1,086 sphere-search nodes. Search replay shares the enumeration
implementation; Rust independently checks validity and score thresholds, not
search completeness. The [compact evidence](research/results/d4-kernel-transfer-v1.json)
binds source/contract/config/native/raw identities and publication readback.

Cold performs32 reductions; cache performs25 reductions plus32 paid kernel
fingerprints. Misses duplicate kernel construction before preparation, and hits
pay recipient certificate audit. Timers and named counters are descriptive;
no weighted speed/energy advantage is inferred. Zero primary hits cannot validate
a tiny probability statistically. The mathematical conditional model parks only
the exact complete-kernel collision route, not preprocessing/reuse generally.
Partial bases, geometry learned from donors, multiple same-header proofs and
adaptive header selection remain open. Neither A nor B is promoted.

The gate passes358 Python tests,23 Rust tests and all differential corpora.
The affected actual FLINT/portfolio check passes168 searches on24 tiny matrices
with no mismatch. Regression tests reject recipient/donor/ledger/score tampering
and retain owned attempts/checkpoints through worker errors, memory errors and
driver interruption, explicitly leaving in-flight work and unavailable Job
measurements unknown. No CPPminer, GPU server/miner or CI was used. Any future
CPPminer implementation must branch from the owner's `release/fork` branch.

## Current conclusion

No deterministic monotone portable reuse-resistant weight is established.
Existing naive vector/score-count weights have counterexamples. A-vs-B remains
open under the critical path; implementation volume does not close it.
Continue with [open questions](OPEN-QUESTIONS.md), falsifying proposed weights
before choosing monetary rules or expanding hardware interfaces.
