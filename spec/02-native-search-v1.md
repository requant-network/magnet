# Native search laboratory protocol v1

This is a local CPU experiment on caller-supplied SIS-LAB-v1 matrices, not a
network endpoint, consensus protocol or difficulty function. Acceptance is
unchanged: nonzero integer vector, first nonzero coordinate positive,
0 < squared norm <= B2, and A*x = 0 modulo prime q. Instances use the bounds
in [SIS-LAB-v1](01-sis-lab-v1.md). The independent verifiers are unchanged.

## Search algorithms

`ball` traverses sign-canonical integer vectors inside the norm ball using
remaining squared norm and incremental residues. A prefix visit is one assigned
coordinate; each visit updates n residues. Maximum recursion depth is m <= 128.
Each nonleaf frame saves a fixed 64-u32 residue array on the stack. There are no
per-prefix heap allocations. The matrix and output vectors are retained.

`mitm` splits at floor(m/2), enumerates signed half boxes, filters half norms
and negative left halves, and retains **all** entries in each syndrome group.
The native table is a vector sorted lexicographically by syndrome, with binary
search for matching groups. Python uses a dictionary. This is an exact native
baseline of the same decomposition, not a claim of identical data structures or
optimal lookup performance. Table construction and sorting are part of search.
Joined vectors must pass total norm and canonical-sign checks.

Output is unique within a run. Ball traversal matches Python; MITM collision
order need not match Python. Compare full sets. Capped outputs are valid partial
sets and cannot prove nonexistence. Repetition redoes the search on the same
already decoded matrix; it does not generate independent mining trials.

## Wire format

All integers are little endian. stdin/stdout contain u32 length-prefixed frames.
Request payload cap is 33336 bytes (36 + SIS1 maximum 33300), checked before
allocation. Truncation or an invalid complete request exits nonzero with stderr
diagnostics; stdout contains only completed binary responses. EOF between frames
is success. The caller supplies a process deadline; an arbitrary stream of
frames is not globally bounded and this CLI is not a network DoS defense.

Request header (36 bytes), followed by one exact SIS1 packet whose vector bytes
must all be zero; a known solution cannot be supplied to the solver:

| Offset | Type | Field |
|---|---|---|
| 0 | 4 bytes | NAT1 |
| 4 | u8 | algorithm: 1 ball, 2 legacy mitm, 3 budgeted mitm |
| 5 | 3 bytes | zero reserved |
| 8 | u64 | node cap, 1..50000000; prefixes for1, aggregate proposals/pairs for3, unused for2 |
| 16 | u32 | table-entry cap, 1..1000000 |
| 20 | u64 | join-pair cap, 1..10000000 |
| 28 | u32 | retained-proof cap, 1..100000 |
| 32 | u32 | repetitions, 1..9 |

All limit fields must be valid even if irrelevant to the selected algorithm.
MITM preflight rejects half boxes larger than 1000000 proposals per half.
Table capacity is a count, not a byte ceiling. A cap stops before exceeding
the corresponding counted operation; detecting proof overflow can perform
additional search after emitting the last permitted proof. Stops are:
0 domain-exhausted, 1 node-limit, 2 table-limit, 3 pair-limit, 4 proof-limit,
5 half-box-limit. Ball uses node/proof caps; MITM uses half-box/table/pair/proof
caps. These are structural bounds, not wall-clock or memory enforcement.

Additive mode3 preserves the same MITM decomposition/output ordering, and also
charges a shared node cap before every left/right proposal and join pair.
Its nodes counter is exactly left+right+pairs. Mode2 retains its historical
nodes=0 semantics and separate caps. Portfolio campaigns use mode3; see
[the paid portfolio specification](10-pool-portfolio-v1.md).

Response header (108 bytes):

| Offset | Type | Field |
|---|---|---|
| 0 | 4 bytes | NSR1 |
| 4 | u8 | stop code |
| 5 | 3 bytes | zero reserved |
| 8 | u16 | vector width m |
| 10 | 2 bytes | zero reserved |
| 12 | u32 | proof count |
| 16 | u32 | repetitions |
| 20 | u64 | charged Vec payload capacities in bytes |
| 28 | 10 u64 | nodes, left, right, norm terms, matrix terms, row reductions, leaves, table entries, pairs, proofs |

Then `repetitions` u64 solver durations in nanoseconds and `count*m` signed i32
coordinates. Maximum response payload: 51200180 bytes. Counts and exact length
must agree. Repeats must reproduce stop, work and ordered proof transcript;
otherwise the native adapter fails. The Python client checks bounds and framing;
experiment/check harnesses independently verify returned proofs.

## Measurement boundary

Native time starts after decoding and ends after returning the solver report.
It includes solver initialization, preprocessing, sorting, enumeration, output
retention and capacity accounting. It excludes SHAKE expansion, validation of
the decoded instance, IPC, serialization, scoring and proof verification.
Subsequent repetitions retain the previous report in the adapter until the next
finishes. This may affect cache/allocator state and whole-process memory.

`owned_capacity_bytes` is the maximum charged live **Vec payload capacity** at
build/search phases: decoded matrix, solver buffers, table and children, proof
list and proof vectors. This monotone estimate is exact for these charged
payloads, not a measured allocator peak. It excludes allocation rounding,
reallocation overlap, stack (including recursive snapshots), sorting scratch,
the request/response buffers, previous reports, caller state, executable and OS.
Do not compare it directly to Python tracemalloc peaks or RSS, or call it a
hard memory budget. The known ball snapshot-array allowance is at most
256*m bytes; it is not an upper bound on the entire call stack.

The laboratory does not calibrate SIS hardness, independent work per proof,
memory hardness, mining profitability or network chainwork.
