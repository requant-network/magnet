# ADR 0001: arithmetic laboratory before consensus selection

Date: 2026-10-08. Status: accepted for the first research phase.

## Decision

Study SIS with exact squared L2 norm B2, bounded verification and deterministic
matrices. Start with independent Python/Rust verifiers using standard libraries.
Caller-supplied matrices are a laboratory facility only.

Keep the repository private. Do not import secrets or key material from MagnetGate.
Run the unified check locally; do not introduce GitHub Actions by default.

## Open decisions

Pure SIS versus SIS+hash target, secure work accounting, chainwork, retarget,
blocks, transaction signatures, GPU algorithm and mainnet parameters remain open.

Nakamoto consensus is a candidate, not an implemented component. Do not invent
weight=1/B2 or copy Bitcoin chainwork to SIS without a work model. A separate
decision must follow the experiments.

## Rationale and next gate

Difficulty and solution reuse can invalidate the construction. Independent
arithmetic checks and exhaustive toy cases provide a foundation before investing
in GPU development or a node fork.

Measure search and solution reuse for A/B, including multiples, combinations and
selection of easy instances. Only then design work accounting and a chain simulator.
Passing verifier tests does not close this research question.
