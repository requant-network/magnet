# 0020. Close the SIS-PoW programme with a negative result

Date: 2026-10-10. Status: accepted. Supersedes the open work-weight gate of 0007, 0012 and 0013.

## Context

The [critical path](../CRITICAL-PATH.md) reduced the programme to one question: does SIS admit a
deterministic, monotone, portable and reuse-resistant PoW work function? It also made an
explicit negative result a valid completion.

Evidence at closure:
- reuse counterexamples to vector and score counting;
- D3 screening: the 2.75× signal did not replicate (576 campaigns);
- D4: exact full-kernel transfer is negligible only under a uniform-matrix assumption;
- B-H: the header-only score lets miners skip SIS for losing headers;
- D5: no GPU advantage in a small pilot.

The remaining experiment was partial-basis D4 amortisation. Its expected outcome follows from
documented lattice-algorithm behaviour: sieving yields exponentially many short vectors per run,
so a proof-bound score gets cheap extra trials.

## Decision

1. Publish [docs/NEGATIVE-RESULT.md](../NEGATIVE-RESULT.md) as the programme's closing note.
2. Stop all further experiments, solver variants, GPU kernels, chain features and monetary work
   from this programme. The partial-basis D4, D5 energy/memory and D6 formalisation steps are
   not run.
3. Keep the repository and its artefacts unchanged as a research record.
4. Request one external cryptographic review of the closing note. Reopen only on a substantive
   error in its Section 4, or on a new construction whose marginal credited-result cost is
   provably close to the first. Either starts as a new critical-path entry.

## Consequences

- No construction (A, B, B-H or C) is promoted. No consensus weight is selected.
- `docs/CRITICAL-PATH.md`, `docs/FINDINGS.md`, `docs/OPEN-QUESTIONS.md`, `docs/STATUS.md` and the
  README carry a closed status and point to the note.
- The owner's GPU reservation no longer matters to this repository: no further runs are planned.
- MagnetGate is unaffected.
