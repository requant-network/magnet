# Exact GPU verification laboratory v1

This optional research adapter screens supplied SIS1 cases, not MGH1 blocks or
mining search. It changes no consensus rule. The existing Python/Rust verifiers
remain independent references. CUDA must actually execute; CPU fallback is refused.

`verify_batch` accepts a plain list/tuple of 1–256 packets. Decode, prime-field
profile, canonical matrix residues, signed-int32 vector shape, first-nonzero
positive sign and the squared norm are checked on the host with exact Python
integers. Malformed/oversized individual packets yield false; an invalid batch
shape/count or aggregate byte budget raises ValueError. No raw unbounded
coordinate reaches the device.

Eligible cases are grouped by q/n/m, at most 32 per CUDA chunk. Transfer and
arithmetic use torch.int64. With q<=65521, m<=128, B2<q^2, admitted coordinates
have magnitude <=65520; absolute dot products are bounded by 128*65520^2,
below 2^63. Products and their sum are exact; floats and int32 accumulators
are forbidden. Norm admission uses host integers to avoid raw norm overflow.

The output preserves input order, including invalid cases. Matrix/vector
products, modular reduction and all-row predicates execute on CUDA, while
sign/norm/encoding rejection is on the host. All rejected inputs may require
no device arithmetic; evidence must include real eligible cases, both accepted
and modularly rejected. `.tolist()` synchronizes observed verdicts.

The adapter caps input bytes and conservative live logical tensor bytes at
64 MiB; this is not an external process/allocator ceiling. CUDA context/runtime
overhead and cached allocator reservations are additional. No memory-hardness
claim is made. CUDA unavailability, import or kernel failures propagate; the
driver marks evidence running-or-incomplete before executing.

The survey requires a separately built Rust SIS1 verifier, reconstructs the
same framed corpus independently, and refuses differing Python/Rust verdicts
before the GPU comparison. It records cases, seeds, corpus/input-source/binary
hashes, exact comparisons, device/toolchain metadata and measured memory. Source
files and binary hashes must stay unchanged until report publication. Evidence
does not claim paid candidate acquisition, hashrate or an isolated speedup.
