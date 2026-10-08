# Exact precommitted-pool supply and fresh-header evidence

2026-10-09. This milestone studies eligible-input supply; it does not select
production chainwork, dynamic difficulty, a cryptocurrency or launch parameters.

## Result

A fixed collection of short vectors has an exactly computable acceptance-count
distribution under an explicit iid-uniform prime-field matrix model. Modular
linear dependencies change that distribution. Pool size alone does not identify
independent valid-vector opportunities, including pools whose every pair is
independent. This quantifies one bounded reuse model; it is not an adversarial
SIS work bound for an adaptive optimized miner.

Delivered: [model and resource contract](../../spec/14-precommitted-pool-supply-v1.md),
bounded exact Python implementation, independent complete-matrix enumeration,
paid setup/fresh-header survey with native audits, and
[ADR 0013](../decisions/0013-precommitted-pool-supply.md).
The [compact evidence](results/precommitted-supply-v1.json) preserves configuration,
two seed labels, every retained pool, exact laws, denominators, setup/scan work,
source hashes and native executable hashes. Raw setup attempts, complete header
encodings, valid vectors and digests are under ignored artifacts/precommitted-supply-v1.json.

## Derivation and assumptions

Choose a pool of k<=6 distinct canonical vectors before seeing a fresh A.
Existing Profile enforces prime q and B2<q^2, so every eligible vector has
nonzero residue modulo q. Each uniform matrix row accepts a fixed vector with
probability 1/q; n independent rows give q^-n.

For a subset S, rank r over F_q gives joint probability q^(-n*r).
The implementation computes every subset rank and uses exact binomial-moment
inversion to obtain P(K=j), where K counts valid vectors. The full specification
contains the proof and finite arithmetic bounds. This is a self-contained
derivation in the declared mathematical model, not an external security theorem.

Under the ADDITIONAL hypothesis of uniform-independent scores conditional on
the matrix and its full valid-vector set, T/2^256 is each valid input's strict
score probability p. The pool-only per-header probability is
sum_j P(K=j)*(1-(1-p)^j). This is not calibrated time, energy or chain weight.
Header expansion and score domain separation do not prove either idealization.
Adaptive pool choice after seeing the new matrix violates the precommitment model.

### Frozen algebraic counterexamples

At q=7,n=1,B2=8, pool ((1,0),(2,0)) contains different proof encodings but the
same acceptance event. P(K=0)=6/7, P(K=1)=0, P(K=2)=1/7. At T=2^255,
the conditional-iid score mixture gives 3/28; falsely assuming independent vector
acceptance gives 27/196. The second vector creates a distinct score input when
valid, without creating a new independent matrix-acceptance event.

Pool ((1,0),(0,1),(1,1)) has pairwise ranks 2 but triple rank 2.
P(K)=(30/49,18/49,0,1/49). Three-vector validity is not jointly independent.
All three vectors are primitive; an integer-primitive restriction alone would
not remove this example. Independence shortcuts can err in different directions;
no universal correction factor or pool speedup follows.

## Complete arithmetic audit

28 cases enumerate 3957 matrices, including repeated underlying matrix spaces
under different pools. Prime q=2/3/5/7, n=1/2 and m=2 exercise single vectors,
independent bases, proportional inputs, modular dependencies and a dependent
triangle. Every empirical complete-space distribution equals the exact law,
with zero mismatches. These are exact enumerations, not statistical uniformity tests.

Unit tests additionally exercise the maximal admitted Profile and six-vector
pool, target 0/1/3/full, external fraction-size rejection, and exact arithmetic
budget 27 versus 26 for the frozen three-vector fixture. Rank operations and
fraction bit sizes are bounded; resource counters do not price all implementation
work or establish memory hardness.

## Paid setup and real headers

Two seed labels, three candidate Profiles and three fresh axes are scheduled.
Each acquired setup probes at most 16 headers, native mode3 with 250000 combined
proposal/pair nodes per attempt, table cap10000, pair cap250000 and output cap6.
Every attempt's generation and every returned proof are independently audited
by Rust using the original MGH1 header. Work and failures are retained before
the pool is frozen. A proof-limit return is a partial pool, not an exhaustive oracle.

At q=7,n=1,m=3,B2=8 both acquired pools contain five vectors. At
q=17,n=2,m=8,B2=8 both contain six. Four additional q=7 diagnostic pools are
preselected proportional/triangle vectors: they are not advertised as solver
acquisitions and no solver call is charged. Validation is recorded explicitly.

Both q=257,n=3,m=14,B2=12 setup attempts exhaust their 16-header allowance
without a returned vector. Each charges 4000000 native proposal/pair nodes.
All stop reasons remain in raw evidence. No absence of mathematical solutions
is inferred from these bounded searches.

The ten setups schedule 30 cohorts; 24 complete, six are explicitly skipped
because their prerequisite setup failed. Each successful pool is held fixed
through 256 nonces, 256 fresh parent/height contexts and 256 fresh payloads.
Axis-specific domains keep all 6144 measured headers globally distinct.
They are real MGH1 encodings with independently derived matrices, not 6144
accepted MGB1 blocks or a running network. Matrix collisions remain possible
and are counted per cohort rather than silently discarded.

All pool vectors are checked and every valid vector is scored even after a hit.
The same digest is compared at four targets; it is not charged as four hashes.
Native audits cover fresh generation, every vector's validity, every score hash
and every valid vector's strict target result. There are 42063 audit requests,
including setup audits, with zero mismatches.

| Profile/pool | Headers | Vector checks | Valid score inputs | Headers with any valid vector | Hits T=2^252 | Hits T=2^255 |
|---|---:|---:|---:|---:|---:|---:|
|7/1/3/8, acquired size5|1536|7680|1078|764|77|453|
|7/1/3/8, proportional size2|1536|3072|468|234|25|174|
|7/1/3/8, triangle size3|1536|4608|671|603|34|304|
|17/2/8/8, acquired size6|1536|9216|40|40|2|12|

All 24 cohorts retain target-zero failures. At full target, hit counts equal
headers with a valid vector. Total fresh scan: 38400 matrix entries expanded,
24576 vector checks, 2257 score hashes and 434144 score-input bytes.
The four acquired pools additionally charge 1763 native proposal/pair nodes;
failed larger-profile setups charge 8000000 more. Setup generation and validation
costs are separate and retained once per declared pool, shared across its three
cohorts. Native audits, model calculation, startup, other hashes and energy are
outside these scan component counts. No wall-clock speed ranking is claimed.

## Verification and remaining gate

The local check gate passes 189 Python tests and 19 Rust tests, existing
Python/Rust differential corpora and full 6236-command independent chain checks.
New negative tests reject false enumeration under python -O, setup-only native
generation corruption, fresh-audit disagreement and stale success after failed
builds. Fresh-context source review found fraction-bound and setup-audit gaps;
both are fixed and regression-tested. This is not external cryptographic review.
No GitHub Actions, cloud GPU jobs or MagnetGate changes were used.

Next: measure paid adaptive pool/header selection and stronger solver portfolios
on the same declared challenges and budgets; account for sparse preselected inputs,
acquisition, rank diversity, preprocessing and failed windows. Develop a portable
adversarial argument before assigning cumulative SIS work or selecting retarget.
This exact fixed-pool model closes a finite arithmetic question, while E3's
economic/security gate and E4's monetary safety gate remain open.
