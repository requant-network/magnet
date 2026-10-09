# Paid unit-sparse candidate search on CMP 50HX

Date: 2026-10-09. Bounded research acquisition, not production block mining.

## Result

CUDA now generates and screens its own candidate vectors. It is no longer
limited to verifying CPU-supplied solutions. Forty-two paired cases, or 84
CPU/CUDA attempts, all complete with equal ordered outputs, stop reasons,
completeness flags and common component ledgers. Independent Rust verification
accepts all 736 returned-proof occurrences from both backends.

This first prototype does **not** demonstrate a speed advantage. Recorded search
time totals are approximately 7.30 seconds for CUDA and 3.22 seconds for the
reference Python baseline in this run. These are descriptive mixed-size timings,
not an isolated benchmark, optimized native CPU comparison or mining hashrate.

See [implementation](../../reference/gpu_search.py),
[contract 17](../../spec/17-unit-sparse-gpu-search-v1.md) and
[committed results](results/gpu-unit-sparse-search-v1.json). Raw matrices, jobs,
outputs and ledgers remain in `artifacts/gpu-unit-sparse-search-v1.json`.

## Candidate domain and paid search

Enumerate canonical positive singleton units, then lexicographic pairs of
coordinates i<j with coefficients `(1,1)` followed by `(1,-1)`. For B2=1 there
are m candidates; otherwise there are m^2. This is a finite support<=2,
unit-coefficient domain. It does not search all short vectors for general B2.
Distinct integer vectors can share modular acceptance events, especially q=2.

The independent Python baseline uses itertools. CUDA constructs ordinals,
triangular support prefixes, pair indices and dense vectors on-device. A matrix
is transferred once per search. Exact int64 products, sums and modular reduction
then screen each vector; no CPU solution list feeds this acquisition path.
The CPU/CUDA comparison and full-domain audits happen separately from acquisition.

Candidate, proof and batch caps are strict and bounded. A final candidate chunk
is truncated to the remaining candidate budget. When the proof cap fires inside
a chunk, every generated/screened candidate in that chunk is still charged,
including accepted vectors discarded from the returned prefix. An exactly
sufficient candidate cap allows domain-exhausted; proof-limit has precedence.
Completeness flags distinguish checked domain from actually returned full proof set.

## Schedule

Seeds are 2026100907 and 2026100908, with shuffled order seed 2026100909.

There are ten fresh deterministic challenge matrices across five profiles:
`(q,n,m,B2)` = `(2,1,4,2)`, `(7,1,8,2)`, `(17,2,16,2)`, `(257,3,32,2)` and
`(65521,4,128,2)`. Each has three settings: full candidate allowance with
batch width 64 or 256, or candidate cap 13 / proof cap 3 / batch width 7.
This gives 30 seeded paired cases, repeating each challenge across settings.

Twelve further paired cases use six explicit zero/identity boundary fixtures,
with two cap settings each. They include B2=1, m=1, q=2 and the maximum n/m
shape. Fixtures test correctness and truncation; they are not random mining
challenges or evidence of production difficulty.

Per backend, there are 368 returned proof occurrences: 79 from seeded cases
and 289 from boundary fixtures. Repeated settings/backend observations are not
distinct proofs or independently solved SIS challenges. The higher-field seeded
profiles return no proofs in this finite domain; this does not establish
hardness for broader search. Proof-limit/candidate-limit completions do not
certify unsolvability even within the unchecked part of this domain.

## Accounting and independent checks

| Completed component | Python | CUDA |
|---|---:|---:|
| Generated and screened candidates | 71424 | 71424 |
| Materialized vector entries | 8577100 | 8577100 |
| Scheduled dense matrix-grid slots | 36154504 | 36154504 |
| Search setup matrix entries | 20344 | 20344 |
| Processed chunks | 732 | 732 |
| Accepted vectors seen, including discarded tails | 391 | 391 |
| Returned vector occurrences | 368 | 368 |
| Device support-prefix entries | 0 | 1414 |
| Explicit tensor H2D payload bytes | 0 | 162752 |
| Explicit tensor D2H payload bytes | 0 | 279792 |

Both backends stop 27 times on domain exhaustion, eight on proof limits and
seven on truncating candidate limits. Accepted-but-discarded tails account for
the difference between 391 seen and 368 returned.

Matrix-grid slots describe a dense schedule; Python verification can
short-circuit failed rows, so these are not executed CPU multiplication counts.
Explicit transfer bytes count matrix tensors, first-ordinal/count scalar reads
and returned vector tensors. They exclude implicit CUDA synchronization,
dynamic-shape metadata, command traffic and allocator operations. They do not
measure actual PCIe traffic or establish a universal work weight.

Twenty-one separate full-domain audits compare every generated GPU vector to
the independent host ordering, including ordinals beyond a capped search's
prefix. They cover 53260 candidate occurrences over domain/width combinations
and preserve ordered-vector hashes. Audits do not provide candidates to search
or count as paid acquisition. Tiny complete cases additionally compare accepted
sets against an exhaustive {-1,0,1} oracle. Every returned CPU and CUDA proof is
checked by the independently built native Rust verifier outside the search.

All source hashes were unchanged during the experiment, and the same snapshot
passes the local gate: 223 Python tests, 19 Rust tests, rustfmt/clippy and all
existing differential corpora. Tests cover complete domain/order, proof-tail
charges, exact boundary precedence, malformed caps, failed proposals and
comparison refusal for altered outputs/counters. Native binary fingerprints
are checked before publication; failed studies retain incomplete markers.

## Runtime scope and limitations

The run uses existing PyTorch 2.14.0+cu130 / CUDA 13.0 on CMP 50HX capability 7.5.
Observed allocator peaks are 4360704 allocated bytes and 23068672 reserved bytes.
The conservative 64 MiB logical tensor allowance excludes context, cache and
runtime overhead and is not an externally enforced GPU-memory ceiling.

Search timers include host validation, runtime/setup, candidate construction,
screening, explicit transfers and synchronized output. Seeded/fixture matrix
generation is recorded separately, totaling approximately 1.49 ms in the
completed schedule; native/domain audits are also separate. Caps bound logical
operations, not an externally enforced wall-time/energy budget. A runtime failure
invalidates the whole study rather than being recorded as a zero-cost search.

The miner container was stopped under the owner's standing authorization and
was exited at the first post-run inspection. A later inspection found it running
again, alongside other miner containers and a resident ComfyUI process. The
restart mechanism was not investigated; no exclusive GPU window or isolated
performance is claimed. The ordinary
local checks also ran on the development host while the Linux survey executed.
No dependency installation, GitHub Actions or paid compute was used.

## Next step

The dense proof-of-correctness kernel materializes whole vectors and evaluates
zero-coordinate products. Replace it with direct column addition/subtraction for
the support<=2 domain, materialize only returned vectors, and reduce launch/scalar
synchronization overhead. Compare that implementation against this audited domain
before extending coefficient ranges or evaluating stronger native CPU competition.

Keep acquisition, generation, preprocessing, unsuccessful attempts and transfers
visible. GPU work does not select chainwork, retarget or monetary parameters;
portable adversarial cost and production hardness remain open questions.
