# ADR 0008 — Charge practical search and bound preprocessing reuse

Status: accepted research constraint; no consensus work function selected.

## Evidence

Practical LLL and exact streaming sphere search are now executed on demand inside
four paid policies, on profiles up to m16. A 256-header study gives 13/20/5/20
initial first/all/reuse/cache-all hit occurrences over 32 runs each. Independent
native availability and bound-proof checks pass; failed searches remain charged.

Fitting cache replay eliminates 273 repeated reductions and 13850 sphere nodes
while retaining matrix generation, verification and 199 fresh scores. Clearing
the cache restores the preparation cost. A capacity-one diagnostic loses the
replay saving on the larger profiles. Initial preparation cannot be discarded.
See [the report](../research/integrated-lattice-policies-v1.md).

## Decision

Keep optimized reduction/search inside paid policy measurements rather than
pricing proofs by an external oracle or naive full enumeration. Keep exact
certificate checks and explicit visitor/cap statuses; first-vector stops never
become completeness claims. Shared operation ceilings are not equal-time fairness.

Permit local reuse of complete pools only under exact profile-plus-matrix keys,
with bounded immutable storage and current-header rescoring. A proof/header score
is never reused as a cached win. Warm repeated-input costs must include their cold
preparation; they do not establish savings for fresh cryptographic instances.
Distinguish eager sorted-pool policies from traversal-order streaming policies.

The in-process FLINT adapter is an explicit isolated research environment,
outside normal gates/verifiers. Its setup and overlapping timer scopes are
disclosed; it does not inherit subprocess deadlines. Prior ADRs remain in force.

## Next gate

Establish common externally enforced resource windows and fresh-context schedules,
then specify permitted header changes/profile selection and adversarial strategies.
Use the evidence to evaluate work models before adopting difficulty or fork choice.
Source review and these toy studies do not replace external cryptographic review.
