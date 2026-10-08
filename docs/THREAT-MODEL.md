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
| Policy → local search | Unbounded attempts or proof retention | Instance-space cap, proposal cap and explicit stop reason |
| MITM table → joins | Memory growth, lost collisions, excessive pair traversal | Half-box/entry/pair caps; collision lists; explicit partial-result status |
| Prefix → ball search | Combinatorial growth or retained recursive state | Prefix-node cap; noncyclic recursion; closed iterator lifecycle |
| Solver → budget harness | Stalled checks, overshoot, leaked global tracing | Cooperative checkpoints; explicit failure reason; unconditional trace cleanup |
| Bytes → native search | Invalid profiles, huge frames, supplied known proofs | Exact bounded decoding; zero placeholder; separate native protocol |
| Native enumeration → retained data | Excessive table/output or recursion | Half-box/entry/pair/proof/node caps; depth <= 128; explicit stop codes |
| Modular matrix → integer lattice | Incomplete kernel lifts or wrong rank | Full RREF lifts; q*pivot rows; independent membership/index audit |
| LLL → certificate | Lost lattice, numerical error or false reducedness | Exact fractions; unimodular U; independent Bareiss/Gram-LDL audit |
| Reduced basis → discovery claim | Empty heuristic mistaken for nonexistence | Separate finite-probe status; exhaustive comparison; frozen missed-solution fixture |
| Header → instance | Supplied easy A or unbound fields | Canonical MGH1; independent seed/matrix generation; vector-only proof |
| Proof → expected policy | Miner selects easy profile or irrelevant parent | Separate trusted network/parent/height/profile context; match before generation |
| XOF → stream | Padding/domain/byte-order mistakes | NIST prefix; independent cross-language rate-boundary and maximum-length tests |

Caller-controlled A makes SIS1 unsuitable for network PoW. The separate MGH1
research proof binds its instance to header bytes with separate tests. It does
not validate payload semantics, timestamp rules, signatures, a chain, difficulty
or work cost. Trusted context must never be reconstructed from the same proof.

One frame is bounded, but the CLI accepts arbitrarily many frames. It is not a
network DoS defense. Python APIs assume ordinary local objects, not hostile
classes with overloaded behavior. Untrusted bytes use bounded decoding.

Reports must distinguish valid solutions from independent work and state when
initial solutions were supplied by an exhaustive oracle. Derived proof counts
are not end-to-end speedups. Sparse screening can have false negatives.

The strategy experiment generates its own matrices and binds profile, seed and
proof in a domain-separated score. It has no network header or monetary rules.
Component counters are not calibrated work; their acquisition subtotals exclude
unsolved instances, while all-instance totals retain unsuccessful search costs.

The MITM baseline preserves all vectors within a syndrome bucket. An entry cap
is not an exact byte budget; output retention also consumes memory. A capped or
interrupted search cannot certify nonexistence. Timing and selected traced
allocation peaks measure these local Python implementations, not intrinsic SIS
cost, process RSS or a network admission policy.

Budget ceilings apply to traced Python allocations and cooperative elapsed time.
Atomic work and cleanup can overshoot; these are not OS resource limits. Repeated
windows reuse public seed schedules, so their aggregate hits are not globally
distinct proofs. Scored vectors are verified inside the measured budget. Tracer
and clock overhead, Python allocation caches and unfinished work remain part of
the experimental cost; a native miner can behave differently.

These controls do not establish SIS hardness, secure PoW work accounting, ASIC
resistance or quantum security. Independent cryptographic review remains necessary.

Native capacity accounting charges selected Vec payload capacities, not allocator
peaks, stack or process memory; caps are operation counts, not byte enforcement.
Native search accepts supplied matrices only as a local experiment. Its public
library entry point obtains instances through bounded decoding. The CLI has no
network listeners and needs a caller-enforced deadline for untrusted streams.
Both native survey outputs become incomplete before a rerun; source hashes
and explicit cap statuses distinguish completed evidence from partial searches.

Lattice reduction bounds dimension, outer steps, size reductions and checked
integer/fraction growth. Arithmetic checks can overshoot transiently and do not
impose OS memory/time limits. A cap after a committed operation retains an
equivalent basis, not a reducedness claim. Discovery counts exclude incomplete
oracles; successful probes do not imply complete reduction or intrinsic work.

Header binding still permits nonce/payload/timestamp grinding. Different seeds
can produce equal toy matrices, and the same vector can satisfy different
matrices. Sampling exhaustion rejects; no weaker profile or substitute seed is
silently selected. Bound proofs check context, length and norm/sign before
generation. SHAKE/matrix adapters have per-frame bounds and require controlled
local processes with caller timeouts. The handwritten Rust SHAKE is not certified
or independently cryptographically audited. Header binding is not service proof.
