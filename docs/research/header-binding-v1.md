# Independent generation and header binding v1

The laboratory can now derive its own SIS instance from a canonical research
header in **both Python and Rust**. The proof carries a header and vector; it
cannot carry a matrix. A separate trusted context fixes network, parent, height
and profile. This closes an implementation gap, **not the SIS-PoW security case**.

See [format and trust boundary](../../spec/04-header-binding-v1.md),
[compact evidence](results/header-binding-v1.json) and
[decision ADR 0005](../decisions/0005-header-binding.md).

## Reproduce locally

~~~sh
python scripts/check.py
python scripts/binding_survey.py
~~~

Cargo builds offline. The survey uses the executable paths reported by its own
builds: debug sis-lab for independent generation/verification, release sis-search
for the previously tested MITM oracle. These are correctness experiments with
**no timing or mining-speed comparison**. No GitHub Actions or paid compute.

Both ignored survey outputs are marked running-or-incomplete before either build.
Only a fully completed run writes passed. Raw artifacts/header-binding-v1.json
retains all header bytes, seeds, matrix hashes, first solutions, proof-set hashes
and probe outcomes. The compact committed summary preserves profile/counts,
deterministic header labels, source/configuration hashes and executable hashes.
The proof-set hash is SHA256 over sorted vectors encoded as concatenated i32-LE;
matrix hashes use row-major u32-LE. They are evidence digests, not network fields.

## Method

Four toy profiles, 256 consecutive nonce values 0..255 each. For each profile,
network/parent/payload are SHA256 of the ASCII label
`magnet-header-binding-v1/q/n/m/b2` followed by `/network`, `/parent`, `/payload`.
Height is 1; opaque timestamp is 20261008. No header is omitted or retried.
The entire canonical header feeds the domain-separated seed derivation.

1. Python derives each seed/matrix; Rust independently derives identical bytes.
2. Prepare the finite coordinate box once per profile and retain nonzero,
   first-positive vectors within B2. Check every retained vector against every
   matrix. No oracle cap is reached. Independently require Rust MITM to exhaust
   its domain and return exactly the same solution set.
3. Test the unit vector e1 on every header: this is a cheap sufficient screen for
   a zero first column, not a complete availability test. A miss proves nothing.
4. Acquire the first accepted vector in lexicographic candidate order from the
   first solvable nonce. Check that fixed vector on every *later* nonce, retaining
   failed attempts. Acquisition accounting includes complete scans of earlier
   empty headers and the successful candidate prefix; generation counts through
   acquisition are separate. The research oracle runs all candidates anyway.
5. Where the preceding nonce has a solution, transplant its first vector to the
   next header. Denominator includes every attempted transplant, even if the next
   header is empty. These first vectors are supplied by the full oracle; this is
   a reuse-validity study, not end-to-end speedup evidence.
6. Rust's context-bound verifier checks all probes and each nonempty instance's
   first oracle solution. Native bound verification totals include duplicate
   vectors across these roles and are not independent work units.

Acquisition is reconstructed logical accounting of a first-match search, not
measured runtime or total survey execution cost. Oracle work counters count vector
checks after norm/sign filtering, not modular
multiply counts or elapsed CPU time. Candidate preparation, matrix generation,
native oracle work, bound verification and acquisition are disclosed separately;
their counts must not be added as equivalent work. Fixed-vector screening still
needs each derived matrix. The study measures nonce families only; timestamp and
payload grinding remain available in the format but are not separately measured.
The Python family matrix-generation count covers each retained instance once;
it excludes additional native mode-2 and proof-verifier generation. These native
calls are counted separately. Repeated seed derivations for evidence are also
outside that family count; no hash-operation or energy accounting is claimed.

## Results from this run

| q,n,m,B2 | Solvable / 256 | Empty | Distinct matrices | Unit screen | Fixed acquired reuse | Adjacent reuse |
|---|---:|---:|---:|---:|---:|---:|
| 7,1,3,8 | 256 | 0 | 183 | 39/256 | 41/255 | 34/255 |
| 17,2,4,8 | 106 | 150 | 256 | 0/256 | 1/250 | 0/105 |
| 17,2,4,3 | 27 | 229 | 256 | 1/256 | 0/249 | 0/26 |
| 257,2,4,8 | 0 | 256 | 256 | 0/256 | 0/0 | 0/0 |

Every profile has 256 distinct 32-byte seeds. The first profile maps them into
only 183 distinct toy matrices; its matrix space is tiny. Seed inequality does
not imply matrix inequality. Accepted transplants likewise do not imply that all
matrices match: a vector can satisfy different matrices.

Totals: **1024 complete oracle instances; 389 solvable, 635 empty; 1872 solution
occurrences; 101888 Python oracle vector checks; 2553 native bound verifications**.
The solution occurrences belong to different headers and may repeat vectors.
Empty counts describe only these sampled headers, not every possible nonce.

| Profile | First acquired nonce | Checks through acquisition | Matrices through acquisition |
|---|---:|---:|---:|
| 7,1,3,8 | 0 | 5 | 1 |
| 17,2,4,8 | 5 | 862 | 6 |
| 17,2,4,3 | 6 | 194 | 7 |
| 257,2,4,8 | none | 40960 | 256 |

The last row charges the entire unsuccessful acquisition attempt; no free initial
solution is assumed for fixed-vector reuse. General optimal screening, successful
score trials, solver races, preprocessing and optimized lattice reduction are
outside this measurement.

## Verification and interpretation

The local check corpus includes independent SHAKE absorb/squeeze rate boundaries,
maximum input/output, q=32771 rejection sampling, maximum matrix dimensions,
header-field mutations, fixed binary fixtures, context mismatches, norm/sign
rejections, malformed profiles, truncations and supplied-matrix packet rejection.
The current exact counts are in docs/STATUS.md and ignored artifacts/local-checks.json.

Do not price a proof as a fresh solve merely because its header is committed.
Changing nonce offers new availability trials; reusing a known vector can succeed
on other matrices. Conversely, a valid header can yield an empty search space.
There is no selected difficulty, accumulated work, retarget or fork choice. The
handwritten Rust XOF is tested and source-reviewed, not certified. These toy
parameters are unsuitable for deployment.
