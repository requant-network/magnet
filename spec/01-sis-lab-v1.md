# SIS-LAB-v1: arithmetic laboratory specification

Status: implemented laboratory specification, 2026-10-08.
This is neither a block format nor a Magnet Network wire protocol.
English is authoritative; the [Russian snapshot](../docs/ru/spec/01-sis-lab-v1.md)
is secondary.

## 1. Parameters and acceptance

| Field | Laboratory range |
|---|---|
| q | Prime, 2 ≤ q ≤ 65521 |
| n | 1 ≤ n ≤ 64 |
| m | 1 ≤ m ≤ 128 |
| B2 | 1 ≤ B2 < q² |

These bounds control laboratory cost, not cryptographic strength. We do not
require n < m or full row rank: degenerate instances are useful attack fixtures.

A has n rows of m canonical integer residues, 0 ≤ a < q. The vector x has m
signed i32 coordinates. Accept exactly when the format is valid and:

~~~text
x is nonzero;
the first nonzero coordinate is positive;
sum(x[i]^2) <= B2;
for each row r: sum(A[r,i] * x[i]) mod q == 0.
~~~

All arithmetic is exact. The sign rule removes x/−x duplication. There is no gcd
or primitivity restriction: multiples and combinations are research subjects.
A matrix with a zero column may admit a trivial but valid solution. The verifier
must accept it; arithmetic validity is different from PoW security.

Invalid parameters are rejected before variable-length decoding. The norm is
checked before matrix multiplication. In Rust, each i32 square fits i64 and is
checked against the remaining u64 norm budget before addition. Accepted coordinates
have magnitude less than q, bounding subsequent modular operations.

## 2. Cross-language binary case

All multibyte values are little-endian; signed coordinates use two's complement.

| Offset | Bytes | Field |
|---|---|---|
| 0 | 4 | ASCII SIS1 |
| 4 | 4 | q, u32 |
| 8 | 2 | n, u16 |
| 10 | 2 | m, u16 |
| 12 | 8 | B2, u64 |
| 20 | 4·n·m | A, row-major u32 |
| 20+4·n·m | 4·m | x, i32 |

Length is exactly 20 + 4·n·m + 4·m, at most 33300 bytes. Reject trailing bytes,
truncation, unknown magic and noncanonical residues. Python bool is not an integer
field. Encoding permits structurally correct but mathematically invalid vectors
for negative fixtures.

Manual fixture:

~~~text
q=7 n=1 m=2 B2=5 A=[1,2] x=[2,-1]
5349533107000000010002000500000000000000010000000200000002000000ffffffff
~~~

## 3. Rust stdin/stdout adapter

Each input frame is a u32 length followed by that many case bytes. Each complete
bounded frame produces one byte: 0 for rejection or 1 for acceptance.

Empty stdin exits successfully. An empty frame produces 0. A truncated length,
truncated frame or length above 33300 exits with an error. Excessive length is
rejected before allocation. Invalid case contents in a complete frame produce 0
and do not prevent processing the next frame.

This is a local utility with no sockets, accounts or session deadline. The test
driver limits subprocess duration. A network adapter would require independent
quotas, concurrency limits and deadlines.

## 4. Python matrix expansion

Seed is exactly 32 public bytes, not a wallet secret. Validate the profile first.

~~~text
domain = ASCII("MagnetNetwork/SIS-LAB/matrix/v1") || 0x00
params = u32le(q) || u16le(n) || u16le(m) || u64le(B2)
stream = SHAKE256(domain || params || seed)
count = n*m
max_draws = 4*count + 1024
cutoff = 65536 - (65536 mod q)
~~~

Read at most max_draws little-endian u16 words. Reject w ≥ cutoff; otherwise emit
w mod q. The first n*m accepted values fill A row-major. Exhausting the budget
is an error: no fallback, seed substitution or unbounded additional sampling.
The maximum stream allocation is 67584 bytes. Python uses hashlib; Rust now
independently implements byte-oriented SHAKE256 and the same expansion.

Frozen fixture:

~~~text
q=7 n=2 m=3 B2=5, seed=32 zero bytes
A = [[1,0,6], [6,0,6]]
~~~

This records implementation behavior, not independent cryptographic certification.
Tests also check the empty-input SHAKE256 known answer, an independently
consumed stream at q=32771 with frequent rejection, and forced budget exhaustion.

Rust also independently expands SHAKE. Header-bound verification uses the separate
[MGH1 research format](04-header-binding-v1.md); SIS1 remains a supplied-A lab format.
Changing B2 in this generator changes the matrix. Threshold studies must explicitly
freeze a generation profile when comparing acceptance bounds on the SAME matrix.

## 5. Exhaustive oracle

For radius=floor(sqrt(B2)), enumerate [-radius,radius]^m after checking the box
contains at most 1 000 000 candidates. Apply norm, sign and modular equations.

A completed empty enumeration proves nonexistence only for that particular tiny
instance. Budget exhaustion is an error, not a proof of nonexistence.
An exact rational LLL baseline is implemented (spec/03); optimized LLL/BKZ and
GPU search are not implemented.

## 6. Verification boundary

python scripts/check.py runs Rust formatting/lints/tests, Python tests including
tiny exhaustive spaces, and 10000 seeded differential cases plus manual and
extreme cases. Separate checks exercise invalid framing and empty streams.

Constructed positive fixtures have identical first columns; they are deliberately
easy verification tests. A differential pass is not long-running fuzzing or a
security audit. No block binding, target, chainwork, reorg or service payment is
encoded here. See docs/STATUS.md for current test counts and experimental results.
