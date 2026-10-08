# Norm-ball enumeration and common local budgets: experiment v1

Date: 2026-10-08. Status: completed local toy experiment.

## Result

Incremental norm-ball search produces exactly the same accepted sets as MITM
on 48 generated instances. MITM is approximately 8.1 to 11.6 times faster in
this untraced exact-search comparison on this host. This compares against a
stronger baseline than box enumeration; it does not establish intrinsic SIS cost.

The separate traced experiment runs 648 cooperative budget windows. At 256 KiB,
all windows reach the time budget. Continuing search produces more successful
scores than restart/reuse in the selected batches. At 32/128 KiB, allocation
limits change or terminate the comparison. There is no universal policy ranking
or calibrated consensus work model in these results.

## Incremental algorithm

At each vector prefix, retain its remaining squared-norm allowance. The next
coordinate is restricted to magnitude at most floor(sqrt(remaining)). Until
the first nonzero coordinate, permit zero and positive values only; thereafter
both signs are allowed. Subtract the coordinate square and update each row's
modular residue incrementally. At a leaf, reject the zero vector and emit the
vector if all residues vanish. No out-of-ball vector is constructed.

Every canonical vector in the norm ball satisfies all prefix restrictions, so
it is visited exactly once. Row updates preserve A*x modulo q; the predicate is
unchanged. Tests compare output against the independent exhaustive oracle for
m=1 through 6. A 20-coordinate, B2=1 test visits only 21 leaves, including zero,
despite its bounding box having 3^20 vectors. This demonstrates why the box-size
cap is not used as a ball-search preflight. A separate 1000000-prefix-node cap
limits work, and a cap/interruption is never reported as complete exhaustion.

The implementation uses recursive methods, avoiding a self-referential closure
that would retain finished searches until cyclic GC. Tests disable cyclic GC
and require completed and explicitly closed search objects to be released.
The MITM baseline adds optional checkpoints at half tuples, table insertions
and collision pairs. With no checkpoint the accepted set and counters remain
unchanged; it still uses half-box, table-entry and join-pair safety caps.

## Exact-search measurement

Run python scripts/budget_survey.py. Full records are written to ignored
artifacts/budget-survey.json. The committed [summary](results/budget-survey-v1.json)
contains configuration, aggregates, environment and source SHA256 hashes.

Each of three profiles gets two batches of eight seeds. Exact-search seed is
SHA256 of the ASCII string
magnet-sis-ball-v1/{q}/{n}/{m}/{b2}/{batch}/{index}, starting both indices at zero.
Every algorithm generates its own matrix and receives no known solution. Three
repetitions alternate algorithm order; deterministic output must agree across
repetitions. Independent acceptance audits and exact-set comparisons are untimed.
No run reaches a safety cap.

The timer includes generation, complete search, retained proof construction,
iterator cleanup and counter snapshots. It excludes scoring and per-proof
verification. Tracing is disabled. Durations below sum per-instance median
elapsed times across 16 instances; they are not total script runtime.

| q,n,m,B2 | Accepted vectors | Ball ms | MITM ms | Local ratio |
|---|---:|---:|---:|---:|
| 17,2,4,32 | 155 | 43.609 | 5.370 | 8.12 |
| 17,2,6,16 | 635 | 232.565 | 19.971 | 11.65 |
| 17,2,8,8 | 556 | 262.712 | 23.910 | 10.99 |

For (17,2,6,16), ball visits 250464 nonempty prefixes and 190352 leaves across
the batch; MITM visits 11664 left and 11664 right tuples and 1842 matching pairs.
These different components cannot be divided to produce a work-price ratio.
The seeds and timed workloads differ from the earlier scored MITM survey, so
its ratios are not a direct before/after comparison on identical tasks.

## Common budget experiment

Every window receives a maximum 50 ms elapsed-time allowance and an incremental
Python-traced allocation ceiling of 32, 128 or 256 KiB. Both solvers use the
same guard and the existing profile/seed/vector score, at targets 2^252 and 2^248.
Generation, preprocessing, search, verification, scoring, reuse, transcript
updates, counter aggregation and iterator cleanup consume the window's time.
Each scored vector is independently verified inside that window. No oracle
supplies initial vectors. The exact-search timing table is a different workload.

| Policy | Behavior after a valid vector whose score misses |
|---|---|
| continue | Resume the same solver on the same instance |
| restart | Close the solver and generate the next matrix |
| reuse | Reduce that vector by its gcd, score admissible positive multiples, then generate the next matrix |

A score hit also starts the next instance. Reuse skips the original vector,
so it is not hashed twice. Retain only eight hit samples and a rolling transcript
hash, rather than a growing proof history. A 4096-instance safety limit and the
solver-specific safety caps are separate from resource limits; the survey rejects
windows ending at those safety limits. No such window occurred.

Each configuration has six windows: two root schedules, repeated three times.
Root seed is SHA256 of the ASCII string
magnet-sis-budget-v1/{q}/{n}/{m}/{b2}/{batch}. Instance i is SHA256 of ASCII
MagnetNetwork/SIS-LAB/budget-seed/v1 followed by a zero byte, the 32-byte root,
and i as little-endian u32. Every algorithm/policy receives the same scheduled
prefix for that batch. Faster policies can consume more seeds. These repeats
do not create six independent seed schedules or globally distinct proofs.
Reported hit sums are outcomes across repeated runs, not monetary rewards.

Cases are rotated and reversed between repetitions. GC runs before each fresh
window, outside its budget. A dedicated tracemalloc session observes allocations
after it starts; the preexisting profile, root and fixed runner preamble are not
included. Peaks include Python allocation caches, transient structures, matrix
and solver state, counter aggregation, hit-sample growth and cleanup. They are
not process RSS or a byte limit on just the table. Tracing and frequent clock
checks add overhead; this experiment cannot be compared directly to untraced
timings or an optimized native miner. Cache growth can dominate small ceilings.

Enforcement is cooperative: a tuple/prefix/pair/score operation can finish
before the next check detects exhaustion. A completed score/hit is counted
before that post-operation check. Cleanup can also overshoot. Maximum observed
elapsed time was 50.141 ms, and the largest allocation-ceiling excess was 1833
bytes. These observations are not hard overshoot guarantees. Checkpoint failures
close active searches, and tracing stops even if the clock raises an exception.

## Budget outcomes

The following table shows summed hits across six repeated windows per cell at
256 KiB. Every window in these rows ended at the time limit, rather than an
allocation/safety limit. All rows still share only two schedules per profile.

| q,n,m,B2 | Target | Ball continue | Ball restart | Ball reuse | MITM continue | MITM restart | MITM reuse |
|---|---|---:|---:|---:|---:|---:|---:|
| 17,2,4,32 | 1/16 | 5 | 3 | 3 | 36 | 12 | 15 |
| same | 1/256 | 0 | 0 | 0 | 3 | 0 | 0 |
| 17,2,6,16 | 1/16 | 6 | 3 | 3 | 39 | 0 | 0 |
| same | 1/256 | 0 | 0 | 0 | 9 | 0 | 0 |
| 17,2,8,8 | 1/16 | 6 | 0 | 0 | 36 | 3 | 3 |
| same | 1/256 | 0 | 0 | 0 | 6 | 3 | 3 |

At 32 KiB all windows terminate at the allocation ceiling. At 128 KiB all ball
windows reach the time limit; most MITM windows terminate at the allocation
ceiling. Full stop counts, elapsed-time medians and peaks are in the summary.
This is a restriction of the implemented Python harness, not a claim that the
mathematical algorithm inherently requires those byte counts.

At (17,2,4,32), 256 KiB and target 1/16, MITM reuse produces 253 score trials
versus 233 for restart, and 15 versus 12 repeated-run hits. Continue produces
850 trials and 36 hits. This illustrates why cheap extra vectors after one
solution and restarting quickly do not automatically maximize results under a
common allowance: preprocessing and traversal order also matter. Small samples,
repeated schedules and scheduler variation preclude a general optimum claim.

Host: Python 3.12.10, Windows 10 build 19045, AMD64 Family 25 Model 117 Stepping
2. Operation counts are deterministic for completed exact searches; budget-window
counts, transcripts and wall times can change with scheduling. Source hashes and
seeds reproduce the setup, not identical measured durations or window endpoints.

## Decision and next gate

[ADR 0002](../decisions/0002-solution-reuse.md) and
[ADR 0003](../decisions/0003-enumeration-cost.md) remain in force. Common local
allowances are now implemented, but local wall time is still not a consensus
oracle, and allocation observations do not establish memory-hardness.

Next compare these CPU algorithms at larger scales with a native implementation
and characterize which parameter ranges remain plausible before choosing a work
model. LLL/BKZ/sieve alternatives and independent cryptographic review remain
separate research gates. Difficulty, chainwork and production parameters are
unselected; no mathematical rule was changed to remove the measured shortcuts.
