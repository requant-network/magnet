# Critical path to understanding

Date: 2026-10-09. Status: working directive for implementation work. This file
narrows the whole programme to the single open decision and the minimum set of
experiments that resolve it. Read it before starting any task; every task must
map to it or be explicitly parked.

## 1. The one open question

**Does SIS admit a deterministic, monotone, portable and reuse-resistant work
function for permissionless proof of work?**

Everything else is secondary. If such a function exists (construction A, or a
defensible reformulation B/C), the project can proceed to a chain. If it does
not, the correct outcome is an **explicit, published negative result** — that is
a valid completion, not a failure.

The scientific risk is concentrated here. Verifiers, native backends, CUDA
kernels, chain/fork/retarget simulations and supply models are *supporting*
machinery; none of them answers this question by itself.

## 2. Rules

1. **One critical path.** Keep `docs/CRITICAL-PATH.md` (this file) as the single
   list of the open decision and the decisive experiments. Every proposed task
   states which experiment below it advances. Tasks that do not map are parked in
   §6, not started.
2. **Decision value, not volume.** Before any milestone ask: *does the result
   change the answer to A vs B?* If no, do not build it (more solver variants,
   more single-scope timings, more specs are not progress).
3. **Falsification first.** Experiments must try to **break** candidate work
   functions (find cheap inflated weight, reuse, screening, preprocessing), not
   to confirm them.
4. **Timebox and kill.** Every experiment gets a budget and an explicit stop
   criterion. On failure: record it, stop, do not chain the next.
5. **Negative result in parallel.** Write the negative-result note (ePrint-style)
   while running, not afterwards.
6. **External review early.** Get one independent cryptographer to review the
   framing and the candidate work functions **before** large investment.
7. **Scale only where it matters.** Move to the **smallest** profiles where the
   solver/verifier asymmetry and the memory/preprocessing effects actually
   appear; state explicitly where "toy" ends and why.
8. **No monetary/consensus surface** until the work function passes review.
   Prototypes stay minimal.
9. **Reduce document sprawl.** Keep one "Findings so far" page and one "Open
   questions" page; add a decision record only for a real fork in the path.

## 3. Candidate work functions and their falsifiers

State each candidate explicitly and the concrete cheap attack that would kill it.

- **A. Pure SIS with a norm threshold.**
  - Falsifiers: instance screening (miner picks easy A/header/nonce); solution
    combination (sign/multiples/gcd/linear combinations); basis/list reuse within
    and across jobs; preprocessing amortisation; superlinear memory scaling;
    self-reported work.
- **B. Fixed SIS profile + outer hash target (score).**
  - Falsifiers: one vector or reduced basis yields many admissible inputs;
    nonce changes score but not the challenge; unique encoding does not imply a
    unique solution; score trials ≠ SIS solves.
- **C. Generalized birthday with lattice constraints (Equihash-like).**
  - Caveat: does **not** inherit SIS hardness; needs its own argument. Only
    pursued after A/B are decided.

For every candidate, the weight must be defined **by component** (generation,
preprocessing, acquisition, failed attempts) and shown **monotone** in the
difficulty knob and **non-transferable** across parents/chains.

## 4. Decisive experiment sequence

Run these in order. Each has a kill criterion: if it fires, record the negative
result for that construction and move to the next candidate (or stop).

- **D1 — Write the path.** Produce this file's concrete experiment list with
  profiles, scopes and thresholds. (done when agreed)
- **D2 — Candidate work functions + falsifiers.** Write §3 formally, with the
  exact cheap attacks and the inputs each one varies.
- **D3 — Screening attack.** On a slightly larger profile, measure whether a
  miner gains **> 2x** from *selecting* headers/matrices/nonces. If yes, a
  standalone SIS work model is very likely unsound.
- **D4 — Preprocessing / amortisation attack.** Measure cost(first) / cost(subsequent)
  for LLL/BKZ/sieve under a shared budget. If reuse breaks monotonicity, A fails.
- **D5 — Memory / time trade-off, matched scope.** One CPU and one GPU at a
  **matched domain, caps, output and timer scope**: is the weight (energy x time)
  portable, or does a memory-rich device win superlinearly?
- **D6 — Formalise and prove.** Only if D3–D5 do not kill A: define the
  work-weight function and prove monotonicity (paper + external review); then E4
  (retarget/fork simulator).

## 5. Success metric

A written, defensible answer to the A-vs-B question, backed by reproducible
evidence and an external review note. **Not** a larger codebase, more tests, or a
miner counter.

## 6. Parked until the path resolves

Do **not** start these before §4 is decided:

- more solver variants / additional survey families that only refine measurement;
- broader GPU kernels or a portable miner beyond what D3–D5 need;
- chain/consensus/retarget features beyond the minimal D6 simulator;
- wallets, pools, payments, or any monetary framing;
- new document families (spec/NNN, ADR/00NN) unless they resolve a fork in §4.

## 7. Relationship to existing documents

- Research plan and gates: `01-SIS-POW-RESEARCH-PLAN.md` (§11 E0–E7, §13 stop/revise).
- Open work-weight gate: `docs/decisions/0007`, `docs/decisions/0012`,
  `docs/decisions/0013`.
- Current implemented state: `docs/STATUS.md`.
- Language: use "experimental SIS-PoW"; make no security claims.

## 8. D2 definitions and frozen D3 experiment (2026-10-09)

This section makes the next falsifier concrete. Existing demonstration consensus
is unchanged. No production work function is selected.

### D2: acceptance, nominal credit and hidden cost

Let c=(network,parent,height,profile) be externally trusted. The permitted miner
surface for this experiment is nonce only; payload,time,c and target are fixed.
MGH1 commits nonce into the matrix seed, so a changed nonce changes both challenge
and score input. This experiment does NOT assume score-only nonce grinding.
A(header,z): canonical nonzero signed vector, ||z||²<=B2 and A(header)z=0 mod q.
B(header,z,T): A AND SHA256(SCORE_DOMAIN||encode_proof(header,z))<T,
with trusted fixed profile and 0<T<=2^256. T=0 admits nothing and has no finite
inverse-target weight. Repeated identical input repeats the same digest.

Candidate credits to falsify (not implemented chainwork):

- A-unit: W=1 per accepted header. Observable, but does not certify equal cost.
- A-density: W=q^n/N(m,B2), where N is the number of canonical nonzero integer
  vectors in the complete norm ball, NOT the support<=3 family. Under uniform
  independent matrix rows, every fixed legal vector has acceptance probability
  q^-n (B2<q² excludes all-zero residues). Hence E[number of solutions]=N/q^n.
  Its reciprocal is not E[cost to find a solution], and correlated vectors do not
  give independent events. Exact N is a mathematical definition, not a cheap
  production verifier implementation. Decreasing B2 cannot increase N, but MGH1 also
  changes the derived matrix; this is no pathwise monotonic-cost proof.
- B-score: W=2^256/T. Under a random-oracle assumption for distinct previously unqueried eligible
  messages, success probability is T/2^256. Geometric mean trials W additionally
  requires an unlimited supply; finite supply may exhaust without success. It does not
  price acquiring those inputs. Multiplying it by a fixed alleged SIS-solve cost
  does not make shared acquisition/multiples/reuse disappear.
- Miner-reported counters/time: rejected as a trusted verifier-computable weight.

For A-density and B-score the displayed knob gives algebraic monotonicity of the
nominal credit, not adversarial compute/energy monotonicity. A witness exposes
validity, not the chosen algorithm's hidden execution. Required component vector:
header/matrix generation, domain setup, discarded-header probes, selected search,
failed proposals, dense proof validation, scoring and all incomplete work.
These are local evidence counters; no weighted sum is installed as consensus.

### D3: paid screening versus strong controls

Version d3-screening-v1. Profiles (q,n,m,B2): (7,1,4,8) calibration,
(17,3,16,12),(7,4,16,12),(257,2,16,12) primary. The first two primary profiles
increase equation count over earlier soluble cohorts; all remain toy-sized.
Existing spec21 bound2 support<=3 order is reused, candidate cap4096 per selected
header; no new solver, GPU kernel or claim of complete SIS search.

Three labels2026100926/2026100927/2026100928 define fixed common header streams:
ASCII `d3-screening-v1/q/n/m/B2/label`, with SHA256(label+'/network', '/parent',
'/payload') commitments, height1,time20261009, nonce0..255. Construction A and
B share the stream; B target2^254. Each run starts cold, no carried proof/basis.

Policies: plain sequential search; single-header probe control; random batch4
control; screened batch4 choosing maximum first-row survivors. Probe the first64
existing candidates against row0 only. Cached flags are paid once and reused
only for the selected header, screening remaining rows before eligibility. All
batch generation, setup, probes, selection/tie comparisons and rejected headers
are paid. Random choice uses a paid hash independent of proxy outcomes. Ties
choose the earliest header. No future complete availability oracle is used.

Use the existing cooperative component model: additive nonnegative logical
counters, informational matrix SHAKE byte count zero-weight. Budget100000 units
per campaign, at most256 generated headers. Charge completed proof transactions
before checking budget; preserve overshoot and use ACTUAL charged units in rate
calculations. Each policy stops when budget/header bound is reached; it can emit
at most one credited result per selected header. Dense checks and scores are paid.

Three repetitions deterministically rotate policy order by group/repetition.
Logical transcripts must reproduce exactly; repetitions are timing observations,
NOT more independent challenges. Total4 profiles*3 labels*2 constructions*4
policies*3 repetitions=288 runs. Global study deadline120 seconds, no tuning or
extension after seeing outcomes. Interrupted/empty/censored runs stay in evidence.

Primary diagnostic: successes/actual logical units. For each primary profile
and construction, aggregate only repetition0 over the three labelled streams.
Screened rate must exceed EACH of plain, probe and random controls by strictly
more than2x, with at least5 successes for every compared policy. Otherwise report
not-triggered or insufficient-successes, never divide by zero or discard misses.
Use exact rational comparisons. Component units are arbitrary: a trigger rejects
uniform-credit cost inference in this tested model, NOT all pure SIS constructions.
Secondary matched cold policy wall times remain descriptive, separate from units.

The run order is profiles,construction(A then B),repetition,label; within each
label rotate [plain,probe-control,random4,screened4] left by (label_index+repetition)
mod4. Evaluate after the complete profile/construction group, not mid-campaign.
All repetition0 campaigns and native/ledger audits must complete their declared
logical stop before a trigger can stand. Deadline/exception/audit failure retains
partial evidence but suppresses all successful comparative conclusions.

| Policy | Probe coverage | Chosen header | Cached flags |
| --- | --- | --- | --- |
| plain | none | next single header | none |
| probe-control | first64,row0 | same single header | reused |
| random4 | first64,row0 on all4 | paid SHA256 selector | reused on selected only |
| screened4 | first64,row0 on all4 | maximum survivors, earliest tie | reused on selected only |

Every selected search traverses the same first4096 candidates sequentially.
B continues after an eligible score miss until a hit, candidate cap or paid
budget stop; A stops on the first valid proof. No previously missed eligible
message is scored twice. Check budget after each completed generation/probe/
selection/candidate transaction. Completed dense validation/score/hit is committed
before its stop check; rejected headers are never searched retrospectively.
Random selector is SHA256(b'D3/random-selection\0'+base.encode()+batch_start.to_bytes(8,'little')),
using its first8 digest bytes as little-endian integer modulo batch length;
count hash/input bytes. Both batch4 paths inspect all probes before choosing.


Build/freeze current Cargo-selected sis-lab before runs. Independently reconcile
ALL generated headers/seeds/matrices (including rejected ones), returned A/B
proofs and eligible score misses through native Rust outside timed campaigns.
Rebuild selected prefix/carry-free ledgers independently in Python. Bind exact
contract/config/source/native/raw digests before and after publication; invalidate
old success before build. Store completed records and unknown current work on
failure. If a declared D3 trigger fires, record the negative finding and stop this
batch; do not automatically proceed to D4/D6 or expand a construction.

## 9. Frozen D3 fresh-stream replication (2026-10-10)

This is a prospective replication of the signal on `(17,3,16,12)`, not an
extension of the old sample after observing more results. Run only this profile,
with A then B and all four unchanged policies. Use the namespace
`d3-screening-replication-v1` and labels2026101001 through2026101024 inclusive.
The namespace replaces the old namespace in the SHA256 commitment derivations
in section8; height1, time20261009 and nonce0..255 stay unchanged. No old stream
is pooled into the new comparison. Confirm distinct encoded headers versus v1
before the run. The profile is deliberately selected from the earlier signal;
this is not an unbiased search over all SIS profiles.

Keep budget100000, header_limit256, candidate_limit4096, probe_limit64 and
B target2^254. The increased number of independent streams (24 rather than3)
addresses the earlier sparse-success floor without tuning the solver, proxy or
per-stream work allowance. Three rotated repetitions remain timing observations;
only repetition0 is diagnostic. Planned maximum: 1*2*24*4*3=576 campaigns.
The global deadline, including replay/native audits but excluding native build,
is240 seconds. Do not extend this deadline or add streams on failure.

Preserve the original exact rule: at least5 successes for EVERY policy and a
screened success/actual-unit rate strictly greater than2x EACH control. Audit
every repetition0 campaign and its native header/proof/score messages before
evaluating the full construction group. On a primary trigger, stop immediately
after that audited group; B may remain unrun after an A trigger. Retain the
planned/completed counts and this explicit stop. Deadline/interruption/source
change/audit failure suppresses all successful comparisons and keeps partial
evidence. Fresh-stream insufficient/not-triggered outcomes are reported as such;
absence of a trigger is not proof of a safe work function. No statistical
confidence claim or general SIS impossibility claim follows from this rule.

The historical default runner and v1 evidence remain separate. Run
`python scripts/screening_replication.py` after the local check and source review.
Commit the protocol and implementation before executing this fresh schedule.
Record findings on the central findings/open-questions pages. This batch does
not automatically advance to D4, add GPU kernels or change consensus.

## 10. Frozen D4 exact full-kernel transfer diagnostic (2026-10-10)

Question: can a paid complete reduced kernel basis be reused for a different
MGH1 matrix? Byte equality is too narrow: distinct matrices can have equal
rowspaces. Use the canonical RREF-derived integer kernel as the FIFO cache key,
including the entire profile and rank. Pay receiving matrix generation and
kernel fingerprint construction even on a hit. Audit the complete certificate
against the receiving matrix, including rank/index; membership alone is invalid.
On a miss the current implementation pays kernel construction twice (fingerprint
and preparation). Preserve this overhead rather than infer a speedup from it.

First exhaustively check all donor/receiver pairs for q3,m2,n1 and n2,
including rank0. For fixed rank-r donor rowspace and independent uniform receiving
rows, containment probability is q^[-n(m-r)]. Equal-rowspace probability is
product(i=0..r-1, q^n-q^i)/q^(n*m). For an adaptive cache of capacity C and H fresh
opportunities, a union bound is min(1,C*H*q^[-n(m-min(n,m))]). These are conditional
finite-field statements, NOT a proof that the actual header generator is random,
NOT SIS hardness or portable work pricing. A fixed legal donor vector has fresh
matrix acceptance probability q^-n, just like the free vector e1; a cold-LLL
comparison alone would therefore be an inadequate donor-vector baseline.

Run only a small correctness integration, namespace `d4-kernel-transfer-v1`.
Profiles are (3,1,2,2) calibration and (17,2,8,8) primary boundary. Labels are
2026101031 and2026101032. For each profile/label, root is the ASCII namespace,
slash, comma-joined profile integers, slash, decimal label. Network and payload
are SHA256(root+'/network') and SHA256(root+'/payload'). Header i=0..7 uses
parent SHA256(root+'/parent/'+decimal i), height i+1, timestamp20261010+i, nonce i.
All headers differ; changes to parent/height/nonce must be reflected in native
proof verification and fresh scores. This is a predetermined header stream,
not adaptive nonce grinding. Cache starts empty in every worker.

Compare `cold` and `kernel-cache`, rotating that order by label index. Schedule:
profile, label, rotated policy, eight workers total. Each worker has shared
search node cap10000, at most8 reductions, per-header search cap2000, FIFO cache
capacity8, proof cap1 per header; preparation/search backend is pinned FLINT
LLL delta0.75 with exact Gram arithmetic. Wall cap15000ms, Windows Job memory
cap192MiB. Global deadline180 seconds includes native/replay audits, excludes
native build. No extensions or additional statistical timing repetitions.

Audit every generated matrix/seed natively, every full certificate against its
recipient, FIFO donor ownership, exact search prefix/stop/ledger, all returned
proofs and new context-bound scores. Complete cold/cache pairs must return the
same proofs and scores. Search replay shares the enumeration implementation;
native verification independently checks validity, not search completeness.
Persist interrupted/censored worker snapshots and unknown in-flight work. Any
failure suppresses successful paired conclusions. Bind contract/config/source/
binary/raw hashes, invalidate old success before build, commit before running.

The exhaustive finite-field result plus this bounded integration can park ONLY
exact complete-kernel collisions under the conditional fresh-uniform model.
Zero primary hits cannot statistically validate a tiny theoretical probability;
an unexpected primary hit is first a generator/cache/audit alarm. Timers are
descriptive, not a hardware speed comparison. Partial bases, geometric reuse,
adaptive header selection and general D4 amortization remain open. No A/B
promotion, GPU integration or consensus change follows automatically.

## 11. Frozen B-H repair and public-gate bypass (2026-10-10)

This is a candidate fork prompted by D4 same-header witness supply, not a claim
to close partial-basis reuse. Existing B hashes header+proof, so multiple eligible
vectors create distinct score inputs. Research candidate B-H instead requires
the same canonical/context-bound SIS proof AND SHA256(D_H||header)<T, where D_H
is ASCII `MagnetNetwork/SIS-LAB/header-gate/v1` followed by one NUL byte. One
score per header eliminates proof-dependent score multiplicity. MGH1, existing
B/MGB1/chain admission and production rules are unchanged.

The explicit nominal hypothesis B-H-SIS is W=K_SIS*2^256/T at a fixed profile,
where K_SIS is an alleged fixed acquisition expense, NOT a selected weight.
Its acquisition premise is that each outer-score attempt must pay a fresh SIS
preparation, so lowering T multiplies the SIS contribution. Falsifier: a public
score-first miner discards target-failing headers before matrix expansion or
reduction, retaining the same accepted outputs. This rejects that premise for
this repair; it does NOT reject ordinary hash credit or target monotonicity,
prove a lower bound for K_SIS, kill A/B generally or promote B-H as secure.

Conditional iid renewal model: header scores are uniform and independent of the
entire target-independent SIS attempt transcript; attempts succeed with s>0 and
have mean cost C, gate generation/hash cost G>0. A solve-all control spends
(G+C)/(p*s) per accepted block; gate-first spends G/(p*s)+C/s, where p=T/2^256.
Cost and success within an attempt may correlate. Under those assumptions,
the SIS contribution is independent of p for gate-first. At p1/4,C>=G, the
control/attack ratio is at least8/5; this is illustrative algebra, not a fitted
timing result, security theorem, operational hashrate or optimized lower bound.
At s0 or T0 there is no finite accepted-block expectation. Finite bounded batches
do not estimate this renewal model or assume every challenge is solvable.

Minimal integration namespace `d4-header-gate-v1`. Profiles are (3,1,2,2)
calibration and (17,2,8,8) primary; labels2026101041..2026101044. Derivation uses
the comma-joined root formula of section10 with this namespace/labels. Network,
parent and payload are SHA256(root+'/network'), SHA256(root+'/parent'), and
SHA256(root+'/payload'); height1,time20261010,nonce i=0..4. Only nonce varies
inside a five-header batch. Freeze T=2^254. Score all five headers and retain
rejects for both arms: `solve-all` invokes cold preparation on every header;
`gate-first` invokes it only on passing headers. The control's early-known hashes
are deliberately not used for filtering: this is a fixed complete-batch
preparation-obligation diagnostic, not a claim about an optimal baseline or
time-to-first-block. Empty passing batches explicitly skip the worker and remain
in evidence with zero admitted results, not zero-cost successes.

Reuse the existing WDP1 cold LLL0.75 worker and recipient/FIFO/ledger audit:
nodes10000,reductions8,search cap2000,proof cap1 per attempted header. Five times
2000<=10000 ensures identical full per-header search allowances in both arms;
removing rejected predecessors cannot change the selected attempts' caps.
Worker wall15000ms,memory192MiB; maximum16 workers, no timing repetitions.
Global deadline270 seconds includes all replay/native audits, excludes build.
Schedule profile,label,policies rotated by label index modulo2. Do not extend.

Native mode4 checks EVERY header score, including rejected/skipped challenges.
Native modes2/3 independently check generated seeds/matrices and returned SIS
proofs. The worker's existing proof-bound scores are auxiliary overhead, retained
and audited but unused in B-H; no unmeasured gate timer or weighted speed claim.
Every declared attempted-header sequence must complete; search-cap misses are
retained as bounded failures, never proof of mathematical absence. Passing
header proof/search-work/stop outputs must match exactly. A primary pair reports
`observed-bypass` only with at least one common native-valid passing proof AND
at least one rejected header whose control preparation was paid and avoided by
gate-first. Zero-output or no-rejection pairs are structural-only. Aggregate
counts retain every pair; no successful conclusion survives any run/audit/
publication failure. There is no inference about how much cheaper one preparation
is than another. Keep cold setup, auxiliary scoring and failed work visible.

Commit source/protocol before execution. Invalidate old success before build;
bind source/contract/config/native/raw hashes and read back published bytes.
Preserve censored snapshots, owned attempt paths and unknown in-flight work.
Publish the positive or negative candidate limitation on the central findings
page. This batch does not automatically proceed to C, GPUs or monetary rules.
