# Magnet Network — SIS-PoW laboratory

Private research into lattice-based Proof of Work for a future Magnet Network.
This repository currently verifies Short Integer Solutions and studies candidate
PoW constructions. It does not implement a blockchain, currency, or GPU miner.

**English is the primary repository language.** Russian is secondary:
see the [Russian documentation index](docs/ru/README.md).

## Implemented

- Exact Python verifier and an independently implemented Rust verifier.
- Bounded binary test adapters and independent Python/Rust SHAKE256 matrix expansion.
- Exhaustive solver for tiny instances with a hard search budget.
- Manual, boundary, exhaustive and cross-language differential tests.
- Reproducible studies of solution availability, reuse and sparse screening.
- Bounded search policies with initial-acquisition and component accounting.
- Exact bounded meet-in-the-middle search and local time/allocation comparisons.
- Incremental norm-ball search and common cooperative time/allocation budgets.
- Native Rust ball/MITM search, bounded local protocol and larger toy CPU studies.
- Exact LLL kernel reduction, independently audited certificates and finite probes.
- Canonical research headers, trusted-context proofs and nonce/reuse studies.
- Optional pinned native FLINT LLL with exact certificate audits and practical comparisons.
- Paid nonce/time/payload selection policies with a separate research score predicate.

The ordinary check gate uses standard libraries. Cargo builds offline without
third-party crates. Explicit practical-LLL surveys additionally use an isolated
hash-pinned python-flint research environment; see the report below.
GitHub Actions are intentionally absent; checks and experiments run locally.

## Run locally

Tested on Windows with Python 3.12.10 and Rust 1.98.1, including rustfmt and clippy.
Other platforms must repeat the checks before claiming support.

~~~sh
python scripts/check.py
python scripts/toy_survey.py
python scripts/reuse_survey.py
python scripts/strategy_survey.py
python scripts/mitm_survey.py
python scripts/budget_survey.py
python scripts/native_survey.py
python scripts/lattice_survey.py
python scripts/binding_survey.py
python scripts/grinding_survey.py
~~~

The first command runs formatting/lint checks, tests and a deterministic
Python/Rust differential corpus. Surveys study bounded toy instances; they do not
benchmark production mining. Reports are written to ignored artifacts/.

## Documentation

- [Research and consensus plan](01-SIS-POW-RESEARCH-PLAN.md).
- [Implemented SIS-LAB-v1 specification](spec/01-sis-lab-v1.md).
- [Current status and verification](docs/STATUS.md).
- [Solution reuse study](docs/research/solution-reuse-v1.md).
- [Search strategies and component accounting](docs/research/search-strategies-v1.md).
- [Meet-in-the-middle search and local measurements](docs/research/meet-in-the-middle-v1.md).
- [Norm-ball search and common local budgets](docs/research/ball-and-budgets-v1.md).
- [Native CPU search and larger toy instances](docs/research/native-cpu-search-v1.md).
- [Native search laboratory protocol](spec/02-native-search-v1.md).
- [Exact lattice-reduction specification](spec/03-lattice-reduction-v1.md).
- [LLL availability and missed-solution study](docs/research/lattice-reduction-v1.md).
- [Lattice-probe decision](docs/decisions/0004-lattice-probes.md).
- [Research header and local generator protocol](spec/04-header-binding-v1.md).
- [Independent generation and header-binding study](docs/research/header-binding-v1.md).
- [Header binding and work-pricing decision](docs/decisions/0005-header-binding.md).
- [Practical LLL and paid header-selection study](docs/research/practical-lll-and-grinding-v1.md).
- [Optional backend and grinding interfaces](spec/05-practical-lll-and-grinding-v1.md).
- [Optimized-solving and header-selection decision](docs/decisions/0006-practical-solvers-and-grinding.md).
- [Research boundary decision](docs/decisions/0001-research-boundary.md).
- [Threat model](docs/THREAT-MODEL.md).
- [Language policy](docs/LANGUAGE.md).
- [Original SIS proposal](docs/research/lattice-sis-pow-deep-dive.md):
  historical hypotheses, not an accepted security specification.

## Scope boundary

The original SIS1 laboratory format accepts a caller-supplied matrix. The new
MGH1 bound proof format derives A internally from a research header and requires
trusted external context. Accepting an arbitrary matrix or miner-chosen policy
would allow deliberately easy instances. These remain local research tools.

Difficulty, chainwork, block consensus, wallets and payments are not implemented.
Small-instance results do not establish GPU advantage, ASIC
resistance, post-quantum security or mainnet parameters. MagnetGate is unchanged.

Next: quantify preprocessing and solution reuse under explicit work models before
selecting difficulty and fork-choice rules. A valid SIS solution is not proof of
network service delivery or of a particular amount of computation.
