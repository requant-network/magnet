# SIS as a standalone proof-of-work function: a negative result for the tested constructions

Magnet Network SIS-PoW laboratory. Date: 2026-10-10. Status: **closing note of the programme**
(see [ADR 0020](decisions/0020-close-sis-pow-programme.md)). English is authoritative; a Russian
summary is in [docs/ru/NEGATIVE-RESULT.md](ru/NEGATIVE-RESULT.md).

## Abstract

We asked whether the Short Integer Solution problem (find nonzero `x` with `A·x = 0 mod q` and
`||x||² <= B2`, `A` derived from a block header) admits a deterministic, monotone, portable and
reuse-resistant work function for permissionless proof of work. We built two independent exact
verifiers, several bounded solvers (exhaustive, meet-in-the-middle, ball enumeration, exact LLL,
pinned FLINT LLL/BKZ, sphere enumeration), a CUDA checker, a toy linear chain, and precommitted
falsification experiments with complete cost accounting. No acceptable work function was found.
For the three constructions we defined, we obtained either concrete counterexamples or an
attack that removes the claimed cost. We also give a structural argument that pricing per-trial
work through a header-bound outer score must fail in one of two ways. If the score depends on the
SIS proof, one solved instance supplies many cheap trials. If it does not, the SIS step can be
skipped for losing headers. We stop the programme here. This is a negative result for the tested
constructions and the stated argument, not an impossibility theorem for all lattice-based PoW.

## 1. Question and requirements

A permissionless PoW work function must give:

1. **Cheap, deterministic verification** of a block's proof against consensus-derived inputs.
2. **A difficulty knob** with a weight that is **monotone in adversarial cost**: raising difficulty
   must raise the expected computation or energy of the cheapest miner, not only a nominal credit.
3. **Portability**: no device class gains superlinearly from an unpriced resource.
4. **Reuse resistance**: work done for one header, parent or chain must not transfer cheaply to
   another, and one paid computation must not yield many independently credited results.

SIS easily satisfies (1): verification is one `n×m` matrix-vector product mod `q` and a norm
check. The laboratory existed to test (2)–(4).

## 2. Constructions examined

The trusted context `c = (network, parent, height, profile)` is fixed by consensus. The miner may
vary only the nonce. The MGH1 header commits the nonce into the matrix seed, so a new nonce gives
a new matrix `A(header)`.

- **A (pure SIS with a norm threshold).** Accept a canonical nonzero `x` with `A(header)·x = 0 mod q`
  and `||x||² <= B2`. Candidate credits: `A-unit` (one per accepted header) and `A-density`
  (`q^n / N(m,B2)`, with `N` the number of canonical integer vectors in the norm ball).
- **B (SIS plus an outer score bound to the proof).** A, and also
  `SHA256(D || header || proof) < T`. Credit `B-score = 2^256/T`.
- **B-H (SIS plus an outer score bound to the header only).** A, and also
  `SHA256(D_H || header) < T`. Proposed credit `K_SIS · 2^256/T`, where `K_SIS` is the claimed
  fixed cost of solving SIS for one header.
- **C (generalized birthday with lattice constraints, Equihash-like)** was listed but not pursued.
  It does not inherit SIS hardness and needs its own argument; nothing below applies to it.

## 3. Evidence from the laboratory

All profiles are toy-sized (`q <= 257`, `n <= 4`, `m <= 16`). Every experiment below was
precommitted (protocol and source committed before execution), charges all generated, rejected
and failed work, and is reconciled by an independent Rust implementation. Compact evidence is in
`docs/research/results/`; full details are on the [findings page](FINDINGS.md).

| Experiment | Result | What it shows |
| --- | --- | --- |
| Reuse probes ([reuse](research/solution-reuse-v1.md), [grinding](research/practical-lll-and-grinding-v1.md), [supply](research/precommitted-pool-supply-v1.md)) | Sign, multiples, linear combinations and repeated score trials give extra legal results without a fresh solve | "One accepted vector or score attempt = one SIS solve" is false. `A-unit` and naive vector counts do not price work. |
| D2 nominal credits ([critical path §8](CRITICAL-PATH.md)) | `A-density` and `B-score` are monotone in their knobs only algebraically | Neither prices the cost of acquiring an input. Monotone credit does not imply monotone adversarial cost. |
| D3 screening, original 288 runs (`d3-screening-v1.json`) | 2.75× signal for A on `(17,3,16,12)`, below the precommitted success floor | No kill criterion fired. |
| D3 replication, 576 campaigns on 24 fresh streams (`d3-screening-replication-v1.json`) | Screened/plain 0.959× (A), 0.769× (B) | The 2.75× signal did not replicate. This is no evidence of safety: profiles are toy-sized and the search family is narrow. |
| D4 exact complete-kernel transfer (`d4-kernel-transfer-v1.json`) | Exact law `q^[-n(m-r)]`, checked exhaustively on 6,642 pairs; union bound ≈3.5·10⁻¹² at `(17,2,8,8)`; 0 primary hits | Only exact full-kernel collisions are negligible, and only if matrices are fresh and uniform. Partial reuse was not tested. |
| B-H public gate (`d4-header-gate-v1.json`) | 16 batches; the same 8 admitted outputs from 8 SIS preparations instead of 40 | **Negative result:** the header-only score lets a miner reject headers before any SIS work. The SIS cost does not grow with `1/T`. |
| D5 matched CPU/CUDA pilot ([matched coefficients](research/matched-coefficients-v1.md)) | CPU lower elapsed time in 716/720 pairs | No GPU advantage for this family. Energy and memory were not measured. |

At closure the local gate passes (364 Python tests, 23 Rust tests, all differential corpora;
re-run on 2026-10-10 at `f75ae73`).

## 4. Structural argument: the outer-score dilemma

The construction A has no hash-like lottery. Each nonce yields a new structured instance whose
solving cost depends on the instance and the algorithm, not on independent Bernoulli trials.
The difficulty knob (`B2` or the dimensions) is coarse, and the cost it implies is neither
verifiable nor monotone pathwise. The standard way to obtain a lottery is an outer hash target,
which gives B or B-H. Let `S(h)` be the eligible proofs for header `h` and `g` the outer score.

1. **If `g` depends only on `h` (B-H),** the miner evaluates `g(h)` first and solves SIS only when
   `g(h) < T`. Under the conditional renewal model of [critical path §11](CRITICAL-PATH.md)
   (gate cost `G`, attempt cost `C`, success probability `s`, gate probability `p = T/2^256`),
   solve-all costs `(G+C)/(p·s)` per block, while gate-first costs `G/(p·s) + C/s`. The SIS term
   no longer depends on `p`. The work becomes hash PoW with SIS as a fixed admission filter. The
   laboratory measured this bypass directly (Section 3).
2. **If `g` depends on `(h, x)` (B),** every distinct eligible `x` is a fresh score trial. The
   credit `2^256/T` then prices SIS work only if each further eligible vector costs about as much
   as the first. Lattice algorithms violate this in at least three ways:
   - Legal transformations and combinations of found vectors give further candidates almost for
     free. The laboratory measured this (Section 3).
   - Enumeration visits many lattice points per tree traversal.
   - A heuristic 2-sieve in dimension `d` ends with a database of about `(4/3)^(d/2) = 2^(0.2075·d)`
     lattice vectors of norm up to about `sqrt(4/3)` times the Gaussian heuristic [NV08, BDGL16,
     Duc18, ADH+19]. Whenever `B2` is loose enough to admit these vectors, one sieve run supplies
     exponentially many score trials.

   If `B2` is instead tightened toward `λ1²`, few vectors qualify and the problem approaches exact
   SVP. That brings back the coarse, non-lottery cost structure of A.

Requiring a unique canonical solution per instance would close case 2. SIS lacks such a solution
by construction, and defining one (for example "the shortest vector") makes verification as hard
as solving. Variants that keep the matrix fixed and vary the target (ISIS with
`b = H(header, nonce)`) fall into the preprocessing trap instead. The lattice is reduced once,
and then many close-vector targets are solved cheaply [Laa16]. MGH1 avoids this only by putting
the nonce into the matrix, which brings back case 1 or 2.

Case 2 is stated from the literature, not measured here at relevant dimensions. It is the main
reason we stop rather than run the remaining partial-basis D4 experiment. The expected outcome
(cheap marginal eligible vectors from sieving) is the documented behaviour of these algorithms.

## 5. Limits: what this note does not show

- **No general impossibility.** Other norms, other lattice problems, interactive or
  proof-of-sequential-work designs, and construction C are untouched.
- **Toy scale.** No experiment ran at dimensions where BKZ or sieving preprocessing dominates.
  The empirical rows of Section 3 neither support nor refute A at real parameters. Section 4
  carries the conclusion.
- **Conditional models.** The D4 law and the B-H renewal algebra assume fresh, uniform and
  independent matrices or scores. We did not prove that the SHAKE-based generator satisfies this.
- **No external review yet.** The plan required one independent cryptographic review. This note
  is the document to review. The closure does not depend on it, but a substantive error found by
  review is a reason to reopen (Section 7).
- **No hardware or energy claim.** D5 is a pilot on one small search family.

## 6. Conclusion

No deterministic, monotone, portable and reuse-resistant SIS work weight was established. Naive
vector and score counts have concrete counterexamples. The proof-independent repair (B-H) turns
SIS into a skippable filter. The proof-bound score (B) is undermined by the cheap supply of
eligible vectors that lattice algorithms produce. Pure SIS (A) has no verifiable monotone cost
and no lottery. The programme is **closed** with this negative result.

The working approach for GPU-friendly PoW is a work function whose cost lies in **each hash trial
itself**, with no algebraic structure to amortise. One example is TNet in the Requant project:
nonlinear requantized int8 layers, where each ticket costs a forward pass and is verified from one
row piece. Requant documents it as an experimental work function without security claims; we cite
it as a design contrast, not as a proven solution.

## 7. What remains, and when to reopen

Reusable artefacts:
- the exact Python and Rust SIS verifiers;
- the SHAKE256 matrix expansion and MGH1/MGB1 encodings;
- the bounded solver suite;
- the exact finite-field transfer law;
- the precommitted-experiment and evidence-binding machinery.

They stay in the repository unchanged. No GPU, miner, chain or monetary work will be started from
this programme.

Reopen only if one of these holds:
- an external review finds a substantive error in Section 4;
- a construction is proposed where the marginal cost of a further credited result is provably
  close to the first, and verification stays cheap and deterministic.

A new proposal must start as a new critical-path entry with its own falsifiers.

## References

- [Ajt96] M. Ajtai. Generating hard instances of lattice problems. STOC 1996.
- [MR07] D. Micciancio, O. Regev. Worst-case to average-case reductions based on Gaussian measures.
  SIAM J. Computing 37(1), 2007.
- [NV08] P. Q. Nguyen, T. Vidick. Sieve algorithms for the shortest vector problem are practical.
  J. Mathematical Cryptology 2(2), 2008.
- [BDGL16] A. Becker, L. Ducas, N. Gama, T. Laarhoven. New directions in nearest neighbor searching
  with applications to lattice sieving. SODA 2016.
- [Laa16] T. Laarhoven. Sieving for closest lattice vectors (with preprocessing). SAC 2016.
- [Duc18] L. Ducas. Shortest vector from lattice sieving: a few dimensions for free. EUROCRYPT 2018.
- [ADH+19] M. Albrecht, L. Ducas, G. Herold, E. Kirshanova, E. Postlethwaite, M. Stevens. The general
  sieve kernel and new records in lattice reduction. EUROCRYPT 2019.
- [BK16] A. Biryukov, D. Khovratovich. Equihash: asymmetric proof-of-work based on the generalized
  birthday problem. NDSS 2016.
