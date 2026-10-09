# Independent native small-coefficient search: five-task block

Date: 2026-10-09. Local laboratory baseline; consensus and SIS1 are unchanged.

| Task | Result |
| --- | --- |
| Native contract | [Spec23](../../spec/23-native-small-coefficients.md): bounded SCP1/SCR1 frames and exact sequential stops |
| Independent Rust engine | [sis-coeff](../../crates/sis-verifier/src/coeff_main.rs): support<=3, coefficients ±1/2, including nonprimitive proofs |
| Strict Python adapter | [Client](../../reference/native_coefficients.py): bounded pipes, timeout, no usable partial failure, complete semantic reconciliation |
| Differential/boundary corpus | [Audits](../../scripts/native_coefficient_checks.py): ordered ledgers, tiny boxes, malformed requests and an actual late search witness |
| Frozen comparisons and refresh | [Survey](../../scripts/native_coefficient_survey.py), [compact evidence](results/native-small-coefficients-v1.json) |

The local gate passes 309 Python tests, 23 Rust tests, rustfmt/clippy and all prior
differential corpora. The new corpus contains 768 native/Python comparisons,
7352 returned-proof validity checks, 48 independent tiny-box/full-ledger audits
(1700 candidates), 16 malformed-input rejections and an empty-stream check.
Release runs repeat that corpus, complete 312 timed comparisons and 192 paid
fresh/control acquisitions, and check 3054 positive/negative verdicts through
the independent release Rust SIS verifier. No dependency, GPU/miner, paid cloud
or GitHub Actions changes were needed.

## What the engine proves

Rust independently enumerates support weights, lexicographic column combinations
and coefficient templates. The Python reference independently constructs the
same declared family. Both retain exact proof order, per-weight/per-coefficient
censuses, 13 logical work counters, the checked interval and the unseen suffix.
Norm-filtered domains differ between bound1 and bound2. A miss only describes
the tested prefix of this support<=3 family, not all SIS solutions.

Output-cap triggering candidates are counted, then search stops immediately.
There is no discarded accepted chunk tail. Proof-limit takes primary-reason
precedence; exhaustion is separately true if that proof is the last candidate.
Exactly sufficient candidate caps exhaust the domain. Legal scalar copies remain
included; a primitive direction is an accounting key, not an independent event.

The maximum-shape audit actually runs native SEARCH at q65521,n64,m16,B2=12.
Thirteen identity rows force the first13 coordinates to zero; one row constrains
the final three columns by (-1,-1,2). Padding to64 rows preserves the problem.
An independent three-coordinate Cartesian oracle predicts six accepted vectors.
Native search screens all18912 candidates and returns all six, including the
late nonprimitive vector `(0,...,0,2,2,2)`. This covers a suffix that a zero-matrix
256-proof output cap would leave unsearched.

## Local timing: three separate scopes

The native timer starts after request framing, before profile/residue validation
and owned matrix copying, and ends after search/census assembly, before response
encoding. Python timing surrounds its existing validation/search/result assembly.
Batch roundtrip starts a fresh process and includes pipe exchange/wait; host
request encoding and all response decoding/reconciliation are outside that timer.

Every individual timing is positive and all three repetitions are retained.
Profiles (q,n,m,B2) are (7,1,5,8),(17,2,12,12),(257,2,16,12),(65521,64,16,12).
Two fixed comparison seeds, both coefficient bounds and four (candidate,proof)
cap pairs are crossed with five fixtures. The frozen total is104 cases per
repetition,312 comparisons. A batch is one process serving all104 requests.

The table below reports the range of the two seeded case medians at cap20000,
proofcap256. It does not divide these differently scoped measurements.

| Profile | Bound | Python median range, ms | Native internal median range, ms |
| --- | ---: | ---: | ---: |
| (7,1,5,8) | 1 | 0.0992–0.1060 | 0.0022–0.0027 |
| (7,1,5,8) | 2 | 0.3547–0.3668 | 0.0042–0.0066 |
| (17,2,12,12) | 1 | 1.2299–1.3283 | 0.0097–0.0105 |
| (17,2,12,12) | 2 | 9.1972–9.5165 | 0.0376–0.0415 |
| (257,2,16,12) | 1 | 2.9515–3.0093 | 0.0185–0.0187 |
| (257,2,16,12) | 2 | 22.6833–22.8750 | 0.0801–0.0830 |
| (65521,64,16,12) | 1 | 3.1312–3.1423 | 0.0196–0.0200 |
| (65521,64,16,12) | 2 | 23.3272–24.6194 | 0.0797–0.0809 |

The104-request roundtrip spans5.7073–6.2360ms, median5.8919ms on this run.
Each response is reconciled by re-running the reference search outside that
roundtrip. The strict adapter therefore is not an end-to-end acceleration claim.
These are small, noisy, local descriptive samples, not isolated/portable hardware
performance, GPU comparisons, difficulty or consensus chainwork estimates.

## New fresh/control schedules

Three new seed labels, four profiles, both bounds, two cohorts and four sequential
steps yield192 acquisitions. Each begins from an empty pool and pays acquisition
at every step (cap4096/proofs32), plus previous/acquired dense checks, stable exact
deduplication, direction accounting and pool32 retention. Matrix preparation is
recorded separately. The existing paid Python refresh policy is used with native
acquisition; independent Rust verifies every tested carry and acquired proof.
This is not an independently rewritten native refresh policy.

| Cohort | Acquisitions | Acquired occurrences | Successful carry / checked | Censored acquisition |
| --- | ---: | ---: | ---: | ---: |
| Fresh matrix | 96 | 687 | 54 / 515 | 47 |
| Same-instance control | 96 | 648 | 486 / 486 | 48 |

Controls repeat exactly their corresponding fresh step-zero matrix. Pools, scalar
copies and repeated controls are correlated observations. Different capped family
prefixes and the finite selected seeds prevent general availability or work-saving
claims. Always-paid acquisition does not establish an adaptive saving policy.

## Provenance and reproduction

Run `python scripts/check.py`, then `python scripts/native_coefficient_survey.py`.
Cargo selects current release `sis-coeff` and `sis-verify` artifacts from build
JSON. Their hashes and the source manifest are captured before experiments and
rechecked through publication. Compact evidence binds the exact UTF8/LF digest
of ignored `artifacts/native-small-coefficients-v1.json`, which retains all
matrices, ordered outputs, timings, transitions and roundtrips. Failed runs
invalidate previous success before builds and preserve completed records plus
unknown in-progress work without a successful timing summary.

Next: a matched in-process small-coefficient GPU comparison with honest output
and host-validation scopes, then stronger adversarial acquisition/work arguments.
The security/economic gate remains open. See
[ADR0019](../decisions/0019-native-small-coefficients.md) and the
[Russian report](../ru/native-small-coefficients-v1.md).
