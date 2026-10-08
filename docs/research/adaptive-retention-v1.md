# Paid adaptive retention: bounded CPU experiment

Date: 2026-10-09. Research evidence only; no production work rule is selected.

## Result

The exact fixed-pool model now drives a paid, bounded retention policy. Its
choices are replayable, its selection cost is visible, and every observed hit
passes independent Rust laboratory admission. This experiment does **not**
demonstrate an improvement in hit counts over FIFO.

There are 336 scheduled attempts: 306 completed and 30 externally terminated
for wall time. Among 84 FIFO/future-supply pairs, both attempts completed in 75
pairs. All 75 have equal stage-hit counts. The other nine pairs are censored or
incomplete and are not treated as ties. Equal hit counts do not imply equal
cost, identical proofs, or absence of an advantage in other workloads.

The policy made non-FIFO choices, so this was not merely FIFO with a different
name. Of 1953 completed-attempt model decisions, 1433 evicted the oldest vector,
486 rejected the incoming vector, 26 evicted index 2 and eight evicted index 1.
Nevertheless, these changed pools produced no paired hit-count improvement in
this finite schedule. The selector's added overhead remains part of the attempt.

## Construction and contract

See [specification 15](../../spec/15-adaptive-retention-lab-v1.md) and
[ADR 0014](../decisions/0014-paid-adaptive-retention.md).

On overflow, the candidates are the existing ordered pool plus the newly
acquired vector. The selector evaluates every order-preserving single-eviction
subset using the exact modular-rank distribution from the
[precommitted-pool model](precommitted-pool-supply-v1.md). It maximizes the
model's probability of at least one eligible score on a **future fresh matrix**.
It does not assign that probability to the already observed matrix from which
the incoming vector was obtained.

The calculation assumes iid uniform future matrix entries and uniform
independent scores conditional on the complete matrix and valid-vector set.
These assumptions are explicit hypotheses, not established properties of the
deterministic SHAKE/SHA-256 construction or bounds against adaptive adversaries.

Capacity is 1–3, model dimension is at most 16, and at most 64 decisions are
evaluated per worker campaign. After this cap, subsequent overflows use an
explicitly counted FIFO fallback. Maximizing ties select the first eviction
index, so FIFO wins a tie only when it is itself maximizing. A callback cannot
inject vectors, duplicate or reorder them, or change the requested capacity.

Campaign counters retain their prior meanings. Modular-rank arithmetic units,
subset evaluations and selection decisions have a separate ledger rather than
being silently counted as solver nodes. Both kinds of work, backend setup,
certificate checks and publication occur inside the worker's external window.
Model rank units and different backends' node counters are not portable prices.

## Reproduce

Run from the repository root on the tested Windows host:

```sh
python scripts/check.py
python scripts/adaptive_survey.py --python artifacts/flint-env/Scripts/python.exe
```

The optional environment must satisfy the existing hash-pinned FLINT lock;
the ordinary test gate uses standard libraries and offline Cargo builds.
This survey does not install dependencies or invoke GitHub Actions.

- Seeds: 2026100903 and 2026100904; shuffled attempt order: 2026100905.
- Profiles `(q,n,m,B2)`: `(7,1,3,8)`, `(17,2,8,8)`, `(257,3,14,12)`.
- Backends: MITM, sparse-first, LLL75, LLL99, BKZ4, BKZ8 and finite sieve.
- Configurations: restart-all/FIFO, pool-all/FIFO, pool-fallback/FIFO and
  pool-fallback/future-supply. Pool capacity 3; combinations disabled.
- Three parent/height stages per campaign; each stage has 16 scheduled headers
  from four nonces, two timestamps and two payloads. There are 288 globally
  distinct scheduled headers, repeated across policies/backends/windows.
- Shared campaign caps: 100000 solver nodes, 24 acquisitions, 8192 checks,
  4096 scores and six acquired proofs per search. Target is `2^252` with the
  existing strict predicate. Budgets persist across stages.
- External Windows Job ceilings: 500 or 4000 ms, 128 MiB private commit.

The immutable raw attempt records are ignored under
`artifacts/adaptive-retention-v1.json`; the committed
[compact result](results/adaptive-retention-v1.json) contains configuration,
grouped outcomes, audits, source/executable hashes and observed FLINT metadata.
Evidence is invalidated before rebuilding and accepted only if source hashes
are unchanged at completion. Source manifests now include `solvers/*.py` and
the FLINT lock as well as the existing source/specification files. Earlier
reports remain historical evidence with their original manifests.

## Observed outcomes

Each table row schedules 42 attempts: three profiles, two seeds, seven backends.
Hits and visited stages below include completed attempts only.

| Policy / retention | Window ms | Completed | Timeouts | Visited stages | Stage-hit occurrences |
|---|---:|---:|---:|---:|---:|
| restart-all / FIFO | 500 | 34 | 8 | 91 | 78 |
| pool-all / FIFO | 500 | 35 | 7 | 94 | 80 |
| pool-fallback / FIFO | 500 | 35 | 7 | 94 | 80 |
| pool-fallback / future-supply | 500 | 34 | 8 | 91 | 78 |
| restart-all / FIFO | 4000 | 42 | 0 | 108 | 84 |
| pool-all / FIFO | 4000 | 42 | 0 | 108 | 84 |
| pool-fallback / FIFO | 4000 | 42 | 0 | 108 | 84 |
| pool-fallback / future-supply | 4000 | 42 | 0 | 108 | 84 |

Completed attempts visit 802 stages with 652 hit occurrences. Three additional
hit occurrences survive in interrupted checkpoints and are audited separately.
These 655 occurrences are repeated laboratory observations, not 655 independent
blocks, distinct challenges, or newly solved SIS instances.

Completed campaign reasons are 222 campaign-exhausted, 44 acquisition-limit
and 40 node-limit. Completing a worker does not mean exhausting the mathematical
search domain or finding a hit on every scheduled stage.

Completed-only component totals include 3606 visited headers, 3420 acquisitions,
5102694 solver nodes, 6196 pool checks and 9380 score hashes. Model selection adds
1953 decisions, 7812 subset evaluations and 901843 rank arithmetic units, with
324 counted FIFO fallbacks after the decision cap. Checkpoints include another
28 model decisions, but the unobserved work of terminated attempts remains
unknown. Accordingly, unconditional work-per-hit is `null`; partial snapshots
are not silently treated as final totals.

The maximum observed Job commit is 43352064 bytes. This is an observed process
tree allocation, not a memory-hardness requirement. All-attempt elapsed time
includes 30 failures and startup/setup; no elapsed-time, energy, profitability
or universal node-weight ranking is inferred. The ordinary local check suite
ran concurrently during part of this series, so hardware performance was not
isolated. Short-window completion counts are host/load observations.

## Independent checks

Every available full or checkpoint transcript is deterministically replayed
against its original header schedule, using recorded acquired outputs rather
than a new solver. Campaign counters, pool evolution, hit records and the exact
retention ledger must agree after actual JSON serialization.

The independent Rust audit checks generation, acquired proofs, carried vectors,
score digests, strict targets and complete trusted-context LabRules admission
for each hit. Across full and partial transcripts it covers 3750 visited header
occurrences, 9489 scores, 655 hit occurrences and 1981 model decisions, using
40442 native requests, with zero mismatches. Some acquisition/pool observations
are deliberately rechecked independently outside the paid worker. This audit
does not supply free proofs or search inputs to the worker.

Outer campaign acquisition charges are also reconciled with backend metadata:
MITM left/right/pair counts, sparse checks, and lattice search plus BKZ nodes.
A consistently altered outer ledger cannot hide native acquisition work.
Regression tests cover this falsification, altered proof/model ledgers, JSON
checkpoints, source-manifest solver edits and failed-build evidence invalidation.

The local gate passed 205 Python tests, 19 Rust tests, rustfmt/clippy and all
existing verifier, generation, score/admission, block and chain differential
corpora. Source review is not external cryptographic certification.

## Interpretation and next gate

The finite model supplies a concrete adaptive strategy with auditable cost.
It is not an upper bound on all adaptive attacks or evidence for a chosen
production profile. This schedule did not reward its changed retention choices
in paired stage-hit counts; other targets, capacities and adversarial pool
construction remain open experiments.

Next compare stronger acquisition/retention policies and optimized hardware on
equal paid scopes. The available local CMP 50HX can support the next correctness
stage; see [GPU readiness and first experiments](gpu-readiness-v1.md). No GPU
miner or GPU speed advantage has yet been demonstrated. Production work,
chainwork, secure retarget and monetary rules remain unselected.
