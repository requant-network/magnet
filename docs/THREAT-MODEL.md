# Laboratory trust boundaries

Assets: verifier correctness, reproducibility, and local CPU/RAM. There are no
wallet keys, user balances or real funds in this laboratory.

| Boundary | Threat | Current control |
|---|---|---|
| Bytes → verifier | Truncation, extra bytes, overflow, huge dimensions | Early bounds, exact length and bounded integer arithmetic |
| Coordinates → arithmetic | Zero vector, sign duplication, excessive norm | Canonical sign; norm before dot products |
| Seed → expansion | Unbounded rejection sampling | Fixed word budget; explicit failure |
| Parameters → enumeration | Combinatorial explosion | Search-space cap before iteration |
| Stream → CLI | Oversized frame or incomplete input | Frame cap; process deadline supplied by caller |
| Verifier → verifier | Shared implementation error | Different implementations, manual and exhaustive checks |
| Known solutions → reuse probe | Excessive derivation work | At most two seeds, bounded coefficients and candidate budgets |

Caller-controlled A makes this format unsuitable for network PoW. A future
header-to-instance binding is a separate security boundary with separate tests.

One frame is bounded, but the CLI accepts arbitrarily many frames. It is not a
network DoS defense. Python APIs assume ordinary local objects, not hostile
classes with overloaded behavior. Untrusted bytes use bounded decoding.

Reports must distinguish valid solutions from independent work and state when
initial solutions were supplied by an exhaustive oracle. Derived proof counts
are not end-to-end speedups. Sparse screening can have false negatives.

These controls do not establish SIS hardness, secure PoW work accounting, ASIC
resistance or quantum security. Independent cryptographic review remains necessary.
