# Matched in-process small-coefficient CPU/CUDA laboratory

Status: separate local research interface. SIS1/spec21/spec23/consensus unchanged.

Five tasks: matched domain/chunk contract; independent C++ scalar CPU/CUDA
engine; owned Python client/failure ledger; complete-domain/boundary/native
audits; frozen paired measurements on the existing local CMP50HX.

## Exact family and chunk semantics

Use spec21 order and validity: prime q2..65521, n1..64,m1..16, B2=1..min(12,q²-1),
bound1/2, support<=3, first nonzero positive, include nonprimitive vectors.
Pattern order is first magnitude, then tail alphabet(1,-1,2,-2), norm filtered.
Weights increase, positions use lexicographic combinations, then patterns.
Maximum domain18912. Candidate cap1..20000, proof cap1..256, chunk width1..4096.

Both backends fully screen the identical capped chunk and return one boolean
per candidate. Host emits the first remaining accepted proofs; accepted tail
within the last paid chunk is counted/discarded explicitly. Proof-limit has
primary-reason precedence; domain exhaustion is independent. No untested suffix
acceptance is inferred. Sequential Rust search has a different stopping prefix
on output-cap hits: compare returned proofs and account the extra paid tail,
never equate its work with chunk work.

effective_limit=min(candidate_cap,domain); each count=min(width,effective_limit-
offset). Stop after the first chunk reaching the proof cap. Otherwise use
candidate-limit iff screened<domain, else domain-exhausted. Full output means
domain exhausted AND zero discarded accepted candidates. Within every validated
mask, accepted=returned+discarded; exactly sufficient candidate cap exhausts.

## ABI and ownership

Separate cc_* ABI1: cc_open(backend,matrix,entries,n,m,q,B2,bound,width,out_handle),
cc_batch(handle,offset,count,mask,length),cc_audit(handle,offset,count,supports,
entries),cc_close(handle),cc_sync(),cc_runtime(out),cc_error(code),cc_abi_version().
Backend0 scalar C++,1 CUDA. A support is six int32: three positions (unused zero)
and three coefficients (unused zero). Reject dimensions/prime/norm/bound/width,
noncanonical residues, lengths and null outputs before owned allocation. Invalid
open resets the output handle. Reject closed/wrapping ranges before FFI in Python.

C types: matrix const int64_t*, B2 uint64_t, entries/length size_t;
backend,n,m,q,bound,width,offset,count C int; handle void*,out_handle void**;
mask uint8_t* (0/1), supports int32_t*. Status C int:0 success,-1 invalid,
-2 host allocation, positive CUDA error; error returns const char*, ABI/runtime
versions C int. Matrix entries=n*m, mask length=count, audit entries=6*count.
Require offset>=0,1<=count<=width,offset<domain,count<=domain-offset. Python
rejects booleans before narrowing. Only owned live handles may be passed:
arbitrary/stale pointers and concurrent close are outside this local C contract.
Null handles reject. Close consumes the handle even on cleanup error; Python
invalidates it before close and prevents later use. Partial open frees buffers
and returns null output on error. Failed batches have no usable mask; acceptance
and unfinished work are unknown. This is not a hostile-C-call sandbox.

Owned host matrix8*n*m bytes; fixed host patterns42*16 bytes maximum. CUDA owns
matrix8*n*m, exactly pattern_count*16 bytes and width mask bytes. No candidate
table or dense device vectors. Explicit H2D matrix+patterns and D2H masks are
counted. Debug support readback is separate and excluded from measurements.
CPU and CUDA share C++ pattern/unrank/screen helpers, so independent Python full
ordered-domain/full-mask and Rust proof/prefix audits are mandatory.

Every session is fresh; close always runs. A successful FFI completion is paid
even if its mask is corrupt or host materialization fails. Report completed
mask progress separately from validated masks; corrupt/failed chunk acceptance
and in-flight work may be unknown, never invented as zero. Cleanup errors cannot
produce success or replace the original failure. No silent CPU fallback.

## Frozen study and timers

Profiles(7,1,5,8),(17,2,12,12),(257,2,16,12),(65521,64,16,12); seed labels
2026100923/2026100924/2026100925 SHA256 over ASCII version/profile/label. Bounds1/2;
chunk widths31/256/4096; candidate caps4096/20000; proofcap32; three repetitions.
This gives144 seeded cases. Include zero,triple-only,nonunit-only,scalar-copy,
singleton and maximum-shape late-witness fixtures: both bounds,widths7/4096,
caps4096/20000,proofcaps1/256 ->96 fixture cases. Total240 paired cases,
1440 measured backend attempts. Deterministically alternate backend order by
case/repetition. Retain every empty/censored outcome and every positive sample.

ASCII label: `matched-coefficients-v1/q/n/m/B2/seed_label`, decimal slash-separated
integers with no newline; SHA256 seeds SIS1 SHAKE. Expansion order is profiles,
seeds,bound,width,cap; then listed fixtures,bound,width,cap,proofcap. CPU first iff
(case_index+repetition)%2==0. Fixture matrices/profiles reuse frozen definitions
in native_coefficient_survey.comparison_cases and native_coefficient_checks.late_fixture;
full matrices remain in raw data. Complete order audits cross m1..16,
B2(1,2,3,4,5,8,9,12),bounds1/2 at q17. Full masks cover every row in fields
q2/3,m3,B2(1,3),bounds1/2, all five fixtures and the complete late family.
Independent tiny Cartesian sets corroborate order. Rust reconciles returned
proofs at configured caps; its sequential screened count cannot exceed the paid
chunk prefix. Complete mask audits cover negative and discarded verdicts too.

Common timer begins before Python validation/domain setup and includes host
ctypes matrix packing, fresh FFI session/pattern construction, CPU host copy or
CUDA allocation/H2D, completed chunk masks, host census/materialization, FFI
close, result ledger. GPU D2H synchronizes completion. Dense Python/Rust audits
occur outside timed calls and are separately recorded. First library load,
first CPU/GPU probe, full audits, builds and challenge generation are recorded
separately. Ratios use paired identical-scope samples, not prior process timings.
CPU is scalar, not optimized SIMD/multicore; clocks and other workloads are not
isolated. No portable performance/energy/ASIC/security/chainwork inference.

Input/profile/boolean-mask validation, domain/ctypes setup and host ledgers are
inside both paths. Independent dense/full-mask/Rust audits remain outside.
Scheduled row/term slots are upper-bound inventories, not actual early-rejected
products or instructions. Actual explicit bytes cover matrix/pattern H2D and
masks D2H only, excluding runtime overhead. Failed ledgers distinguish completed
and validated chunks. Each elapsed sample must be positive; publish paired ratios
only after both paths and all audits pass. Any later failure suppresses all
success summaries and ratios.

## Evidence lifecycle

Invalidate success before build; freeze source manifest, Cargo-selected release
sis-coeff/sis-verify, CUDA source/compiler flags/library metadata and exact
pre-build snapshot. Verify snapshots/artifact hashes before and after study.
Bind exact UTF8/LF raw digest. Failed reports preserve completed/partial pairs,
unknown current work and no success ratios. Local standard-library check gate
uses fake FFI for lifecycle; the explicit local hardware survey exercises actual
CPU/CUDA and malformed C inputs. No new dependency, cloud or GitHub Actions.

Durable append-only progress records are written outside the common timer.
Each opened pair, pending search and returned output is journaled with flush/fsync;
parent interruption recovery accepts only the same source/version header and
bounded journal. The interrupted final append and work after the last durable
event remain unknown. Completed outputs retained after interruption have not
necessarily passed every later audit; failed evidence never upgrades them to
successful pairs/performance claims. No durable event can describe work that
was killed before its acknowledgement was saved.
