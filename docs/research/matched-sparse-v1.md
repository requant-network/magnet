# Matched CPU/GPU sparse search and unit triples

Date: 2026-10-09. Research evidence, not a production mining benchmark.

This block completes three tasks: a common in-process CPU/GPU search contract,
an extension through unit weight-three candidates, and an audited measurement
schedule. All 504 search attempts agree with an independent Python reference;
7584 returned proof occurrences pass the independent Rust verifier. CPU group
totals are lower than GPU totals in this schedule. These measurements do not
establish a portable hardware winner or calibrate consensus work.

See the [contract](../../spec/20-matched-sparse-search.md),
[compact evidence](results/matched-sparse-v1.json) and
[decision](../decisions/0016-matched-scope-and-unit-triples.md).
The compact artifact binds the exact raw JSON bytes with `raw_artifact_sha256`.
Raw evidence and build manifests remain in ignored local artifacts.

## What is matched

Both backends use the same Python validation, session API, chunk scheduling,
boolean masks, output decoding, stopping rules and per-weight ledger. Every timed
search owns a fresh session and pays validation, host matrix copying, allocation,
screening, readback, output decoding and cleanup. Proof audits are outside search
timers. GPU search additionally pays device allocation, matrix upload and mask
download. CPU search uses scalar C++ and advances a sequential support cursor;
GPU threads unrank individual ordinals.

The two C++ backends share support and arithmetic helpers, so agreement alone
is not independent validation. Separate Python itertools/arithmetic audits and
Rust proof checks supply that evidence. This is a matched integration scope,
not an isolated kernel comparison. Historical Rust/PyTorch/fused timings from
earlier reports have different scopes and must not be divided into these times.

Library loading and tiny CPU/GPU first probes complete before the schedule,
followed by synchronization. They are recorded separately: 1.252 ms library
load, 0.173 ms CPU first probe and 299.387 ms GPU first probe. These ordered
probes are not controlled cold-start benchmarks. Case-specific setup remains
inside every search timer.

## Candidate family and prefix limitations

The new domain contains coefficients in {-1, 0, 1}, with the first nonzero
coefficient positive and at most two or three nonzero coordinates. It orders
singles, then pairs, then triples lexicographically. The weight-two size is m²;
the weight-three size is m² + 4*C(m, 3), subject to the norm bound.

At m=128 the full weight-three domain contains 1381888 candidates. The search
cap is 65536, with at most 256 returned proofs and chunks no larger than 4096.
The cap therefore covers all 16384 singles/pairs and only 49152 of 1365504
triples (3.60%), concentrated near early coordinates. Prefix yield cannot be
extrapolated to the whole triple domain. At q=2 sign-related candidates also
have correlated modular acceptance.

Triples can find solutions unavailable to the smaller family: for A=[1,2,3]
modulo 17 and B2=3, (1,1,-1) is valid while the singles/pairs domain has no
solution. Each full seeded group/repetition adds 231 accepted triple occurrences.
The two chunk groups and three repetitions reuse the same challenges; these
counts are not independent discoveries or fresh SIS work.

Each successful full chunk is paid, including accepted candidates beyond the
output cap. The ledger records checked intervals, unchecked suffixes, proof-cap
stops, candidate-cap censoring, accepted tail discards and per-weight counts.
An exactly sufficient candidate cap means domain exhaustion, not censoring.

## Schedule and results

There are 84 cases, three repetitions and two backends: 504 attempts. Sixty
seeded cases span five profiles, two challenge labels, two maximum weights and
three cap/chunk settings. Twenty-four fixtures include zero matrices, a
triple-only solution, identity, norm-one, singleton and maximum dimensions.
Ten unique SHAKE-generated matrices are shared across related settings.
Order seed is 2026100912; challenge labels are 2026100913 and 2026100914.
Backend order alternates by case/repetition.

Per backend, 252 searches screen 2145192 candidates in 17178 chunks, see 26946
accepted candidates, emit 3792 proofs and discard 23154 accepted tail candidates.
Accepted occurrences by weight are 1074 singles, 24468 pairs and 1404 triples.
There are 150 zero-output attempts, 39 proof-cap stops, 72 candidate-censored
attempts and 108 attempts with an unchecked suffix; these categories overlap.
Zero matrices dominate discarded tails and do not represent mining parameters.

Total elapsed milliseconds across all three repetitions:

| Group | CPU | GPU |
| --- | ---: | ---: |
| Small chunks, weight 2 | 32.314 | 87.505 |
| Small chunks, weight 3 | 140.513 | 494.690 |
| Large chunks, weight 2 | 23.415 | 50.825 |
| Large chunks, weight 3 | 76.942 | 83.189 |
| Capped prefix, weight 2 | 15.471 | 25.109 |
| Capped prefix, weight 3 | 15.221 | 23.567 |
| Fixtures, weight 2 | 18.203 | 200.067 |
| Fixtures, weight 3 | 18.211 | 24.157 |

Individual samples, per-repeat totals and per-case median ratios remain in
evidence. Large-chunk weight-three GPU repeat totals are 27.940, 28.011 and
27.238 ms, versus CPU 25.563, 25.465 and 25.914 ms. Fixture weight-two GPU
repeat totals are 8.071, 179.318 and 12.678 ms, including a 171.379 ms individual
spike. We retain that observation without attributing a cause or selecting a
more favorable rerun. The host was not exclusively isolated for benchmarking.

Each backend copies 3260928 host matrix bytes. GPU also uploads 3260928 bytes
and downloads 2145192 mask bytes. Maximum logical host matrix storage is 65536
bytes; maximum device matrix-plus-mask storage is 69632 bytes. These are payload
and logical buffer counts, not process memory, energy or memory-hardness claims.

## Verification and publication integrity

The local gate passes 266 Python tests, 21 Rust tests, rustfmt/clippy and prior
differential corpora. Twenty-two new tests cover domain/search and evidence
failure handling. The previous 373-case native column corpus remains unchanged.

Fourteen exhaustive support configurations audit 1423296 ordinals per backend,
including every ordinal of the largest 1381888-candidate domain. Independent
oracle hashes agree. Boundary audits exercise 650 C ABI rejections, 106 full
mask cases and 988 backend chunks covering 34518 backend ordinals. Maximum
q/n/m regions include modular wraparound and chunk boundaries near the start,
pair/triple transition, capped-prefix edge and domain end. Forty-six applicable
pair-domain cases also match the existing Rust search. All 7584 emitted proof
occurrences pass Rust SIS verification.

Sources are frozen before compilation: 184 source files. Native binaries are
fingerprinted immediately after Cargo artifact selection, checked after CUDA
compilation and retained without resealing. Source, native/library/build-metadata
and build snapshot hashes are checked through publication. The compact report binds the
raw file digest. Hashes support reproducibility, not trust in a malicious compiler.

Every elapsed sample must be a positive strict integer. A failed build, backend,
audit or timeout produces failed evidence and no timing ratios. Successful FFI
chunks followed by malformed masks remain completed work, while independently
validated progress is recorded separately and the corrupted chunk's accepted
count is unknown. Killed child processes also retain unknown counts instead of
inventing zero work. Cleanup failures remain attached to the original failure.

Audits are separately paid and excluded from search times: Python reference
1033.614 ms, exhaustive support 1548.138 ms, mask/boundary 267.939 ms and native
pair/proof checks 560.334 ms. Matrix generation takes 13.344 ms and CUDA
compilation 1015.664 ms.

## Environment and reproduction

The existing local CMP 50HX has compute capability 7.5 and driver 610.43.03.
Existing nvcc 13.3.73 builds with `-O3 --shared --cudart=static
-Xcompiler=-fPIC -arch=sm_75`; linked CUDA runtime is 13.3. Rust is 1.98.1,
offline/locked with the existing unsafe-code prohibition. No packages, cloud
GPUs or GitHub Actions were added. The miner was inactive before/after; ComfyUI
retained 132 MiB of GPU memory. No unrelated service was changed.

Run from the repository, using the existing Python environment on the CUDA host:

```sh
python scripts/check.py
python scripts/run_matched_sparse.py --nvcc /usr/local/cuda/bin/nvcc --arch sm_75
```

The runner builds and audits the artifacts before publishing results. CPU-only
unit checks do not substitute for the hardware survey. The next research block
should examine broader non-unit solution families and paid amortization across
fresh challenges before selecting any security parameters or consensus work rule.
