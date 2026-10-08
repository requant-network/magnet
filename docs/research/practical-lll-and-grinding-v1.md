# Practical LLL and paid header-selection study

This milestone adds a **pinned optional native FLINT LLL backend** and studies
nonce, timestamp and payload selection with a common research score threshold.
Both remain SIS laboratory tools, not a selected network work function.

See [interfaces](../../spec/05-practical-lll-and-grinding-v1.md),
[FLINT evidence](results/flint-v1.json), [grinding evidence](results/grinding-v1.json)
and [ADR 0006](../decisions/0006-practical-solvers-and-grinding.md).

## Reproduce on the measured Windows environment

~~~powershell
python scripts/check.py
python -m venv artifacts/flint-env
artifacts/flint-env/Scripts/python.exe -m pip install --only-binary=:all: --no-deps --require-hashes -r benchmarks/flint-win.lock
python scripts/flint_survey.py --python artifacts/flint-env/Scripts/python.exe
python scripts/grinding_survey.py
~~~

Only the explicitly invoked practical survey needs this package; the ordinary
check gate and Rust verification have no added dependencies. Nothing modifies
system Python or MagnetGate. The lock pins python-flint 0.9.0's Windows ABI3
wheel; the measured wheel bundles FLINT 3.6.0, GMP 6.3.0 and MPFR 4.2.2. Runtime
requires version 0.9.0 and records installed native/library/license hashes plus
worker interpreter identity. Hash-pinned installation is provenance, not runtime
wheel authentication. Other environments require their own pins and checks.

The wrapper's API is documented by the
[python-flint project](https://python-flint.readthedocs.io/en/latest/fmpz_mat.html#flint.fmpz_mat.lll).
Wheel license metadata is preserved in the evidence: MIT wrapper, LGPL libraries
and compiler/runtime license components. Binaries/licenses remain in the isolated
environment; this repo distributes our adapter and evidence, not the wheel.

Both outputs of each survey are invalidated before the build. Failure, timeout or
audit rejection leaves running-or-incomplete. Raw ignored reports retain complete
certificates/probes, header bytes, policy traces and hit packets. Committed compact
reports retain source/config/backend/executable hashes, seed schedules, counts,
conditional denominators and proof digests. GitHub Actions were not used.

## Practical LLL method and result

Reuse all **1100** previous lattice-study seed/profile pairs, add **100** matrices
(25 each at 257,3,14,12; 65521,4,16,8; 257,4,16,8; 32771,4,12,8), and explicitly
repeat the frozen exact-reference miss as a labelled regression. Thus **1201
records**, not 1201 new or necessarily distinct instances.

Three native reductions per record request integer B and U at delta=0.75,
eta=0.5. Every one passes the unchanged independent exact audit: full kernel
index, membership, unimodularity, B=U*B0 and reduced inequalities. Internal
approximate arithmetic does not replace these checks. Probe reduced rows and the
same bounded two-row combinations. Independently verify the unique native MITM
oracle output and require complete enumeration before counting availability.

All **1201** oracles complete: **468** records have a solution, **733** do not.
The FLINT row/pair probe finds a vector in **all 468 solvable records** in this
run. Reduced bases do not change across the three repeats. Success/miss counts
use repeat one; repeats are not independent matrices. The frozen miss produces
one FLINT probe vector while the exact-reference probe still misses it.

This does **not** make the finite probe a complete algorithm or overturn the
previous counterexample. Different valid LLL bases can expose different vectors.
The 37 exact-reference comparisons are 36 shared native inputs plus the frozen
case; their no-vector counts must be interpreted with oracle availability.

Timers separate exact RREF kernel construction, native matrix allocation/LLL/
conversion, and Python probe validation/deduplication. The worker core timer
excludes import, warmup, IPC and parent-side certificate audit. Aggregate worker
process time includes import/warmup/IPC/worker metadata, but excludes input
serialization and parent-side audit. Exact-reference timing includes its own
construction; native MITM measures complete enumeration with a different goal.
Therefore these are not a fair mining-speed ranking. Recorded local times and
profile medians are in the compact report; no energy, RSS or GPU result is claimed.

## Header selection method

Four toy profiles, two deterministic base batches, three fields, 64 headers per
family: **24 families / 1536 header occurrences**, **1520 distinct headers**.
Each batch shares its base header across the three fields. Nonce/time add index;
payload variants use the domain-separated hash specified in spec/05. Payload/time
semantics are deliberately not enforced, so arbitrary variants are not a claim
of future valid blocks. No joint field search or FLINT-based grinding is measured.

The external score predicate hashes the complete bound proof packet and compares
strictly to **2^256/16**. The target is a lab choice, not a difficulty selection.
Run unit screening, first-solution search, all-valid-vector scoring and paid
fixed-vector reuse independently. Each actually derives matrices, checks vectors
and hashes accepted proofs; no policy receives the complete availability oracle.
All stop at their first hit. Reuse pays failed acquisition and scores its initial
vector, then rechecks that same vector against each subsequent matrix.

Separately, native MITM exhausts every family header and provides an audited
availability/ideal-score inventory. It observes **580** occurrences with a solution
and **145** with at least one eligible score. That is oracle lookahead used only
to assess policy coverage; it is not free information supplied to a miner.

| Policy | Successful families / 24 | Processed headers | Vector checks | Score hashes |
|---|---:|---:|---:|---:|
| Unit vector | 2 | 1521 | 1521 | 55 |
| First solution | 10 | 1085 | 100661 | 235 |
| All accepted vectors | 12 | 953 | 105303 | 236 |
| Paid acquisition then fixed reuse | 3 | 1419 | 66944 | 59 |

No proposal cap is reached in this run. Totals include unsuccessful families and
early stop at hits. They are repeated policy trials over overlapping families,
not unique independent proofs or exchangeable work units. `family-exhausted`
does not mean the header family has no valid solution or score hit.

`headers_processed` counts actual matrix derivations; family construction and
payload-variant hashes precede policy timing. Canonical-domain preparation is
inside first/all/reuse timing but separately counted, not in vector checks.
Matrix-entry counts describe accepted output entries, not rejection draws/XOF
operations. Policy timers include generation, preparation, verification and
scoring in Python; they exclude availability/native audits. All **27 policy hits**
pass Rust's bound SIS verifier and Python's strict score predicate. Rust does not
implement the new score predicate. Complete audit scoring costs are recorded
separately from policy score hashes; no allocation/energy measurement is made.

## Consequences

The optimized backend is a stronger practical baseline than the deliberately
transparent exact-rational reducer. Its success on this set cannot define SIS
hardness. Header selection and within-instance multiple proofs produce competing
cost distributions; one accepted score cannot be priced as a universal fresh SIS
solve. Candidate profiles still contain many empty instances and occasional
cheap vectors. None is selected for deployment.

Next compare stronger lattice/search methods and combined selection policies
under explicit cost models, then propose a candidate only if those models survive
adversarial testing. Block/payload/time rules must make the allowed grinding
surface explicit before difficulty, accumulated chainwork or fork choice.
