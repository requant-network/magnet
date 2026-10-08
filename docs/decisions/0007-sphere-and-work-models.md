# ADR 0007 — Separate eligible score difficulty from SIS work pricing

Status: accepted research constraint; consensus parameters remain unselected.

## Evidence

Exact rational sphere enumeration over certified full kernel lattices agrees
with independent native MITM on every proof set in 1101 complete toy records.
It retains 526 canonical proof occurrences across 408 solvable records; 693
records are empty. The finite FLINT row/pair probe misses 55 vectors, even though
it finds at least one on all solvable records in this particular schedule.

Equal-size single/joint header families with four score targets yield 512 paid
policy runs. Outcomes and component costs depend on policy and allowed header
surface; a score threshold does not specify the cost of acquiring eligible SIS
vectors. See the [report](../research/sphere-and-work-models-v1.md).

## Decision

Use exact sphere search as another complete bounded solver baseline, with
independent certificates and explicit caps. Keep optimized backend reduction
optional and outside consensus/verifiers. Completion is stronger than a finite
probe; a stopped tree is not evidence of absence.

Treat 2^256/T as an idealized eligible-score-trial model, conditional on uniform
independent hashes, not as a calibrated SIS cost or a selected chainwork rule.
Equal proof counts do not calibrate CPU cost, and a hypothetical fresh full SIS
search cannot be charged when measured policies need fewer proposals or reuse
prior acquisition. Prior ADRs 0002–0006 remain in force.

Record work by component and include failed attempts. Do not construct a monetary
chain or retarget around a model whose security assumptions have not been tested.
No current client or prover can provide trustworthy evidence of its own hidden
computation merely by submitting a valid SIS proof.

## Next gate

Connect optimized reduction plus sphere/first-vector enumeration to paid header
policies on larger profiles; measure preprocessing reuse and amortization under
common budgets. Formulate candidate parameter/target/time/payload validity rules
and adversarial strategies, then test which model can support a defensible
fork-choice specification. Obtain external cryptographic review before security
claims or a monetary testnet.
