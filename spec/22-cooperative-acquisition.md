# Cooperative acquisition and retention comparison

Status: local hypothesis experiment. No SIS1/consensus or earlier API changes.

Five tasks: a common component meter; sparse bound1/2 streaming adapters;
BallSearch/MitmSearch integration; exact-vector versus direction retention;
and a frozen fresh/control schedule with budget-frontier summaries.

## Model and meter

One model unit per reported logical operation counter. The sole zero-weight
informational counter is matrix.shake_output_bytes. Model version is
cooperative-components-v1; it is arbitrary, not cycles, portable work or money.
Raw phase/component vectors accompany totals. Legacy table_buckets is excluded
because it is inventory; table_entries counts insertions. Other existing solver
work counters are included as documented logical events. Common setup counts
matrix expansion, generated entries, shape validation, and solver construction
shape checks when performed. Python allocator/bookkeeping/cleanup instructions
are not exhaustively priced; no memory-hardness or universal efficiency claim.

Snapshots must contain strict nonnegative integers and cannot regress. Snapshot
validation is atomic. Updates record completed work even after exhaustion.
Budget checks occur at cooperative boundaries; used>=limit raises a local stop.
No hard operation/time/memory bound is claimed. Record observed excess and final
solver deltas after closing; do not silently discard work between callbacks.
The cap-triggering produced/verified proof is committed before a post-operation
stop. Partial proofs and valid carry outcomes remain explicit on budget stops.

Proof screening, validation and retention form a transaction; completed validity
and retention are committed before its final budget check. Unchecked carry
vectors are excluded. The meter records the first snapshot/update reaching the
limit and the units subsequently charged (post_boundary_units), including final
flushes and the remaining proof transaction. Those units are a subset of used,
not a second charge. Report-only direction histograms and oracle/native audits
are outside this laboratory model.

## Acquisition and retention

Restrict profiles to n<=3,m<=6,B2<=12. Algorithms sparse1/sparse2 reuse the
spec21 norm-filtered family and order, without changing its standalone API.
Ball/MITM search the whole norm ball, with existing finite structural limits.
Use their checkpoints to synchronize work and check budget. Close iterators in
finally and synchronize their final counters. No fallback creates success.

Every carried/emitted vector receives counted shape/sign/norm and dense modular
checks before retention. Report actual early-rejected rows. Pool cap is8 and
acquisition proof cap64. Continue acquisition even if retention is full; this
fixed policy does not adaptively save acquisition. Exact policy uses the vector
as dedup key. Direction policy uses vector/gcd as the key but retains the verified
original vector, never a synthesized proof. Count gcd inputs and dedup comparisons.
Both policies report normalized direction multiplicities, overlaps and overflow.
SIS1 scalar copies remain valid, correlated proofs under either policy.

Stop reasons distinguish budget, output and underlying solver limits/exhaustion.
The run's known checked prefix is not proof of solution absence outside it.
Full-ball and sparse-domain completeness are different properties. Common meter
limits do not make algorithm domains/order or operation types equivalent.

Exhaustion means observed completion. Ball/MITM stopped at a yield may have
unobserved exhaustion even if an external oracle knows the last solution was
returned; do not advance them after a stop to manufacture that observation.
Sparse adapters can recognize their final ordinal before yielding.

## Frozen study

Profiles (q,n,m,B2): (7,1,4,8),(17,2,5,8),(257,2,6,12). Budgets750/5000/50000,
algorithms sparse1/sparse2/ball/mitm, policies exact/direction and cohorts fresh/
control. Four sequential steps each, empty initial pool per combination. All
combinations use the same labelled matrices; controls repeat fresh step0. Public
label seed2026100916. Labels join version, seed, q,n,m,B2,step with '/'; SHA256
ASCII label seeds SIS1 SHAKE expansion. Iterate in the declared nested order.
There are576 planned steps, including zero-output and budget-stopped attempts.
Matrix preparation is performed/countable inside each step. Native audit work
and independent oracle work are separate verification phases outside the model.

Audit complete tiny solution sets against an independent Cartesian norm-ball
oracle; filter only for sparse-family checks. A capped solver is never a full
oracle. Validate meter snapshots and paid dense verification independently,
exercise exact limits, partial results, finally closure and failed publication.
Rust verifies emitted/carry verdicts including rejection. Replay transitions and
check component totals/overshoot; report success/empty/censored denominators and
per-matrix budgets, not a selected winner across non-equivalent domains.

Invalidate evidence before build; freeze sources/current Cargo-selected verifier,
exact raw digest and model configuration. A failed study preserves completed
records and unknown unfinished work, never successful comparative summaries.
No new dependencies, GPU jobs, paid cloud or GitHub Actions are required.
