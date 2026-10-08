# Native CPU search and larger toy instances

Date: 2026-10-08. Scope: supplied-matrix SIS-LAB-v1 CPU baselines, not a miner
benchmark, consensus work calibration or hardness assessment.

## Implementation and reproduction

Both exact solvers now have Rust implementations. Ball search updates residues
per coordinate with fixed stack snapshots instead of per-prefix allocations.
MITM preserves every syndrome collision in a sorted vector table and uses binary
search for matching groups. Python uses a dictionary. Acceptance is unchanged,
including sign canonicalization and the squared-norm bound. The
[native protocol](../../spec/02-native-search-v1.md) exposes distinct exhaustion
and cap statuses; requests cannot supply known solution vectors.

```sh
python scripts/check.py
python scripts/native_survey.py
```

No GitHub Actions, remote compute or third-party dependencies are needed. The
survey builds an offline locked release executable with overflow checks. This
run used Python 3.12.10, Rust 1.98.1, x86_64-pc-windows-gnu and an AMD64 host
(family 25, model 117). Compiler identity, executable and source/configuration
SHA256 hashes are in the [committed summary](results/native-survey-v1.json).

The full local report, `artifacts/native-survey-v1.json`, includes each seed,
stop, counters, timing samples, capacity charges and sorted proof-set digest.
The companion is `artifacts/native-survey-summary-v1.json`. Both are invalidated
before a rerun starts; a failed run cannot leave stale success. The committed
summary describes this run and is not refreshed automatically. Its base commit
identifies the starting snapshot; hashes identify the new sources measured.

## Method and timing boundary

Six profiles have six generated matrices each: two batches of three seeds.
The seed is SHA256 of ASCII `magnet-sis-native-v1/q/n/m/B2/batch/index`; matrix
expansion uses the existing Python SHAKE generator. Solvers run three times.
Native algorithm order alternates with batch/index/repetition. Python follows
its corresponding native solver on the first two profiles. Those shared profiles
have identical exact sets across languages. On larger profiles native ball/MITM
sets agree; Python independently verifies every emitted vector in every
repetition. Duplicates or an unexpected cap fail the survey.

Each native sample uses a fresh process and one request, avoiding previous-report
retention during another measured solve. Its internal timer excludes startup,
decoding and IPC. It includes initialization, preprocessing, sorting, enumeration,
output retention and capacity accounting. Python times construction, enumeration,
retention and iterator cleanup on a pre-expanded matrix in the reused survey
process. Its counter snapshot and proof audits are outside timing. Shape checks
and the matrix tuple copy are in Python construction, while native decoding is
untimed. Both exclude expansion, scoring and proof verification. These are
disclosed implementation comparisons, not identical runtime environments or
end-to-end PoW throughput.

Use each instance's median of three samples, then sum the six medians. Repeated
runs are not independent proofs. Scheduling, CPU frequency and allocator state
are uncontrolled; there is no affinity, confidence interval or portability claim.
Small-profile ratios varied materially in development reruns. The summary
preserves the final run rather than selecting the best timing.

## Exact-set results and local solver time

All 36 complete instances exhaust their domains. There are 216 native measured
solves and 72 Python measured solves on shared profiles. Each algorithm emits
53534 accepted vectors across the distinct instances, counted once per instance.
These are not 53534 independent units of PoW work.

| q, n, m, B2 | Vectors over six instances | Ball time, ms | MITM time, ms | Ball / MITM |
|---|---:|---:|---:|---:|
| 17, 2, 6, 16 | 231 | 1.2976 | 0.3763 | 3.45 |
| 17, 2, 8, 8 | 220 | 1.0302 | 0.5427 | 1.90 |
| 257, 3, 10, 8 | 0 | 6.2929 | 1.4649 | 4.30 |
| 257, 3, 12, 12 | 0 | 252.6947 | 18.6419 | 13.56 |
| 257, 3, 14, 12 | 5 | 1529.5256 | 93.4343 | 16.37 |
| 17, 2, 12, 12 | 53078 | 214.2980 | 24.1205 | 8.88 |

On shared profiles native ball is about 67 and 98 times faster than Python ball;
native MITM about 20 and 16 times faster than Python MITM in these solver-only
timings. Ratios combine runtime effects, different table structures and accounting
overhead. They cannot be attributed solely to Rust or extrapolated to mining.

At m=14,B2=12, ball visits 24365729 coordinate prefixes and 14177271 leaves
per matrix. MITM considers 823543 proposals per half and retains 16830 entries;
its preprocessing is timed. At m=12,B2=12 the q=17 and q=257 profiles share norm
geometry but differ in modular constraints and output retention. Complete
enumeration, rather than a timeout, establishes zero solutions for all six
sampled q=257,n=3,m=12 instances. Four of the six m=14 instances have solutions.

## Capacity charges, not process memory

| q, n, m, B2 | Ball charged bytes, min–max | MITM charged bytes, min–max |
|---|---:|---:|
| 17, 2, 6, 16 | 1616–2648 | 18520–19552 |
| 17, 2, 8, 8 | 1832–3208 | 20016–21392 |
| 257, 3, 10, 8 | 172 | 75000 |
| 257, 3, 12, 12 | 204 | 643216 |
| 257, 3, 14, 12 | 236–444 | 2508416–2508624 |
| 17, 2, 12, 12 | 809096–856616 | 1431632–1479152 |

The measure charges live Vec payload capacities at build/search phases, including
matrix and proofs. It excludes allocator metadata, rounding, reallocation overlap,
stack, sorting scratch, executable/OS memory, wire buffers and caller state.
Ball snapshot arrays alone have a 256*m-byte allowance; other stack contents
also exist. Small ball values above are not the full required process memory.
Do not compare directly to earlier Python tracemalloc measurements or infer
mandatory memory for every miner.

## Partial results and verification

A separate q=257,n=3,m=16,B2=12 seed has a 1000000-node ball cap. Ball stops
at exactly that count with `node-limit`. MITM rejects its half-box preflight
(7^8 > 1000000), before enumeration. Both emit zero proofs; this cannot establish
nonexistence. Their times are excluded from the complete-solver table.

Checks cover maximum modulus/norm, modular wrap, zero columns, collision retention,
m=1 and odd splits, huge box/small ball, exactly sufficient caps, proof overflow
and malformed frames. 103 differential instances produce 206 search outputs
with no discrepancies; 1940 proof occurrences are independently verified.
The suite has 55 Python and 8 Rust tests, plus the existing verifier corpus.
Independent source review found and resolved a stale-summary lifecycle issue;
the regression test forces build failure and checks both report statuses.

## Consequences and next gate

MITM retains its advantage over incremental ball traversal on these native
instances. Reference runtime and naive box size remain unsuitable intrinsic proof
prices. Larger dimensions also do not guarantee usable availability: two profiles
have no solutions in all sampled matrices, while a smaller-modulus profile has
many thousands per matrix. Study availability and reuse together with attacks.

Before difficulty or accumulated chainwork, add a competing lattice-reduction
or sieving baseline, examine larger-parameter availability and preprocessing/reuse,
and define/test block-header-to-instance binding. LLL/BKZ, GPU execution,
independent Rust SHAKE expansion, work/retarget rules and network consensus are
absent. This milestone does not establish secure SIS-PoW or mainnet parameters.
