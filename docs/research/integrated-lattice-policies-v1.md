# Practical lattice policies and paid preprocessing amortization

Date: 2026-10-08. Research only; no consensus or calibrated network work.

Practical FLINT LLL and exact sphere search now run inside paid header policies.
The study compares first-vector discovery, all-vector scoring, paid acquisition
plus reuse, and complete-pool caching. It extends beyond the earlier small
coordinate-search families while preserving independent native availability and
proof checks. Cached preparation can save later work on identical instances;
the initial work and continuing verification/scoring cannot be discarded.

## Reproduce

~~~sh
python scripts/check.py
artifacts/flint-env/Scripts/python.exe scripts/integrated_survey.py
python scripts/sphere_survey.py --python artifacts/flint-env/Scripts/python.exe
python scripts/flint_survey.py --python artifacts/flint-env/Scripts/python.exe
~~~

Provision the isolated pinned FLINT environment explicitly according to
[spec 05](../../spec/05-practical-lll-and-grinding-v1.md); no install/fallback
occurs in these commands. Ordinary checks still use stdlib/offline Cargo and
injected exact reference reducers. Explicit experiments exercise FLINT 0.9.0.
See [interfaces and budgets](../../spec/07-integrated-lattice-policies-v1.md),
[ADR 0008](../decisions/0008-paid-lattice-preprocessing.md) and
[committed evidence](results/integrated-v1.json).

Raw ignored `artifacts/integrated-v1.json` retains every family/header, certificate,
complete/partial vector set, score and stop. The local compact file is
`artifacts/integrated-summary-v1.json`. Source/lock/executable/backend fingerprints,
labels and schedules make the run reproducible. Both files are invalidated before
building; interruption or audit failure cannot leave stale success. Older Git
reports remain historical snapshots rather than being silently rewritten.

The [fresh regression summary](results/integrated-regressions-v1.json) confirms
all 1101 complete sphere sets again, and 3603 native reductions over 1201 FLINT
records after the shared-helper refactor. It records the same current source
fingerprints as this study; historical repeated inputs remain explicitly labelled.

## Strategies and trust boundaries

- **First:** pay kernel construction, native LLL and independent certificate audit
  for each visited matrix; exact sphere stops on the first verified canonical
  vector, scores it once and advances if unsuccessful.
- **All:** use the same paid preparation, scoring verified discoveries in traversal
  order until a hit, full exhaustion or explicit cap.
- **Reuse:** pay unsuccessful first-vector searches and acquisition; check the
  acquired vector on subsequent matrices, scoring only when it remains valid.
  There is no hidden fallback reduction when reuse fails.
- **Cache-all:** eagerly enumerate the complete pool before scoring; store it by
  exact profile plus matrix, using sorted canonical vector order. On reads,
  revalidate vectors and hash the proof containing the current header. No score
  or approximate-matrix match enters the cache.

The cache-all versus all comparison changes **both preparation and vector order**.
Warm versus cold-reset cache-all compares the same sorted score stream. Only
complete pools populate the local bounded LRU. Empty pools are real entries;
partial/capped pools reject. Cache capacity is 32, at most 256 vectors per entry,
with immutable copies and exact key equality. Internal completeness comes from
trusted sphere results, not from an authenticated public cache service.

FLINT setup/version metadata and one warmup are recorded once outside policy
timers. Each policy acquires preparation on demand, without precomputing unvisited
headers. The same native reduction helper serves the old worker and the new
in-process adapter. Every reduction receives an exact audit, followed by another
sphere audit. Oracle data is used only by the experiment's separate audit.

## Cohort and availability

Four profiles, two seed batches each, nonce16 and joint2x2x4 families yield
16 families, 256 header occurrences, 240 unique headers and 188 distinct instance
fingerprints. The first profile is an intentional tiny collision control.

| q,n,m,B2 | Header occurrences | Occurrences with a solution | Initial first/all/reuse/cache-all hits |
|---|---:|---:|---|
| 2,1,3,1 | 64 | 58 | 5 / 7 / 5 / 7 |
| 17,2,8,8 | 64 | 64 | 4 / 8 / 0 / 8 |
| 257,3,14,12 | 64 | 40 | 4 / 5 / 0 / 5 |
| 257,4,16,8 | 64 | 0 | 0 / 0 / 0 / 0 |
| Total | 256 | 162 | 13 / 20 / 5 / 20 |

Each hit column aggregates eight runs per profile: two families, two batches and
two targets, T=2^256/8 and 2^256/32. Independent native MITM completes all 256
availability domains; every oracle vector is checked for validity and uniqueness.
All completed sphere sets match; partial streamed outputs are checked as subsets.
Every emitted score vector/digest is audited outside policy timing.

The four initial policies give 128 runs and 58 hit occurrences. Cache-all also
gets 32 warm and 32 cleared-cache replays, giving 192 main run occurrences and
98 total hit occurrences. All 98 pass Python's strict external score predicate
and Rust's independently generated bound proof verification. The repeats are
deliberately correlated; they are neither 98 unique proofs nor new mining blocks.
All main runs stop at hits or exhaust their chosen family; no budget cap occurs
in this cohort. Explicit cap regressions cover all implemented limits separately.

## Component accounting and cache experiment

| Strategy/phase | Runs | Hits | Reduction calls | Sphere nodes | Score hashes |
|---|---:|---:|---:|---:|---:|
| first / cold | 32 | 13 | 390 | 11846 | 209 |
| all / cold | 32 | 20 | 291 | 12604 | 231 |
| reuse / cold | 32 | 5 | 156 | 2708 | 57 |
| cache-all / cold | 32 | 20 | 273 | 13850 | 199 |
| cache-all / warm replay | 32 | 20 | 0 | 0 | 199 |
| cache-all / cold-reset replay | 32 | 20 | 273 | 13850 | 199 |

Every denominator includes failed attempts. Per-hit component ratios retain
exact numerator/denominator, or null if no hits. No weights convert these
heterogeneous counts into a universal CPU price. At the high-q empty profile,
preparation and unsuccessful searches remain charged despite zero hits.

Cold cache-all has 18 hits on previously prepared exact matrices within its runs;
these savings arise in the collision control. The larger-profile cold schedules
do not show such cross-header cache hits. The warm replay has all 291 visited
matrices cached and performs no new reductions or sphere search. Its score stream
and stop reasons exactly match cold and cold-reset. Initial cold preparation
still contributes 273 reductions, 13850 sphere nodes and 438 canonical sphere
checks, plus 438 fill checks. Warm replay performs 291 matrix expansions covering
13192 entries, 199 cache-read checks and 199 fresh proof hashes.

Thus cold-plus-warm costs include all initial preparation and two rounds of the
remaining operations. Cleared-cache replay directly confirms the return of the
273-reduction/13850-node preparation cost. Saving this work on repeated exact
inputs is not evidence that arbitrary fresh high-q headers can reuse it.

Four additional nonce families are repeated at target zero with cache capacity
one, yielding eight diagnostic runs outside the main win denominator. The tiny
collision control needs 13 reductions per pass and gets three cache hits. Each
larger family needs 16 reductions on both passes, zero cache hits and continuing
evictions. A fitting replay benefit disappears when the working set is evicted;
an unlimited free cache is not assumed.

## Timing, limits and interpretation

Shared default ceilings: 100000 sphere nodes, 64 reductions and 4096 scores per
run, 256 retained vectors and 4096 checked fraction bits per instance. A visitor
stop is explicitly incomplete; hitting on the final permitted score wins. Failed
or capped work remains in totals. Capped cache preparation is not stored or
scored, while streaming all may already have scored valid partial discoveries.

Native construction/reduction timers exclude audits. Reducer elapsed includes
them and its audit; sphere elapsed includes its own audit, exact GSO, search and
visitor scoring. Total policy time includes matrix expansion, key operations,
cache verification, scoring, result construction and these overlapping scopes.
They must not be summed as independent timers. Interpreter/process startup is
outside recorded backend setup. The in-process adapter has no per-call subprocess
timeout; interrupted/stalled experiments require external termination. Cooperative
operation/fraction limits are not OS time/RAM enforcement or memory hardness.

The current results compare concrete bounded local policies, not equal wall-time
windows, optimized-miner throughput, BKZ/GPU/sieve performance or intrinsic SIS
cost. More scores and more wins do not necessarily mean the best cost per win.
Same-instance vector pools and repeated matrices are not independent network
work. q2 collision results do not establish an attack against future large-q
profiles. Unknown strategies, larger norms/dimensions, proof availability,
amortization across genuinely fresh headers and permitted timestamp/payload
semantics still need separate experiments.

## Next gate

Measure these policies under common externally bounded elapsed/memory windows
with explicit abort semantics; test persistent preprocessing/reuse across fresh
header/context schedules instead of only fitting replays. Define candidate
timestamp/payload/profile rules and evaluate adversarial easy-instance selection
before writing a fork-choice/difficulty proposal. E1 and independent cryptographic
assessment remain open; no monetary blockchain or MagnetGate integration follows.
