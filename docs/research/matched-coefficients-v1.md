# Matched small-coefficient CPU/CUDA: bounded D5 pilot

Date: 2026-10-09. Local supporting experiment for the work-weight question.
No consensus/SIS1/spec21/spec23 validity change or production miner.

Five tasks are complete: exact matched domain/chunk contract, independent
C++ scalar CPU/CUDA engine, owned Python client with failure accounting,
independent complete-order/mask/prefix audits, and frozen paired local timing.
See [spec24](../../spec/24-matched-small-coefficients.md),
[engine](../../cuda/matched_coefficients.cu),
[client](../../reference/matched_coefficients.py),
[survey](../../scripts/matched_coefficient_survey.py) and
[compact evidence](results/matched-coefficients-v1.json).

## Result and decision value

All240 paired cases, three repetitions and1440 measured backend attempts pass.
CPU and GPU agree on proofs, order, paid chunk prefixes, weight/coefficient
censuses, counters, output tails and independent stopping flags. The local gate
passes330 Python tests,23 Rust tests, rustfmt/clippy and earlier corpora.

CPU has the lower common elapsed sample in716 of720 pairs; GPU has the lower
sample in4. All24 seeded profile/bound/width groups have median paired
CPU/GPU time ratios below1 (range0.241–0.814). This does not show a GPU advantage
for this family and owned-session workload. It corrects any inference from
incompatible native-process versus GPU timing boundaries. It does not resolve
construction A versus B or prove portable PoW work: energy, memory scaling,
stronger CPU implementations and relevant non-toy parameters are unmeasured.

This is supporting D5 evidence. Continue with explicit candidate weights and
the D3 screening falsifier in [open questions](../OPEN-QUESTIONS.md), rather
than expand the GPU interface without a decisive work-model question.

## Domain, output and paid work

Profiles(q,n,m,B2) are (7,1,5,8),(17,2,12,12),(257,2,16,12),
(65521,64,16,12). Both bounds1/2 include legal scalar copies, support<=3,
positive first coordinate and norm-filtered spec21 pattern order. The native
engine independently builds at most42 patterns, then un-ranks column combinations.
It never receives a free precomputed candidate table.

Each CPU/GPU call fully screens the same chunk. The host emits only the first
remaining accepted proofs, explicitly charging accepted-but-discarded tail.
Proof-limit is the primary reason when hit; exhaustion is independent. Full
output requires complete domain screening AND no discarded accepted candidates.
Candidate-cap and output censoring are reported separately. Scheduled row/term
slots are upper-bound inventories, not measured early-rejected arithmetic.

Across720 pairs, one side of each pair screens2121792 candidates, returns7467
proof occurrences and discards2388 accepted tail occurrences. There are231 empty
pairs and147 incomplete-domain pairs; all remain in the evidence. These totals
include repeated matrices/scalar copies and are not independent trials or unique
discoveries. The independent sequential Rust comparison covers240 cases: identical
returned proofs, but chunk semantics pay12542 additional candidates in total.
That difference is recorded, not silently assigned to sequential Rust work.

## Honest matched timing

Both paths use the same Python wrapper and scalar/CUDA branches of the same
library. The common timer includes Python profile/input/domain validation,
ctypes packing, fresh owned FFI session, native pattern construction and matrix
copy, CUDA allocation/H2D where applicable, completed masks, boolean validation,
host materialization/censuses, close and result ledger. CUDA D2H acknowledges
completion. Dense independent Python/Rust audits and durable journal I/O remain
outside the timer. Load/first probes, challenge generation, builds and complete
audits are recorded separately.

Three fixed seeds per profile create12 unique seeded matrices. Both bounds,
widths31/256/4096 and candidate caps4096/20000 with proofcap32 produce144 seeded
cases. Six fixtures (zero,triple-only,nonunit-only,scalar-copy,singleton,late
witness), both bounds,widths7/4096,caps4096/20000,proofcaps1/256 add96 cases.
Three repetitions alternate CPU/GPU order by case/repetition parity. Every
individual sample is positive and all samples are retained.

The table uses bound2,width4096 groups: each has18 paired samples, combining
three seeds,two candidate caps and three repeats. Time columns are separate
group medians; ratio is the median of per-pair CPU/GPU ratios, not their quotient.

| Profile | CPU median ms | GPU median ms | Median paired CPU/GPU ratio |
| --- | ---: | ---: | ---: |
| (7,1,5,8) | 0.3746 | 0.6864 | 0.537 |
| (17,2,12,12) | 0.8138 | 1.1037 | 0.791 |
| (257,2,16,12) | 1.1657 | 1.3219 | 0.779 |
| (65521,64,16,12) | 1.3901 | 1.6214 | 0.814 |

Host: existing local CMP50HX, driver610.43.03, CUDA runtime13030. Mining was not
running. The resident ComfyUI Python process remained; no other service was
stopped. CPU is scalar C++, not best SIMD/multicore search. Clocks, caches and
concurrent workload are not isolated. The four lower GPU samples do not override
the grouped result; this finite local run supports no universal hardware winner,
energy comparison, ASIC-resistance, monetary parameter or secure chainwork claim.

## Audits and failure evidence

Complete support-order audits cross m1..16, eight norm limits and both bounds:
256 cases,606832 decoded ordinals across both backends. Tiny Cartesian enumeration
independently confirms filtered candidate order. Complete positive/negative mask
audits cover152 matrices/families,45890 candidate checks across both backends
and22945 independent Rust SIS verdicts. Another4978 Rust checks validate returned
proofs from first-repetition CPU/GPU calls. Direct malformed C probes reject29
inputs. CPU/GPU share native helpers; these independent audits are essential.

The maximum q65521,n64,m16,B2=12 fixture screens all18912 candidates and finds
all six expected proofs, including `(0,...,0,2,2,2)`, with outputcap256. Outputcap1
fixtures separately exercise paid acceptance tails, without implying full output.

Successful FFI work stays charged if Python mask allocation/validation or hit
materialization fails. Diagnostics distinguish completed versus validated masks,
known versus unknown acceptance and unfinished work. Close consumes the owned
handle even on cleanup error and cannot replace the original failure. Raw C
handles are a trusted process-local interface, not a hostile caller sandbox.

Interrupted runs recover bounded durable progress records, tied to the source
manifest/version. The runner clears previous progress before builds, including
same-source reruns. Partial final appends and work after the last durable event
remain unknown. Recovered outputs are evidence of completed calls, not proof that
all later audits passed; failure reports publish no performance ratios.

## Reproduction and provenance

Ordinary local gate: `python scripts/check.py`. Explicit hardware entry point:
`python scripts/run_matched_coefficients.py --arch sm_75 --nvcc /usr/local/cuda/bin/nvcc`.
It builds current Cargo-selected release sis-coeff/sis-verify and an nvcc-O3
shared library using the existing local compiler. No dependency/cloud/Actions.

Source hashes, CUDA source/compiler/flags/library metadata and a pre-build
snapshot are frozen before the study and checked through publication. Compact
evidence binds exact UTF8/LF raw bytes. Ignored raw data contains every matrix,
paired sample, census, reference and Rust prefix. Failure-journal tests cover
interruption, same-source stale evidence, allocation failure and stop overruns.
See the [findings](../FINDINGS.md) and
[secondary Russian report](../ru/matched-coefficients-v1.md).
