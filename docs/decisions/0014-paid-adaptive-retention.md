# ADR 0014 — Pay for adaptive pool selection without assigning chainwork

Status: accepted bounded laboratory policy; portable work/security gate open.

Permit an optional validated, order-preserving single-eviction selector in the
existing campaign. Implement a capacity-1–3 future-supply policy using the exact
fixed-pool correlation law, with a campaign-wide 64-decision cap and explicit
FIFO fallback. Keep selection/model work separately visible and inside external
resource windows. Existing FIFO semantics and consensus interfaces remain intact.

Use the model only for a future independent matrix, under explicit iid matrix
and conditional score hypotheses. Do not reinterpret a pool obtained from the
current matrix as a precommitted pool on that same matrix. Preserve acquisition,
failed carry, scoring and selection costs across stages.

Replay JSON transcripts and immutable checkpoints, reconcile outer charges with
backend counters, and independently audit every observed hit through Rust
trusted-context laboratory admission. Preserve censored attempts and report
conditional paired outcomes without manufacturing unconditional work totals.

The first 336-attempt study has 75 jointly completed FIFO/model pairs, all with
equal stage-hit counts; nine pairs remain incomplete. Non-FIFO pool choices are
observed, but no paired hit-count improvement is established. This outcome
adopts no calibrated work weight, production profile, fork choice or retarget.

The next hardware stage begins with exact GPU/CPU/native correctness comparisons,
then separately measured paid search. LLL/BKZ need not move to GPU first. A busy
GPU can support bounded correctness probes but not an isolated speed comparison.
External cryptographic review and an adversarial work argument remain required
before a monetary network is considered.
