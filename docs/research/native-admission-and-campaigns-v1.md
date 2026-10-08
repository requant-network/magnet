# Independent native admission and persistent campaigns v1

Date: 2026-10-08. Laboratory implementation/evidence, not a production PoW or
calibrated consensus weight. This milestone closes native acceptance gaps and
compares paid single-vector reuse across fresh contexts.

## Reproduce

~~~sh
python scripts/check.py
python scripts/campaign_survey.py --python artifacts/flint-env/Scripts/python.exe
python scripts/windows_survey.py --python artifacts/flint-env/Scripts/python.exe
~~~

Use the isolated pinned python-flint 0.9.0 environment from the earlier backend
report. Windows Job Objects are required. Cargo remains offline/locked; the
ordinary check gate has no third-party dependencies. All work ran locally,
without GitHub Actions, cloud GPU jobs or changes to MagnetGate.

See [native score/admission interfaces](../../spec/09-native-score-and-admission-v1.md),
[persistent campaigns](../../spec/10-persistent-campaigns-v1.md),
[ADR 0010](../decisions/0010-independent-acceptance-and-campaigns.md),
[committed campaign evidence](results/campaign-v1.json) and
[old-window regression evidence](results/windows-regressions-v2.json).
Ignored raw `artifacts/campaign-v1.json` retains every header, availability digest,
execution order, certificate, scored vector, hit and worker outcome. Per-attempt
directories retain requests and immutable checkpoints. Compact evidence preserves
source/lock/backend/executable hashes, settings, host and all group denominators.

## Independent acceptance

Rust now implements bounded SHA-256, the **unchanged** domain-separated lab score,
strict 0..2^256 external target and full LabRules admission. A canonical 33-byte
big-endian target represents the full interval without overflow. Equal score/target
rejects; zero accepts none; 2^256 admits every otherwise valid proof. Context,
profile, time range and allowed commitments remain trusted outside the proof.
Malformed local configuration fails the adapter; well-configured invalid proofs
return false. MGL1 modes 0–3 remain unchanged; modes 4–6 add hash/score/admission.

The frozen admission fixture binds an existing MGH1 proof to one digest/rule wire
and six threshold boundaries. The local gate checks **10814** additional native/
Python differential cases: 568 raw SHA-256 messages, six frozen admissions,
3072 strict-score cases, 5120 proof-admission variants and 2048 trusted-rule
variants. All agree; 13 malformed new requests fail cleanly. Mutations are not
assumed invalid when mathematical coincidences could preserve acceptance.

The handwritten native SHA-256 follows [FIPS 180-4](https://csrc.nist.gov/pubs/fips/180-4/upd1/final)
and has known-answer and padding/length checks. These engineering tests and source
review do not certify cryptography. The predicate is still a laboratory rule,
not a chain-derived difficulty, payload-body or parent-chain validation function.

## Paid campaigns and experiment design

Four profiles, two schedules and three salted seeds produce 24 input cohorts,
each with three stages of eight headers. The **576 header occurrences** contain
**480 distinct headers** and **368 exact profile/matrix identities**. Of the 576
occurrences, 346 have solutions in independently exhausted native MITM domains.
Python and Rust generation agree. Oracles sit outside measured windows and never
provide initial vectors to workers.

`fresh-nonce` advances nonce ranges under one parent; `fresh-parent` changes parent
and height while retaining one network/profile. The schedules share stage 0.
Each cohort gets two same-input repeats of three policies at 400 and 1200 ms,
with a 64-MiB Windows committed-memory ceiling: **288 attempts**. A recorded global
shuffle interleaves the jobs. Fresh process/backend setup occurs each attempt;
one vector and a campaign-wide budget persist across stages. There is no matrix
cache. The two repeats are correlated mathematical replays, not independent wins.

- Restart-first pays fresh first-vector search for every visited header.
- Carry-first pays acquisition once when possible, then rechecks the same vector
  across headers and contexts, without a hidden fallback or invalid-vector score.
- Carry-fallback explicitly pays a new first-vector search after invalid carry,
  replacing the vector when acquisition succeeds.

Fallback currently generates A for the carry check and again inside the existing
fresh-acquisition helper. Both generations are charged. This transparent wrapper
does not represent the best optimized implementation. Acquisition snapshots retain
initial cost; node/reduction/score ceilings do not reset with a new parent.

## Outcomes and censoring

The observed host identifies its processor as AMD64 Family 25 Model 117 Stepping 2,
AuthenticAMD, with 16 logical CPUs, Windows 10.0.19045 and Python 3.12.10. Backend
binary/license fingerprints are retained. No CPU affinity, thermal/load isolation,
physical RAM inventory or energy measurement is claimed.

| Allowance, 64 MiB commit | Attempts | Completed | Timeouts | Stage hits from completed workers | Stages recovered from aborted workers |
|---|---:|---:|---:|---:|---:|
| 400 ms | 144 | 86 | 58 | 80 | 75 |
| 1200 ms | 144 | 144 | 0 | 88 | 0 |

There are 230 completed and 58 censored attempts, with 168 completed-stage hit
occurrences. Including seven recovered aborted hits, **175** hit occurrences pass
both Python and independent Rust **full** admission. The seven are diagnostic,
excluded from the 168 wins. Every recovered score is recomputed against its
correct header and checked for oracle membership; complete sphere sets agree
with the oracle, while partial sets are verified subsets.

All-attempt observed in-window elapsed time sums to 100.98 seconds. Maximum
process commit is 31825920 bytes (about 30.35 MiB) and maximum deadline overshoot
15.62 ms. The 64-MiB main ceiling is nonbinding. Windows commit metrics are not
RSS, total machine RAM, energy or memory hardness. Existing actual-OS controls
separately confirm stalled termination and denied large allocation.

Completed-only logical totals include 3040 reductions, 77880 sphere nodes,
2588 carry checks and 2216 score hashes, including unsuccessful campaigns. Lost
logical work in all 58 interrupted workers remains unknown. Unconditional logical
work per hit is null. The completed 400-ms subset favors whichever cases finish;
it cannot serve as an unconditional strategy comparison. Host state/OS caches
and backend startup contribute to these elapsed windows.

## Full-window comparison

At 1200 ms, every policy has 48 completed campaigns and 144 stage opportunities:
four profiles × two schedules × three seeds × two repeats × three stages.
Elapsed per-attempt range across this full cohort is 218.64–608.40 ms.

| Policy | Stage-hit occurrences / 144 | Reductions | Sphere nodes | Carry checks | Score hashes |
|---|---:|---:|---:|---:|---:|
| restart-first | 38 | 988 | 28422 | 0 | 540 |
| carry-first | 12 | 336 | 6744 | 762 | 160 |
| carry-fallback | 38 | 876 | 27570 | 652 | 540 |

Across the three salted seeds respectively, full-window restart yields 14/8/16
stage hits, carry 8/2/2, fallback 14/8/16. This is variation across a small
deterministic toy cohort, not a confidence interval, independence theorem or
mining throughput distribution.

All successful carry validations in this full cohort occur in the q2/n1/m3/B²1
control: 124 for carry-first, 112 for carry-fallback. For each policy, 100 of these
validations change the **exact matrix identity relative to the vector's latest
paid acquisition**, rather than merely replaying an identical matrix. The vector
can therefore survive some changed toy instances. These are occurrence counts
with repeats, derived from raw acquisition/instance records.

No carry validation succeeds on the larger profiles in this cohort. The
q257/n4/m16/B²8 sampled complete domains are empty, so no vector is acquired there;
those acquisition failures remain charged. Fallback's 112 fewer reductions than
restart come from 112 successful carry checks, all on the tiny control. The
larger profiles do not demonstrate a persistent-vector saving here. No universal
absence or usefulness of richer cross-instance vector pools follows.

## Regression and remaining gate

The old WLP1 experiment is rerun with the expanded worker/native crate. Its
1200-ms complete policy groups retain exactly the previous mathematical hit and
component-counter totals; new OS timings/borderline completion counts are recorded
as new observations. The historical windows-v1 committed report is preserved.
Repeated cold measurements need not reproduce earlier 400-ms timeouts.

The final local gate passes **131 Python tests and 15 Rust tests**, rustfmt/clippy,
10009 SIS, 103 native-search, 1936 generation/binding and 10814 admission
differential cases with no mismatches. Campaign regressions exercise initial
paid acquisition, failed carry, explicit fallback charges, global caps, final-
score hit/stop precedence, valid real headers, shuffled coverage, canonical
transport and stale-report invalidation. Independent source review found no
required issues; this is not external cryptographic review or long-running fuzzing.

Next broaden stronger solver and vector-pool/precomputation competition, compare
steady-state campaigns with cold cost retained, and measure actual permitted
time/payload grinding surfaces. Then specify trusted chain-derived target/profile,
parent/body/time validity and upgrades before evaluating retarget/fork choice.
No blockchain, chainwork, wallets, payments or MagnetGate integration is added.
