# Exact sphere search, joint headers and competing work models

Date: 2026-10-08. Research only; no consensus, difficulty, chainwork or currency.

The new complete bounded lattice search recovers every independently verified
solution in the sampled sphere cohort. Joint header selection and target sweeps
also demonstrate why a target is not a measured SIS cost. These two experiments
are separate: lattice reduction/sphere are not yet used inside the paid header
policies. Connecting them under common budgets is the next gate.

## Reproduce and inspect

~~~sh
python scripts/check.py
python scripts/sphere_survey.py --python artifacts/flint-env/Scripts/python.exe
python scripts/joint_survey.py
~~~

Use the explicitly installed hash-pinned optional FLINT environment from
[spec 05](../../spec/05-practical-lll-and-grinding-v1.md). No auto-install, paid
CI or GitHub Actions. The ordinary check gate remains offline Cargo/stdlib Python.
See [new interfaces](../../spec/06-sphere-and-work-models-v1.md) and
[ADR 0007](../decisions/0007-sphere-and-work-models.md).

Committed summaries: [sphere-v1.json](results/sphere-v1.json) and
[joint-v1.json](results/joint-v1.json). Full ignored artifacts are
`artifacts/sphere-v1.json` and `artifacts/joint-v1.json`; compact local outputs
are the corresponding `*-summary-v1.json`. Both reports are invalidated before
build on rerun. Hashes identify source, lock, executable and optional backend;
raw evidence preserves every seed/header/certificate and per-run result.

## Complete bounded lattice enumeration

The existing finite probe only checks rows and small pair combinations. The new
solver searches all integer basis coefficients inside the norm sphere, using
exact rational Gram-Schmidt and integer square-root boundaries. The independently
audited basis spans the full modular kernel; complete tree exhaustion therefore
covers every vector in the bounded lattice domain. Canonical vectors are verified
again using SIS-LAB. Tests compare exhaustive coordinate search, equivalent
unreduced bases, deficient ranks and the old frozen missed-solution case.

Ceilings are explicit: dimension 16, 256-bit input basis/certificate entries,
one million coefficient edges, 100000 retained vectors and 4096 checked fraction
bits. A cap preserves valid partial results and never certifies nonexistence.
The survey also compares every output set with native MITM, whose vectors are
independently checked for mathematical validity and uniqueness.

| q,n,m,B2 | Records | Solvable | Empty | Canonical proof occurrences | Vectors missed by finite FLINT probe |
|---|---:|---:|---:|---:|---:|
| 17,2,4,8 | 1000 | 398 | 602 | 512 | 55 |
| 257,3,14,12 | 26 | 10 | 16 | 14 | 0 |
| 65521,4,16,8 | 25 | 0 | 25 | 0 | 0 |
| 257,4,16,8 | 25 | 0 | 25 | 0 | 0 |
| 32771,4,12,8 | 25 | 0 | 25 | 0 | 0 |
| Total | 1101 | 408 | 693 | 526 | 55 |

Both algorithms exhaust all 1101 domains with identical canonical sets, no caps
and no mismatches. Total sphere counters: 8646 coefficient edges, 2153 leaves,
59368 reconstruction terms and 526 canonical SIS checks. Zero and negative-sign
leaves account for the difference between leaves and retained vectors.

Schedule: the 1000 cheap historical lattice-v1 inputs, the 100 flint-v1 extension
inputs, and a labelled repeat of the frozen missed-solution fixture. The full
historical 1100-case lattice cohort is not repeated here. In particular, the dense
q17,n2,m12,B2=12 profile is outside this experiment. The frozen repeat has one
solution. FLINT's finite probe already finds it, while the old exact-reference
probe misses it; the new exact sphere also completes on that old reference basis
in the regression test. A single repeated fixture is not independent evidence.

The finite FLINT probe finds at least one solution on every solvable record in
this schedule, but misses 55 additional vectors. Thus sampled discovery success
still does not imply complete proof enumeration. Finding multiple vectors may
offer additional scores from one instance; it does not create independent units
of work. High-q empty profiles also show why arbitrary norms cannot simply be
adopted as a viable mining task.

Timers/counters are deliberately separate. Sphere elapsed includes its own
certificate audit, exact GSO, tree, reconstruction and verification, and excludes
construction/LLL/oracle/scoring/IPC. Native LLL construction/reduction and worker
process time are recorded separately; the client audit additionally costs time.
MITM's native timer covers its own solver scope. Different scopes prevent a direct
intrinsic-speedup claim. Local medians are machine observations in the JSON,
not portable mining rate. Arithmetic checks and captured worker output are not
OS resource enforcement or a memory-hardness proof.

## Joint header families and four score targets

The four profiles and two bases per profile are unchanged from grinding-v1.
For each base, compare nonce 64, timestamp 64, payload 64 and joint 4x4x4: 32 families,
2048 header occurrences and 1952 unique encoded headers. Shared base/axis members
explain the duplication. Each family has the same size but a different surface.
Joint ordering is timestamp-major, payload-middle, nonce-minor. Arbitrary time or
payload variants have no future block-validity guarantee.

Full availability audits complete: 769 occurrences have at least one SIS vector.
At target divisors 8/16/32/64, 329/197/89/56 occurrences have an eligible score.
This is oracle availability, not success of a particular paid policy. No oracle
enters the policy decision loop. Policies expand matrices, pay unsuccessful
checks and initial acquisition, then score actual valid vectors. Work and
domain preparation are retained even for failed runs.

| Target T | Unit hits | First hits | All hits | Reuse hits |
|---|---:|---:|---:|---:|
| 2^256/8 | 7 | 21 | 22 | 7 |
| 2^256/16 | 3 | 15 | 17 | 5 |
| 2^256/32 | 0 | 12 | 14 | 3 |
| 2^256/64 | 0 | 7 | 11 | 3 |

Each cell covers 32 runs. Overall 512 runs produce 147 hit occurrences. All 147
pass independent Rust bound validity and Python's strict external score predicate.
The same proof can occur at several targets/strategies; this is not 147 distinct
ledger blocks. Each policy/target restarts from scratch for reproducibility;
cross-target preparation is not secretly amortized. Smaller target runs retain
nondecreasing paid component counters on every family and policy.

At T=2^256/16 the joint family yields hits 1/5/5/2 versus nonce 0/3/4/1,
timestamp 0/4/5/1 and payload 2/3/3/1, each over 8 families. These outcomes do not
establish a universal joint advantage: the samples are small/correlated, and joint
uses fewer variants along each axis. The earlier single-axis result is preserved.

At the hardest sampled target the all policy makes 164643 vector checks and 468
eligible score hashes for 11 hit occurrences. First makes 157878 checks and 452
scores for 7 hits. Reuse makes 89796 checks and 91 scores for 3 hits. Unit makes 2048
checks and 76 scores with no hit; its per-hit cost is null, not zero. These costs
cannot be compared solely by successful runs or by uncalibrated checks/second.

## What the three work models mean

| Model | What it represents | What this evidence says |
|---|---|---|
| One unit per accepted proof | A counting convention | Always 1 despite changing targets and policy costs; no CPU calibration |
| 2^256/T | Ideal expected eligible score trials, assuming independent uniform hashes | Values 8/16/32/64; omits eligible-vector acquisition and correlated/repeated trials |
| Fresh SIS search per accepted proof | Assumed acquisition work before every score/hit | Universal fresh-full-search assumption remains unsupported by actual paid strategies |

The exact `ideal_target_trials` helper implements the second expression for
positive targets only. It is descriptive, not accumulated chainwork. The first
model is only a comparison convention; the third is a hypothesis to challenge,
not an implemented pricing function. A verifier cannot observe hidden prover work.

Unit policies test one sparse vector per header and can win without enumerating
the full domain. This still performs real generation, SIS checks and scoring;
zero enumeration-loop calls do not mean zero computation. Reuse pays its initial
search and then tests that vector on subsequent headers. All-vector search can
score several solutions from one instance; sphere now enumerates such sets via
a competing algorithm rather than relying on naive coordinate enumeration.

Therefore a valid vector or target hit does not certify one fresh expensive
complete SIS solve. Nor does the toy evidence prove an optimized attack on any
future production profile: larger optimized paid solver experiments are absent.
The measurable object remains a vector of preparation/generation/check/score
costs. Summaries divide **all-run** totals by hit occurrences, with exact
numerator/denominator and null for zero hits, retaining unsuccessful work.

Uniform independent score trials are an explicitly hypothetical model here.
Repeated proofs, shared headers, easy-instance selection, same-instance solutions
and preprocessing can correlate or amortize costs. No statistical fit, energy
estimate, hardware-independent conversion or selected retarget rule follows.

## Next gate

Integrate certified practical reduction and sphere/first-vector search into paid
header strategies on larger feasible profiles. Measure preprocessing/amortization,
shared-instance scores and failed acquisition under common budgets; define the
permitted time/payload surface before evaluating network work models. Only then
write a candidate fork-choice/difficulty specification with explicit adversarial
assumptions. External cryptographic review is still required before monetary use.
