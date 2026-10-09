# Research status

Date: 2026-10-09. Phase: paid unit-sparse CUDA acquisition and optimization preparation.
English is primary. The [Russian initial-phase snapshot](ru/docs/STATUS.md)
records the earlier milestone and is not the current status.

## Implemented

SIS-LAB-v1 specification; exact Python and independent Rust verifiers; bounded
stdin/stdout adapters; independent Python/Rust SHAKE256 matrix expansion; exhaustive tiny solver;
sparse screening, rank and known-solution reuse probes; four instrumented search
policies that acquire their own initial solutions; bounded exact meet-in-the-
middle search; incremental norm-ball enumeration; common cooperative time and
traced-allocation budgets; native Rust ball/MITM solvers and a bounded local
search protocol; larger toy CPU studies; a local check command.
Exact-rational LLL on full modular-kernel bases, independent lattice certificates
and a finite row/pair probe now provide a competing solver family.
Canonical MGH1 headers and context-bound proofs derive A internally; the
separate SIS1 format remains supplied-matrix research input. Exact rational sphere
enumeration now completes bounded kernel searches with explicit caps; joint
header families and target grids expose competing descriptive cost models.
Streaming visitors and an explicitly isolated in-process native backend now
connect practical LLL/sphere to paid first/all/reuse/cache-all policies.
Windows Jobs now enforce process/job commit ceilings before worker execution and
terminate externally bounded attempts. Immutable checkpoints preserve interrupted
evidence. Fresh schedules and LabRules constrain the independently trusted surface.
Independent bounded Rust SHA-256/score/target/admission now matches Python.
Persistent one-vector campaigns share budgets across stages and compare shuffled
seeded repeats in externally bounded workers.

The private repository is danifest751/magnet. The workspace is
C:/Projects/MagnetNetwork. Cargo.lock contains only the sis-verifier package;
the ordinary check gate has no third-party dependencies. Explicit practical LLL
experiments use isolated, hash-pinned python-flint 0.9.0. No paid CI or cloud GPUs were used.
CodeGraph and local artifacts are ignored by Git.

## Experiments

### Initial availability survey

python scripts/toy_survey.py exhausts 128 deterministic instances at
q=17,n=2,m=3,B2=8. Exactly 15 have canonical solutions, with 18 solutions total.
The remaining 113 have none within the complete bounded domain; this is not
a timeout-based inference.

### Reuse and screening survey

python scripts/reuse_survey.py studies 320 fixed matrices across three toy
profiles and up to six norm bounds. See the [report](research/solution-reuse-v1.md)
and [committed summary](research/results/reuse-survey-v1.json).

Key findings:

- At the maximum bound all sampled matrices admit solutions; some have up to 21.
- Given one oracle-selected solution, simple transformations produce up to five
  distinct valid vectors in these batches, including the supplied one.
- Primitive-vector restrictions alone do not prevent linear-combination reuse.
- All sampled matrices have full row rank; full rank does not certify hard search.
- Sparse screening can miss valid nonsparse solutions.

These are exact toy-instance observations, not mining-speed estimates or a
security proof. Initial vectors come from an exhaustive oracle. Their acquisition
cost is not included in a claimed speedup; no such speedup is claimed.

### Search strategy accounting

python scripts/strategy_survey.py runs four policies on 448 toy instances,
including 113 with no solution at the smallest profile. Policies generate their
own matrices; total counters include failed search, first acquisition, sparse
screening, reuse and scoring components. No oracle supplies initial solutions.
See the [report](research/search-strategies-v1.md) and
[committed summary](research/results/strategy-survey-v1.json).

In one 128-instance batch, first-reuse produces 181 distinct score trials versus
128 for first-restart with only 171 additional candidate proposals, plus recorded
derivation/scoring operations. Sparse-first search sometimes reduces proposals
but increases matrix arithmetic. These are logical component counts, not measured
hashrate, calibrated work or a cost-per-win ranking. The experiment's score
binds profile, seed and proof. That historical score study does not use the new
MGH1 header binding and does not implement block consensus.

### Meet-in-the-middle baseline

python scripts/mitm_survey.py compares full box search with an exact split-table
solver on 64 generated toy instances, two seed batches per profile and three
score conditions. All-proofs sets and per-instance score-hit existence agree.
No search reached a cap. See the [report](research/meet-in-the-middle-v1.md) and
[committed summary](research/results/mitm-survey-v1.json).

Local instrumented Python elapsed-time ratios range from about 1.5 to 204 in
favor of MITM. Representative Python-traced peak allocations are higher for MITM;
they are not process RSS or worst-case memory. Each timed call includes generation,
preprocessing, search, scoring and output construction; audits and memory probes
are separate. These observations do not calibrate consensus work or mining rate.

### Norm-ball search and common budgets

python scripts/budget_survey.py checks exact accepted sets on 48 generated
instances and runs 648 budget windows. It compares incremental ball search with
MITM under 50 ms and 32/128/256 KiB traced-allocation ceilings, for continue,
restart and first-vector reuse at two score targets. See the
[report](research/ball-and-budgets-v1.md) and
[summary](research/results/budget-survey-v1.json).

MITM is about 8.1 to 11.6 times faster in the untraced complete-search comparison.
At 256 KiB, continuing search yields more repeated-run hits than restarting or
reuse in these batches; tighter ceilings frequently stop the Python harness.
Each six-window configuration repeats two seed schedules three times. These are
local outcomes, not independent proof counts, portable memory requirements or
a calibrated work function. Limits are cooperative and measured overshoot is
reported. Exact-search timing excludes scoring/verification; budget timing
includes them and tracemalloc overhead.

### Native CPU scale study

python scripts/native_survey.py compares native exact solvers on 36 matrices
over six profiles, including 12 shared Python comparisons, three repetitions
per solver, and a separate cap probe. Exact sets agree; every output is
independently verified. The largest complete profile is q=257,n=3,m=14,B2=12.
See the [report](research/native-cpu-search-v1.md) and
[summary](research/results/native-survey-v1.json).

MITM takes about 1.9 to 16.4 times less solver time than native ball in this run.
The q=257,n=3 profiles at m=10 and m=12 have no solutions in the sampled complete
domains. q=17,n=2,m=12,B2=12 yields 53078 vectors across six matrices. These are
toy observations, not independent units of consensus work. Native time excludes
expansion/decoding/IPC/scoring/audits; selected Vec capacity charges exclude
stack and allocator/process overhead. No memory-hardness claim is made.

### Exact LLL study

python scripts/lattice_survey.py studies 1000 cheap and 100 larger matrices,
including all 36 historical native-v1 inputs. All lattice certificates and
complete-oracle comparisons pass. Of 458 solvable matrices, the row/pair probe
finds a vector on 457. One certified reduced basis misses the existing norm-12
vector; a frozen regression preserves that case. See the
[report](research/lattice-reduction-v1.md) and [summary](research/results/lattice-survey-v1.json).

All 1100 reductions, probes and oracles complete in this run. In general,
availability/probe-success counts exclude capped oracles while retaining
reduction status. Exact rational reference time is not optimized reduction speed;
no memory, energy, mining-rate or hardness claim is made.

### Independent generation and header binding

The [binding study](research/header-binding-v1.md) checks 1024 nonce headers across
four toy profiles. Python and Rust agree on all derived instances and complete
solution sets: 389 are solvable, 635 empty, with 1872 solution occurrences.
The smallest profile has 183 distinct matrices for 256 distinct seeds and
accepted cross-header vectors. A different profile has no solution on all 256
sampled nonces. Binding does not certify work cost or availability.

The proof interface accepts no A; separately trusted context fixes network,
parent, height and profile. Timestamp/payload/nonce are committed but remain
grindable; chain/payload/time validity is not implemented. Reuse acquisition
counts are reconstructed logical checks, not elapsed cost. Raw ignored evidence
retains every header and outcome; compact committed evidence preserves seeds'
deterministic schedule, source/config/executable hashes and denominators.

### Practical LLL and paid header selection

The [new study](research/practical-lll-and-grinding-v1.md) audits 3603 native FLINT
reductions over 1201 records (1100 historical inputs, 100 extensions and an
explicit repeated frozen miss). All native MITM oracles complete: 468 records
are solvable and 733 empty. The FLINT row/pair probe succeeds on all 468 in this
sample, including the old exact-reference miss. No completeness claim follows.

A separate 24-family experiment varies nonce/time/payload on four toy profiles:
1536 header occurrences, 1520 unique; 580 have a solution and 145 an eligible
score. Paid unit/first/all/reuse policies succeed on 2/10/12/3 families respectively.
All 27 hits pass Rust bound validity and the Python lab score. Native LLL is not
used by these grinding policies, and the research score is not a network target.
Counters and local timings disclose preparation, acquisition and audit boundaries.

### Exact sphere and joint work-model study

The [latest study](research/sphere-and-work-models-v1.md) completes exact sphere
and independent MITM on 1101 records: 408 solvable, 693 empty, 526 proof occurrences.
Every complete set agrees. The finite FLINT probe misses 55 individual vectors.
The cohort includes 1000 cheap historical cases, 100 extensions and one labelled
frozen repeat; it is not the entire earlier lattice cohort.

The joint/single-axis study covers 32 equal-size families, 2048 header occurrences,
1952 unique headers and 512 paid policy runs at four targets. All 147 hit occurrences
pass independent Rust bound validity and the Python score predicate. Failures
remain in component totals; zero-hit per-hit costs are null. Neither the ideal
2^256/T model nor measured counters select chainwork or calibrated SIS cost.

### Integrated practical policies and preprocessing

The [integrated study](research/integrated-lattice-policies-v1.md) runs four
on-demand lattice policies on 16 families/256 header occurrences, with profiles
up to m16 and two score targets. Native availability audits complete; 162 header
occurrences have solutions. Initial policies give 13/20/5/20 hits over 32 runs
each. Warm and cleared-cache repeats bring the total to 192 main runs and 98
hit occurrences, all checked by independent Rust bound validity and Python score.

A fitting cache replay eliminates 273 new reductions and 13850 sphere nodes,
while retaining 291 matrix expansions and 199 vector checks/scores. Cold costs
remain charged; reset replay restores them. Eight capacity-one/target-zero
diagnostic runs show eviction removing the replay saving on larger profiles.
Cached complete pools use exact profile/matrix keys and never retain scores.
Discovery order, overlapping timing scopes and correlated replays are explicit.

### External windows and fresh-context admission

The [external-window study](research/external-windows-and-fresh-context-v1.md)
runs 192 workers at 200/400/1200 ms and 48/128 MiB committed-memory limits.
Of 192 input header occurrences, 160 headers and 128 profile/matrix identities
are distinct. Independent generation and complete native oracles agree.
98 workers complete; 94 time out. Completed stages contain 105 hit occurrences;
112 including seven recovered aborted-stage hits pass Rust bound validity and
Python score/admission. The seven do not enter completed-window win totals.

All 200-ms workers stop before a stage checkpoint; all 1200-ms workers complete.
Intermediate windows recover 38 stages from interrupted workers. Aborted logical
work remains unknown and unconditional per-hit work is null. OS elapsed costs
retain every attempt. Commit metrics are not RSS or a memory-hardness claim.
Actual tests separately confirm timed termination and denied large allocation.

Fresh schedules carry no repeated headers within a schedule. In full windows,
all 58 exact-cache hits come from the tiny-q collision control; larger profiles
have none in this cohort. Stage budgets/acquisition reset; only the cache persists.
Fixed-order one-pass results and shared OS cache state do not rank mining speeds.
Trusted rules fix context/profile/target, timestamp range and allowed commitments
outside packets, without implementing payload-body validity or a live chain.

### Independent admission and persistent campaigns

The [new study](research/native-admission-and-campaigns-v1.md) adds independent
native acceptance of the unchanged lab score and trusted header surface. Frozen
vectors and 10814 deterministic SHA-256/score/admission cases agree; 13 malformed
new requests fail cleanly. Target transport represents 0..2^256 exactly in 33
big-endian bytes; equality at the threshold rejects. Handwritten cryptography
remains laboratory code, not certified production primitives.

Three paid campaigns compare restart-first, persistent carry-first and explicit
carry-fallback across fresh nonce/parent schedules. One budget and vector persist
across all stages, without an external initial solution or matrix cache. Failed
carries never score; fallback charges both matrix derivations and fresh search.
Three salted seeds, two identical-input repeats and one recorded shuffled order
produce 288 external attempts. The 576 input occurrences contain 480 distinct
headers and 368 exact profile/matrix identities. All availability oracles complete.

230 workers complete and 58 time out. Completed workers yield 168 stage-hit
occurrences. Including seven recovered aborted hits, all 175 pass independent
Rust full admission as well as Python checks; the seven stay out of completed
win totals. At 1200 ms all 144 workers complete: restart/carry/fallback yield
38/12/38 stage hits over 144 stage opportunities each, with 988/336/876 paid
reductions. These are repeated toy measurements, not a calibrated speed ranking.

## Paid pools and experimental blocks (backlog 1–10)

Persistent FIFO vector pools now retain paid acquisition, deduplication, eviction,
current-instance checks and bounded combinations across joint header campaigns.
Seven paid solver backends include capped native MITM, sparse screening, LLL,
limited projected-SVP BKZ and a finite pair sieve. Native mode 3 charges every
left/right proposal and joined pair; historical mode 2 remains unchanged.

The final portfolio completed 479 of 700 external windows, with 221 timeouts and
1610 completed stage hits. Nine recovered interrupted-window hits are audited
but excluded from win totals. A separate 56-worker extended campaign completed
with 170 hits; 12 workers reached the shared node cap. Both studies are bounded
toy campaigns with overlapping host load, not isolated speed rankings.

An hour-long differential run checked 1,300,992 inputs with zero mismatches.
Admission sources and its executable remained unchanged; the report explicitly
records changes to two unused native-search sources during that run.

MGB1 commits body, recipient, target and version into the bound proof and block
ID. The Python linear-chain prototype checks fixed policy, parent, height, median
past time, trusted-clock future tolerance and full proof before append. Rust
independently checks hashes and proof admission, not a complete block parser or
chain engine. The selected toy profile produced eight demo blocks. See the
[milestone report](research/pool-portfolio-and-blocks-v1.md) and
[ADR 0011](decisions/0011-experimental-construction-and-chain.md). Production
parameters and the portable work/comparability gate remain open.

## Independent chain and fork/retarget laboratory (backlog 11–15)

Rust now independently parses MGB1 and implements the complete fixed-policy
linear chain state machine. The local corpus compares 6236 commands plus height/
clock/max-shape probes and a reachable 4096-block history, with zero mismatches.
The fork tree uses real blocks, fully replays proposed histories before atomic
canonical changes and exposes detach/attach events. Equal depth retains the
first chosen tip; preference remains nominal fixed-policy depth, not priced SIS.

Sixteen delivery/partition scenarios converge after explicit reliable post-heal
retry, with 25 reorgs; 624 native branch replays cover 2985 block occurrences.
Four paid tiny block campaigns contain 15 carried-vector hits among 64 blocks;
they refute fresh solver acquisition per block, not establish a portable work price.
The separate score-arrival simulator compares 720 retarget hypotheses over 92160
candidate events. Median+1 timestamp strategies cause severe availability failures
in these particular adjustment formulas. No production rule is selected.

Validated storage, branch depth, combined queues, per-label submissions, TTL and
drain work are bounded. Malformed/orphan floods and optimized-Python evidence
refusal are checked. Finite trusted labels are not Internet Sybil protection.
See [report](research/chain-forks-and-retarget-v1.md) and
[ADR 0012](decisions/0012-fork-simulation-without-priced-work.md).

## Verification

### Latest GPU acquisition milestone

[Unit-sparse CPU/CUDA search](research/gpu-unit-sparse-search-v1.md) now acquires
its own candidates on the device. All 42 paired cases (84 attempts) complete
with equal outputs/common ledgers; 71424 candidates per backend produce 368
returned occurrences, including repeated settings and boundary fixtures.
736 independent native proof checks and 53260 separately audited GPU candidate
ordinals have zero disagreements. Ten fresh seeded challenges are distinguished
from degenerate fixtures. Proof-cap chunk tails remain fully charged.

The dense first prototype is not faster in this descriptive run: 7.30 seconds
CUDA versus 3.22 seconds reference Python. Other resident GPU activity and mixed
setup make this an unisolated correctness experiment. Next replace dense products
with sparse column arithmetic and reduce synchronization, before optimized native
CPU comparisons or broader search. The miner was stopped for the GPU runs and
observed exited immediately afterward, then running at a later inspection;
no production consensus rule changes.

### Latest GPU milestone

[Exact CUDA verification](research/gpu-verification-v1.md) ran on the local CMP
50HX using existing PyTorch/CUDA. All 731 pipeline verdicts agree with Python
and independent native Rust: 470 CUDA arithmetic cases (228 accepted, 242 modularly
rejected) and 261 host rejections. The oversized native frame is separately
rejected. Corpus, source, native release binary and runtime metadata are preserved.
Evidence publication refuses a changed binary after metadata collection.

This is supplied-matrix verification, not GPU acquisition, scoring or block
admission. No hashrate or isolated hardware advantage is claimed. The miner
container was stopped with owner authorization, preserved, and later observed
running after the break. The next GPU stage is paid bounded candidate screening.

### Latest adaptive milestone

[Paid adaptive retention](research/adaptive-retention-v1.md) compares four campaign
configurations with seven CPU backends in 336 externally bounded attempts.
306 complete and 30 time out. All 75 jointly completed FIFO/model pairs have
equal stage-hit counts; nine other pairs remain incomplete. Non-FIFO selection
is observed without a paired hit-count improvement in this schedule.

Independent transcript and native audits cover 3750 visited headers, 9489
scores, 655 hit occurrences (652 complete plus three checkpoint) and 1981 model
decisions through 40442 native requests, with zero mismatches. Selection is paid
inside windows and separately counted. Unconditional censored work stays unknown.
Source fingerprints now include solvers and the FLINT lock. The full gate
passed; source review found no outstanding required issues.

The local CMP 50HX and existing CUDA/PyTorch were inspected through authorized
SSH. The device was occupied by an existing miner at inspection; no workload
was stopped during discovery. [GPU plan](research/gpu-readiness-v1.md) begins
with exact CPU/GPU/native comparisons before performance claims.

### Previous supply milestone

[The precommitted-pool study](research/precommitted-pool-supply-v1.md) computes
exact valid-vector count distributions using modular subset ranks, then tests
them against complete matrix spaces. 28 cases enumerate 3957 matrices with zero
disagreements. The separate paid real-header study covers 6144 globally distinct
MGH1 headers and 42063 independent native audit requests, including setup
generation/proof audits, with zero mismatches. Eight successful/preselected pools
complete 24 cohorts; two capped larger-profile acquisitions retain their full
costs and explicitly skip six prerequisite-dependent cohorts.

Uniform independent matrices and scores conditional on the complete valid set
remain model assumptions. Distinct proofs and even pairwise-independent pools
do not imply joint acceptance independence. [ADR 0013](decisions/0013-precommitted-pool-supply.md)
adopts this finite model without assigning portable SIS work, production
chainwork or retarget. Failed setup windows do not certify unsolvability.

python scripts/check.py currently passes:

- rustfmt and clippy without warnings;
- 223 Python tests and 19 Rust tests;
- 10009 differential Python/Rust cases, 2665 accepted, no mismatches;
- three malformed-frame checks and two empty-input/frame checks.
- 103 native-search differential instances (309 searches, 2910 verified proof
  occurrences), zero mismatches, 13 cap checks, 16 malformed native requests
  and one native empty-stream check.
- 1936 generation/binding differential cases (174 SHAKE, 200 matrices, 109
  headers, 1451 proofs, two frozen checks), zero mismatches; 25 malformed
  request/frame rejections and one empty-stream check.
- 10814 SHA-256/score/admission differential cases, zero mismatches; 13 malformed
  new request rejections.
- 64 deterministic MGB1 blocks and 311 independent native hash/admission requests.
- 6236 full native/Python chain commands, two height/clock boundary chains,
  one maximum-shape block and a complete 4096-block storage history, zero mismatches.

Tests cover manual vectors, norm and size limits, rejection sampling and its
budget, exact tiny spaces, solution reuse, support-limited search, rank, policy
completeness, acquisition accounting, caps and strict score thresholds.
MITM tests cover exact sets, collision preservation, odd dimensions, zero-left
vectors, modular wrap, norm boundaries, memory/pair caps and iterator closure.
Ball/budget tests also cover norm-ball completeness, huge box/small ball behavior,
prompt release without cyclic GC, caps/checkpoints, reuse deduplication, distinct
instance seeds and tracer cleanup on clock failures.
The latest local check report includes source hashes. An interrupted rerun
marks its report running-or-incomplete rather than leaving stale success.
Native tests include maximal modulus/norm and exactly sufficient cap boundaries.
Native reruns invalidate both reports before building; a regression test forces
a failed build to check this lifecycle.
Lattice tests cover noninitial pivots, rank deficiency, certificate tampering,
independent reducedness, exact caps, arithmetic exhaustion after a committed
swap, heuristic misses, evidence invalidation and conditional denominators.
Binding tests cover absorb/squeeze boundaries, XOF bounds, rejection sampling,
all committed fields, externally expected policy, early sign/norm/context
rejection, frozen encoding, malformed inputs and both transplant outcomes.
New tests reject malformed optional-backend requests, tampered certificates and
inexact reducedness, and preserve evidence invalidation, capped-oracle denominators,
family/context bounds, strict scores, paid acquisition and last-proposal precedence.
The explicit practical survey separately exercises the actual pinned FLINT backend.
New sphere tests cover exact rational boundary intervals, full sets across ranks,
equivalent unreduced bases, frozen misses, all caps and immediate state release
without cyclic GC. Joint tests cover preallocation bounds, axis compatibility,
overflow, monotone paid target work, failed-run denominators and repeated hits.
Both new surveys invalidate evidence before a failed build.
Integrated tests exercise paid acquisition, failed reuse, all limits, last-score
hit precedence, warm rescoring, exact-key misses, empty-pool caching, eviction,
partial-pool rejection, local corruption rejection and evidence invalidation.
Visitor stops retain verified vectors and do not claim completeness; state is
released without cyclic GC. Explicit native surveys exercise the shared reducer.
External-window tests cover suspended-launch ABI/limits, actual stalled-worker
termination and allocation denial, bounded completion markers, fresh contexts,
conditional censored totals and evidence invalidation. Admission tests cover
early forbidden-surface rejection, strict external scores and malformed rules.
New tests preserve frozen native-score/rule encoding, padding boundaries,
campaign-wide caps, paid persistent acquisition, failed-carry behavior, explicit
fallback charges, final-score stop/hit precedence, shuffled-repeat coverage and
stale-evidence invalidation before a failed campaign build.

Separate source reviews covered the completed milestones. The initial Cargo executable-
selection issue was fixed; the harness uses the artifact returned by the current
build. No required implementation findings remain in the reviewed laboratory.
This is source review, not an independent cryptographic audit.

## Still absent

High-dimensional optimized/GPU mining, a portable adversarial work function,
secure production fork-choice/retarget, native fork database, persisted peer
nodes, transaction/state rules, wallet and MagnetGate integration. Complete
linear engines and bounded simulation are experimental. E3's economic/security
gate and E4's monetary safety gate remain open.

## Decision and next step

[ADR 0002](decisions/0002-solution-reuse.md) rejects the assumption that each
accepted proof or score trial necessarily requires a fresh SIS solve. It does
not reject every possible SIS-based PoW.

[ADR 0003](decisions/0003-enumeration-cost.md) also rejects pricing an SIS proof
by naive box enumeration. Native baselines now extend the CPU parameter scale.
The exact LLL baseline now supplies a competing family; [ADR 0004](decisions/0004-lattice-probes.md)
keeps its misses inconclusive. Header binding and independent generation now
have separate tested interfaces; [ADR 0005](decisions/0005-header-binding.md)
keeps binding distinct from work pricing. [ADR 0006](decisions/0006-practical-solvers-and-grinding.md)
adds native solver competition and paid header selection to future cost models.
[ADR 0007](decisions/0007-sphere-and-work-models.md) keeps ideal eligible-score
trials distinct from actual SIS work. [ADR 0008](decisions/0008-paid-lattice-preprocessing.md)
keeps optimized search inside paid policies and bounds exact-instance preparation
reuse. [ADR 0009](decisions/0009-external-windows-and-trusted-surface.md) adds
external resource enforcement, fresh schedules, immutable evidence and trusted
lab admission. [ADR 0010](decisions/0010-independent-acceptance-and-campaigns.md)
adds independent native acceptance and shared-budget persistent campaigns.
Next test stronger adaptive acquisition/retention policies and exact GPU
execution, then confront portable adversarial work/profile comparability, optimized/GPU
baselines and independent review; add persistence/pruning and real synchronization
after the simulator. Production difficulty and accumulated chainwork remain
unselected. Common local
budgets are experimental resource allowances; local time is not a consensus
oracle and observed allocation is not a memory-hardness proof.
