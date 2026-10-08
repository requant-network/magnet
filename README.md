# Magnet Network — SIS-PoW laboratory

Private research into lattice-based Proof of Work for a future Magnet Network.
This repository currently verifies Short Integer Solutions and studies candidate
PoW constructions. It does not implement a blockchain, currency, or GPU miner.

**English is the primary repository language.** Russian is secondary:
see the [Russian documentation index](docs/ru/README.md).

## Implemented

- Exact Python verifier and an independently implemented Rust verifier.
- Bounded binary test adapter and Python SHAKE256 matrix expansion.
- Exhaustive solver for tiny instances with a hard search budget.
- Manual, boundary, exhaustive and cross-language differential tests.
- Reproducible studies of solution availability, reuse and sparse screening.

Only standard libraries are used. Cargo builds offline without third-party crates.
GitHub Actions are intentionally absent; checks and experiments run locally.

## Run locally

Tested on Windows with Python 3.12.10 and Rust 1.98.1, including rustfmt and clippy.
Other platforms must repeat the checks before claiming support.

~~~sh
python scripts/check.py
python scripts/toy_survey.py
python scripts/reuse_survey.py
~~~

The first command runs formatting/lint checks, tests and a deterministic
Python/Rust differential corpus. Surveys exhaust tiny finite spaces; they do not
benchmark production mining. Reports are written to ignored artifacts/.

## Documentation

- [Research and consensus plan](01-SIS-POW-RESEARCH-PLAN.md).
- [Implemented SIS-LAB-v1 specification](spec/01-sis-lab-v1.md).
- [Current status and verification](docs/STATUS.md).
- [Solution reuse study](docs/research/solution-reuse-v1.md).
- [Research boundary decision](docs/decisions/0001-research-boundary.md).
- [Threat model](docs/THREAT-MODEL.md).
- [Language policy](docs/LANGUAGE.md).
- [Original SIS proposal](docs/research/lattice-sis-pow-deep-dive.md):
  historical hypotheses, not an accepted security specification.

## Scope boundary

The laboratory accepts a caller-supplied matrix. A network PoW verifier must
instead derive its own instance from a block-bound header. Accepting an arbitrary
matrix from a miner would allow deliberately easy instances.

Header binding, difficulty, chainwork, block consensus, wallets and payments are
not implemented. Small-instance results do not establish GPU advantage, ASIC
resistance, post-quantum security or mainnet parameters. MagnetGate is unchanged.

Next: quantify preprocessing and solution reuse under explicit work models before
selecting difficulty and fork-choice rules. A valid SIS solution is not proof of
network service delivery or of a particular amount of computation.
