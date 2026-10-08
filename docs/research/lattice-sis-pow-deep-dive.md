# Lattice / SIS proof-of-work — deep dive

The most credible "not yet mined" candidate for a real post-quantum GPU PoW. This note covers the
problem, the PoW construction, the design trap (difficulty/grinding), the GPU mining algorithm,
parameter sketches, verification, ASIC-resistance, a build plan and the open risks.

## 1. The problem

**SIS (Short Integer Solution, Ajtai 1996).** Given a uniformly random matrix
`A ∈ Z_q^{n×m}`, find a nonzero `x ∈ Z^m` with `A·x ≡ 0 (mod q)` and `‖x‖ ≤ β` (small).

**ISIS** (inhomogeneous): given also `b ∈ Z_q^n`, find short `x` with `A·x ≡ b (mod q)`.

Security: finding short solutions is as hard as worst-case lattice problems (SIVP/SVP), which are
**believed hard for quantum computers** — hence "post-quantum". Best known algorithms are
**lattice sieving**, complexity `~2^{0.292 m}` (BDGL'16) down to `~2^{0.265 m}` with tricks, or
`~2^{0.31 m}` heuristic. Crucially, hardness grows **exponentially in the dimension m**.

## 2. Turning it into PoW (draft)

- `A = H(header)` reduced mod q (bind A to the header, no miner choice).
- Miner finds a nonzero `x` with `A·x = 0 (mod q)` and `‖x‖ ≤ β`.
- **Verification = compute `A·x mod q` and check the norm.** Cost is one `n×m` mat-vec: for
  `n,m ~ 256-1024` that is `10^4-10^6` modular MACs → **sub-millisecond on a CPU**. Excellent
  (compare: re-executing an ML proof, or a ZK verification).

Difficulty knob: **β** (smaller β = exponentially harder), or dimensions `n,m`/`q`.

## 3. The design trap: difficulty, grinding, variance (the crux)

A hash PoW has a clean structure: every nonce is an independent Bernoulli(1/difficulty) trial, so
"expected work" maps linearly to a single target and miners trivially grind nonces. **SIS does not
have this by default**, and this is the #1 reason there is no live SIS-PoW coin.

Three concrete problems:

1. **No natural grinding.** With `A = H(header)` there is exactly one lattice per block. All miners
   would solve the *same* lattice (wasteful, not a lottery), and there is no nonce to vary.
   Fix: make the *target* depend on a nonce — solve **ISIS** `A·x = b`, `b = H(header, nonce)` — so
   each nonce is a fresh instance. But now the miner must solve an instance *per nonce*, which is far
   more expensive than a hash per nonce.
2. **Variance / heavy tails.** A sieve returns the shortest vector it can find; whether `‖x‖ ≤ β` is a
   geometric event with high variance. Difficulty adjustment via β is not proportional to work the
   way a hash target is; reward-per-work becomes lumpy and hard to calibrate across a network.
3. **Asymmetric shortcuts.** Unlike hash brute force (one strategy, linearly more hashes = linearly
   more work), SIS has *algorithmic* speedups (better sieves, big-memory trade-offs, preprocessing of
   `A`). A miner with more memory or a new sieve can get a super-linear edge — dangerous for a
   permissionless network. Difficulty must be defined so that the throughput/latency trade-off does
   not create big unfair advantages.

**Practical resolution used by birthday-style PoWs (Equihash/Wagner):** reformulate as *find a set of
vectors with a sum constraint* (generalized-birthday), which restores nonce grinding and a clean
difficulty. A "lattice-flavored Equihash" (Wagner on lattice vectors with a norm/syndrome constraint)
is the pragmatic design most likely to work; the pure "solve SIS, verify norm" version needs a new
difficulty theory.

## 4. GPU mining algorithm

Two families, both parallel and memory-heavy:

- **Lattice sieving (BDGL/heuristic).** Build a short basis of `L = {x : A x = 0 mod q}` (dim m,
  det `q^n`), generate a huge list of lattice vectors, iteratively reduce close pairs. Complexity
  `~2^{0.29 m}`; **bottleneck is memory + random access** (nearest-neighbor / bucketing), which suits
  GPUs' large HBM. Reference CPU implementation: **G6K** (lattice sieving library). GPU sieving for
  SVP has been demonstrated in the literature (FPGA/GPU sieves), but there is **no production GPU
  SIS-PoW miner** — you would write it.
- **Generalized-birthday (Wagner).** For the Equihash-style formulation: generate lists, collide on
  partial syndromes, combine in k rounds. Equihash proved this is GPU- and memory-hard-friendly;
  a lattice version replaces XOR with `Z_q`/syndrome+norm constraints.

For a *mineable* instance the dimension must be small enough that a GPU sieve finishes in seconds
(see §5), i.e. deliberately scaled-down SIS — legitimate for PoW (difficulty is adjustable), but the
calibration is the research.

## 5. Parameter sketch (illustrative, must be tuned)

Goal: a GPU sieve returns a vector below β in ~seconds, and a CPU verifies in <1 ms.

- `q` prime ~ 2^16…2^32 (keep modmul cheap; use small limbs for verifiability).
- `n` ~ 64…256, `m` ~ 1.3–2·`n` (need solutions to exist: `m > n·log q` region).
- Gaussian-heuristic shortest norm `ρ ≈ q^{n/m}·√(m/2πe)`; set the **target** `β = c·ρ` with `c<1`
  (e.g. 0.8–0.95) so solutions below β are rare and the sieve must work to find them.
- Dimension `m ~ 40–80` keeps sieving `2^{0.29·m} ≈ 2^{12}–2^{23}` operations → GPU-seconds.
  (Real cryptographic SIS uses m in the hundreds-thousands — those are **not mineable**; PoW lives
  in the small-m regime and re-derives its security from the *PoW difficulty*, not from full SIS
  hardness.)
- Retarget β per epoch like Bitcoin; cap β changes for stability.

This is the part needing a cryptographer: prove that (a) solutions exist at the target rate, (b) the
cheapest known algorithm is monotone in the difficulty knob, (c) memory/parallelism do not create a
> `k`-factor edge.

## 6. Verification & consensus

- Verifier (every node): `A·x mod q == 0` and `‖x‖ ≤ β`. One mat-vec. Trivially cheap; no ZK needed.
- Header binds `A`; solution `x` (small, `m·log β` bits) goes in the block. Block size fine.
- Node: fork Bitcoin Core/btcd; replace `CheckProofOfWork`; WTEMA-style retarget on β.
- Pool: stratum-like, but the "share" is a short vector below a per-share β. Need to define share
  difficulty carefully (see §3 variance).

## 7. ASIC resistance

- Sieving is **memory-bandwidth and random-access bound**, not a tiny arithmetic core — much harder to
  ASIC than Keccak/SHA. Good.
- But large-memory ASICs / HBM-attached accelerators could win if profitable. Mitigation: make the
  working set huge (memory-hard), and keep the algorithm research-active (so any ASIC is obsolete
  fast). Net: **moderately ASIC-resistant, not ASIC-proof.**

## 8. Why it does not exist yet

- The §3 design problem (difficulty/grinding/variance) is genuinely unsolved in the literature for a
  *pure SIS* PoW; Equihash sidesteps it with a birthday structure but is not SIS-hard.
- No off-the-shelf GPU sieve for this shape; G6K is CPU and SVP-oriented.
- Small-m instances are "toys" cryptographically — a reviewer or exchange may not like that the
  security is entirely in the difficulty parameter, not in a standard hardness assumption.
- Opportunity: exactly because no one has shipped it, the niche is open.

## 9. Build plan & effort

**Team:** 1 lattice cryptographer (design/parameters), 1–2 CUDA engineers (sieve kernels), 1
consensus/node engineer, part-time security reviewer.

**Milestones.**
1. **Offline spec + simulation** (CPU/NumPy, G6K for baselines): fix (n,m,q,β), measure solve-time
   distribution, build the difficulty model. ~1–2 PM. *Gate: expected work is monotone and low-variance.*
2. **Reference verifier + node PoW** (fork btcd, replace PoW). ~1 PM.
3. **GPU sieve miner** (bucketing/nearest-neighbor on `Z_q`, memory plan for VRAM). ~2–4 PM. *Gate:
   beats Cuckoo/Equihash-style throughput on a 3090/2080 and is stable under retarget.*
4. **Pool + stratum + difficulty/share logic.** ~1–2 PM.
5. **Parameter hardening + security review** (grinding, preprocessing, memory trade-offs, 51%
   economics). ~2–3 PM.
6. **Testnet → mainnet** (fair launch, liquidity, listing). ~3–6 PM.

**Total to a credible testnet: ~6–12 PM** (as before), but realistically **~9 PM** after the design
gates; **mainnet ~2x**. **Difficulty: high, research-flavored** (the design gates in 1 and 3 are the
risk, not the coding).

## 10. Verdict

- Attractive: **post-quantum, memory-hard, ASIC-resistant, cheap verification, no live competitor.**
- Real risk is **not** "can a GPU sieve SIS" (yes) but **"can we define a nonce-grindable, low-variance,
  monotone difficulty on SIS"**. The pragmatic path is a **lattice-flavored generalized-birthday
  (Equihash-like) construction**, not pure SIS.
- If the design gates pass, this is the most launch-ready "new-algorithm" GPU coin of the four.

### References to start from
- Ajtai, *Generating hard instances of lattice problems* (SIS), 1996.
- Laarhoven–Mosca–van de Pol / BDGL'16 — sieving complexity and methods.
- **G6K** — lattice sieving library (CPU baseline).
- Biryukov–Khovratovich, *Equihash* — the birthday PoW blueprint to adapt.
- Literature on GPU/FPGA sieving for SVP (baseline for the kernel you must write).
