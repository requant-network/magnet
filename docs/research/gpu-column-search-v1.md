# Column arithmetic and boolean-only CUDA output

Date: 2026-10-09. Exact optimization of the previously audited unit-sparse domain.

## Result

The optimized CUDA search generates support tuples on-device, checks the two
relevant matrix columns, and transfers one boolean mask per chunk. Full vectors
are reconstructed on the host only for returned solutions. The former dense
Python/CUDA implementations remain available for comparison.

All 50 comparison cases complete: 42 legacy cases run four backends each, and
eight larger-chunk cases run two column backends each, giving 184 attempts.
Ordered proofs, stopping/completeness semantics and shared candidate ledgers
agree within every case. Independent Rust accepts all 1472 returned-proof
occurrences. Separate full-domain support/vector audits cover 88076 ordinals
across 25 domain/width configurations, with no disagreements.

In the current legacy-width run, CUDA columns take about 0.216 seconds in total
versus 0.536 seconds for dense CUDA, about 2.48 times less search time. However,
the corresponding column Python baseline takes about 0.037 seconds. The CPU
algorithm optimization materially changes the comparison. Larger chunks reverse
that descriptive Python/CUDA ordering in this particular no-hit group, but no
optimized native CPU comparison or portable GPU advantage is established.

See [implementation](../../reference/column_search.py),
[contract 18](../../spec/18-column-search-optimization-v1.md) and
[committed results](results/gpu-column-search-v1.json). Raw jobs, matrices,
results and per-call memory observations are in `artifacts/gpu-column-search-v1.json`.

## Algorithm and paid scope

Keep the exact canonical unit-sparse ordering: positive singletons, then
lexicographic coordinate pairs with second coefficient +1 followed by -1.
The domain has m candidates at B2=1 and m^2 otherwise, and is incomplete for
general short-vector SIS. No block admission, score function or consensus rule
changes. The same finite domain can have no proofs on larger-field toy profiles.

Represent a singleton as `(first,first,0)` or a pair as `(first,second,sign)`.
The residual is `A[:,first] + sign*A[:,second]`, using exact int64 arithmetic.
CUDA independently constructs ordinal/support arrays with integer triangular
prefixes. Its residual calculation uses no dense candidate tensor and receives
no CPU-found solution/support oracle. The host's decoding of an accepted ordinal
is deterministic representation work, not independent solution discovery.

One boolean mask read per chunk replaces explicit first-ordinal/count scalar
and output-vector reads. It gives the host all accepted candidates, including
the discarded tail after a proof limit. Only the remaining prefix of valid
ordinals is materialized as returned vectors. The whole processed chunk remains
paid; candidate caps truncate the final chunk exactly. An exactly sufficient
candidate cap is domain-exhausted unless the proof cap also fires.

Candidate/proof limits remain 16384/256. Column batch widths extend to 4096,
with strict range/type checks and conservative logical tensor bounds before
device allocation. Dense backends retain their old maximum width 256.

## Reproducible comparisons

The legacy group repeats the existing 42 cases with the same ten seeded
challenges and boundary fixtures, candidate/proof caps, and widths 7/64/256.
Each case runs dense Python, dense CUDA, Python columns and CUDA columns.
Execution order rotates; overall shuffled order seed is 2026100910.

The larger-chunk group reuses four of those seeded challenges at m=32/128,
with widths 1024 and 4096: eight cases, two column backends each. All of these
cases exhaust their restricted domains without a proof. They test failed-search
accounting and overhead, not cost per successful proof. The study still has ten
unique seeded challenge matrices, not 50 independent random challenges.

Within a case, common proposal/check counts and stop conditions are identical.
Backend-specific vector materialization, setup and transfer ledgers are checked
against their own algorithms instead of being forced equal. Different batch
widths can change paid proof-limit tails, so timing across widths is not
automatically an equal-work comparison.

## Observed components and timings

Each legacy backend screens 71424 candidates in 732 chunks, sees 391 valid
candidates and returns 368 proof occurrences. This preserves the prior 23
accepted-but-discarded tail candidates. Rust checks each backend's returned
occurrences separately, rather than counting them as new blocks or distinct SIS
challenges.

| Legacy backend | Search seconds | Logical materialized vector entries | Explicit tensor D2H bytes |
|---|---:|---:|---:|
| Dense Python | 3.283 | 8577100 | 0 |
| Dense CUDA | 0.536 | 8577100 | 279792 |
| Python columns | 0.037 | 33510 | 0 |
| CUDA columns | 0.216 | 33510 | 71424 |

The dense matrix-grid schedule remains 36154504 slots per backend for historical
comparison. Column algorithms instead schedule 588050 column reads and represent
214272 support entries. Python can short-circuit failed rows, so these are
schedule/upper-bound counters, not executed CPU instruction counts. Logical
vector entries exclude temporary Python containers, runtime and allocator details.

CUDA H2D matrix payload is unchanged at 162752 bytes. Boolean-only D2H reduces
the legacy explicit payload by about 3.92 times. These payloads exclude implicit
command/shape/synchronization traffic and do not measure actual PCIe bus use.

The larger-chunk group screens another 69632 candidates per column backend in
44 chunks, with zero accepted/returned vectors. CUDA columns record about
15.86 ms of search and Python columns 32.57 ms in total. Setup, transfer and
output reconstruction are inside search timers; matrix generation is separately
recorded, approximately 1.87 ms across all 50 cases. Native/domain audits occur
outside paid search and do not supply search inputs.

The legacy dense CUDA peak allocated tensor memory is 4360704 bytes; legacy
CUDA columns peak at 167424 bytes. Column large-chunk peak is 497664 bytes.
These per-call PyTorch allocated peaks exclude cached reservations, total
device/context memory and host allocations. The 64 MiB logical bound is not an
externally enforced allocator ceiling or memory-hardness property.

The former historical study's 7.30-second dense CUDA total was a different run
with different load/order/setup conditions. It must not be compared directly to
this run as an optimization speedup. The table above compares current-run cases.

## Verification and hardware state

Host tests exhaust small matrices at q=2/3 against the independent dense baseline,
check full support/ordinal ordering, failed-proposal materialization, proof-tail
charges, B2=1/m=1, exact caps and corrupted ledgers. On CMP 50HX, actual support
generation is streamed back for full ordering/hash audits, including ordinals
beyond capped acquisition prefixes. Native Rust independently verifies every
emitted proof. All source fingerprints stay unchanged, and native binary hashes
are checked before evidence publication. Failed runs invalidate prior success.

The same source snapshot passes 231 Python tests, 19 Rust tests, rustfmt/clippy
and all existing differential corpora. Existing PyTorch 2.14.0+cu130 / CUDA 13.0
and an offline native release build are used; no packages or paid compute were
needed. English remains primary, with a [secondary Russian report](../ru/gpu-column-search-v1.md).

The active GPU miner container was identified from the CMP's compute-process
list and stopped under the owner's standing authorization. It was exited at
post-run inspection; ComfyUI remained resident. No startup configuration or
unrelated workload was changed. Cold/setup effects and concurrent activity are
not fully isolated, so timing is descriptive and no energy/chainwork calibration
is claimed. GitHub Actions were not used.

## Next step

Add an optimized native CPU baseline for the same domain before deciding whether
GPU scheduling pays. Then consider fused CUDA kernels and wider search families,
retaining exact differential checks and paid preparation/failed-search accounting.
Cheap sparse-domain search and short local timings do not determine production
SIS profiles, portable work, retarget or monetary rules.
