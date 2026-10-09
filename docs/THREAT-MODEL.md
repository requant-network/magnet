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
| Optional native LLL → certificate | Inexact arithmetic or lost lattice | Unchanged independent exact audit of B,U,index and reducedness for every repeat |
| Local worker → experiment | Wrong dependency, hang, oversized input/output | Explicit isolated version/hash pin; bounded JSON; process timeout; incomplete report on failure |
| Header selection → score | Free acquisition, oracle lookahead or incomplete commitment | Paid policies; separate oracle audit; hash entire proof; trusted external target/context |
| Kernel sphere → completeness | Rounded boundaries, lost vectors, capped tree mistaken for empty | Exact rational intervals; full-kernel audit; independent complete-set comparisons; explicit caps |
| Joint family → local work | Huge Cartesian allocation, overflow, free failed search | Product bound before construction; shared axis rules; all-run paid work totals |
| Target → work model | Score trials mistaken for SIS cost or ledger weight | Explicit ideal-hash assumption; separate component counters; no selected chainwork |
| Sphere visitor → policy | Unverified discovery or early stop labelled complete | Verify before callback; strict bool; explicit visitor-stop; cleanup on all exits |
| Preparation pool → cache | Approximate-key reuse, partial/poisoned data or stale scores | Exact full profile/matrix keys; completed immutable pools; current vector validation and header hash |
| Warm replay → cost claim | Free cold preparation or unrealistic unlimited storage | All-run costs; fitting versus cleared/churn diagnostics; bounded LRU; repeated-input labels |

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

The optional FLINT backend is research-only, not part of verification/consensus.
Approximate internal Gram arithmetic does not weaken exact acceptance checks.
Installed binary/license hashes are evidence; wheel pinning is installation
provenance, not a hostile-environment runtime authenticity proof. Worker output
capture and native transient allocation are not OS memory limits.

The grinding score remains a research predicate, now independently implemented
in Rust with strict external targets (spec 09). Counters describe instrumented policy work; family preparation
and full oracle audits are separate. Arbitrary time/payload variants do not imply
valid future blocks. Early hit totals and repeated base headers are not independent
network weight, and heuristic family exhaustion is not nonexistence evidence.

Sphere node/proof/fraction ceilings are cooperative mathematical bounds. Certificate
audit, transient arithmetic, GSO allocation and sorting can consume work outside
node counters; none is an OS memory/time limit. Recursive state is released on
completion or caps without relying on cyclic GC. Only full tree exhaustion over
a certified full lattice proves the bounded vector set. Dense/high-dimensional
profiles outside the survey remain unmeasured. Sphere is connected to paid
laboratory policies; a complete algorithm is not a hardness theorem.

Joint target sweeps restart each policy independently, preserve unsuccessful work
and distinguish repeated experimental hits from distinct proofs. 2^256/T is only
an ideal expected eligible-score-trial expression. Hidden prover computation is
not observable from the valid proof; no component counter or timing determines
future consensus weight. Time/payload validity and allowed grinding surface still
need an explicit future block specification.

Integrated policies execute native LLL and exact search only on visited matrices.
Fresh acquisition and failures are charged; a reused vector that fails receives
no score and no hidden fallback reduction. Eager sorted-pool cache-all differs
from traversal-order streaming all. Common node/reduction/score ceilings do not
imply equal wall-time or close competition from unknown optimized solvers.

Cache completeness relies on trusted internal sphere results, not untrusted
caller assertions or an authenticated external cache. Exact keys include profile
and norm bound; header-dependent scores never enter storage. Every vector read
is validated again. Cold preparation is retained in replay costs, and eviction
can destroy its benefit. Tiny-q collisions do not imply reuse on production profiles.

The explicit in-process FLINT environment amortizes one paid backend setup; it
retains independent exact audits but has no subprocess timeout/preemption. A
stalled experiment needs caller-enforced process termination and leaves evidence
incomplete. Setup and nested per-stage timers are not disjoint total costs;
component ceilings are cooperative, not OS memory/time enforcement.

The new external-window driver applies Windows process/job committed-memory
ceilings before resuming a suspended worker and terminates its Job at a deadline.
It is a controlled-experiment resource boundary, not a hostile-code sandbox or
hard real-time guarantee. Scheduling, low-power states and cleanup can affect
elapsed time; overshoot is retained. Commit usage is not RSS or a memory-hardness
proof. Fixed-order processes share OS cache and load despite empty Python caches.

Immutable stage files have bounded length/digest completion markers. These detect
partial writes, not malicious file tampering; directories remain ignored forensic
artifacts. Aborted work is unknown, complete-window hit totals exclude recovered
aborted stages, and unconditional logical cost per hit is null when censored.
Unclassified native aborts must not be relabeled memory exhaustion without evidence.
Source/protocol errors invalidate the whole survey rather than becoming limit wins.

Trusted LabRules fix profile/context, timestamp interval, payload commitments
and score target outside submitted proofs. Forbidden surfaces are rejected before
instance generation. Rules do not prove parent-chain existence, payload-body
validity or consensus time. Fresh-parent schedules are deterministic lab inputs,
not a live chain; WLP1 stages reset budgets and vector acquisition. Rust now has
independent full lab admission, while windows-v1's historical survey still uses
bound SIS verification alone. New WCP1 experiments use native full admission.
The next gates in ADR 0009 remain necessary before choosing difficulty or chainwork.

New SHA-256 is handwritten bounded laboratory code, checked with known answers
and Python hashlib at padding/length boundaries; neither hash implementation is
cryptographically certified. Target transport is canonical 33-byte big-endian
for 0..2^256 and cannot come from a submitted proof as trusted policy. Local
adapter rules are caller-controlled configuration, not authenticated remote input.

Persistent campaigns carry one paid vector across parent/height changes while
keeping the network/profile fixed. Every carry is verified against regenerated A
and scored only when valid; failed carry receives no score. Explicit fallback
charges fresh reduction and its repeated matrix derivation. Campaign-wide limits
do not reset; skipped stages retain the initial stop reason. No external oracle
seeds acquisition. Shuffled repeats reuse mathematical inputs and share host state;
they do not represent independent proofs or steady mining. Interrupted logical
work remains censored regardless of recovered hits or available checkpoints.

The WXP1 portfolio adds paid FIFO multi-vector pools and combinations of vectors
valid on the current matrix. Eager acquisition is charged in full even if scoring
stops early. Every carried vector is revalidated; changing parent/header does not
make old vectors automatically valid or automatically impossible. Finite sparse
and sieve probes cannot certify an empty full search. Bounded projected BKZ tours
are not high-dimensional optimized attack estimates. Node kinds differ by backend;
the Job enforces host resource allowances, not economic equivalence.

MGB1 commits target, recipient, body and version into the derived challenge.
Externally configured chain policy chooses one network/profile/target and a
trusted anchor. A peer-supplied target or profile never overrides that policy.
Canonical packet/body bounds precede matrix expansion; network/profile/parent/
height/time failures reject before expansion. Body hashing is bounded but is paid
before header-surface checks. State changes only on full proof acceptance.
Future-time deferral is distinct from proof invalidity. Non-tip parent status
does not mean a competing branch was validated or intrinsically rejected.

The linear chain assumes a trusted integer local clock and controlled callers,
not authenticated peers or accurate network time. It stores at most 4096 immutable
blocks and has no transactions, monetary state, persistence, concurrent append,
fork selection or retarget. Fixed-policy accepted-block count is only nominal
laboratory weight. Native proof/hash interoperability is not an independent
native MGB1 parser/chain engine. Production consensus and portable work remain
separate open gates despite the executable prototype.
## Independent chain and bounded fork laboratory

The complete native engine independently parses canonical MGB1 and enforces the
same trusted fixed profile/target, parent, height, upper-median/future-time and
proof-before-storage order as Python. It does not infer policy from peer packets.
MCP1 transport is local, length/command bounded and contains no network handlers.

Fork ancestry is branch-local; proposed preferred history is fully revalidated
before atomic switching. Nominal depth and first-arrival ties are experimental,
not economic chainwork. Opaque history replacement is not transaction rollback.
Invalid revalidation preserves accepted nodes/canonical state. Normal local
clock advancement can expire pending entries even on rejected submissions.

Combined orphan/future queues, TTL, validated nodes, depth, trusted-label rates
and explicit drain bounds limit retained state and admission calls. Duplicate
submission cannot refresh TTL. Unknown-parent proofs are not trusted merely
because canonical shape passes. A drain's full-path replay can cost 1032 admission
calls; an eight-attempt cap must not be described as eight proof checks. Wire
byte caps exclude interpreter overhead. Trusted finite labels are not a deployed
peer identity system; pruning, persistence, peer admission and fairness remain open.

Synthetic retarget experiments assume independently eligible score inputs and
explicit hypothetical supply multipliers; neither they nor inverse target
calibrate SIS work. Timestamp-based availability failures are retained as negative
results. Dynamic targets are not installed in real block admission, and no
production fork/retarget safety claim follows from finite toy convergence.

## Native and CUDA column-search laboratory boundaries

CPS1 requests are local framed data, capped at 32800 bytes. Profile, matrix
residues, exact lengths and search limits are checked before search allocations.
CSR1 decoding bounds outputs and rejects inconsistent work/flags, noncanonical
witnesses, out-of-prefix proofs and reversed order. Malformed input exits the
native process without returning usable partial evidence.

The CUDA C ABI is trusted local FFI: supplied pointers must reference valid
spans, and each owned session handle must be used serially and closed once.
It is not a pointer sandbox, network handler or peer security boundary. Python
validates types/bounds before ctypes narrowing; C rechecks dimensions, span
lengths, residues and chunk bounds before allocation/launch. Checked synchronous
mask copies detect kernel completion failures. Failed calls propagate, close
resources and invalidate study results; no CPU fallback manufactures success.

Compile and load only the explicitly selected research library. Source, compiler
and binary fingerprints protect reproducibility, not against a malicious local
administrator or a compromised compiler. Buffers are logically bounded; runtime
resource isolation, energy pricing and memory-hardness properties are not claimed.
