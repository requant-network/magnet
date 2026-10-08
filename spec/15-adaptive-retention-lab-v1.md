# Adaptive future-supply retention v1

This is an isolated WAX1 laboratory extension of WXP1. MGH1/MGB1 admission,
fixed-policy fork preference, production difficulty and monetary rules are unchanged.

## Campaign and retention

The existing paid campaign controls the finite header surface, matrix generation,
pool checks, combinations, eager acquisition and scores. Its optional retention
callback receives an immutable ordered candidate tuple only on a unique insertion
that overflows capacity. It must return an ordered single-eviction subsequence
of the same tuple, exactly capacity elements. Validation occurs before assigning
the pool or insertion/eviction counters. Default FIFO behavior and WXP1 stay intact.

WAX1 capacities are 1..3; overflow has 2..4 candidates. A future-supply retainer
evaluates every possible ordered retained subset using spec14's exact law and
conditional-iid score mixture at the trusted target. Keep the highest FUTURE
fresh-header model probability. Options are ordered by evicted index, with FIFO
first; ties choose the first maximizing option. FIFO wins only if it is a maximum.
Current acquired vectors need not imply independent opportunities; current A
has already been observed and is NEVER assigned this precommitted-pool law.
An optimized retention score is a hypothesis, not proved actual mining probability.

Selection decisions <=64 per campaign, no reset at a stage/header boundary.
The worker creates a fresh retainer for every independent run. After its decision
allowance, each overflow performs an explicit counted FIFO fallback without model
evaluation. Up to four laws over three vectors per decision bound exact arithmetic;
record all options, selected index, rank units, evaluations and fallback counts.
Search-node counters never absorb or disguise selection work. Both selection and
backend setup/reduction execute inside the same externally timed/memory-limited Job.

## Strict worker and resource boundary

WAX1 contains exactly WXP1's fields plus retention and decisions, version WAX1.
Retention is fifo or future-supply; decisions integer1..64, capacity integer1..3.
It normalizes the remaining fields to the existing strict WXP1 decoder before
optional imports/solver construction. The window driver explicitly allowlists
adaptive_worker.py; arbitrary filenames and diagnostic overrides reject.
Existing external wall/commit caps and immutable checkpoints remain active.

Finished snapshots retain full campaign/selection counters. Aborted windows
retain checkpoint observations but unconditional logical work is unknown, not
zero; elapsed time and outcome denominators include every scheduled attempt.
Identical trusted header schedules are paired by profile/seed/backend/window;
policies can visit different prefixes after hits/caps. Repeated scheduled
challenges across policies and windows are not independent blocks or unique work.

## Verification requirements

Audit every visited header's native generation, every acquired/carried/scored
proof's native validity and score hashes, and strict trusted admission of hits.
Replay the recorded retention decisions, complete option probabilities and
selected pool updates from the paid acquisition/combination transcript. Check
all component caps and native mode3 accounting identity where present. Native
and model re-audits occur outside the worker, never supply mining inputs.

Comparisons retain failed searches, timeouts, partial checkpoints and explicit
conditional denominators. Backend nodes have different meanings. No CPU/GPU,
ASIC-resistance, portable joule cost, mainnet profile or chainwork result follows.
