# Native CPU and fused CUDA column search

Date: 2026-10-09. Executed on the owner's local CMP 50HX. Research only.

Three tasks are complete: an independent optimized Rust column search, a fused
CUDA kernel with a bounded owned-session interface, and a reproducible four-way
comparison. All **600 attempts agree**, with **4416 returned proof occurrences**
independently checked by `sis-verify`. The fused implementation reduces the
PyTorch orchestration overhead on this schedule. Native Rust computation is
very short; these measurements do not establish a portable GPU mining advantage.

See [contract 19](../../spec/19-native-fused-column-search.md),
[committed evidence](results/native-fused-column-v1.json),
[Rust engine](../../crates/sis-verifier/src/column_main.rs),
[CUDA kernel](../../cuda/unit_sparse.cu), and
[survey](../../scripts/native_fused_survey.py).
Raw matrices, per-attempt outputs and timings are retained locally in
`artifacts/native-fused-column-v1.json`.

## Algorithms and work

All backends search the same restricted canonical unit-sparse domain. Positive
singletons precede lexicographic pairs, with +1 then -1 in the second coordinate.
B2=1 permits only singletons; otherwise the domain has m² candidates. This is
not complete SIS search for larger norm bounds. None changes block validity,
score admission, difficulty or chainwork.

Rust independently enumerates nested supports, transposes the matrix once and
short-circuits failed rows. CUDA independently decodes each ordinal by integer
triangular subtraction in registers and checks the exact int64 modular column
sum. It launches one kernel per chunk and returns one acceptance byte per
candidate. It does not materialize candidate tensors or receive CPU-discovered
solutions. Python reconstructs only emitted vectors.

Both retain full paid chunks: accepted-but-discarded tail candidates count, and
candidate caps truncate exactly. Proof-cap precedence, exhausted-domain flags
and complete-proofset flags match Python. CPS1/CSR1 framing validates exact
lengths, dimensions, residues, caps and output prefix/order. The Rust executable
uses safe Rust and standard libraries only.

Each fused search creates and closes its own session, paying allocation and
matrix transfer every time. Session device ownership is exactly `8*n*m+width`
logical bytes, at most 65600 in the measured legacy group and 8192 in the
large-chunk group. These are buffer sizes, not observed total device memory,
allocator peaks, a hard OS ceiling or evidence of memory hardness. Runtime and
context overhead are excluded. Scheduled column reads are upper bounds because
the Rust and fused kernels can reject on the first failing row.

## Matched schedule and outcomes

Repeat the prior 50-case column schedule three times: 42 legacy cases and eight
larger-chunk cases per repetition. There are ten unique seeded challenges plus
fixtures, not 150 independent random challenges. Legacy widths are 7/64/256;
the larger group repeats four challenges at widths 1024/4096. GPU/Python order
rotates per case and repetition. Native requests run in one 50-request process
per repetition, before the GPU work for repetitions 0/2 and after it for 1.
This is a documented bulk placement, not a fully interleaved native timing study.

Per backend, all three legacy repetitions screen 214272 candidates in 2196
chunks, see 1173 accepted candidates, and return 1104 proof occurrences. Thus 69
accepted candidates are discarded by proof caps. Each backend's large-chunk
group screens 208896 candidates in 132 chunks with no accepted proof. Those
failed-search costs remain present; zero proof counts are not zero-cost success.
Each backend materializes 100530 logical returned vector entries in total.

## Timings and scope

Aggregate times below cover all three repetitions, in milliseconds.

| Backend | Legacy: 126 searches | Large chunks: 24 searches | Timing scope |
|---|---:|---:|---|
| Python columns | 112.793 | 144.746 | Validation, transpose, search, output |
| Rust columns | 2.048 | 1.478 | Internal parse/validation/transpose/search; excludes serialization/transport |
| PyTorch CUDA columns | 629.621 | 47.608 | Validation, setup, transfer, search, readback, output, cleanup |
| Fused CUDA columns | 105.889 | 22.671 | Validation, session allocation, transfer, search, readback, output, close |

On these matched inputs the two GPU search wrappers have the same paid matrix
payload and mask traffic. Fusing takes approximately 5.95 times less search
wrapper time in the legacy group and 2.10 times less in the large-chunk group.
This is a descriptive same-run improvement over PyTorch, not a speedup over
optimized native CPU or a hardware-independent performance claim.

The native **complete adapter wall** across all 150 requests is separately
recorded: 198.393, 201.525 and 204.238 ms per 50-request process, totaling
604.157 ms. It includes process startup, encoding, pipes, decoding and host
validation of returned proofs. The native engine total is 3.526 ms. The bulk
adapter does extra host proof checks relative to the GPU wrappers, so neither
this wall time nor the internal engine alone is an equivalent end-to-end mining
comparison. The transport cost shows why future integration should avoid
repeated processes and choose a matched trust/verification boundary.

Cold library/first-probe setup is 297.202 ms; PyTorch import/first-probe setup is
1180.556 ms, measured sequentially on a shared CUDA context. These are distinct
ordered setup scopes, not independent cold-start benchmarks. Compilation takes
865.496 ms. Matrix generation is separately recorded. Boundary/domain audits
take about 36.234/286.578 ms; host and independent native returned-proof audits
take 4106.290/321.519 ms. Audits supply no solutions to paid searches.

Both GPU backends explicitly transfer 546624 matrix bytes and read 423168 mask
bytes in total. These counters exclude implicit command/context traffic and do
not measure PCIe bandwidth. Rust reports 473175 actual row checks compared with
the logical upper bound implied by the same domains; the counter is not an
instruction or energy measurement.

## Verification, provenance and reproduction

- Local gate: 244 Python tests, 21 Rust tests, rustfmt/clippy and all existing
  differential corpora. New native corpus: 373 cases, 21177 screened candidates,
  14 malformed frame/request rejections, zero mismatches.
- Actual GPU C ABI: 14 rejected invalid requests; full masks for 71 cases,
  249 chunks and 16804 candidate ordinals, including every small q=2/3 matrix
  and a q=65521, n=64, m=128 mixed-column case.
- Fused support audit: 25 domain/width configurations, all 88076 ordinals,
  compared to independent host enumeration and ordered vector hashes.
- Every returned occurrence from all four backends is checked by the existing
  independent native verifier: 4416 checks, zero disagreement.
- Freeze 174 source fingerprints, including CUDA, and native/search/library/
  build-metadata binaries. Recheck before publication; failures invalidate
  compact and local raw reports before builds or surveys.

The existing compiler is nvcc 13.3.73 with `-O3 --shared --cudart=static
-Xcompiler=-fPIC -arch=sm_75`. The library reports CUDA runtime 13.3 (13030);
PyTorch 2.14.0+cu130 uses its own CUDA 13.0 runtime. CMP 50HX capability is 7.5.
Rust 1.98.1 release builds use the locked offline standard-library package.
No packages, cloud compute or GitHub Actions were needed.

On a locally selected compatible Linux CUDA host with existing PyTorch and nvcc:

```sh
python scripts/check.py
python scripts/run_native_fused.py --nvcc /usr/local/cuda/bin/nvcc --arch sm_75
```

Use the Python interpreter that already contains PyTorch for the hardware study.
The driver invalidates stale evidence before builds, resolves actual Cargo
artifacts, fingerprints the compiler/library, and runs the fixed schedule.
It does not manage services or install dependencies. GPU mining was inactive at
pre/post inspection in this run; ComfyUI remained resident with 132 MiB.
Concurrent CPU/service load and clocks were not isolated, so results are local
descriptive observations. The [Russian report](../ru/native-fused-column-v1.md)
is secondary.

## Next research gate

Retain the fused implementation as an independently audited baseline. Before
expanding GPU claims, compare matched in-process native/GPU scopes on broader
candidate families and representative distributions, including failed search
and preparation. Keep larger short-vector search, solver competition, reuse,
grinding and portable work pricing ahead of consensus parameter selection.
