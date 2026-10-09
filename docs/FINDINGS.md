# Findings so far

Date: 2026-10-09. Primary question and ordering follow the working
`docs/CRITICAL-PATH.md`. These findings concern tested constructions,
not a general impossibility theorem for lattice-based PoW.

## Validity does not price work

Python and Rust independently verify SIS1 and laboratory header/block validity.
A valid short vector does not certify a particular number of operations, energy
cost or delivery of network service. The verifier is useful supporting machinery,
not the missing work-weight argument.

Legal sign/scalar/combination reuse and repeated score trials invalidate the
simple equivalence “one accepted vector or score attempt = one fresh SIS solve”.
See [reuse](research/solution-reuse-v1.md),
[header selection](research/practical-lll-and-grinding-v1.md) and
[paid fresh supply](research/precommitted-pool-supply-v1.md). These are concrete
counterexamples to those simple accounting assumptions; they do not reject all
possible constructions A or B.

## Logical meters and local timing remain descriptive

Equal-weight component budgets preserve paid preparation, acquisition and
retention, but their coefficients are an arbitrary experimental model.
See [component comparison](research/cooperative-acquisition-v1.md).
Fixed proof counts and normalized direction counts contain dependencies.

[Native small coefficients](research/native-small-coefficients-v1.md) distinguish
internal search from process roundtrip and host audit. The matched
[CPU/CUDA block](research/matched-coefficients-v1.md) is a bounded D5 pilot:
equal domain, caps, output and host timer. CPU has lower elapsed time in716/720
pairs and in every seeded group's median paired ratio. It shows no GPU advantage
for this family/fresh-session workload. It does not measure energy or memory
scaling and cannot resolve portable work.

## Current conclusion

No deterministic monotone portable reuse-resistant weight is established.
Existing naive vector/score-count weights have counterexamples. A-vs-B remains
open under the critical path; implementation volume does not close it.
Continue with [open questions](OPEN-QUESTIONS.md), falsifying proposed weights
before choosing monetary rules or expanding hardware interfaces.
