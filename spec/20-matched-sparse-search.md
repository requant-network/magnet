# Matched in-process CPU/GPU unit-sparse experiment

Research only. This adds a separately versioned local laboratory library and
does not change specs/17–19, consensus, scoring, chainwork or accepted profiles.
It compares integration scopes and a broader finite candidate family, not
production miners or general SIS completeness.

## Exact domain and limits

Select maximum weight 2 or 3. Effective weight is min(maximum weight, B2).
Coordinates are ±1, first nonzero coefficient positive. Enumerate positive
singletons, then lexicographic i<j with second sign +1,-1, then (if allowed)
lexicographic i<j<k with second sign +1,-1 outer and third sign +1,-1 inner.
Domain sizes are m, m², or m²+4*C(m,3). Profiles retain SIS1 bounds; q² is
calculated in widened unsigned arithmetic. Maximum domain is 1381888.

This experiment's caps are candidate 1..65536, proof 1..256, chunk 1..4096.
These do not loosen earlier APIs. Check and charge the entire chunk before
stopping for proof cap. Candidate cap truncates the final chunk; an exactly
sufficient cap is exhausted, with proof-cap reason taking precedence.

Report the checked interval [0,checked), domain/tested/accepted/emitted/discarded
counts separately by weight. Distinguish proof cap hit, unchecked domain suffix,
accepted discarded tail and truncating candidate cap. The prefix is biased:
at m=128, cap65536 samples only 49152 of 1365504 triples (3.60%), mostly i=0/1.
Repeated profiles/seeds/caps/repetitions are not independent challenges.
q=2 sign choices can share acceptance events. No representative supply-rate or
security conclusion follows from these censored domains.

## ABI v1 and owned sessions

Compile `cuda/matched_sparse.cu` locally. `sp_open` takes backend 0 CPU or 1 GPU,
canonical int64 matrix and explicit span length, n,m,q,B2,max-weight,chunk width.
Scalar/profile/span/residue checks precede allocations. Matrix input spans and
handles are trusted local pointers; valid spans, exclusive serial ownership and
one close are caller duties. No network handler or sandbox is introduced.

Both sessions own the same row-major host matrix copy. GPU additionally owns
device matrix and one byte mask/chunk. CPU starts each chunk with an ordinal
decode and advances a sequential support cursor. GPU independently unpacks
each ordinal per thread. Exact int64 sums, early row rejection and a byte flag
per candidate are used by both. `sp_batch` fills the caller's exact count-byte
mask; invalid parameters or CUDA launch/completion errors propagate. There is
no fallback. `sp_close` frees all resources on success and failure.

`sp_audit` separately emits six int32 values per support: three indices then
three coefficients. Inactive positions use the last active index and zero
coefficient. Audit work is outside paid search and does not provide solutions.
The Python wrapper validates before ctypes conversion/allocation and reconstructs
only returned vectors. Its validation/session/mask/decode/close code is identical
for CPU and GPU; independent proof verification is outside both timers.

## Measurement and evidence

Each invocation pays validation, host copy/session setup, all checked chunks,
mask delivery, output decoding and cleanup. GPU additionally pays allocation,
H2D and synchronous D2H. Library/compiler/first CPU and first GPU probes are
separately recorded. Initial probes use a fixed tiny fixture, complete the
kernel/readback/cleanup and explicitly synchronize before measured cases. All
measured GPU masks are synchronous; case-specific allocation, validation and
copies never move into warmup. Do not amortize setup through hidden session reuse.
Three repeated runs rotate CPU/GPU order per job. Report per-repeat group times
and paired ratios; changes of workload are not attributed to implementation
optimization. Shared-process scope is matched; hardware, parallelism and
different enumeration algorithms remain explicit variables. CPU is a scalar
C++ baseline, not the strongest conceivable CPU implementation.

Audit complete support order against Python itertools, full small-field masks,
maximum dimensions/modulus and chunk/family boundaries. Compare existing Rust
pair search where the domain is the same; independently Rust-verify every emitted
proof. Record acquisition, failed/censored attempts and preparation. Freeze the
original pre-build source manifest and compiler/library/native binary hashes
through survey handoff and publication. Invalidate stale raw/compact success
before builds. Standard local checks and the real-device survey must pass.

Any unexpected backend/audit/build failure invalidates paired timing publication.
Preserve stage, elapsed time and known completed chunks in failure diagnostics;
retain completed unpaired records only as incomplete evidence. A failed sample
is distinct from a valid capped search and is never a zero-time observation or
paired with a successful backend for a ratio.
