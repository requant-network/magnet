# ADR 0002: do not equate an accepted SIS proof with a fresh SIS solve

Date: 2026-10-08. Status: accepted research constraint.

## Evidence

The [reuse study](../research/solution-reuse-v1.md) exhausts 320 toy instances and
includes exact counterexamples. Sign-canonical multiples and primitive linear
combinations can provide additional valid proof inputs from known solutions.

## Decision

Candidate B remains a hypothesis. Do not assign chainwork using hash-trial counts
as if each hash necessarily required a new full SIS search. A future model must
account for solution multiplicity, amortization and precomputation.

Canonical encoding, sign normalization, full matrix rank and a primitive-vector
rule are not by themselves sufficient fixes. Do not change consensus or lab
acceptance rules to hide these findings.

## Limitations and next gate

The toy results do not prove universal insecurity or estimate large-instance
attack cost. The next step is a bounded end-to-end cost comparison including
acquisition of the initial vectors. Difficulty and chainwork remain unselected.
