# ADR 0006 — Keep optimized solving and header selection in work models

Status: accepted research constraint; no consensus parameters selected.

## Evidence

Pinned native FLINT LLL plus the existing finite probe succeeds on all 468
solvable records in a 1201-record study, including a labelled repeat of the frozen
exact-reference miss. All 3603 reductions receive unchanged independent exact
audits. This is sampled success, not a completeness or hardness proof.

The separate 24-family header-selection study finds 27 policy hits across four
policies. Policies pay unsuccessful search, acquisition, generation and scores;
complete oracles are outside their decision loop. Full accepted-vector scoring
and first-vector scoring yield different outcomes/costs. See the
[report](../research/practical-lll-and-grinding-v1.md) for denominators and limits.

## Decision

Keep FLINT an explicitly pinned, isolated **research backend**, outside verifiers,
ordinary offline checks and future consensus dependency selection. Independently
audit every reported reduction rather than trusting approximate arithmetic or a
completed library status. The existing exact reference remains an executable
correctness baseline; do not weaken its acceptance inequalities.

Any work-price proposal must include optimized solver competition, failed
acquisition, easy-instance screening, same-instance vectors and permitted header
selection. No current elapsed timer, vector-check counter, difficulty-like score
target or basis property becomes network accumulated work by this decision.

Timestamp/payload sensitivity experiments do not establish valid future payloads
or timestamp ranges. A future block-validity specification must constrain the
allowed surface explicitly. Prior ADRs 0002–0005 remain in force.

## Next gate

Measure stronger solvers/combined policies, preprocess/reuse costs and availability
on larger feasible profiles. Evaluate explicit competing work models before
selecting a target/retarget/fork rule. Seek independent cryptographic review
before production security claims or a monetary testnet.
