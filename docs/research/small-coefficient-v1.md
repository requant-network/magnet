# Small coefficients and fixed paid matrix refresh

Date: 2026-10-09. Laboratory correctness and operation accounting only.

This block completes three connected tasks: bounded support search with
coefficients ±2, independent complete-domain and ledger audits, and a fixed
refresh experiment on fresh matrices versus same-instance controls. It does
not change SIS1 validity, consensus, admission or the earlier GPU APIs.

In six complete tiny cases, bound 2 adds 143 valid vectors and 122 normalized
directions relative to bound 1. The distinction matters: scalar copies are legal
SIS1 proofs but have correlated acceptance. The campaign performs 96 acquisition
searches and 612 paid carry checks across 48 records. Rust independently checks
23450 positive/negative verdicts across the audits and experiment.

See [spec 21](../../spec/21-small-coefficient-search.md),
[compact evidence](results/small-coefficient-v1.json),
[ADR 0017](../decisions/0017-small-coefficients-and-refresh.md) and the
[secondary Russian report](../ru/small-coefficient-v1.md).

## Family, order and scope

The new Python interface caps m at 16 and B2 at 12, with support size at most3,
coefficient bound 1 or2, candidate cap 20000 and proof cap 256. It includes all
sign-canonical vectors in that family, including nonprimitive ones. The largest
family contains 18912 candidates. Norm-filtered coefficient templates are
enumerated by support weight, lexicographic positions and the specified signed
coefficient order. This is a separate API, not a modification of unit GPU search.

For A=[1,2] modulo17 and B2=5, (2,-1) is valid while the bound 1 family is empty.
For A=[1,1] and B2=8, both (1,-1) and (2,-2) are legal, but represent the same
primitive direction. Every nonprimitive vector in this family is twice a unit
vector. Profiles permitting coefficient2 have odd prime q, so multiplication by2
does not change kernel membership. Distinct primitive directions can still be
linearly dependent; direction counts are not independent-work counts.

The operation ledger counts candidate generation, actual sparse row products
and modular reductions with early rejection, template visits/norm terms,
materialized entries and gcd terms. Matrix/vector shape-validation visits are
reported separately. These are defined component counts, not all machine
instructions, cycles, allocator traffic or an economic work formula.

Search stops sequentially at output/candidate limits. Every cap-triggering
candidate is paid. There is no discarded accepted chunk tail; the unchecked
suffix has unknown acceptance. Independent cap/exhaustion flags preserve exact
boundaries, and completeness always refers to the entire declared family.
Per-weight and per-coefficient-pattern censuses expose prefix bias.

## Independent verification

Eighty tiny Cartesian cases cover m=1..5, B2 values1/2/3/4/5/8/9/12 and both bounds.
The independent signed-box oracle compares every ordered candidate. Rust checks
all 2995 candidate verdicts, including negatives. An independent oracle rebuilds
every full/capped search field: returned vectors, charged work, weight/pattern
censuses, checked intervals and stop/completeness flags. Tampered counters,
empty censuses and fabricated completion are rejected by regression tests.

Six filtered comparisons use an exhausted full BallSearch at m=4, q=7 and B2
5/8/12. At B2=12, the full ball has 53 solutions, but bound 2/support<=3 has 26;
the remaining 27 demonstrate that the new family still omits valid SIS solutions.
No agreement is accepted if the ball oracle stops at its node cap.

The maximum-shape audit uses q=65521, n=64, m=16 and B2=12. All 18912 sparse verdicts
agree with dense Python and Rust. A constructed last-support witness with
coefficients (2,2,2), norm 12 and modular wraparound occurs at ordinal 18906.
This checks the whole maximum family mask, not just early returned proofs.

The local gate passes 279 Python tests and 21 Rust tests, rustfmt/clippy and all
prior differential corpora. Thirteen new tests cover enumeration, norm/caps,
scalar copies, carry rejection, stable retention, validation accounting,
tampered evidence, schedule/control mapping and failed-build invalidation.

## Frozen refresh schedule

Profiles are (q,n,m,B2): (7,1,5,8), (17,2,12,12), (257,2,16,12) and
(65521,3,16,12). Each has six fresh steps and six same-instance control steps.
Both coefficient families share the current matrix. Seed label 2026100915 and
exact label derivation are frozen in spec21 and source before outcomes.
The fresh cohort has 24 distinct matrix digests; controls repeat each profile's
fresh step 0. Seed labels are public experiment inputs, not secret keys.

At every step the policy pays matrix expansion, densely rechecks the previous
pool, acquires up to 32 new proofs within 4096 candidates and revalidates acquired
proofs. It always performs acquisition, even if carry already fills the pool.
Stable union keeps carried vectors first, then distinct acquired vectors,
retaining at most32. Exact-vector overlap and distinct overflow are separate;
direction counts and retained multiplicities expose scalar-copy occupancy.
Dense carry/acquisition-recheck rows short-circuit; their actual products and
reductions, shape-validation visits, merge comparisons, retained entries and
direction-gcd terms are separate counters. Rust verification is an audit phase.

| Cohort across both families | Carry checks | Valid carried vectors |
| --- | ---: | ---: |
| Fresh matrices | 297 | 32 |
| Same-instance controls | 315 | 315 |

All 32 fresh carry successes occur in the q=7 tiny profile: 10 for bound 1 and22
for bound 2. The other fresh profiles yield zero successful carry checks. Pools
with no acquired proofs supply no carry trials; their empty results remain in
denominators. Sequential pool observations, scalar copies and control repeats
are correlated, so this table is not an independent probability estimate.

The same-instance control mostly rediscovers its deterministic first inventory.
It tests validity/replay, not useful accumulation or saved acquisition. Since
this policy pays new search every time, carry success alone establishes no cost
saving. We do not convert the new vector counts into consensus work.

Bound1 campaigns exhaust their family. Forty-seven bound 2 searches leave an
unchecked suffix due to candidate or output caps. The two enumeration prefixes
cover different candidates. Raw records retain their tested intersection and
accepted shared candidates; a capped output difference is not full-family yield.
Full cross-family comparisons are restricted to six separately exhausted q=7/m=5
cases: 55 bound 1 proofs versus 198 bound 2 proofs, with 143 extra vectors and 122
extra directions summed per case. These are not globally unique discoveries.

## Reproducibility and next step

Prior evidence is invalidated before building. Cargo selects the verifier from
the current offline/locked build, and its hash is captured before experiments.
The report freezes 190 source files and binds the exact UTF8/LF raw JSON digest.
Sources and verifier are checked through publication. Failed runs retain
completed records, unknown in-progress work and failure diagnostics instead of
successful summaries. Local raw evidence stays in ignored artifacts.

Run `python scripts/check.py` and `python scripts/small_coefficient_survey.py`.
The study uses standard-library Python and the existing Rust verifier. No new
packages, GPU allocation, miner/service changes, GitHub Actions or cloud jobs
are required. No hardware speed ratio is measured in this block.

Next compare broader acquisition strategies under common paid budgets and
fresh-challenge schedules, then add an optimized native/GPU implementation of a
selected family when measurements justify it. Full SIS supply, portable work
pricing, security parameters and production accumulated chainwork remain open.
