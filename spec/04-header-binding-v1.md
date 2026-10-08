# Research header binding v1

This is a local laboratory format, **not a block consensus or PoW specification**.
It tests independent generation and prevents the proof interface from accepting
a supplied matrix. It does not establish work cost, hardness, liveness, timestamp
rules, signatures, a valid parent chain, payload validity or difficulty.

## Canonical header: MGH1

All integers are unsigned little endian; byte strings have exactly the stated
length. No optional fields or trailing bytes. Total header length: **140 bytes**.

| Offset | Bytes | Field |
|---|---:|---|
| 0 | 4 | ASCII MGH1 (format version) |
| 4 | 32 | network identifier |
| 36 | 32 | parent commitment |
| 68 | 32 | payload commitment |
| 100 | 8 | height |
| 108 | 8 | timestamp (opaque lab value) |
| 116 | 8 | nonce |
| 124 | 4 | q |
| 128 | 2 | n |
| 130 | 2 | m |
| 132 | 8 | B2 |

Profile validation is exactly [SIS-LAB-v1](01-sis-lab-v1.md).
The seed is the first 32 bytes of SHAKE256 over
`b"MagnetNetwork/SIS-LAB/header-seed/v1\0" || canonical_header`.
Use that seed and the header profile with the **unchanged** SIS-LAB matrix
expansion and rejection budget. Sampling exhaustion means rejection, not a new
seed or weaker bound. B2 is part of both domains' inputs.

Both Python (hashlib) and Rust independently implement these bytes and matrix
generation. The byte-oriented Rust SHAKE256 follows
[FIPS 202](https://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.202.pdf);
the empty-message prefix is checked against the
[NIST example](https://csrc.nist.gov/csrc/media/projects/cryptographic-standards-and-guidelines/documents/examples/shake256_msg0.pdf).
Differential tests include absorb/squeeze rate boundaries. This does not imply
CAVP validation or a cryptographic audit. Non-byte-aligned messages are unsupported.

## Proof and trusted expected context

A proof is `canonical_header || m signed i32 little-endian coordinates`.
Its exact length is `140 + 4*m`, at most **652 bytes**. There is no supplied
matrix, seed, target, auxiliary certificate or alternative encoding.

The verifier requires a **separately supplied trusted context**: network (32),
parent (32), height (u64) and profile (`<IHHQ`, 16), total **88 bytes**.
These must match the header before deriving the instance. This prevents the proof
from selecting a different easy profile or irrelevant parent. Constructing context
from the same untrusted proof defeats that protection; caller policy is a real
trust boundary. The local CLI accepts context from its controlling test harness.
It is not a policy authentication protocol or a remotely deployable service.

After checking framing, profile, context, vector norm and canonical sign, derive A
internally and require `A*x = 0 (mod q)` using the original verifier. Early rejects
avoid matrix generation. A seed or matrix never supplied by the proof author.
Payload and timestamp are committed as bytes, but their meaning is not validated.

Changing nonce or payload changes the seed, but this is not a theorem that the
resulting matrices differ or that every old vector becomes invalid. Small matrices
can collide and a vector can satisfy multiple matrices. Nonce/payload grinding,
timestamp grinding, cheap availability screening, preprocessing and same-instance solution reuse
remain adversarial strategies to measure. All observed costs are lab evidence,
not consensus weights. No score threshold is attached to this proof format.

## Bounded local adapter: sis-lab

Input and output frames each have a u32 little-endian length followed by bytes.
Empty stream succeeds; malformed requests/framing exit nonzero with diagnostics
on stderr. No network listener or files. Per-request input at most **2057 bytes**;
per-response output at most **67584 bytes**. Bounds are per request, not aggregate
process CPU/RSS limits. Run only controlled local tests with a process timeout.

Each request starts with ASCII MGL1 followed by a one-byte mode:

| Mode | Following request bytes | Response bytes |
|---:|---|---|
| 0 | u32 output length, then input (0..2048 bytes) | SHAKE256 prefix (0..67584 bytes) |
| 1 | profile (16), seed (32) | row-major matrix entries (u32) |
| 2 | MGH1 header (140) | seed (32), then row-major matrix entries (u32) |
| 3 | trusted context (88), then proof | one byte: 0 reject, 1 accept |

Modes 1/2 must have the exact specified length and a valid profile. Mode 3 requires
valid context; malformed proofs return 0. Unknown modes, invalid contexts, truncated
lengths/frames and oversized requests/output lengths are fatal. A zero-byte frame
is an invalid request. Mode 0's zero-length output is a valid zero-byte response.
