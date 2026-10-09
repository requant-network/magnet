# Unit-sparse CPU/CUDA acquisition laboratory v1

The search acquires its own canonical candidate vectors. It is a restricted
support<=2, coefficient +/-1 domain, not complete SIS search or block mining.
No consensus/admission, score kernel or work weight is changed.

For any existing Profile, enumerate positive singleton units in coordinate
order, then lexicographic supports i<j, with second coefficient +1 then -1.
When B2=1 only singletons are eligible. Otherwise domain size is m^2. All vectors
are distinct canonical integer inputs, but their modular acceptance events may
coincide (notably q=2). Proof count is not independent supply or calibrated work.

Python uses an independent itertools generator. CUDA generates ordinal ranges,
triangular support-prefix tables, support pairs and dense int64 vectors on the
device, then screens against one transferred matrix with exact int64 products,
sum and modular reduction. No CPU-found proofs/candidate arrays feed CUDA.
Each candidate has norm 1 or 2 and first nonzero coordinate positive. Host
Profile/matrix validation and batch/candidate/proof caps precede device allocation.

Caps: 1–16384 candidates, 1–256 proofs, 1–256 batch width. Batches never exceed
the remaining candidate cap. A processed chunk is fully generated, screened and
charged, including the tail after the proof cap. The returned vectors are the
first remaining capacity in ordinal order. accepted_seen counts all valid
vectors in checked chunks, including any discarded tail.

Stop precedence: proof-limit, then a truncating candidate-limit, then domain-exhausted.
A candidate limit exactly sufficient for the domain does not truncate it and
reports domain-exhausted unless the proof limit also fires.
domain_exhausted separately means every domain candidate was checked;
all_proofs_returned additionally means none of the checked valid vectors was
discarded. Exhaustion is only over this restricted domain and never proves
the absence of other short SIS solutions.

Ledger: generated/screened candidates, materialized vector entries, scheduled
dense matrix-grid slots, setup matrix entries, batches, valid candidates seen,
returned proofs, device support-prefix entries and explicit tensor H2D/D2H
payload bytes. Matrix-grid slots
are a schedule metric; Python can short-circuit row checks and is not charged
as if every multiplication executed. Transfer payload excludes implicit CUDA
runtime/command/allocator/shape metadata. The current kernel returns the first
ordinal and accepted count scalars to the host, plus emitted vector tensors.

The 64 MiB conservative logical tensor allowance is not an external allocator
ceiling; context, cache and runtime overhead are additional. Runtime failures
propagate and CUDA refuses CPU fallback. Search elapsed scope includes host
validation, optional runtime import/setup, candidate generation, screening,
explicit transfers and synchronized output. Seeded matrix generation is host
work measured separately, not an uncharged claim of end-to-end mining speed.

Evidence compares CPU/CUDA deterministic outputs and common ledgers under the
same chunk/caps, and independently verifies every returned vector with Rust.
Full-domain tiny cases also compare complete accepted sets. Preserve seeds,
configuration, source/native fingerprints, bounded failures and raw records.
Failed runs invalidate evidence. Timing is descriptive and not optimized-CPU
competition, energy calibration, hardness or an isolated GPU advantage.
