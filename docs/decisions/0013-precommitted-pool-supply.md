# ADR 0013 — Quantify fixed-pool correlations without pricing adaptive mining

Status: accepted bounded research model; production work/retarget gate open.

Use the existing prime-field Profile, canonical short vectors and exact modular
subset ranks to compute a precommitted pool's valid-count distribution under
explicit iid-uniform matrices. Compare it to complete tiny matrix spaces and
separate fresh deterministic header cohorts. Keep all setup costs, bounded-search
failures, skipped cohorts and independent native audits visible in evidence.

Distinct integer proof inputs may share an acceptance event. Pairwise independent
vectors may form a jointly dependent pool. Therefore pool size and primitive
vector count are not automatically independent eligible-input supply.

An optional score-hit mixture requires uniform-independent scores conditional
on the whole matrix and valid-vector set. It does not assert actual SHAKE/SHA-256
independence, adaptive attack bounds, high-dimensional hardness or energy costs.
The model is isolated from MGB1 admission, fixed-target fork choice and synthetic
retarget experiments. No new consensus weighting rule is adopted.

Future work must price adaptive pool acquisition/selection, sparse strategies,
joint header grinding, optimized solvers and preprocessing on comparable scopes.
Portable adversarial work, cross-profile comparisons, production retarget and
external cryptographic review remain required before monetary launch decisions.
