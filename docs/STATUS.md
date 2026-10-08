# Research status

Date: 2026-10-08. Phase: exact CPU search and lattice-reduction baselines.
English is primary. The [Russian initial-phase snapshot](ru/docs/STATUS.md)
records the earlier milestone and is not the current status.

## Implemented

SIS-LAB-v1 specification; exact Python and independent Rust verifiers; bounded
stdin/stdout adapter; SHAKE256 matrix expansion in Python; exhaustive tiny solver;
sparse screening, rank and known-solution reuse probes; four instrumented search
policies that acquire their own initial solutions; bounded exact meet-in-the-
middle search; incremental norm-ball enumeration; common cooperative time and
traced-allocation budgets; native Rust ball/MITM solvers and a bounded local
search protocol; larger toy CPU studies; a local check command.
Exact-rational LLL on full modular-kernel bases, independent lattice certificates
and a finite row/pair probe now provide a competing solver family.

The private repository is danifest751/magnet. The workspace is
C:/Projects/MagnetNetwork. There are no third-party dependencies: Cargo.lock
contains only the sis-verifier package. No paid CI or cloud GPUs were used.
CodeGraph and local artifacts are ignored by Git.

## Experiments

### Initial availability survey

python scripts/toy_survey.py exhausts 128 deterministic instances at
q=17,n=2,m=3,B2=8. Exactly 15 have canonical solutions, with 18 solutions total.
The remaining 113 have none within the complete bounded domain; this is not
a timeout-based inference.

### Reuse and screening survey

python scripts/reuse_survey.py studies 320 fixed matrices across three toy
profiles and up to six norm bounds. See the [report](research/solution-reuse-v1.md)
and [committed summary](research/results/reuse-survey-v1.json).

Key findings:

- At the maximum bound all sampled matrices admit solutions; some have up to 21.
- Given one oracle-selected solution, simple transformations produce up to five
  distinct valid vectors in these batches, including the supplied one.
- Primitive-vector restrictions alone do not prevent linear-combination reuse.
- All sampled matrices have full row rank; full rank does not certify hard search.
- Sparse screening can miss valid nonsparse solutions.

These are exact toy-instance observations, not mining-speed estimates or a
security proof. Initial vectors come from an exhaustive oracle. Their acquisition
cost is not included in a claimed speedup; no such speedup is claimed.

### Search strategy accounting

python scripts/strategy_survey.py runs four policies on 448 toy instances,
including 113 with no solution at the smallest profile. Policies generate their
own matrices; total counters include failed search, first acquisition, sparse
screening, reuse and scoring components. No oracle supplies initial solutions.
See the [report](research/search-strategies-v1.md) and
[committed summary](research/results/strategy-survey-v1.json).

In one 128-instance batch, first-reuse produces 181 distinct score trials versus
128 for first-restart with only 171 additional candidate proposals, plus recorded
derivation/scoring operations. Sparse-first search sometimes reduces proposals
but increases matrix arithmetic. These are logical component counts, not measured
hashrate, calibrated work or a cost-per-win ranking. The experiment's score
binds profile, seed and proof; actual block-header binding remains absent.

### Meet-in-the-middle baseline

python scripts/mitm_survey.py compares full box search with an exact split-table
solver on 64 generated toy instances, two seed batches per profile and three
score conditions. All-proofs sets and per-instance score-hit existence agree.
No search reached a cap. See the [report](research/meet-in-the-middle-v1.md) and
[committed summary](research/results/mitm-survey-v1.json).

Local instrumented Python elapsed-time ratios range from about 1.5 to 204 in
favor of MITM. Representative Python-traced peak allocations are higher for MITM;
they are not process RSS or worst-case memory. Each timed call includes generation,
preprocessing, search, scoring and output construction; audits and memory probes
are separate. These observations do not calibrate consensus work or mining rate.

### Norm-ball search and common budgets

python scripts/budget_survey.py checks exact accepted sets on 48 generated
instances and runs 648 budget windows. It compares incremental ball search with
MITM under 50 ms and 32/128/256 KiB traced-allocation ceilings, for continue,
restart and first-vector reuse at two score targets. See the
[report](research/ball-and-budgets-v1.md) and
[summary](research/results/budget-survey-v1.json).

MITM is about 8.1 to 11.6 times faster in the untraced complete-search comparison.
At 256 KiB, continuing search yields more repeated-run hits than restarting or
reuse in these batches; tighter ceilings frequently stop the Python harness.
Each six-window configuration repeats two seed schedules three times. These are
local outcomes, not independent proof counts, portable memory requirements or
a calibrated work function. Limits are cooperative and measured overshoot is
reported. Exact-search timing excludes scoring/verification; budget timing
includes them and tracemalloc overhead.

### Native CPU scale study

python scripts/native_survey.py compares native exact solvers on 36 matrices
over six profiles, including 12 shared Python comparisons, three repetitions
per solver, and a separate cap probe. Exact sets agree; every output is
independently verified. The largest complete profile is q=257,n=3,m=14,B2=12.
See the [report](research/native-cpu-search-v1.md) and
[summary](research/results/native-survey-v1.json).

MITM takes about 1.9 to 16.4 times less solver time than native ball in this run.
The q=257,n=3 profiles at m=10 and m=12 have no solutions in the sampled complete
domains. q=17,n=2,m=12,B2=12 yields 53078 vectors across six matrices. These are
toy observations, not independent units of consensus work. Native time excludes
expansion/decoding/IPC/scoring/audits; selected Vec capacity charges exclude
stack and allocator/process overhead. No memory-hardness claim is made.

### Exact LLL study

python scripts/lattice_survey.py studies 1000 cheap and 100 larger matrices,
including all 36 historical native-v1 inputs. All lattice certificates and
complete-oracle comparisons pass. Of 458 solvable matrices, the row/pair probe
finds a vector on 457. One certified reduced basis misses the existing norm-12
vector; a frozen regression preserves that case. See the
[report](research/lattice-reduction-v1.md) and [summary](research/results/lattice-survey-v1.json).

All 1100 reductions, probes and oracles complete in this run. In general,
availability/probe-success counts exclude capped oracles while retaining
reduction status. Exact rational reference time is not optimized reduction speed;
no memory, energy, mining-rate or hardness claim is made.

## Verification

python scripts/check.py currently passes:

- rustfmt and clippy without warnings;
- 65 Python tests and 8 Rust tests;
- 10009 differential Python/Rust cases, 2665 accepted, no mismatches;
- three malformed-frame checks and two empty-input/frame checks.
- 103 native-search differential instances (206 searches, 1940 verified proof
  occurrences), zero mismatches, seven cap checks, 16 malformed native requests
  and one native empty-stream check.

Tests cover manual vectors, norm and size limits, rejection sampling and its
budget, exact tiny spaces, solution reuse, support-limited search, rank, policy
completeness, acquisition accounting, caps and strict score thresholds.
MITM tests cover exact sets, collision preservation, odd dimensions, zero-left
vectors, modular wrap, norm boundaries, memory/pair caps and iterator closure.
Ball/budget tests also cover norm-ball completeness, huge box/small ball behavior,
prompt release without cyclic GC, caps/checkpoints, reuse deduplication, distinct
instance seeds and tracer cleanup on clock failures.
The latest local check report includes source hashes. An interrupted rerun
marks its report running-or-incomplete rather than leaving stale success.
Native tests include maximal modulus/norm and exactly sufficient cap boundaries.
Native reruns invalidate both reports before building; a regression test forces
a failed build to check this lifecycle.
Lattice tests cover noninitial pivots, rank deficiency, certificate tampering,
independent reducedness, exact caps, arithmetic exhaustion after a committed
swap, heuristic misses, evidence invalidation and conditional denominators.

Separate source reviews covered all seven milestones. The initial Cargo executable-
selection issue was fixed; the harness uses the artifact returned by the current
build. No required implementation findings remain in the reviewed laboratory.
This is source review, not an independent cryptographic audit.

## Still absent

An independent Rust SHAKE generator, long-running fuzzing, practical optimized
LLL/BKZ/sieve baselines, GPU mining, header binding, a work function, retarget,
blockchain, wallet and
MagnetGate integration. E1 is not claimed fully closed under the broader plan.

## Decision and next step

[ADR 0002](decisions/0002-solution-reuse.md) rejects the assumption that each
accepted proof or score trial necessarily requires a fresh SIS solve. It does
not reject every possible SIS-based PoW.

[ADR 0003](decisions/0003-enumeration-cost.md) also rejects pricing an SIS proof
by naive box enumeration. Native baselines now extend the CPU parameter scale.
The exact LLL baseline now supplies a competing family; [ADR 0004](decisions/0004-lattice-probes.md)
keeps its misses inconclusive. Next independently test header-to-instance binding
and generation alongside a practical reduction comparison and further
availability/preprocessing/reuse studies. Difficulty
and accumulated chainwork remain unselected. Common local
budgets are experimental resource allowances; local time is not a consensus
oracle and observed allocation is not a memory-hardness proof.
