# Small-coefficient search and paid matrix refresh

Status: laboratory contract only. SIS1 validity and all earlier APIs are unchanged.

## Family

Accept existing validated SIS1 profiles with m<=16 and B2<=12. Coefficient bound
is strictly integer 1 or 2. Candidate limit is 1..20000 and proof limit 1..256;
booleans are invalid. Matrix dimensions/residues are checked before enumeration.
The family contains all nonzero sign-canonical vectors with support size <=3,
absolute coordinates <=the bound and squared norm <=B2. Nonprimitive vectors
remain included because SIS1 permits them; their gcd category is reported.

Order support weights 1,2,3, then lexicographic coordinate combinations, then
coefficient products: first positive magnitude 1..bound and subsequent values
in [1,-1,2,-2] truncated by bound. Filter coefficient templates by squared norm.
At m16/B2=12/bound2 the full family has 18912 candidates. This is not the full
SIS norm ball: larger coefficients and supports may be omitted.

Every visited candidate is generated and screened once. Modular rows stop at
the first nonzero residue; actual coefficient products and row reductions are
counted. Setup template visits/norm terms and domain counts are separate from
screening. Output materialization and gcd classification are counted. There is
no GPU kernel or paid chunk in this interface. A candidate/proof limit can
leave an unchecked lexicographic suffix. Stop precedence is proof-limit,
candidate-limit, domain-exhausted, with independent exhaustion and cap flags.
Exactly sufficient limits do not imply an unchecked suffix. Sequential search
does not discard an accepted tail; proof caps censor unseen candidates instead.

`all_proofs_returned` refers to the whole declared family, never just the tested
prefix. Include per-weight and per-coefficient-pattern domain/tested/accepted
counts. Matrix/vector validation entry counts are logical visits, not cycles.

## Independent audits

For bounded tiny dimensions, independently scan the complete Cartesian box
[-bound,bound]^m, classify sign/support/norm and sort eligible vectors by the
specified order. Compare every candidate and capped output/ledger. Compare
complete accepted sets against BallSearch after filtering the same family;
record unfiltered ball solutions separately. Rust verifies both positive and
negative candidate verdicts using SIS1, including refreshed pool candidates.

## Fixed refresh experiment

Use six labelled steps per profile, fresh SHAKE matrices and a same-instance
control. Both coefficient families share each matrix. Each step pays matrix
generation and checks every previously retained vector against the current
matrix. Run new acquisition regardless of carry success: candidate cap4096,
proof cap32. Stable union retains valid carried vectors first, then distinct
acquired vectors, capped at32; duplicates and distinct overflow are separate.
This is a fixed-refresh policy, not an optimized adaptive miner. The acquisition
output is also the fresh-only baseline; do not infer saved work from carry hits.
Record prior pool, each carry verdict and work, acquisition ledger/proofs,
overlap, overflow and retained pool so every transition can be replayed.

Carry checks use dense coordinates and short-circuit rows. Acquired proofs are
also revalidated with their own counted terms/rows. Dedup comparisons, retained
entries and direction-gcd terms are separate counters. Retained direction
multiplicities expose legal scalar copies: each nonprimitive bound2 vector is
twice a unit vector, with identical acceptance for admissible odd-prime profiles.
Independent Rust audits and prefix-intersection audits are separate verification
work, not free search operations or an asserted consensus price.

Seed/label distinctness does not guarantee independent modular events; retain
matrix digests and collisions. Repeated controls are explicitly correlated.
For complete tiny cohorts, compare full accepted sets between bounds. For capped
cohorts, ordering differs and a bound2 prefix need not contain the bound1 prefix;
do not label output-count differences as total extra solutions.

## Evidence

Freeze the schedule before outcomes: profiles (q,n,m,B2) are (7,1,5,8),
(17,2,12,12), (257,2,16,12), (65521,3,16,12), in that order. Within each profile,
fresh cohort precedes same-instance control, steps0..5 and bound1 precedes bound2.
Initial pools are empty. Public label seed is 2026100915. Each label commits the
version/seed/profile/step; SHA256 of its ASCII text seeds existing SIS1 SHAKE
expansion. Controls use fresh step0 for all six steps. Publish exact labels/seeds,
matrix digests, shared tested-prefix counts and full tiny-cohort comparisons.
Sequential inventory observations and sums of directions are not independent
discoveries or a count of globally unique directions.

Invalidate prior raw/compact evidence before building. Capture the current
Cargo-selected verifier hash, freeze source/configuration and verify through
publication. Raw bytes have an exact digest in the compact report. Failures
retain completed records and stage but suppress success summaries; in-progress
work is unknown if it cannot be recovered. No timing ratio or consensus pricing
is published. Ordinary local checks and the affected study must pass before
commit. No cloud jobs, new packages or changes to consensus/GPU APIs are required.
