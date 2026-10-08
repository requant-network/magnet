# WXP1 paid pool and bounded solver portfolio

Research interface, not a network wire protocol. English is normative.

One campaign contains 1–8 stages of 1–16 canonical MGH1 headers (m<=16).
Within a stage network/parent/height/profile are identical. Across stages network
and profile remain identical; parent/height may change. Joint families are the
finite Cartesian product of nonce offsets, timestamp offsets and deterministic
payload commitments. Each axis has 1–8 entries; product <=16; u64 overflow rejects.
The trusted experiment supplies this surface before solver execution.

The pool is FIFO, capacity 1–16, deduplicated by exact canonical vector. All
insertions and evictions are counted. It persists across stages. Every carried
vector is revalidated against the current derived matrix before scoring.
Combinations are +/- of pairs of currently valid carried vectors, one finite
round. Zero, duplicates, out-of-norm and invalid combinations consume check work.
Valid combinations may enter the pool. Each distinct vector is scored at most
once per visited header; equal digests on later headers are still paid trials.

Policies: restart-all discards the pool on every visited header; pool-fallback
acquires only when there are no valid carried candidates; pool-all acquires when
no carried/combination hit has occurred. Acquisition eagerly obtains a bounded
set, charges the whole search, inserts its entire set and then scores in output
order until a hit/score cap. The pool can retain solutions never scored on their
acquisition header. No oracle supplies mining inputs or vectors.

Shared non-resetting ceilings: 1..1,000,000 search nodes, 1..128 acquisitions,
1..100,000 carried/combination checks, 1..100,000 scores, 1..256 proofs per
acquisition. A hit on the final allowed score wins that stage. Later stages obey
the remaining campaign budget. Unvisited stages preserve the original stop cause.
Backend partial output can be used if independently valid; partial is never empty
or complete evidence. Solver node kinds differ; their sums bound execution, not
hardware-independent economic work. Validation/reduction/setup/writing are paid
in the external window even when not represented by search-node counters.

Backends: native Rust MITM (descendant process inherits the Job), paid sparse-first
support<=2 screening (does not run a full fallback search), FLINT LLL .75
or .99 with exact Gram representation, bounded BKZ-4/BKZ-8 projected-SVP tours
followed by full sphere enumeration, and seeded finite pair-reduction sieve.
LLL certificates independently establish full kernel, determinant, unimodular
transform and .75 reducedness. The .99 setting is a requested backend setting,
not an independently certified .99 inequality. BKZ uses exact rational projected
enumeration and primitive unimodular insertion followed by LLL. One tour and
nodes <=half acquisition allowance; limit means partial improvement. Even a
completed tour is not a fixed-point BKZ certificate. The sieve is a bounded
heuristic (pool64, ternary row combinations); it never certifies completeness and
is not G6K, a GPU sieve or a high-dimensional security benchmark.

Portfolio MITM uses NAT1 mode3 (mitm-budgeted). Its node cap charges each left
half-box proposal, right half-box proposal and syndrome join pair, with the exact
identity nodes=left+right+pairs. Reaching the allowance does not fabricate an empty
domain; a later operation would return node-limit. Exactly sufficient allowance
can still finish normally. Legacy NAT1 mode2 remains frozen for historical surveys:
its nodes field is0 and it separately caps table/pairs/half-box geometry. It is
not used for a shared node-budget claim. Sorting/syndrome arithmetic and process
cost remain paid in the external window and separate native counters.

WXP1 JSON has exactly version/backend/policy/target/stages/capacity/combine/budget/seed.
Target is canonical decimal string 0..2^256. Header hex is lowercase280 characters.
Input <=65,536 bytes. Worker paths are a fixed driver allowlist; input cannot
select an executable. Pinned FLINT is optional and imported only after validation.
The fixed release native artifact is built and fingerprinted by the survey.
Windows Job time/commit ceilings apply before resume. Immutable checkpoints1..8
are hash/length verified and bounded at8MiB each. Forced termination means total
logical work unknown; checkpoints are partial observations. Completed campaign
counts may still have cooperative node/score/check caps and unvisited stages.

References: [FLINT LLL](https://flintlib.org/doc/fmpz_lll.html),
[python-flint0.9](https://python-flint.readthedocs.io/en/latest/fmpz_mat.html),
[fpylll projected BKZ overview](https://fpylll.readthedocs.io/en/latest/).
The portable BKZ implementation is original; no external BKZ code was copied.
