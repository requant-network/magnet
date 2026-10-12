# Magnet Network — SIS-PoW laboratory

**Status: closed on 2026-10-10 with a negative result.** No acceptable SIS work
function was found for the tested constructions; see the
[closing note](docs/NEGATIVE-RESULT.md) and
[ADR 0020](docs/decisions/0020-close-sis-pow-programme.md). The code and evidence
below stay as a research record; no further experiments are planned.

Private research into lattice-based Proof of Work for a future Magnet Network.
This repository currently verifies Short Integer Solutions and studies candidate
PoW constructions. It now includes an experimental linear-chain prototype;
there is no currency, production network or GPU miner.

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
- Complete bounded exact sphere search on certified kernel lattices.
- Joint header families, four-target sweeps and explicit descriptive work models.
- On-demand practical lattice policies with streaming hits and bounded exact-instance preparation caches.
- Windows Job time/commit ceilings, immutable checkpoints and censored-attempt accounting.
- Fresh nonce/parent schedules and externally trusted laboratory header admission.
- Independent native SHA-256, strict score targets and full laboratory admission.
- Persistent paid vector campaigns with shared budgets and shuffled seeded repeats.
- Persistent multi-vector FIFO pools, paid combinations and joint header grinding.
- Paid MITM/sparse/LLL/limited BKZ/sieve portfolio with externally bounded campaigns.
- MGB1 body/recipient/target commitments and fixed-policy laboratory chain admission.
- Explicit construction/parameter/work decisions scoped to demonstration use.
- Independent complete Rust MGB1 parser and fixed-policy linear chain engine.
- Bounded real-block forks, atomic canonical replay and delivery/partition simulation.
- Synthetic retarget hypotheses and concrete paid block-reuse counterexamples.
- Exact precommitted-pool correlation laws, complete matrix audits and paid fresh-header supply studies.
- Paid bounded adaptive retention, replayed JSON checkpoints and independent native hit admission.
- Optional exact CUDA SIS verification, tested against Python/Rust on a local CMP 50HX.
- Bounded on-device unit-sparse candidate acquisition with paid chunk ledgers and independent CPU/native audits.
- Exact sparse-column CPU/CUDA acquisition with boolean-only readback and larger bounded chunks.
- Independent native Rust column search and fused CUDA kernels with paid chunks, owned sessions and matched-domain audits.
- Matched in-process scalar CPU/GPU search through unit triples with per-weight prefix and failure accounting.
- Bounded non-unit sparse search, independent complete-ledger audits and paid fresh-matrix refresh with direction accounting.
- Cooperative component budgets across sparse/ball/MITM acquisition, paid direction retention and frozen budget-response campaigns.
- Independent native small-coefficient search, strict framed reconciliation, late-witness audits and fresh-seed comparisons.
- Matched in-process small-coefficient CPU/CUDA chunks, complete negative-mask audits and durable interruption evidence.
- Explicit nominal A/B work definitions and frozen paid nonce-screening attacks with strong controls, independent ledger/native audits and insufficient-evidence reporting.
- Precommitted fresh-stream D3 replication: 576 audited campaigns, sufficient controls and no declared screening trigger; next D4 amortisation.
- Conditional exact full-kernel transfer laws, exhaustive finite-field checks and eight audited D4 integration workers; general reuse resistance remains open.
- Research-only B-H header-score repair: a public gate avoids rejected challenges' SIS preparation; 16 audited batches reject fresh-SIS-per-hash amplification for this candidate.

The ordinary check gate uses standard libraries. Cargo builds offline without
third-party crates. Explicit practical-LLL surveys additionally use an isolated
hash-pinned python-flint research environment; see the report below.
GitHub Actions are intentionally absent; checks and experiments run locally.

## Run locally

Tested on Windows with Python 3.12.10 and Rust 1.98.1, including rustfmt and clippy.
Other platforms must repeat the checks before claiming support.

~~~sh
python scripts/check.py
python scripts/screening_survey.py
python scripts/screening_replication.py
python scripts/preparation_survey.py
python scripts/header_gate_survey.py
python scripts/native_coefficient_survey.py
python scripts/toy_survey.py
python scripts/reuse_survey.py
python scripts/strategy_survey.py
python scripts/mitm_survey.py
python scripts/budget_survey.py
python scripts/native_survey.py
python scripts/lattice_survey.py
python scripts/binding_survey.py
python scripts/grinding_survey.py
python scripts/joint_survey.py
python scripts/chain_survey.py
python scripts/fork_survey.py
python scripts/work_weight_study.py
python scripts/supply_survey.py
python scripts/difficulty_survey.py
python scripts/resource_survey.py
~~~

The complete lattice sphere survey uses the explicit optional environment:

~~~sh
python scripts/sphere_survey.py --python artifacts/flint-env/Scripts/python.exe
artifacts/flint-env/Scripts/python.exe scripts/integrated_survey.py
python scripts/windows_survey.py --python artifacts/flint-env/Scripts/python.exe
python scripts/campaign_survey.py --python artifacts/flint-env/Scripts/python.exe
python scripts/portfolio_survey.py --python artifacts/flint-env/Scripts/python.exe
python scripts/soak_survey.py --python artifacts/flint-env/Scripts/python.exe
python scripts/adaptive_survey.py --python artifacts/flint-env/Scripts/python.exe
artifacts/flint-env/Scripts/python.exe scripts/portfolio_checks.py
python scripts/rejection_cost.py
python scripts/mine_lab_chain.py
python scripts/endurance_fuzz.py --seconds 3600
~~~

The first command runs formatting/lint checks, tests and a deterministic
Python/Rust differential corpus. Surveys study bounded toy instances; they do not
benchmark production mining. Reports are written to ignored artifacts/.

## Documentation

- [Closing note: negative result](docs/NEGATIVE-RESULT.md) and [closure decision](docs/decisions/0020-close-sis-pow-programme.md).
- [Critical path and frozen D2/D3 protocol](docs/CRITICAL-PATH.md).
- [Findings so far](docs/FINDINGS.md) and [open work-weight questions](docs/OPEN-QUESTIONS.md).
- [Matched small-coefficient CPU/CUDA: bounded D5 pilot](docs/research/matched-coefficients-v1.md).
- [Matched small-coefficient contract](spec/24-matched-small-coefficients.md).
- [Independent native small-coefficient search: five-task block](docs/research/native-small-coefficients-v1.md).
- [Native small-coefficient exchange contract](spec/23-native-small-coefficients.md).
- [Native small-coefficient baseline decision](docs/decisions/0019-native-small-coefficients.md).
- [Cooperative acquisition and retention: five-task block](docs/research/cooperative-acquisition-v1.md).
- [Cooperative component-budget contract](spec/22-cooperative-acquisition.md).
- [Cooperative budgets and retention decision](docs/decisions/0018-cooperative-component-budgets.md).
- [Small coefficients and paid matrix refresh](docs/research/small-coefficient-v1.md).
- [Small-coefficient contract](spec/21-small-coefficient-search.md).
- [Small coefficients and refresh decision](docs/decisions/0017-small-coefficients-and-refresh.md).
- [Matched CPU/GPU search and unit-triple evidence](docs/research/matched-sparse-v1.md).
- [Matched search contract](spec/20-matched-sparse-search.md).
- [Matched scope and unit-triple decision](docs/decisions/0016-matched-scope-and-unit-triples.md).
- [Native Rust and fused CUDA measured baselines](docs/research/native-fused-column-v1.md).
- [Native/fused contract and timing scopes](spec/19-native-fused-column-search.md).
- [Baseline decision and open production-work gate](docs/decisions/0015-native-fused-baselines.md).
- [Column arithmetic optimization and CPU/GPU comparison](docs/research/gpu-column-search-v1.md).
- [Optimized column-search contract](spec/18-column-search-optimization-v1.md).
- [Paid GPU unit-sparse acquisition](docs/research/gpu-unit-sparse-search-v1.md).
- [CPU/CUDA candidate-search contract](spec/17-unit-sparse-gpu-search-v1.md).
- [Executed CUDA verification and next GPU stage](docs/research/gpu-verification-v1.md).
- [Exact GPU verification contract](spec/16-gpu-verification-lab-v1.md).
- [Research and consensus plan](01-SIS-POW-RESEARCH-PLAN.md).
- [Implemented SIS-LAB-v1 specification](spec/01-sis-lab-v1.md).
- [Current status and verification](docs/STATUS.md).
- [Backlog 1–10 milestone](docs/research/pool-portfolio-and-blocks-v1.md).
- [Backlog 11–15 milestone](docs/research/chain-forks-and-retarget-v1.md).
- [Paid adaptive retention results](docs/research/adaptive-retention-v1.md).
- [Adaptive policy contract](spec/15-adaptive-retention-lab-v1.md).
- [Adaptive retention decision](docs/decisions/0014-paid-adaptive-retention.md).
- [Local GPU readiness and first experiments](docs/research/gpu-readiness-v1.md).
- [Exact precommitted-pool supply study](docs/research/precommitted-pool-supply-v1.md).
- [Supply model and resource contract](spec/14-precommitted-pool-supply-v1.md).
- [Fixed-pool correlations and open adaptive-work gate](docs/decisions/0013-precommitted-pool-supply.md).
- [Native full-chain specification](spec/12-native-chain-v1.md).
- [Fork and retarget experiments](spec/13-fork-and-retarget-lab-v1.md).
- [Fork simulation and open work-weight decision](docs/decisions/0012-fork-simulation-without-priced-work.md).
- [Experimental construction and chain decision](docs/decisions/0011-experimental-construction-and-chain.md).
- [Paid pool/solver specification](spec/10-pool-portfolio-v1.md).
- [Experimental block and linear-chain specification](spec/11-experimental-block-chain-v1.md).
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
- [Exact sphere, joint headers and work-model study](docs/research/sphere-and-work-models-v1.md).
- [Sphere and work-model interfaces](spec/06-sphere-and-work-models-v1.md).
- [Eligible scores versus SIS work pricing](docs/decisions/0007-sphere-and-work-models.md).
- [Paid practical search and preprocessing study](docs/research/integrated-lattice-policies-v1.md).
- [Integrated lattice policy interfaces](spec/07-integrated-lattice-policies-v1.md).
- [Preprocessing accounting decision](docs/decisions/0008-paid-lattice-preprocessing.md).
- [External windows and fresh-context study](docs/research/external-windows-and-fresh-context-v1.md).
- [External resource and lab admission interfaces](spec/08-external-windows-and-lab-admission-v1.md).
- [Trusted header surface and difficulty requirements](docs/decisions/0009-external-windows-and-trusted-surface.md).
- [Independent native score/admission interfaces](spec/09-native-score-and-admission-v1.md).
- [Persistent campaign and repeated-window interfaces](spec/10-persistent-campaigns-v1.md).
- [Native admission and seeded campaign study](docs/research/native-admission-and-campaigns-v1.md).
- [Independent acceptance and campaign accounting decision](docs/decisions/0010-independent-acceptance-and-campaigns.md).
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

Production difficulty/chainwork, wallets and payments are not implemented.
MGB1 linear engines and the fixed-policy fork tree are experimental prototypes.
Dynamic-target experiments use a separate synthetic model.
Small-instance results do not establish GPU advantage, ASIC
resistance, post-quantum security or mainnet parameters. MagnetGate is unchanged.

Closed: the [negative-result note](docs/NEGATIVE-RESULT.md) states the conclusion, its limits
and the conditions for reopening. External cryptographic review of that note is the one
outstanding request. A valid SIS solution is not proof of network service delivery or of a
particular amount of computation.

## License

MIT. See [LICENSE](LICENSE).
