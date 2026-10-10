# Local GPU readiness and first experiments

Date: 2026-10-09. Planning and read-only inventory; no GPU miner implemented.

Update: verification, acquisition and matched small-coefficient CPU/CUDA pilots
have now executed; see [verification](gpu-verification-v1.md),
[acquisition](gpu-unit-sparse-search-v1.md) and
[matched comparison](matched-coefficients-v1.md). The stage descriptions below
retain the original plan. The matched pilot shows no GPU advantage for its
small sparse family. The inventory records the earlier discovery.

## Verified host capability

An existing authorized SSH connection to the local Linux research host was
tested. Credentials, host addresses and access-file contents are intentionally
outside this repository. No packages, services or mining configuration changed.

| Item | Observed value |
|---|---|
| GPU | NVIDIA CMP 50HX |
| Reported device memory | 20480 MiB |
| Compute capability | 7.5 |
| Driver | 610.43.03 |
| Existing PyTorch | 2.14.0+cu130 |
| PyTorch CUDA runtime | 13.0 |
| CUDA availability | true; device identity matches CMP 50HX |
| Existing nvcc | CUDA 13.3, V13.3.73 |
| Utilization at inspection | 100%; an existing cppminer workload was running |

These queries establish discovery/runtime readiness, not successful execution
of our arithmetic kernels or a performance result. The existing isolated
PyTorch environment is available; installation is not a prerequisite for a
first small experiment. Toolchain acceptance of the target architecture must
still be tested for any compiled CUDA kernel.

## Stage 1: exact batched verification

Implement a research-only GPU adapter for batched `A*x mod q == 0`, with integer
arithmetic and explicit shape/type/resource limits. CPU checks must first reject
invalid encodings, zero/noncanonical vectors and excessive norms. Verification
is only one component; it is not a GPU search algorithm.

Use int64 accumulation. With existing profile bounds `q <= 65521`, `m <= 128`
and `B2 < q^2`, each admitted coordinate has magnitude at most 65520, and the
absolute sum of 128 products is below `128 * 65520^2`, comfortably within int64.
Int32 accumulation is insufficient. Norm checks on arbitrary raw inputs must
use overflow-safe host integers before GPU transfer; a permissive raw int64
sum of squares is not a safe input validator.

Compare every GPU verdict to both the exact Python verifier and independent
Rust SIS1 verifier. Include valid/invalid toy solutions, all-zero input, sign and
norm boundaries, modular wrap, rank-deficient matrices, maximum allowed values,
malformed dimensions and batches that exceed the declared memory cap. Freeze
seeds, source hashes, software versions and expected outputs. First prove that
the device kernel executes and agrees exactly; do not infer hashrate from it.

## Stage 2: paid candidate screening

Extend to batched sparse/finite candidate generation, validity screening and
deduplicated canonical outputs. Count candidate proposals, transferred bytes,
matrix generation, preprocessing, verification, scoring and failed attempts.
Keep host/device synchronization, startup and allocation within explicit scopes.
GPU screening must acquire its own candidates rather than consume a free CPU
oracle's solutions in a claimed mining comparison.

Initially keep LLL/BKZ acquisition on CPU. This allows CPU reduction plus GPU
screening and independent CPU/GPU enumeration variants to be compared without
pretending that all solver families parallelize alike. Matrix expansion and
score kernels can be separate later stages with their own cross-language vectors.

## Stage 3: meaningful comparison

Only compare speed or energy in an agreed free GPU window, with the background
miner managed by its owner. Until then, small bounded correctness probes may be
possible, but utilization, contention and timing must be disclosed; no isolated
speed advantage can be claimed. Do not stop or reconfigure unrelated workloads
as part of a readiness check.

Repeat equal-paid-scope CPU/GPU workloads across seeds, include unsuccessful and
interrupted runs, disclose cold/warm setup and batch sizes, and measure device
memory/process resources. Observe power only if a suitable meter/telemetry
exists; avoid invented energy estimates. Larger dimensions and stronger CPU
baselines are needed before discussing hardware advantage or work calibration.

## Scope

Owner update (2026-10-10): the GPU is reserved for other work. Do not use it,
stop its miner or run GPU experiments until the owner explicitly releases it.
Current B-H candidate checks run locally on CPU without contacting that server.

This work broadens research options. It selects no GPU requirement for users,
no ASIC-resistance claim, no production consensus and no token economics.
Repository tests and experiments remain local, without GitHub Actions or paid
GPU services. The existing MagnetGate deployment is unaffected.

## CPPminer reuse and integer Tensor Core hypothesis (2026-10-10)

This is a parked D5 implementation option requested by the owner, not a new
solver, completed integration or a change to the decisive D3/D4 ordering.
The [owner's CPPminer fork](https://github.com/danifest751/CPPminer) already
documents packed INT8 Tensor Core paths for Turing and newer NVIDIA devices.
The locally indexed checkout `C:/Projects/ArmCompute/pearl/CPPminer` on
`feat/abacus-backend` was inspected at `e6d3492`; it contains
`cp_turing_period_batch`, `cp_turing_pack` and architecture dispatch. It also has
untracked ongoing work; this research batch did not modify that checkout.

Owner instruction: any CPPminer implementation for this project starts in a
separate checkout on a new branch based on `release/fork` from the owner's fork.
Do not use `feat/abacus-backend` as the implementation base or alter its pending
work. Record the exact base commit before adding an opt-in offline SIS target.

Reuse the device/runtime handling, packing/tiling experience and test harness
patterns. Do not call the complete Pearl kernel as a SIS engine: its K dimension,
cumulative milestones, hash tiles and jackpot predicate belong to Pearl. An
opt-in offline SIS benchmark executable in a separate checkout is the preferred
first integration. It accepts frozen jobs and caps, generates its own candidate
stream, returns canonical vectors/masks and component counts, and sends no pool
shares. Recheck outputs with the existing independent Rust admission/derivation
tools. Final miner dispatch/network integration waits for a selected work rule.

The accelerated expression would be `Y = A * Z`, with candidates as columns of
Z; the predicate is every required residue `Y[row,column] mod q == 0`. Turing
supports INT8 products with INT32 accumulation, as described by
[NVIDIA](https://docs.nvidia.com/cuda/turing-tuning-guide/index.html#tensor-core-operations).
This gives a plausible exact integer path; it does not accelerate SIS solution
acquisition automatically. A small sparse candidate may need only1..3 column
products and early row rejection, so dense tile padding/packing can cost more
than ordinary CUDA integer arithmetic. Compare against the existing native CPU
and sparse CUDA engines, not only Python. Keep LLL/BKZ preprocessing separate.

For the current q17, coefficients +/-1/+/-2, m16 profile, both inputs fit signed
INT8 and the dense sum bound16*16*2=512 excludes INT32 overflow. Larger existing
profiles do not fit one such multiply. One exact exploratory decomposition is
base128: unsigned residue a in0..65520 uses three digits in0..127; the magnitude
of x in0..65520 uses three such digits, with its sign applied to every digit.
Compute up to nine signed-INT8 dot products and reconstruct in INT64 before
modular reduction. With m<=128, each partial dot has absolute value at most
128*127^2=2064512, below INT32 limits; the reconstruction also stays within INT64
under these profile bounds. This arithmetic argument does not test device
instructions, prove speedup or cover malformed inputs before host validation.
Small coefficients need fewer digit passes; modular wrap and all boundary cases
still require independent checks. Do not silently round inputs or switch the
consensus profile to fit INT8. Approximate FP16/TF32 is not a default verifier.

Before a D5 implementation, freeze the same candidate order, caps, proof output,
matrix generation, rejected/partial work and timer scope across native CPU,
CUDA integer and Tensor Core engines. Include packing/transfers, tail tiles,
device synchronization and job changes in a declared host scope; report cold
startup separately from steady-state. Measure energy only with disclosed actual
telemetry. An INT8 device self-test and proof recheck precede every comparative
claim. Adopt the Tensor path only if the complete matched workload benefits;
otherwise retain the sparse kernel. No hashrate estimate is inferred from
CPPminer's Pearl TMAC/s figures.
