# ADR 0009 — Bound experiments externally and fix admission policy outside proofs

Status: accepted research constraints; difficulty, retarget and chainwork deferred.

## Decision

Measure practical policies in suspended-launched Windows Jobs with shared time
and committed-memory allowances. Charge imports/setup and checkpoint publication
inside the elapsed window. Preserve aborted-attempt OS costs; never replace lost
logical counters with zero or call recovered hits complete-window wins. Keep
immutable checkpoints with bounded completion markers so abrupt termination and
Windows file contention cannot manufacture a finished result.

Compare fresh nonce and fresh parent/height schedules, not just fitted replay.
Store complete exact-instance pools only under the existing bounded cache rules.
Retain acquisition cost and disclose stage resets, cold worker startup and shared
OS state. Fixed-order single-pass local timings cannot choose the fastest miner
or establish a portable mining rate. Commit ceilings are not memory hardness.

Admit a lab proof against externally supplied network/parent/height/profile,
timestamp interval, allowed payload commitments and score target. Reject forbidden
surfaces before expensive derivation. Do not accept the threshold or eligibility
policy from the miner's packet. This is an executable lab boundary, not a full
consensus implementation. See [interfaces](../../spec/08-external-windows-and-lab-admission-v1.md)
and [fresh-window evidence](../research/external-windows-and-fresh-context-v1.md).

## Requirements before a difficulty candidate

1. Define an exact eligible profile schedule and deterministic target derivation
   from trusted chain state. Specify bounds, integer rounding, overflow and all
   rejection paths; never downgrade profiles after search or sampling failure.
2. Specify valid parent/height transitions and payload-body commitments. Define
   timestamp units, chain-derived time bounds and allowed miner changes. A local
   clock or a lab allowlist cannot become chain validity by assumption.
3. Price the actual permitted nonce/time/payload surface, including parallel
   selection, fresh-context preprocessing, cross-context vector campaigns,
   variable proof multiplicity, sparse screening and optimized solver competition.
   This bundle tests only two narrow deterministic schedules.
4. Compare repeated, rotated-order, hardware-described external windows with
   multiple independent seeds. Separate cold-start deployment costs from steady
   mining while retaining all initial setup/preparation in campaign accounting.
   Include stronger LLL/BKZ/sieve/native/GPU baselines where applicable. Avoid
   winner-only or completed-only generalizations.
5. Implement and independently test any selected score and target rule in both
   verifiers. Current Rust checks bound SIS validity, not the Python lab score.
   Freeze cross-language vectors for strict inequalities and target boundaries.
6. Treat chainwork and retarget as separate design decisions. Specify adversarial
   timestamp behavior, extreme-rate changes, empty/low-availability periods,
   short forks, tie-breaking, reset boundaries and overflow before simulation.
   No time measurement or self-reported computation may determine block weight.
7. Require adversarial cryptographic review of parameters, preprocessing/reuse,
   availability and solver economics before a monetary testnet proposal.

`2^256/T` describes ideal eligible-score trials when score assumptions hold; it
does not calibrate SIS solving cost. Existing counters, toy solutions and source
reviews select neither mainnet parameters nor consensus weight. MagnetGate
integration, wallets, payments and production mining remain outside this gate.
