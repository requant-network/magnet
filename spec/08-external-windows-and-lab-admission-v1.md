# External resource windows and trusted laboratory admission v1

Status: implemented local experiment interfaces. No block consensus or network
difficulty is selected. This extends specs 04, 05 and 07 without changing their
header encoding, score hash or policy algorithms.

## 1. Windows resource boundary

`scripts.windows_job.run_job(command, cwd=..., wall_ms=..., memory_mib=...)`
requires Windows Job Objects. Other platforms fail explicitly; there is no
cooperative fallback. Exact integer bounds are 10–30000 ms and 16–512 MiB;
booleans are rejected. Commands have 1–16 nonempty NUL-free string arguments and
must fit the Windows command-line limit. The selected executable and environment
are trusted local configuration, not a public process-launch API.

Before the worker runs, the parent creates an unnamed Job with process and job
commit ceilings plus kill-on-close. It creates the process suspended and hidden,
assigns the process to the Job, then resumes its main thread. Assignment failure
terminates the still-suspended process. No breakaway flag is enabled. Timeout
terminates the Job and requires the process to exit within a separate 5-second
cleanup wait. Handles are closed on every path; normal exits also trigger Job
termination to prevent a surviving child from continuing the attempt.

Both ceilings are `memory_mib * 2^20` bytes of **committed virtual memory**.
Reported `peak_process_commit_bytes` and `peak_job_commit_bytes` are the Windows
API's two counters; they are not interchangeable with RSS, Python allocations,
machine RAM or a proof of memory hardness. See [Microsoft's structure
definition](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_extended_limit_information)
and [Job Object lifecycle](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects).

`elapsed_ns` starts immediately before `ResumeThread` and ends after observed
exit or termination. It includes Python/native imports, backend fingerprinting
and warmup, visited-header generation, search, audits, scores and worker
checkpoint writes. It excludes CreateProcess/Job setup, parent request
serialization, reading/rechecking results, and separate complete oracles.
`deadline_overshoot_ns = max(0, elapsed_ns - wall_ms*10^6)` is recorded.
Scheduling, termination and low-power states prevent a hard real-time guarantee;
[Microsoft documents wait behavior](https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-waitforsingleobject).
These are controlled workers, not a sandbox against malicious code.

## 2. Bounded worker request

`scripts.window_worker.decode(bytes)` accepts at most 65536 bytes of JSON with
exactly these keys:

| Field | Requirement |
|---|---|
| `version` | `WLP1` |
| `policy` | Existing `first`, `all`, `reuse`, or `cache-all` |
| `target` | External lab score target, integer 0 through 2^256 |
| `stages` | 1–3 lists, each 1–16 canonical lowercase MGH1 header hex strings |
| `budget` | Exact `LatticeBudget` fields and existing bounds from spec 07 |
| `cache_capacity` | Exact integer 1–32 |

Each header encodes exactly 140 bytes. Within a stage, network, parent, height
and profile must agree; the dimension must not exceed 16. Request validation
precedes optional FLINT import. The driver serializes a bounded request to an
ignored, uniquely created directory under `artifacts/`, and starts the explicitly
selected pinned research interpreter. Source and paths are local trusted inputs.

One `PracticalReducer` setup is paid per worker. A `cache-all` worker keeps one
bounded `CandidateCache` across its stages. Cooperative budgets and `reuse`
acquisition reset **at every stage**. No vector-acquisition campaign carried
between stages is tested. Every worker starts with an empty Python cache; OS
file caches and host scheduling can still be shared between attempts.

## 3. Immutable evidence protocol

After stage k the worker writes `checkpoint-k.json`, at most three checkpoints.
They are cumulative reports with status `running`, containing the backend
identity/setup time and stage results from spec 07. All stages finishing produces
a separate `response.json` with status `completed`. Each file is written once
using exclusive creation, closed, then accompanied by `<name>.ready` containing
exactly 40 bytes: little-endian u64 content length followed by SHA256(content).
The output bound is 8388608 bytes **per file**, not a combined-directory ceiling.
No file is replaced or renamed. This avoids observed Windows watcher/file-lock
contention while preserving prior completed checkpoints during forced exit.

The parent checks errors, final response, then checkpoints from 3 to 1. It reads
at most 41 marker bytes and 8388609 content bytes. An absent, truncated, oversized,
length-mismatched or digest-mismatched marker is ignored; a prior valid checkpoint
can survive. A verified marker certifies write completeness, not authenticity:
this is a controlled-worker protocol, not a signature or external trust proof.
Per-attempt directories remain ignored forensic artifacts; they are not deleted
in the measurement path. Operators may archive them after workers have exited.

`error.json` carries `memory-error` when Python catches `MemoryError` (exit 77),
or bounded `worker-error` diagnostics (exit 78). Source/protocol errors abort the
survey rather than masquerading as a resource limit. Native aborts or failures
without a valid memory-error report are `worker-failed-unclassified`; no OS
completion-port memory-event classifier is implemented. A failed attempt to
publish the error can therefore remain unclassified. Fixed sleep/allocation
diagnostics are separate private CLI probes, outside WLP1 requests.

Whole-worker outcomes are `completed`, `wall-timeout`, `worker-memory-error` or
`worker-failed-unclassified`. Only completed workers have `logical_work_known`.
Recovered stages can be independently audited after interruption, but their
hits never enter completed-window win totals. Lost work is **unknown**, not zero.
All attempts retain OS elapsed/commit measurements. Logical totals and per-hit
ratios are explicitly conditional on completed workers; unconditional logical
work per hit is null if any attempt is censored. Complete unsuccessful workers
remain charged. Zero-hit ratios are null.

## 4. Fresh schedules

`windows_survey.stages_for(profile, schedule)` creates three stages of eight
headers using SHA256 of `magnet-windows-v1/q/n/m/b2` with `/network`, `/parent`
and `/payload` suffixes. Base height is 1, timestamp is the opaque lab value
20261008, and nonce starts at 0. The timestamp is not a claimed Unix date.

- `fresh-nonce`: one parent/height, nonce ranges 0–7, 8–15 and 16–23.
- `fresh-parent`: stage 0 uses the base parent; stage i>0 uses
  SHA256(base-parent || u64le(i)), height i+1, nonce range 0–7.

Headers do not repeat within a schedule. The two schedules share stage 0,
policies/resource windows repeat their cohorts, and tiny-q matrices can collide
despite different seeds. Report header occurrences, distinct headers and exact
profile/matrix identities separately. These are deterministic lab contexts,
not real linked blocks or private unpredictable future challenges.

The survey compares four fixed profiles, three time allowances and two commit
ceilings, with one attempt per cell in fixed order. Independent Rust/Python
generation and complete native MITM oracles sit outside measured windows and
never provide vectors to a worker. Every recovered score is checked against the
oracle and recomputed digest; hits additionally pass Python lab admission and
independent Rust bound verification. This version's survey does not use native
score/admission; the independent implementation is added in spec 09. Both reports
are invalidated before building.
Source, configuration, executable and native backend fingerprints are retained.

## 5. Trusted admission policy

`reference.header_rules.LabRules(context, target, earliest, latest, payloads)`
is immutable trusted configuration. `context` is an `ExpectedContext` fixing
network, parent, height and profile. The external target is integer 0–2^256;
timestamp endpoints are exact u64 integers with earliest <= latest. Payloads are
1–8 distinct 32-byte commitments in a tuple. The submitted packet never chooses
these rules or its accepted score threshold.

`permits(header)` checks that context, an inclusive timestamp range and payload
membership agree. Nonce remains any u64. `admit_proof(packet, rules)` bounds and
decodes the packet, rejects forbidden headers or target zero before deriving A,
then calls existing `verify_scored_proof` with external context and strict
`big_endian(score_digest) < target`. A score equal to T is rejected; T=0 admits
none and T=2^256 admits every mathematically valid bound proof.

The survey admits one payload per stage and timestamp base±1, although it only
mines the fixed base timestamp/payload. It does not test the full allowed range.
An allowlist is not payload-body validation. A matching parent hash is not proof
that a parent exists or belongs to a valid chain. An interval is not a consensus
clock rule. No block body, signature, transaction, subsidy, retarget or fork choice
is added. Profile eligibility and adversarial grinding still require larger,
broader studies and external review before any consensus use.
