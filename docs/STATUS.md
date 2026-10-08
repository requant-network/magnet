# Research status

Date: 2026-10-08. Phase: arithmetic foundation and first solution-reuse study.
English is primary. The [Russian initial-phase snapshot](ru/docs/STATUS.md)
records the earlier milestone and is not the current status.

## Implemented

SIS-LAB-v1 specification; exact Python and independent Rust verifiers; bounded
stdin/stdout adapter; SHAKE256 matrix expansion in Python; exhaustive tiny solver;
sparse screening, rank and known-solution reuse probes; a local check command.

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

## Verification

python scripts/check.py currently passes:

- rustfmt and clippy without warnings;
- 24 Python tests and 3 Rust tests;
- 10009 differential Python/Rust cases, 2665 accepted, no mismatches;
- three malformed-frame checks and two empty-input/frame checks.

Tests cover manual vectors, norm and size limits, rejection sampling and its
budget, exact tiny spaces, solution reuse, support-limited search and rank.
The latest local check report includes source hashes. An interrupted rerun
marks its report running-or-incomplete rather than leaving stale success.

Separate source reviews covered both milestones. The initial Cargo executable-
selection issue was fixed; the harness uses the artifact returned by the current
build. No required implementation findings remain in the reviewed laboratory.
This is source review, not an independent cryptographic audit.

## Still absent

An independent Rust SHAKE generator, long-running fuzzing, LLL/BKZ/sieve baselines,
GPU mining, header binding, a work function, retarget, blockchain, wallet and
MagnetGate integration. E1 is not claimed fully closed under the broader plan.

## Decision and next step

[ADR 0002](decisions/0002-solution-reuse.md) rejects the assumption that each
accepted proof or score trial necessarily requires a fresh SIS solve. It does
not reject every possible SIS-based PoW.

Next compare bounded end-to-end strategies, including initial-solution acquisition,
generation, screening and reuse. Establish what an attempted unit of work costs
before defining difficulty or accumulated chainwork.
