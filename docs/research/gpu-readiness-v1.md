# Local GPU readiness and first experiments

Date: 2026-10-09. Planning and read-only inventory; no GPU miner implemented.

Update: [stage 1 has now executed on CMP 50HX](gpu-verification-v1.md), with
exact host/CUDA/Rust agreement. The inventory below records the earlier discovery;
candidate search and performance stages remain future work.

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

This work broadens research options. It selects no GPU requirement for users,
no ASIC-resistance claim, no production consensus and no token economics.
Repository tests and experiments remain local, without GitHub Actions or paid
GPU services. The existing MagnetGate deployment is unaffected.
