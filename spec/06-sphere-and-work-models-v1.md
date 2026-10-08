# Exact sphere enumeration and joint work-model laboratory v1

This extends the local research tools. SIS1, MGH1, their verifiers and the
research score predicate are unchanged. No chainwork or consensus rule is selected.

## Exact kernel sphere

`solvers.sphere.enumerate_kernel` accepts a SIS-LAB Profile, canonical matrix and
full modular-kernel certificate. Before the independent exact audit, bound
dimension to 16 and all initial/B/U entries to 256 bits. Audit lattice membership,
index q^rank, unimodularity and B=U*initial. A reduced certificate must satisfy
the unchanged delta=3/4, eta=1/2 inequalities. A valid equivalent unreduced
certificate is also sufficient for enumeration completeness, though less efficient.

Compute direct exact-rational Gram-Schmidt of rows b_i, with orthogonal rows
b*_i, squared norms g_i >0 and coefficients mu[j][i]. For integer coefficients
z, the norm identity is:

~~~text
||sum_i z_i b_i||^2 = sum_i g_i (z_i + sum_{j>i} mu[j][i] z_j)^2.
~~~

Enumerate i from m-1 to 0. With remaining squared radius R and center
c=-sum_{j>i} mu[j][i] z_j, require (z_i-c)^2 <= R/g_i. For reduced Fraction
c=a/b and radius squared d/e >=0, compute L=isqrt(floor(d*b^2/e)), then the
integer interval ceil((a-L)/b)..floor((a+L)/b). This is exact, including equality,
negative centers and half-integer boundaries. Recurse after subtracting exact
cost. At each leaf reconstruct z*B, ignore zero/negative canonical sign and
independently verify every retained vector with SIS-LAB. The full-rank basis
has unique integer coordinates; outputs are sorted canonical vectors.

Default/maximum ceilings: 1,000,000 coefficient-edge nodes, 100,000 retained
proofs and 4096 checked numerator/denominator bits. Exact positive integers only,
excluding bool. Reasons are `domain-exhausted`, `node-limit`, `proof-limit`,
`arithmetic-limit`. Check caps before the next charged node or retained proof:
exactly sufficient caps may complete. Partial vectors remain valid but cannot
certify completeness or nonexistence. Certificate rejection raises ValueError;
internal failed mathematical assertions raise RuntimeError.

Counters: coefficient edges, leaves (including zero/negative sign), m^2
reconstruction terms per leaf, canonical SIS checks and maximum checked fraction
bits. They exclude audit, GSO arithmetic operations, LLL and expansion. Fraction
checks occur after operations; transient arithmetic/audit and Python recursion
are not OS resource bounds. No timing or memory-hardness theorem is implied.

Background: the official [fplll project](https://github.com/fplll/fplll) documents
Kannan-Fincke-Pohst enumeration as a lattice-search family. This implementation
uses its own exact rational bounded recursion; it is not fplll, BKZ, a sieve,
pruned enumeration or an optimized native lattice miner.

## Joint headers and target grid

`joint_family(base,nonces,timestamps,payloads)` uses the unchanged single-axis
family derivations and scalar u64 overflow rules. Each exact count is 1..512;
product <=512 is checked before allocation. Ordering is timestamp outer,
payload middle, nonce inner. The first member is base; context stays fixed.
No payload contents, timestamp validity or block semantics are supplied.

The joint survey reuses grinding-v1 bases for four profiles and two batches:
nonce64, timestamp64, payload64 and joint4x4x4. These are equal-size 64-member
families, not identical search surfaces. Each is evaluated from scratch with
unit/first/all/reuse policies at T=2^256/d for d=8,16,32,64: 512 policy runs.
Preparation, acquisition, failed attempts and actual scores remain charged by
the existing policies. No complete oracle supplies vectors or guides selection.

Python/Rust independently derive every instance. A separate complete native MITM
oracle audits availability and eligible scores, with vector validity/uniqueness
checked in Python. Each actual policy hit passes Rust bound verification and
Python's external strict score target. Rust does not implement the score predicate.
For the unchanged deterministic policies, smaller targets continue the same
proposal sequence until a later hit/cap; each work component must not decrease.

## Descriptive work models

1. Unit accepted-proof weight (one per accepted proof): a possible accounting
   convention, but insensitive to changing score targets and solver costs.
2. Target-only `2^256/T`: exact Fraction for 1<=T<=2^256, interpreted solely as
   expected **eligible score trials under independent uniform score assumptions**.
   T=0 admits nothing and has no finite weight. This is neither an implemented
   fork-choice rule nor measured CPU/energy/SIS cost. The assumptions have not
   been proved for the sampled correlated headers/vectors.
3. Fresh SIS search per accepted proof: not a sound universal cost assumption.
   Compare actual paid strategies and multiple eligible vectors per instance;
   do not charge a hypothetical complete search that an actual policy omitted.

`search_loop_calls` counts policy enumeration-loop entries: unit=0,
first/all=processed headers, reuse=acquisition index+1 (or processed headers if
never acquired). Zero does not mean zero SIS work: unit still expands/checks/scores
and may repeat many times. These are descriptive policy counters, not a consensus
oracle for a prover's hidden work.

Summaries retain totals over all runs, including failures. Each component per
hit is an unreduced exact numerator/denominator, null if no hits. Preparation
box-vector count is separate from matrix/check/score counters. Repeated proofs
across families, policies, targets or repeated fixtures are experimental
occurrences; they cannot be added as globally distinct ledger work. No arbitrary
conversion from heterogeneous counters to a scalar work price is made.

## Evidence lifecycle and reproduction

Both new surveys invalidate raw and compact local evidence before building.
Only complete successful audits mark status passed. Capped sphere/oracle pairs
are excluded from availability comparisons and retain their separate statuses.
The sphere schedule contains 1000 cheap lattice-v1 cases, 100 flint-v1 extensions
and one labelled frozen repeat, not the full historical 1100-case lattice cohort.
Raw ignored artifacts retain seeds, certificates/proofs, per-run stops/counters
and oracle comparisons. Compact Git reports preserve source/lock/executable
hashes, backend identity, deterministic schedules and all denominators.

~~~sh
python scripts/check.py
python scripts/sphere_survey.py --python artifacts/flint-env/Scripts/python.exe
python scripts/joint_survey.py
~~~

The isolated optional interpreter must be provisioned explicitly according to
[spec 05](05-practical-lll-and-grinding-v1.md); the ordinary gate stays standard
library/offline Cargo. Timers are local observations: sphere time includes its
certificate audit and GSO, excludes construction/LLL/oracle/scoring/IPC; backend
worker process time additionally includes its client-independent protocol work.
Joint policy time includes its own domain preparation, generation, checks and
scores, excludes family construction and the full availability audit. Raw traces
store each scope; no optimized-miner speedup or secure network weight follows.
