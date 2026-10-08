# Magnet Network: SIS-PoW research and consensus plan

Date: 2026-10-08. Version: 0.2, English primary edition.
Status: research plan, not a completed protocol or a security claim.
See [current status](docs/STATUS.md) for implemented work.
The [original Russian edition](docs/ru/01-SIS-POW-RESEARCH-PLAN.md) is secondary.

## 1. Objective and sequence

Determine whether Short Integer Solution (SIS) can support standalone PoW:
costly search, inexpensive independent verification, understandable difficulty
adjustment, and resistance to work reuse.

A future MagnetGate may provide a wallet and connectivity. This phase covers
mathematics, PoW, verifier, miner and chain selection. Tariffs, token economics,
listings, user wallets and transport are outside this phase.

Deliver a reproducible laboratory and a decision to continue, revise or reject
the construction. A negative result is useful.

Sequence: mathematical specification → reference verifier → tests and simple
attacks → CPU measurements → work model → consensus simulator → GPU miner →
local network → external review → public testnet.

Do not fork a monetary blockchain before defining acceptable work.

## 2. Corrections to the starting proposal

The [original deep dive](docs/research/lattice-sis-pow-deep-dive.md) contains
hypotheses, not verified schedules, performance, novelty or hardware-resistance claims.

| Assumption | Correction |
|---|---|
| One matrix per header means no nonce search | Mutable header fields change the matrix; study easy-instance selection |
| A norm bound defines difficulty | It defines acceptance, not predictable search cost |
| Low variance is necessary | Randomness is normal; characterize distributions and control behavior |
| An asymptotic exponent gives GPU seconds | Measure algorithms, preprocessing, memory and constants |
| Lattice PoW makes the entire chain post-quantum | PoW, signatures and key establishment require separate analysis |
| Replace only CheckProofOfWork | Format, sync, difficulty, chainwork and resource limits also change |
| Memory demand guarantees ASIC resistance | It is a hardware-cost hypothesis |
| Equihash-like structure inherits SIS security | A new construction needs its own argument |

The original parameter sketches are inconsistent. Do not adopt them as defaults.
Existence depends on norm, bound and domain; m > n·log(q) is not a universal
condition for every SIS variant.

## 3. Initial laboratory choices

Changes to these choices require documented decisions.

| Question | Initial choice |
|---|---|
| Task | Dense SIS; ISIS as a later comparison |
| Norm | Exact squared L2 bound B2 |
| Verification | Deterministic integer arithmetic |
| Matrix generation | SHAKE256, domain separation, rejection sampling |
| Reference | Transparent Python arbitrary-precision arithmetic |
| Independent verifier | Rust with explicit bounds and overflow analysis |
| Solvers | Tiny exhaustive search, linear algebra, LLL/BKZ, suitable sieving |
| GPU | After problem selection and profiling |
| Consensus candidate | Nakamoto chain with cumulative-work fork choice |
| Difficulty | Fixed first; dynamic only after a work model |
| Execution | Local; no default paid GPUs or GitHub Actions |
| Integration | Separate later interface; existing MagnetGate remains operational |

SIS validity does not prove bandwidth delivery, storage or other services.

## 4. Mathematical core and encoding

For prime q, positive n,m, A in Z_q^(n×m), and integer bound B2:

~~~text
x != 0
A*x == 0 (mod q)
sum(x[i]^2) <= B2
~~~

The lab chooses L2; other definitions use different norms [S1].
Require B2 < q² to exclude q·e_i. This is not a hardness proof. Test sparse
vectors, dependent columns, deficient rank and other cheap solutions.

For prime q the kernel lattice has determinant q^rank(A), equal to q^n only at
full row rank. Gaussian heuristics do not guarantee an admissible solution.
A timeout means not found, not nonexistent.

Manual fixture:

~~~text
q=7 n=1 m=2 B2=5 A=[1,2]
[2,-1]: equation zero, squared norm 5 → accept
[0,0]: reject zero
[1,0]: reject equation
[7,0]: reject norm
[2,-1] at B2=4: reject norm
~~~

These are toy values. Network verification must derive A, not accept a miner's
chosen matrix. Before optimization fix widths, byte order, signed encoding,
lengths, residues, dimensions, domain strings and versions. Reject alternative
encodings/trailing bytes and bound allocation before variable-length parsing.

Canonical sign: first nonzero coordinate positive. This removes x/−x only, not
other short vectors or combinations. For ISIS, negation generally changes b.

## 5. Binding work to blocks

Avoid circular dependencies by separating preheader, proof and final block ID:

~~~text
preheader = encode(chain_id, protocol_version, pow_version, parameter_profile,
                   previous_block_id, height, transaction_root,
                   timestamp, difficulty_descriptor, reward_commitment, nonce)
instance_seed = SHAKE256(domain_instance || preheader)
A = expand_matrix(instance_seed, profile)
proof = canonical_encode(x)
block_id = HASH(domain_block || preheader || proof)
~~~

This is a field sketch, not a finalized serialization. Fix exact hashes and
widths before networking. Consensus determines allowed profiles/difficulty.
Bind payout to the body; define consistency if coinbase is already committed
through transaction_root.

Work must not transfer freely between parents/chains. Payout, transaction and
difficulty changes must change the challenge. Include every field giving new
score attempts. Replaying the same proof must not create additional work.

An old x may coincidentally solve a changed matrix: tests must check regeneration
and independent validity, not assume mathematical coincidences are impossible.

## 6. Candidate constructions

### A. Pure SIS with a norm threshold

Search header-bound instances; vary B2 inside a fixed profile. Verification is
simple, but cost can be discrete and affected by instance selection, memory and
preprocessing. Do not define weight as 1/B2 or an arbitrary vector-length function.

### B. Fixed SIS profile and an outer hash target

~~~text
score = HASH(domain_score || preheader || canonical_encode(x))
accept if score <= target
~~~

This is a candidate, not solved work accounting. One vector or reduced basis can
yield many admissible proof inputs. Study signs, multiples, gcd reduction,
combinations, symmetries and free fields. A nonce changing score but not the
challenge is unacceptable. Unique encoding does not ensure a unique solution.

For a uniform k-bit score and inclusive target T, success probability is
(T+1)/2^k. Its reciprocal counts score trials, not automatically SIS solves.
A work function must account for amortization.

### C. Generalized birthday problem with lattice constraints

A separate Equihash-inspired branch [S4]; it does not inherit SIS security.
Compare A/B first, then decide whether to pursue C. Distinct constructions need
distinct pow_version identifiers and incompatible vectors.

Compare intended solvers with attacks. Honest implementation speed does not
establish the adversary's minimum cost.

## 7. Consensus decisions

Explore Nakamoto consensus: miners propose, full nodes validate, greatest
cumulative work selects among valid chains. Votes or operator signatures do not
substitute for PoW.

An initial fixed-difficulty simulator may use equal weights as an explicit
assumption, not as evidence of SIS security. Dynamic difficulty requires a
deterministic work function. Do not use height alone, sum vector lengths, trust
miner-reported seconds or use benchmark measurements as a consensus oracle.
Bitcoin's target/work formula relies on hash search [S5].

| Decision | Required specification |
|---|---|
| Fork choice | Validity, weight, safe accumulation and equal-work behavior |
| Equal work | Initially retain first accepted branch until greater work arrives |
| Retarget | Ancestor-derived adjustment, starting value, bounds and rounding |
| Timestamps | Past/future limits; temporary deferral vs permanent invalidity |
| Block interval | Compare 30/60/120 seconds before selecting; no speed promise |
| Proof | Format, maximum bytes, worst-case acceptance/rejection cost |
| Header sync | Delivery and verification of SIS proofs, including light clients |
| Profiles | Allowed parameters and activation; reject unknown profiles |
| Reorg | Rollback, revalidation and no duplicate reward |
| Upgrades | Version activation and behavior of old nodes |

Confirmations are probabilistic, not absolute finality. Dummy committed
transactions in a simulator do not create a monetary blockchain. Before public
testnet separately specify state, signatures, fees, subsidy/maturity, block
limits and rollback.

Compare fixed difficulty, windowed adjustment and per-block adjustment.
Do not select WTEMA/ASERT by name before understanding the work model.
Simulate capacity ×0.1/×0.5/×2/×10, major miners leaving, oscillation, propagation
delays and timestamp manipulation using measured SIS distributions.

Changes to B2 must not hide different work costs, cause prolonged unsolvable
periods or permit cheap inflated-weight branches. Changing dimensions is a
profile change requiring separate comparability analysis.

## 8. Test plan

Current implementation coverage is tracked separately in docs/STATUS.md.

| ID | Case | Expected property |
|---|---|---|
| M01 | Manual fixtures | Exact accept/reject |
| M02 | Wrong/missing vector lengths | Early rejection |
| M03 | Norm boundary and one above | Exact cross-language agreement |
| M04 | Extreme/signed coordinates | Defined arithmetic or safe refusal |
| M05 | q·e_i, sparse/column dependencies | Expose trivial profiles |
| M06 | Unknown versions/huge dimensions | Reject before large allocation |
| M07 | Alternative encodings, extra bytes, −x | Canonical encoding |
| M08 | Same seed across platforms | Same matrix and intermediate bytes |
| M09 | Rejection-sampling boundaries | Independent reference agreement |
| M10 | Exhaustive tiny domains | Exactly the oracle's solution set |

A mutation may yield another valid vector: do not assume every mutation is invalid.

| ID | Attack | Investigate |
|---|---|---|
| A01 | Change parent/root/payout/nonce/chain/version | Regeneration and free score fields |
| A02 | Replay proofs/jobs | Duplicate credit |
| A03 | Screen many matrices | Easy-instance selection |
| A04 | Reuse bases/lists | Amortization within/across jobs |
| A05 | Combine solutions | Cheap score multiplicity |
| A06 | Scale memory/devices | Nonlinear advantage and hardware barriers |
| A07 | Almost-valid proofs | Expensive rejection/node overload |
| A08 | Manipulate target/time | Inflated weight and retarget bypass |

Consensus tests: shorter higher-work branch wins; invalid proof or target never
wins on claimed work; equal-work forks; partitions/recovery; interrupted writes
and reorg; genesis resync; bounded invalid-header queues; version activation.
State convergence assumptions, including eventual connectivity and the
adversary's effective-work share.

Start with manual cases, exhaustive tiny spaces and ≥10000 reproducible
differential cases. Add a bounded one-hour local fuzzing session with saved seeds.
This budget is not certification. GPU outputs must pass exact verification even
when their search heuristics use approximate arithmetic.

## 9. Measurements and provisional targets

Define an attempt per construction. Solutions/second at different profiles, or
against Equihash, are not directly comparable.

Record source/config hashes, seeds, CPU/GPU/RAM/VRAM, OS/drivers/compiler flags;
generation, reduction, search, proof and verification time; peak memory and
transfers; first/subsequent solution costs; failures/timeouts; reliable energy
measurements; and attack costs in comparable units.

Separate cold and steady state. Preserve failures. Treat timeouts as censored
observations. Publish raw data and uncertainty; do not infer p99 from a few successes.

Initial sampling: 1000 cheap or 100 expensive instances before budgeting more.
Provisional filter: verification including generation p95 ≤10 ms on a documented
ordinary CPU; proof ≤16 KiB. Revisions must be explicit. ARM and history-sync
costs require separate evaluation. These are engineering screens, not promises.

## 10. Project layout and tools

~~~text
spec/                 mathematical and protocol specifications
reference/            transparent Python verifier and bounded probes
crates/sis-verifier/   independent verifier
solvers/              future CPU algorithms
miners/               future GPU implementations
simulator/            future chain and difficulty experiments
tests/vectors/        fixed fixtures
tests/adversarial/    future regression corpus
benchmarks/           future pinned experiments
docs/decisions/       decisions and evidence
~~~

G6K/fplll/fpylll [S2] are potential research tools, not network consensus code.
Pin versions and review licenses. GPU lattice research [S3] does not establish
our parameters or consumer-hardware suitability. Reproduce and profile first.
Use isolated Linux/WSL if needed after inspecting existing tools.

Keep one local fast-check command. Expensive fuzzing and benchmarks require
explicit commands, never automatic execution when opening the project.

## 11. Milestones

| Stage | Deliverable | Gate |
|---|---|---|
| E0 | Math, encoding, seed, threats, manual cases | Coherent definitions |
| E1 | Verifiers, corpus, exhaustive oracle | Agreement and bounded parsing |
| E2 | CPU baselines, raw data, attacks | No known trivial bypass in retained candidates |
| E3 | A/B decision, difficulty/work argument | Model and independent expert review |
| E4 | Fork/retarget/time/overload simulator | Deterministic rules, no known cheap inflated-weight branch |
| E5 | GPU miner and hardware comparison | Exact verification; resource/energy/scaling data |
| E6 | Local nodes and ≥2 miner processes | Sync, forks, restart and reorg pass |
| E7 | External testnet and published artifacts | Blocking findings closed; complete transaction/resource rules |

Local processes do not establish independent operation. External testnet requires
separate operators, machines and networks. Testnet does not imply coin value.
E2/E3 are research: estimate effort after data, not from the proposal's
unvalidated person-month numbers.

## 12. First sprint

Specify laboratory and competing hypotheses; implement exact verifier and manual
cases; add deterministic generation/vectors; compare exhaustive tiny spaces;
add Rust and differential tests; probe trivial solutions/combinations; collect
CPU baselines including timeouts; report rejected profiles and open questions.

Success means another developer reproduces the results, not a large codebase
or an increasing miner counter.

## 13. Stop or revise when

- Accepted proofs multiply cheaply without corresponding work accounting.
- Easy-instance screening invalidates the work model.
- Work cannot be compared after difficulty changes.
- Invalid proofs cheaply overload full nodes.
- Memory requirements exclude target hardware or GPU benefit is unsupported.
- A changed task retains an obsolete security argument.
- Progress depends on unestablished claims.

Reject or revise the hypothesis explicitly. Switching away from SIS is a new
decision, not a hidden fallback.

## 14. Open questions

Task choice; practical profiles; reuse; instance selection and distributions;
weight/retarget; CPU/ARM history cost; light-client proof delivery; concentrated
memory/private solvers; node base; and required independent cryptographic review.

Use “experimental SIS-PoW” until specific claims have adequate evidence.

## 15. Sources

Checked 2026-10-08. These establish definitions and examples, not our security.

- [S1: MIT SIS definitions](https://65610.csail.mit.edu/2024/handouts/pset1.pdf).
  Its L∞ definition differs from this lab's L2 choice.
- [S2: G6K](https://github.com/fplll/g6k).
- [S3: Advanced Lattice Sieving on GPUs](https://eprint.iacr.org/2021/141).
- [S4: Equihash](https://orbilu.uni.lu/handle/10993/22277).
- [S5: Bitcoin chain rules](https://developer.bitcoin.org/devguide/block_chain.html)
  and [mining](https://developer.bitcoin.org/devguide/mining.html).
- [S6: NIST post-quantum cryptography](https://csrc.nist.gov/Projects/Post-Quantum-Cryptography).
