# Persistent single-vector campaigns and repeated windows v1

Status: bounded laboratory comparison of three policies; no mining-rate or
work-weight claim. Existing WLP1 and integrated policies keep their semantics.

## Campaign input and state

`reference.campaign.run_campaign(stages, policy, target, reducer, budget=...,
on_stage=...)` accepts 1–3 stages, each 1–16 LabHeaders at dimension <=16.
Within a stage network/parent/height/profile agree. Across stages network and
profile agree, while parent/height may change. The externally configured target
uses the existing 0..2^256 bounds. A callable reducer and optional callable stage
observer are required; no initial vector or external oracle pool is accepted.

One campaign-wide LatticeBudget from spec 07 applies to all stages: reductions,
sphere nodes and scores do **not** reset. Sphere proof/bit limits remain per
visited instance. Certificate construction/audit, generation and other operations
are still paid execution outside cooperative node counts; the Windows process
boundary supplies time/commit limits. One backend setup is paid per worker.

Only one acquired vector persists, with no exact-instance matrix cache or pool:

- `restart-first`: search for the first vector independently on every visited header.
- `carry-first`: pay for acquisition until a first vector exists; recheck that
  vector on every subsequent header/context, without fallback if it fails.
- `carry-fallback`: recheck the carried vector; if invalid, explicitly pay for
  fresh first-vector acquisition and replace it when acquisition succeeds. An
  empty fresh search leaves the earlier vector available for later checks.

Fresh acquisition calls the existing on-demand `first` policy for one header,
with remaining campaign-wide node/score ceilings and one permitted reduction.
Its first score is used directly; it is not rehashed or given a second trial.
Acquisition records cumulative work through that score. A failed carried-vector
check gets no score. A valid carried vector is freshly hashed under the current
header. At most one candidate is scored per visited header. Only the first hit
in a stage is retained; later headers in that stage are skipped, but state and
remaining budgets carry into the next stage. A hit on the final allowed score
wins for that stage, then later stages remain subject to the same ceiling.

Current fallback first derives A for its carry check, then the existing acquisition
helper derives A again. **Both expansions are charged**. This transparent wrapper
does not claim the best optimized fallback implementation. `headers` counts
actual matrix derivations rather than distinct headers visited; fallback can
therefore count a header twice. Timings/counters are descriptive, not consensus
cost. Partial sphere stops retain their existing reason and do not prove emptiness.

## Results and stops

The result stores policy/target/budget, total work, stage work deltas, current-
header scored vectors/digests, hits/proofs, paid acquisition snapshots and fresh
LLL/sphere evidence. Stage work sums exactly to campaign work. Carry checks store
their header/stage indices and validity reason. Fresh evidence keeps the existing
certificate and sphere tree status. No score/cache win transfers across headers.

Stages are reported in order with `score-hit`, `stage-exhausted`, an explicit
logical cap or `not-visited` after an earlier halt. The initial stop cause is
retained; later skipped stages do not overwrite it. A logical cap is a completed,
known measurement of limited search, not a complete vector-domain conclusion.
A killed worker remains unknown regardless of recoverable stage checkpoints.
Elapsed campaign timing includes observer/checkpoint work between stages;
checkpoint serialization can expose only the last finished checkpoint, not the
unfinished current stage. Immutable completion markers remain from spec 08.

## WCP1 extension

The existing bounded worker additionally accepts `version=WCP1` with a campaign
policy name. Fields remain version/policy/target/stages/budget/cache_capacity.
`cache_capacity` must be exactly 1 as a protocol guard: this mode has one carried
vector and **no** matrix cache. Validation, same-network/profile checks and all
header/budget bounds precede optional FLINT import. WLP1 continues to accept only
its existing four policies; its stage budget/reset/cache behavior is unchanged.

A WCP1 process publishes cumulative `checkpoint-k.json` after stage k, then a
separate completed response. A logically halted campaign still reports remaining
skipped stages and a bounded final response. Parent outcomes, error semantics,
Windows Job controls and censorship rules are unchanged. These are controlled
local workers, not hostile-code sandboxes or public process-launch APIs.

## Repeated seeded experiment

`scripts/campaign_survey.py --python <pinned interpreter>` uses four profiles from
windows-v1, two schedules, seeds 2026100811/12/13, two same-input repeats,
three policies and two windows (400/1200 ms, both 64 MiB commit): **288 attempts**.
A deterministic shuffle with seed 2026100814 interleaves the entire job list;
the complete job tuple and execution sequence are retained. One shuffled pass
does not establish an execution-order-invariant performance ranking.

Base labels are `magnet-campaign-v1/q/n/m/b2/seed`, SHA256-salted with `/network`,
`/parent`, `/payload`. Height=1, timestamp=100, nonce=0. Three eight-header stages
either advance nonce (0–7/8–15/16–23), or set parent for i>0 to
SHA256(base-parent || u64le(i)), height i+1 and nonce 0–7. The two schedules share
stage 0; repeats are identical inputs, not independent proofs. Separate salted
seeds give distinct header challenges, not a general statistical independence
or unpredictable live-chain assumption. No timestamp/payload search is performed.

All cohorts get separate Python/Rust generation and complete native MITM
availability audits **outside** windows. Workers see only headers, budgets and
target. Every recovered fresh sphere set is checked for equality if complete,
or subset membership if capped. Every score/vector is recomputed against its
proper context; hits pass both Python and new Rust full admission with one
payload and timestamp interval 99–101. Native accepted hits include recovered
aborted diagnostics, which remain excluded from complete-window hit totals.

Reports preserve source/lock/backend/executable hashes, host processor/logical
CPU metadata, order, repeats, aggregate/per-seed/per-schedule results and censored
denominators. Failed reruns invalidate both reports before builds. OS measurements
include startup, backend setup and checkpoint I/O; parent audits and process/Job
creation remain outside. Logical all-run cost per hit stays null if any attempt
is interrupted. Cold-start/deployment costs cannot be read as steady mining.

Stronger LLL/BKZ/sieve/GPU solvers, vector pools, private precomputation and larger
profiles remain outside this experiment. Work pricing, chain-derived targets,
retarget and fork choice need separate evidence and decisions.
