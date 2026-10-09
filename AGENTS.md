# Magnet Network working rules

- Read `docs/CRITICAL-PATH.md` first. It names the single open decision (a
  portable, monotone, reuse-resistant work function) and the decisive experiment
  sequence. Every task must map to it or be explicitly parked; do not expand the
  lab (more solver variants, more single-scope timings, more specs) unless it
  changes the A-vs-B answer.
- English is primary for code, documentation, issues and commits. Russian is
  secondary under docs/ru/; label translations and historical snapshots.
- This is a research laboratory, not a production PoW or monetary blockchain.
  Distinguish mathematical validity, measured cost and security claims.
- Preserve source/configuration hashes, seeds and limitations with experiments.
- Run python scripts/check.py locally before committing code changes. Run the
  affected survey when its algorithm or measurement logic changes.
- Do not introduce paid CI, cloud GPU jobs or GitHub Actions by default.
- Do not import keys or secrets from MagnetGate. Keep artifacts and CodeGraph
  indexes outside Git; commit compact reproducible research summaries.
- Prefer CodeGraph for structural questions; direct reads are appropriate for
  known files and literal text. Sync the existing index after source changes.
- Do not silently weaken checks or change a consensus candidate to another task.
