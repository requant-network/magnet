# ADR 0016: Matched integration scope and unit triples

Date: 2026-10-09. Status: accepted for laboratory use only.

## Context

Prior native bulk protocols and GPU wrappers measured different integration
scopes. Pair-only unit candidates also omit valid solutions and can understate
the supply available to a competing solver.

## Decision

Add the separate spec-20 local search contract with scalar C++ CPU and fused
CUDA backends behind the same validation, session, scheduling, decoding and
ledger. Preserve the existing spec-17–19 interfaces. Include unit triples,
per-weight prefix accounting, explicit output discards and failure progress.
Audit shared backend helpers against independent Python ordering/arithmetic
and independent Rust proof verification. Freeze build sources and binaries and
bind compact results to the exact raw artifact.

Keep warm first-probe, compilation and audit times separate from per-search
fresh-session measurements. Retain individual repetitions and outliers. Compare
only the declared scope; do not convert historical timings into speedup claims.

## Consequences

The 84-case, three-repeat, two-backend schedule agrees in all 504 attempts;
7584 returned proof occurrences pass Rust verification. CPU group totals are
lower in this measured schedule. Neither observation establishes a portable
winner, ASIC resistance, useful-work pricing or a production parameter choice.

Triples enlarge the available search family. The capped lexicographic prefix
is biased and repeated challenges are correlated. Additional solutions and
accepted occurrences are not independently priced consensus work. Full-domain
support audits establish enumeration correctness, not full-domain yield.

No consensus rule, LabRules profile, target or chain admission changes. Broader
non-unit solvers and paid fresh-challenge amortization remain prerequisites to
any security or accumulated-work decision. See the
[report](../research/matched-sparse-v1.md) for evidence and limitations.
