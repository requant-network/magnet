# Optional practical LLL and header-selection laboratory v1

Neither interface selects consensus, difficulty or chainwork. Supplied-A SIS1
and bound MGH1 proof validity remain unchanged.

## Optional FLINT boundary

The ordinary `python scripts/check.py` uses standard libraries and offline Cargo.
Native LLL experiments additionally use an **isolated** python-flint 0.9.0
interpreter. `benchmarks/flint-win.lock` pins the Windows x86_64 CPython ABI3 wheel
hash. Install explicitly with pip `--only-binary=:all: --no-deps --require-hashes`.
There is no automatic installation, fallback solver or network consensus dependency.
Different platforms need a separately documented/pinned environment.

Worker stdin is one JSON object, at most 1 MiB, keys exactly `version,cases`.
Version MFL1; 1..100 cases, each exactly `profile,matrix`. Profile fields are
q,n,m,b2 from SIS-LAB. Validate canonical residues/shape before backend import;
m <=16. Build the full integer modular kernel using the existing exact RREF.
Run native LLL with delta=0.75, eta=0.5, integer-basis representation and approximate
internal Gram arithmetic, requesting its integer transformation U. These are
exactly representable parameter values, not a general floating-point guarantee.

Output is JSON MFR1 with backend metadata and one result per input, in order.
Each result carries initial basis, reduced basis, U, rank, completed status and
construction/reduction timers. Worker-produced basis/U entries are limited to
256 bits; arithmetic exhaustion is fatal. The client caps output encoding at
8 MiB and uses a 60-second process timeout. Input/output bounds are local protocol
limits; output capture/checking and the backend's transient allocations do not
constitute OS RAM limits. Controlled worker code must not be replaced with an
untrusted process. Timeout/failure/audit rejection leaves the survey incomplete.

The **unchanged independent exact audit** checks lattice index q^rank, initial
membership, unimodularity, B=U*B0 and all delta=3/4, eta=1/2 reduced inequalities.
A backend's status alone never proves reducedness. Each repeated result is audited.
The same finite row/pair probe tests SIS vectors; it is not complete SVP/SIS.

Backend metadata records installed native-file/license hashes, package version
and worker interpreter/platform. Runtime enforces package version. The wheel hash
pins installation provenance; installed binary hashes are evidence, not runtime
authentication against that wheel. No binaries are distributed in Git.

API reference: [python-flint fmpz_mat.lll](https://python-flint.readthedocs.io/en/latest/fmpz_mat.html#flint.fmpz_mat.lll).
The wheel metadata preserves MIT wrapper, FLINT/GMP/MPFR copyleft and compiler
runtime licensing; see the report for the recorded license expression. This
research separation makes no legal claim about a future distribution.

## Research score and header families

MGH1 is unchanged. An external lab predicate uses:

~~~text
digest = SHA256(b"MagnetNetwork/SIS-LAB/grinding-score/v1\0" || MGH1_proof)
hit = valid_bound_proof AND big_endian_integer(digest) < trusted_lab_target
~~~

Target is an exact integer 0..2^256, separately chosen by the researcher. Zero
accepts no score; 2^256 accepts every valid proof. It is not encoded in MGH1, used
by Rust's bound verifier, or adopted as network work/difficulty. Invalid SIS does
not become acceptable merely because its score hash meets target.

Families contain 1..512 headers, with unchanged trusted context. Index 0 is the
base header. Nonce/time variants add index to the base u64 value (reject overflow).
Payload variants for index>0 use SHA256 of
`b"MagnetNetwork/SIS-LAB/payload-grind/v1\0" || base_payload || u64_LE(index)`.
Payloads are opaque commitments; these variants do not construct valid payload
bodies or enforce future timestamp rules. They are sensitivity experiments.

## Bounded policies

All stop at the first score hit or explicit proposal ceiling (1..100000). Check
the ceiling before generating another header and before another vector check.
Canonical norm candidates are prepared once per policy run from a box capped
at 100000. Matrix generation, unsuccessful candidates and acquisition all count.

| Policy | Action on each new header |
|---|---|
| unit | Check e1, then score only if valid |
| first | Search lexicographically for the first valid vector; score it once |
| all | Continue scoring valid candidates until a hit or full domain traversal |
| reuse | Search until the first acquisition; thereafter check/score only that fixed vector |

First/reuse move to the next header after an unsuccessful hash; all continues on
the same instance. Reuse includes the acquisition hash attempt itself and all
earlier empty headers. `family-exhausted` only describes policy exhaustion, never
general absence of solutions or score hits. A cap yields `proposal-limit`;
neither capped result nor a cheap screen certifies nonexistence.

Counters separately report processed headers (matrix derivations), expanded entries, vector checks,
score hashes/input bytes, and candidate preparation. Acquisition records a
snapshot through the first successful vector (before its score); all-run totals
include later/unsuccessful work. These count instrumented operations rather than
hardware instructions, energy or comparable consensus weight. A transcript hash
commits the ordered scored messages; retain first eight score samples and any hit.
Header-family construction and payload-variant hashes occur before the timed
policy call. Domain preparation occurs inside it and is counted separately from
vector checks. Matrix-entry counts cover output entries, not XOF bytes/draws.
