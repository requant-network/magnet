# Exact CUDA verification on CMP 50HX

Date: 2026-10-09. First executed GPU correctness stage; not a GPU miner.

## Result

The optional CUDA adapter executed exact int64 SIS modular products on the local
NVIDIA CMP 50HX. Across 731 cases, the complete pipeline agrees with the existing
exact Python verifier and independently built Rust verifier, with zero mismatches.
Of these cases, 470 actually reach CUDA: 228 are accepted and 242 fail the modular
equations. The other 261 are rejected by host encoding/sign/norm checks. Reporting
all 731 as device comparisons would overstate GPU coverage.

Rust handles 730 bounded frames with matching verdicts. The remaining case is
an oversized transport frame, checked separately for nonzero-exit rejection.
It still receives a false verdict in the Python/CUDA-adapter pipeline.

The implementation is [reference/gpu_verify.py](../../reference/gpu_verify.py),
with [contract 16](../../spec/16-gpu-verification-lab-v1.md). The
[compact result](results/gpu-verification-v1.json) commits seeds, corpus hash,
source hashes, native binary hash and device/runtime metadata. The raw packet
and verdict transcript is retained locally under `artifacts/gpu-verification-v1.json`.

## Arithmetic and resource scope

The host decodes SIS1 packets and validates prime-field profile bounds, canonical
residues, signed-int32 coordinate shape, positive first nonzero coordinate and
the squared norm using exact Python integers. Arbitrary raw input is not fed
into a GPU sum of squares, which could overflow before rejection.

Admitted cases are grouped by q/n/m and processed in chunks of at most 32.
CUDA tensors, multiplication, sum and modular reduction use int64 throughout.
Under `q <= 65521`, `m <= 128`, `B2 < q^2`, each admitted coordinate has magnitude
at most 65520. Dot-product magnitudes are at most `128 * 65520^2`, below int64's
limit. The kernel uses elementwise integer products and reduction, without
floating-point arithmetic or integer matrix-multiplication assumptions.

A request has 1–256 packets and a bounded aggregate input byte allowance.
Conservative logical live tensors are capped at 64 MiB, but CUDA context,
runtime and cached allocator overhead are additional. Observed peak tensors
are 4243456 allocated bytes and 23068672 reserved bytes; these are PyTorch
allocator metrics, not total device usage or an externally enforced ceiling.
CUDA unavailability or kernel failure propagates; CPU fallback is refused.

## Corpus and provenance

Seed 2026100906 generates valid correlated-column witnesses, modularly invalid
short vectors and random vectors across six profiles, including q=2 and the
maximum q/n/m profile. Boundary fixtures exercise zero/noncanonical signs,
norm limits, signed-int32 extremes, maximum residues, modular wrap, malformed
profile/residue fields, truncated/trailing bytes and oversized frames. A further
128 seeded packet mutations broaden rejection coverage.

The framed-corpus SHA-256 is recorded with all 731 packet bytes in the raw
transcript. All source/specification fingerprints were unchanged during the
run and match the local source snapshot. The Rust verifier was built offline
in release mode from copied research sources on the Linux host. No repository
keys or credentials were copied. Its binary fingerprint is checked at entry
and again by the publication helper after metadata collection, before writing
passed evidence. A regression test replaces the binary during metadata collection
and requires the running-or-incomplete markers to remain.

| Runtime | Observed value |
|---|---|
| Device | NVIDIA CMP 50HX, compute capability 7.5, 20480 MiB |
| Driver | 610.43.03 |
| PyTorch / CUDA runtime | 2.14.0+cu130 / 13.0 |
| Python | 3.12.3 on Linux |
| Rust | 1.98.1, offline release build |

The existing miner container was stopped with the owner's authorization for
GPU work and preserved for restart. On inspection after the break it was running
again. No isolated timing comparison is claimed, and no automatic restart cause
has been established. The pre-existing ComfyUI process was not reconfigured.
No packages, paid GPU services or GitHub Actions were needed.

## Reproduce on a CUDA host

Use an existing compatible CUDA/PyTorch environment and installed Rust toolchain:

```sh
cargo build --release --offline --locked --bin sis-verify
python scripts/gpu_verify_survey.py --native target/release/sis-verify
```

On the ordinary Windows development host, `python scripts/check.py` remains
dependency-free with respect to PyTorch. It passes 214 Python tests, 19 Rust
tests, rustfmt/clippy and all existing differential corpora. The explicit Linux
CUDA survey exercises the real optional runtime separately. Host safety tests
alone are not GPU execution evidence.

## What is next

Verification is now available as a GPU component. It does not acquire solutions,
generate MGH1 matrices on GPU, implement a score kernel or admit blockchain
blocks. It therefore establishes neither mining speed nor a GPU requirement.

Next implement bounded candidate generation and screening that pays for its
own acquisition, with CPU/Rust output-set comparisons and explicit host/device
transfer, setup and failed-attempt accounting. Keep LLL/BKZ on CPU initially.
Only after correctness and equal-scope search should isolated CPU/GPU speed or
energy comparisons be considered. Production work, chainwork and retarget
remain open; see the [hardware roadmap](gpu-readiness-v1.md).
