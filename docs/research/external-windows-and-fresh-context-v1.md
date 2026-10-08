# External windows, fresh contexts and trusted admission v1

Date: 2026-10-08. Descriptive Windows laboratory evidence, not calibrated mining
or a consensus proposal. This study extends the paid practical policies without
changing their algorithms or the existing score hash.

## Reproduce

~~~sh
python scripts/check.py
python scripts/windows_survey.py --python artifacts/flint-env/Scripts/python.exe
~~~

Use the explicitly isolated, hash-pinned python-flint 0.9.0 environment described
in [the practical backend report](practical-lll-and-grinding-v1.md). Windows Job
Objects are required; there is no platform fallback. All builds and experiments
are local, Cargo is offline/locked, and no GitHub Actions or cloud jobs are used.
See [spec 08](../../spec/08-external-windows-and-lab-admission-v1.md) and
[ADR 0009](../decisions/0009-external-windows-and-trusted-surface.md).

[Committed compact evidence](results/windows-v1.json) preserves configuration,
native backend identity, source/lock/executable hashes, availability counts and
all resource/policy/schedule aggregates. Ignored `artifacts/windows-v1.json`
retains headers, exact-instance fingerprints, oracle set digests, every worker
result and recovered proof/certificate/score. Ignored per-attempt `window-*`
directories preserve requests, immutable checkpoints and completion markers.
Reports are invalidated before builds so a failed rerun cannot retain stale success.

## Cohorts and paid boundaries

Four profiles use three stages of eight headers, for two schedules. `fresh-nonce`
advances nonce from 0–7 to 8–15 and 16–23 under the same parent. `fresh-parent`
uses three deterministic parent/height contexts, resetting nonce to 0–7. The
schedules share stage 0; policies and resource allowances repeat the same cohorts.
This gives 192 header occurrences, **160 distinct headers** and **128 exact
profile/matrix identities** across the input cohorts. Counts are not independent
block/proof discoveries.

| q / n / m / B² | Nonce: solvable occurrences / 24 | Parent: solvable occurrences / 24 | Distinct matrices: nonce / parent |
|---|---:|---:|---:|
| 2 / 1 / 3 / 1 | 22 | 22 | 7 / 8 |
| 17 / 2 / 8 / 8 | 24 | 24 | 24 / 24 |
| 257 / 3 / 14 / 12 | 19 | 17 | 24 / 24 |
| 257 / 4 / 16 / 8 | 0 | 0 | 24 / 24 |

All independent native MITM oracles exhaust their bounded domains. Python and
Rust derive identical matrices from each header. Oracles are outside resource
windows and supply no vectors to policies. Empty complete domains are availability
observations for these profiles, not evidence that interrupted search found none.

Each of four policies gets a fresh suspended-launched process at each time/memory
configuration. The common window covers all three stages, Python/FLINT import,
backend identity/warmup, generation, search, exact audits, scoring and checkpoint
I/O. It excludes parent serialization/process creation, Job setup, reading/auditing
outputs and independent oracles. One reducer setup is charged per worker;
cooperative budgets and first-vector acquisition reset each stage. Only the
bounded cache-all preparation cache persists between stages. Persistent
cross-context vector-acquisition campaigns are not compared.

## OS outcomes and censoring

Three time allowances and two committed-memory ceilings, 48 and 128 MiB, yield
192 attempts: 64 attempts per time allowance, one fixed-order pass per cell.

| Whole-worker allowance | Completed / 64 | Timeout / 64 | Observed elapsed range, ms | Stages recovered from aborted workers |
|---|---:|---:|---:|---:|
| 200 ms | 0 | 64 | 200.05–215.00 | 0 |
| 400 ms | 34 | 30 | 239.42–416.04 | 38 |
| 1200 ms | 64 | 0 | 247.35–749.28 | 0 |

All 200-ms attempts terminate before publishing a stage checkpoint. This is a
cold-worker result, not a zero-search-cost measurement. The 400-ms boundary
produces interrupted processes with recoverable completed stages; no such stage
becomes a completed-window win. All 1200-ms attempts complete at both commit
ceilings. The main cohort has no classified memory failure or unclassified abort.

Total observed in-window elapsed time is 61.55 seconds across all attempts.
Maximum reported process commit is 31748096 bytes (about 30.28 MiB); maximum
deadline overshoot is 16.04 ms. These are Windows committed-memory counters and
local measured timing, not RSS, energy, portable limits or hard real-time bounds.
The 48-MiB main allowance did not bind these tiny cases. Separate actual-OS tests
confirm a 100-ms stalled worker is terminated and a 256-MiB allocation is denied
inside a 48-MiB Job; catching MemoryError reports exit 77. Missing native diagnostics
alone do not establish memory exhaustion.

Across the 98 completed workers, 105 stage hit occurrences are retained. Their
logical totals include 1302 reductions, 38553 sphere nodes and 1792 score hashes,
including complete unsuccessful stages. These totals are conditional on completed
workers. All 94 aborted workers have unknown total logical work; unconditional
logical work per hit is **null**, never calculated by substituting zeros.

All recovered scored vectors match complete oracles and recomputed digests.
There are 112 independently checked hit occurrences including seven recovered
from aborted workers. Each passes the Python lab score/admission and Rust bound
SIS verification. The seven are excluded from the 105 completed-stage hits.
Rust still does not independently implement the Python score/admission predicate.

## Full-window policy comparison and fresh preparation

For the 1200-ms cohort all 16 workers per policy complete: four profiles, two
schedules and two memory ceilings. Each worker has three stages, so the hit
denominator is 48 stage opportunities per policy. Memory-ceiling pairs repeat
the same deterministic mathematical experiment.

| Policy | Stage hit occurrences / 48 | Paid reductions | Sphere nodes | Score hashes | Exact-cache hits |
|---|---:|---:|---:|---:|---:|
| first | 10 | 352 | 8436 | 226 | 0 |
| all | 24 | 272 | 9292 | 334 | 0 |
| reuse | 0 | 138 | 2920 | 78 | 0 |
| cache-all | 24 | 214 | 10674 | 394 | 58 |

These counts describe these visited headers and discovery orders. Reductions,
nodes and hashes are not interchangeable work units. Cache-all eagerly completes
sorted pools, while all streams candidates and can stop earlier; identical hit
counts do not establish identical preparation or elapsed cost. Failed reuse
attempts remain charged even though this fixed-vector policy gets no eligible
score in these stages.

All 58 cache hits in the full-window cohort come from the tiny q=2 collision
control. Every larger profile has zero exact-cache hits under both fresh schedules.
The input matrices really repeat in that control despite distinct headers/seeds.
This contrasts with fitted replay in the previous milestone: fresh headers do not
automatically preserve preprocessing savings. Zero hits in these larger tiny
batches also do not prove impossibility of useful cross-instance strategies.

## Trusted surface and interpretation

The parent configures LabRules independently for each stage: exact context and
profile, target 2^256/16, one allowed payload commitment, inclusive base timestamp
±1. The experiment mines only the fixed timestamp/payload. Nonce remains bounded
by the header's u64 encoding. Forbidden context/profile/time/payload and a zero
target are rejected before matrix derivation; score equality at T is rejected.

This makes admission policy executable without treating miner-selected settings
as trusted. It does not establish payload-body validity, parent-chain existence,
consensus clock rules or network target derivation. Fresh-parent contexts are
deterministic inputs, not linked real blocks. Difficulty, chainwork, retarget,
wallets, payments and MagnetGate integration remain absent.

The fixed-order single-pass worker runs share OS cache/load and have no repeated
independent seed batches or rotated execution order. Results near 400 ms are
sensitive to host state and backend startup. No policy throughput ranking,
deployment recommendation, GPU/ASIC advantage, cryptographic hardness or
production parameter selection follows. Stronger solvers and broader permitted
grinding surfaces remain unmeasured.

## Verification and next gate

The local gate passes 120 Python tests, 13 Rust tests, rustfmt/clippy and all
10009 verifier, 103 native-search and 1936 generation/binding differential cases
with zero mismatches. New regressions cover actual OS timeout/allocation denial,
Windows ABI sizes, malformed protocol, interrupted completion markers, fresh
schedules, stale-evidence invalidation, strict external targets and censored
work/hit denominators. A separate source review found no required findings.
These are engineering checks, not an external cryptographic audit.

Next repeat independent seeded/rotated windows, separate steady-state campaigns
from cold startup while retaining initial cost, test persistent cross-context
acquisition and stronger practical baselines. ADR 0009 records requirements for
chain-derived profile/target, payload/time validity, cross-language score rules
and adversarial retarget/fork-choice simulations before a consensus candidate.
