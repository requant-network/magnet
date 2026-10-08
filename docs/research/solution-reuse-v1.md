# SIS solution reuse and sparse screening: experiment v1

Date: 2026-10-08. Status: completed toy experiment, not a PoW security assessment.

## Question and result

Does one valid SIS vector correspond to one independent expensive computation?
**No such correspondence follows from the current acceptance predicate.** Known
solutions can generate more accepted vectors through gcd reduction, multiplication
and small linear combinations. This directly challenges a naive work model for
candidate B (SIS plus an outer hash target).

This does not prove that every possible SIS-PoW is insecure. It does mean that
counting every proof or score input as a fresh full SIS solve is unjustified.

## Method

Run python scripts/reuse_survey.py. Raw records are written to
artifacts/reuse-survey.json. The committed [summary](results/reuse-survey-v1.json)
contains profiles, aggregates and hashes of the research code.

Seed i is SHA256 of the ASCII string:

~~~text
magnet-sis-reuse-v1/{q}/{n}/{m}/{maximum_b2}/{i}
~~~

Use SIS-LAB-v1 generation with maximum_b2 once per seed. Hold A fixed when varying
the acceptance bound. This matters: the current generator binds B2, so regenerating
A at every bound would confound a controlled threshold comparison. This experiment
is a mathematical comparison, not an implementation of consensus retargeting.

The study uses 320 matrices: 128 at (17,2,3,64), 128 at (17,2,4,32), and 64 at
(31,2,4,64). Bounds are 2,4,8,16,32,64 up to each profile maximum.

For each matrix:

1. Run the support-at-most-two sparse probe independently of the full oracle.
2. Exhaust the complete bounded space at the largest B2.
3. Filter the exact solution set for each smaller bound.
4. Give the reuse probe the first one/two solutions in the oracle's lexicographic
   enumeration order. This is an explicit source of initial knowledge, not a
   measurement of a practical miner's time to obtain those vectors.
5. Divide each seed vector by its coordinate gcd, try admissible positive multiples,
   and combine two primitive seed vectors using coefficients in [-3,3].
6. Verify every proposed vector and require all outputs to belong to the exhaustive
   solution set. Count distinct canonical vectors, not repeated submissions.

The sparse probe exhausts support ≤2 only. It is not a complete SIS solver and a
negative result does not imply that the matrix is unsolvable. Full row rank is
recorded separately; every sampled matrix in this run had full row rank.

The first two oracle solutions may be collinear; they are not necessarily two
independently discovered directions. The bounded combination probe is incomplete
and does not enumerate their entire integer span within the norm ball.

## Controlled threshold results

For q=17, n=2, m=3, the same 128 matrices generated with B2=64 were reused:

| Acceptance B2 | Solvable matrices | Matrices with >1 proof | Maximum proofs per matrix | Sparse hits |
|---|---:|---:|---:|---:|
| 2 | 4 | 0 | 1 | 4 |
| 4 | 5 | 0 | 1 | 4 |
| 8 | 11 | 4 | 2 | 6 |
| 16 | 40 | 5 | 2 | 11 |
| 32 | 106 | 22 | 4 | 13 |
| 64 | 128 | 116 | 6 | 13 |

Acceptance expands monotonically on a fixed matrix, but this does not establish
a linear relationship between B2 and search cost. These are availability and
multiplicity measurements, not solver-time distributions.

At the largest bound in each setup:

| q,n,m,B2 | Matrices | Solvable | Max proofs | Sparse hits | Max proofs derived from one known vector |
|---|---:|---:|---:|---:|---:|
| 17,2,3,64 | 128 | 128 | 6 | 13 | 5 |
| 17,2,4,32 | 128 | 128 | 17 | 38 | 4 |
| 31,2,4,64 | 64 | 64 | 21 | 9 | 5 |

The last column includes the supplied vector, and its maximum need not occur on
the same matrix as the maximum in the proof-count column. Using two known vectors
produced 108, 153 and 95 additional vectors respectively across the three maximum-
bound batches (excluding the supplied vectors, deduplicated per instance).

## Explicit counterexamples

### Multiplicity after one known solution

~~~text
q=17, A=[1,2], B2=80
known x=[4,-2]
primitive x/gcd(x)=[2,-1]
valid canonical vectors: [2,-1], [4,-2], [6,-3], [8,-4]
squared norms: 5, 20, 45, 80
~~~

All four inputs pass the existing verifier. Producing them requires elementary
arithmetic after the initial solution; no fresh lattice search is performed.
For candidate B they are four distinct score inputs under the same preheader.
This does not mean four guaranteed successful hashes, four independent SIS solves,
or four accepted blocks. No target-selection experiment is implemented here.

### Requiring gcd=1 is insufficient by itself

~~~text
q=17, A=[1,1,1], B2=6
u=[1,-1,0], v=[0,1,-1]
u+v=[1,0,-1]
u-v=[1,-2,1]
~~~

Both new vectors are primitive, sign-canonical, and satisfy the same equation
and norm bound. A primitive-only rule would remove multiples, but not these
combinations. It would change the task and still require a work analysis.

### Full rank does not imply difficult search

~~~text
q=17, A=[[1,1,0],[0,0,1]], B2=2
rank(A)=2
x=[1,-1,0]
~~~

Conversely, A=[[1,1,0],[0,1,1]], B2=3 has x=[1,-1,1] while the sparse probe finds
nothing. Both cases are regression tests, so neither rank nor a negative sparse
screen is incorrectly treated as a hardness or nonexistence certificate.

## What was NOT measured

- GPU speed, energy cost, real mining throughput, chain attacks or quantum cost.
- LLL/BKZ/sieve search behavior or the time to find the supplied seed solutions.
- Actual profitability or speedup of screening versus solving every candidate.
- A complete preprocessing attack, optimal combination strategy or real retarget.
- Whether selected large parameters preserve any of these observed frequencies.

Candidate-check counts and exhaustive-box sizes use different operations and
cannot be interpreted as a speedup ratio. Counts are deterministic; no machine-
dependent timings were used as evidence for a security claim.

## Decision and next experiment

Do not promote candidate B with an assumption of one expensive solve per score
trial. Keep A experimental too: no chainwork or calibrated search-cost model has
been established. Do not automatically replace SIS with another algorithm.

Next compare explicit bounded search strategies end-to-end, including first-
solution acquisition, matrix generation, sparse screening and reuse. Preserve
failures and total work; separate fixed-matrix threshold experiments from actual
header/profile changes. Then decide whether larger-profile CPU solver work is
justified. A consensus implementation remains premature.
