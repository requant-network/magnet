# ADR 0017: Small coefficients and fixed paid refresh

Date: 2026-10-09. Status: accepted for laboratory use only.

## Context

Unit triples omit valid small-coefficient SIS vectors. Expanding coefficients
also adds legal scalar copies and changes capped enumeration prefixes. Fresh
matrix carry must be paid and cannot be inferred from repeated-instance success.

## Decision

Introduce separate spec21 search: coefficient bounds1/2, support<=3, m<=16,
B2<=12 and bounded sequential enumeration. Preserve SIS1's nonprimitive vectors
and report normalized directions/multiplicities rather than silently changing
validity. Independently audit candidate order, complete/capped ledgers and
maximum-shape verdicts, including negative outcomes.

Freeze a four-profile/six-step schedule before outcomes. Compare fresh matrices
with controls repeating step 0. A fixed-refresh policy pays carry screening and
new acquisition every step, validates acquired proofs, stably merges exact
vectors and retains at most32. Record intersection of tested family prefixes;
restrict full availability comparisons to exhausted cohorts.

## Consequences

Six complete tiny cases add 143 vectors and 122 directions under bound 2. Fresh
carry succeeds 32 times in 297 checks, only on the smallest profile; same-instance
controls succeed315/315. These correlated finite observations are not proof of
optimized amortization, portable work or security. Bound2 search remains capped
in 47 attempts and the family still omits general SIS solutions.

All 18912 maximum-family verdicts match independent Python/Rust checks. The
ordinary gate and affected study are local; no GPU or cloud jobs are required.
No consensus, target, fork rule or prior GPU API changes. Broader paid acquisition
and fresh-challenge competition precede production parameter/work decisions.
See the [report](../research/small-coefficient-v1.md).
