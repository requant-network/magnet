# Meet-in-the-middle SIS baseline: experiment v1

Date: 2026-10-08. Status: completed local toy experiment.

## Result and interpretation

An exact meet-in-the-middle (MITM) search solves the same SIS-LAB-v1 task as the
existing enumeration baseline. Across the selected toy batches, it took about
1.5 to 204 times less elapsed time in these instrumented Python implementations.
It used more Python-traced peak allocation in every representative memory probe.

This is evidence against pricing the task by naive box enumeration. It does not
establish a production mining rate, large-parameter hardness, ASIC resistance or
a secure chainwork formula. The acceptance predicate and score format are unchanged.

## Algorithm and completeness

Split x into a left part of floor(m/2) coordinates and a right part. For every
left part in the bounded integer box:

1. Compute its squared norm and reject it if it exceeds B2.
2. Reject a negative first nonzero coordinate; a negative left part can never
   produce a sign-canonical complete vector. Keep the all-zero left part.
3. Compute its modular syndrome A_left*x_left and store the vector and its norm
   in a dictionary bucket keyed by that syndrome.

Enumerate right parts with squared norm at most B2. Look up the bucket for
-A_right*x_right modulo q. For every entry in that bucket, require the combined
norm to be positive and at most B2 and the whole vector's first nonzero
coordinate to be positive. Emit it without repeating a full matrix multiplication.

Every accepted whole vector lies inside the enumerated half boxes; its two
syndromes sum to zero and its halves survive pruning. Thus a completed run
enumerates the exact accepted set. Buckets store lists, rather than one vector,
so colliding syndromes do not silently discard solutions. Each pair of halves
identifies one vector: no proof-deduplication set is required. Tests compare the
result against independent exhaustive enumeration, including zero matrices,
odd dimensions, m=1, modular wrap, and vectors with a zero left part.

The search bounds each half box at 100000 tuples, retained table entries at
100000, and visited collision pairs at 1000000. Excessive half boxes are rejected
before search. Exceeding an entry/pair limit reports a distinct stop reason;
partial results do not prove nonexistence. Explicit iterator closure records
interruption, including closure before its first step. Completed searches have
reason domain-exhausted. A limit equal to the exact required number can complete;
the solver stops only when another insertion or collision visit would exceed it.

The table entry cap is an object-count bound, not an exact byte limit. Vectors,
syndromes, bucket lists and retained output also consume memory. Highly colliding
matrices can approach the pair cap even with a small number of buckets.

## Reproduction and measurements

Run python scripts/mitm_survey.py. The raw report is written to the ignored
artifacts/mitm-survey.json. The committed [summary](results/mitm-survey-v1.json)
preserves configuration, aggregate counters, environment and source SHA256
hashes; it omits per-seed proofs and individual timing samples.

Four profiles each receive two batches of eight seeds: 64 generated instances
in total. A seed is SHA256 of the ASCII string
magnet-sis-mitm-v1/{q}/{n}/{m}/{b2}/{batch}/{index}, with both indices starting at
zero. Neither solver receives a solution or oracle output. Each independently
generates its own matrix. There is no preselection based on solution availability.

Both solvers use the existing domain-separated profile/seed/vector SHA256 score
from the [strategy study](search-strategies-v1.md). Conditions are: target zero
to enumerate all proofs, target 2^252 (nominal 1/16), and target 2^248 (1/256).
For positive targets stop immediately at the first hit. Full search permits
1000000 proposals; MITM uses its default bounds. No run reached a cap.

Each solver runs three times per instance/target, alternating which solver goes
first. A small unrecorded instance warms up both paths. perf_counter_ns measures
generation, preprocessing, search, scoring, output construction and logical
counter instrumentation. Acceptance audits, exact-set comparisons and report
aggregation happen outside the timer. Deterministic results must agree across
repetitions. Time sums below are sums of per-instance median elapsed times,
not total script runtime or medians of batch runtimes.

Memory is probed separately with tracemalloc after garbage collection for batch
zero, index zero, target zero, once per profile and solver. The reported peak is
incremental Python-traced allocation during that call, including temporary
structures and retained proofs. It excludes preexisting interpreter allocations,
untraced native allocations and process RSS. One chosen seed cannot establish
typical or worst-case memory. Existing object reuse can affect traced allocation.

Host: Python 3.12.10, Windows 10 build 19045, AMD64 Family 25 Model 117 Stepping
2. Other running processes, GC and scheduling can affect elapsed time. Three
repetitions and small batches do not establish statistical confidence. Logical
operation counts are deterministic; elapsed times need not reproduce exactly.

## Observations

Each row covers 16 instances; durations are milliseconds summed as above.
Ratio is full-search elapsed time divided by MITM elapsed time.

| q,n,m,B2 | Condition | Full search ms | MITM ms | Local ratio | Instances with score hit |
|---|---|---:|---:|---:|---:|
| 17,2,3,8 | all proofs | 1.799 | 1.159 | 1.55 | 0 |
| same | 1/16 | 1.833 | 1.218 | 1.51 | 0 |
| same | 1/256 | 1.760 | 1.151 | 1.53 | 0 |
| 17,2,4,32 | all proofs | 149.471 | 6.144 | 24.33 | 0 |
| same | 1/16 | 125.809 | 5.318 | 23.66 | 7 |
| same | 1/256 | 148.538 | 6.020 | 24.68 | 0 |
| 17,2,6,8 | all proofs | 159.607 | 5.904 | 27.03 | 0 |
| same | 1/16 | 137.222 | 5.346 | 25.67 | 8 |
| same | 1/256 | 154.513 | 5.805 | 26.62 | 1 |
| 17,2,6,16 | all proofs | 4396.698 | 21.757 | 202.08 | 0 |
| same | 1/16 | 2592.247 | 14.368 | 180.42 | 15 |
| same | 1/256 | 4188.974 | 20.539 | 203.95 | 2 |

All-proofs runs yield exactly the same sets: 0, 146, 91 and 650 vectors total
across the four batches respectively. All 16 matrices in the first batch have
no accepted vector. This small outcome is retained, not discarded. Positive
targets also agree on which individual instances admit a hit. Different traversal
orders can produce different vectors and hash-trial counts before the first hit.
No score hits in a target-zero row are expected by definition.

At (17,2,6,16), full enumeration visits 8503056 whole vectors across the batch.
MITM visits 11664 left and 11664 right tuples, stores 2064 left entries in total,
and visits 1806 matching pairs. These are different operations and are not a
standalone speedup ratio. Matrix dot-product terms fall from 2284032 to 37056.
Preprocessing is rebuilt for every instance, and is included even for an early hit.
MITM norm counters also include every visited half tuple; sign, matrix, row,
table, lookup and collision counters are recorded separately. They do not cover
all allocations, hash-table operations or machine instructions.

Representative traced peak allocations in bytes:

| q,n,m,B2 | Full search | MITM |
|---|---:|---:|
| 17,2,3,8 | 3474 | 7248 |
| 17,2,4,32 | 4682 | 30801 |
| 17,2,6,8 | 4722 | 29233 |
| 17,2,6,16 | 9418 | 74817 |

The enumeration baseline is deliberately simple and visits negative-sign and
out-of-ball vectors before rejection. Incremental ball enumeration or compiled
solvers could narrow these ratios. MITM also has overhead and a memory cost;
neither implementation is an optimized miner. Comparisons are across independent
profile-bound matrices, not fixed-matrix changes to B2 or a real retarget.

## Decision and next gate

[ADR 0003](../decisions/0003-enumeration-cost.md) prohibits treating enumeration
runtime as the intrinsic price of an SIS proof. [ADR 0002](../decisions/0002-solution-reuse.md)
still requires accounting for multiple score inputs after one solution.

Next add an incremental norm-ball enumeration baseline and compare it with MITM
under explicit time and memory budgets. Include restart, continued search and
solution reuse in that comparison; repeat across more seeds and parameter scales.
This establishes an empirical solver envelope before considering large-profile
lattice solvers or proposing difficulty and accumulated chainwork. No blockchain
consensus, work formula or production parameters are selected here.
