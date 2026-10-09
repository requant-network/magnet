# Native and fused unit-sparse search experiment

Research only. This extends spec/18 without changing candidate validity,
consensus, chainwork or the bounded candidate domain. It is not general SIS
mining, a security reduction, or a memory-hardness claim.

## Native transport

`sis-column` accepts a stream of little-endian u32-length frames. Each CPS1
payload is `<4sIHHQIII`: magic, q, n, m, B2, candidate limit, proof limit,
chunk width; followed by exactly n*m canonical u32 matrix residues, row-major.
Caps are respectively 16384, 256, 4096 (all positive). Profile bounds are
those of SIS1. A request is at most 32800 bytes. Empty stream exits cleanly;
malformed/truncated frames or packets exit unsuccessfully, without recovery.

Each framed CSR1 response is `<4sBBBBHHII5Q`: magic, reason (1 proof cap,
2 truncating candidate cap, 3 exhausted), exhausted flag, complete proofset
flag, zero byte, m, zero u16, returned count, domain, engine nanoseconds,
checked count, chunks, accepted count, actual row checks; then returned
vectors as signed i32. Response size is at most 60+256*128*4 bytes.
The caller rejects inconsistent flags, counters, vectors, or extra bytes.

Singletons precede pairs; pairs use nested i<j, +1 then -1. B2=1 excludes
pairs. CPU transposes once and rejects at the first nonzero residual. A whole
chunk is charged before checking proof cap, including accepted discarded tail.
Proof-cap reason has precedence; exactly reaching the domain is exhaustion,
not a truncating candidate cap. Only emitted proofs materialize full vectors.

Native engine time includes parsing, validation, transpose and search, but
excludes response serialization and pipe I/O. Bulk process time includes
startup, request/response transport and decoding. These scopes are separate.

## CUDA ABI v1

`cuda/unit_sparse.cu` is an explicitly compiled local research library.
Python validates profile, matrix and caps before loading/opening a session.
The C ABI checks scalar/span lengths and matrix residues before allocating.
Pointers and handles are trusted local FFI values, not an untrusted network
API: valid pointed spans and exclusive handle ownership are caller duties.
No exceptions cross the ABI; all CUDA failures propagate, with no fallback.

A session owns an int64 matrix (8*n*m bytes) and a byte mask of chunk width.
One thread per ordinal decodes support with integer triangular subtraction
and checks exact modular column sums. One mask copy pays count bytes per
chunk. Returned vectors alone are reconstructed on the host. Owned device
storage is 8*n*m+chunk bytes, excluding driver/context/allocator overhead.
Logical scheduled column reads are an upper bound because of early rejection.

An additional audit kernel exposes support triples, outside paid search
timings. Every support in each audited domain must match an independent host
iterator, including chunk crossings, singleton boundaries and the last pair.
Session close frees resources on success and failure. Calls are serial.

## Evidence and measurements

Compare all four column backends on the spec/18 schedule (50 cases), three
repetitions, identical inputs/caps, rotating order. Preserve seeds and matrices
in local raw evidence; publish compact totals, stop reasons and fingerprints.
Audit every returned vector using the independent native verifier. Compare
ordered proofsets, all common work counters and stop flags, not just timings.
Record native engine and bulk time separately; CUDA per-search time includes
session allocation, matrix transfer, mask reads, host decoding and cleanup.
Library/CUDA cold initialization and compilation are reported separately.
Do not label different timing scopes as a fair CPU/GPU speedup.

Freeze source hashes (including .cu), verifier/search/library binaries and
compiler command/version. The build driver passes its original pre-build
manifest and post-build binary hashes to the survey; the survey must not replace
this baseline with a fresh source snapshot at the process-launch boundary.
Invalidate stale evidence before starting. Reject
publication if any frozen source or binary changes. Local tests and hardware
audits are required; no cloud GPU or CI consumption is necessary.
