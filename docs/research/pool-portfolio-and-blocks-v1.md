# Paid vector pools, solver portfolio and laboratory blocks

Date: 2026-10-08. English is primary. This milestone implements the laboratory
deliverables for backlog items 1–10; mathematical/economic production gates are
tracked separately below.

## Delivered interfaces

| Item | Implemented result | Boundary |
|---|---|---|
|1|FIFO multi-vector pools 1/4/16, dedup, eviction, paid acquisitions, current-instance validation, +/- combinations|Finite bounded pool; no universal reuse claim|
|2|Paid Rust MITM, sparse easy-instance screen, exact-Gram FLINT LLL .75/.99, bounded projected-SVP BKZ4/8, finite pair sieve|m<=16; not optimized fplll/G6K or GPU|
|3|Non-resetting campaign budgets, 8 parent/height stages, separated cold/warm counts and paid setup|Finite campaigns; steady-state limits are not proved|
|4|Joint nonce/time/payload families and cheap sparse-first competition|Predeclared finite allowed surface, no free oracle selection|
|5|Timed native/Python mutation and near-valid endurance runner; local framing corpus retained|Controlled stdin mode 6, not a public network service|
|6|Candidate B (SIS + outer score) chosen for the laboratory|Production construction security gate remains open|
|7|Explicit demonstration profile 17/2/8/8 and fixed target 2^252; contrasting larger toy profiles|No production security parameters chosen|
|8|Descriptive cost vectors, conditional/censored per-hit statistics, explicit ideal-score assumption, fixed-policy nominal weight|No calibrated cross-profile work/retarget/fork weight|
|9|MGB1 bounded body, recipient/target/version binding, canonical encoding, proof and block ID|Opaque body; no transactions or asset rewards|
|10|Trusted-anchor linear chain: profile/target, parent, height, median time, future deferral, body/proof admission|Python engine; no forks, persistence or peers|

The selected lab construction and remaining gates are recorded in
[ADR 0011](../decisions/0011-experimental-construction-and-chain.md).

## How the experiments are paid

The portfolio worker imports the pinned native backend only after request
validation. Windows Job commit/time limits apply before resume. Native MITM
descendants inherit the same Job. Eager proof acquisition, failed/capped searches,
pool checks and combinations enter counters; setup, certificate audit, process
startup, transport and checkpoint writing enter the external elapsed window.
Backend node types are not economically interchangeable.

Each of two salted seeds supplies eight distinct parent/height contexts and eight
joint nonce/time/payload headers per context, for 64 potential headers per campaign.
Five profiles, seven backends, five policy/pool settings and two windows produce
700 shuffled attempts. Windows 500/4000 ms, committed-memory ceiling 128 MiB, shared
budgets 100,000 search nodes/64 acquisitions/8192 pool or combination checks/4096
scores/32 proofs per acquisition. One fixed T=2^252 is used across all backends.

The bounded native MITM availability baseline is outside mining windows. Its
proofs are never supplied to miners. Independent Rust generation is compared
before mining; every recovered score is checked in Python and every recovered
hit is independently admitted by Rust against the predeclared surface. Partial
checkpoints retain diagnostic hits but do not manufacture completed-window wins.
Completed workers can themselves have cooperative caps; acquisition stop reasons
and unvisited stages are retained.

Raw records/checkpoints stay under ignored artifacts/. Compact committed reports
contain seeds, source/executable fingerprints, caps, failures, conditional ratios
and limitations. The final local comparisons overlapped the endurance fuzzer,
each other and local regressions on the same host. They cannot establish an isolated timing ranking,
portable hashrate, energy cost or high-dimensional hardness. Two seeds are not an
availability-tail/security study.

## Reproduce locally

~~~sh
python scripts/check.py
python scripts/portfolio_survey.py --python artifacts/flint-env/Scripts/python.exe
python scripts/soak_survey.py --python artifacts/flint-env/Scripts/python.exe
artifacts/flint-env/Scripts/python.exe scripts/portfolio_checks.py
python scripts/rejection_cost.py
python scripts/mine_lab_chain.py
python scripts/endurance_fuzz.py --seconds 3600
~~~

The ordinary gate uses standard libraries and
Cargo offline; optional solver comparisons use the already pinned python-flint
environment. No GitHub Actions, paid CI or cloud resources are used.

## Measured results

On the local AMD Ryzen 7 8745HS host (8 cores/16 threads, 42.7 GB physical RAM),
the [portfolio](results/portfolio-v1.json) completed 479 of 700 external windows;
221 were censored by the deadline. Completed campaigns produced 1610 stage-hit
occurrences; native admission also checked 9 recovered hits from interrupted
windows, which are excluded from completed win totals. The unconditional logical
work-per-hit ratio is null. Even among completed campaigns 110 stopped on the
shared cooperative node cap; completed worker does not mean all eight stages
or every proof domain was exhausted.

The [extended campaigns](results/soak-v1.json) use 128 possible joint headers,
T=2^248, ceilings of 1,000,000 nodes/128 acquisitions/15,000 checks/10,000 scores/
64 proofs per acquisition, 30 s and 128 MiB. All 56 workers completed; 44 exhausted
their finite campaign and 12 stopped on the node budget. They visited 364 of 448
potential stages and produced 170 stage hits (20 cold/150 warm). Warm work retains
all cold setup in the campaign totals. These are eight-stage measurements, not
an asymptotic steady-state claim or thirty seconds of work per completed miner.

The separately bounded baseline establishes solutions on 128/128 sampled headers
for the demonstration 17/2/8/8 profile and 66/128 for257/3/14/12; its other 62 are
complete empty searches. For 769/4/16/24 and 12289/4/16/64, all 128 headers per profile
hit the MITM half-box preflight cap: availability is unknown, not zero. q=2 is a
cheap attack-control cohort, excluded from chain policy. These finite observations
support a runnable demo profile and do not choose secure production parameters.

[Actual-backend differential](results/portfolio-complete-probe-v1.json) compares
168 searches on 24 tiny complete oracle cases with zero mismatches. Completed full
searches match entire proof sets; partial/sparse/sieve output is checked as a
subset. A paid native campaign also exhausts exactly its 10-node shared allowance.
The [legacy regression](results/native-legacy-regressions-v3.json) preserves all
six historical cohorts' exact proof counts and logical work.

The [hour endurance run](results/endurance-fuzz-v1.json) processed 1,300,992 inputs
over 3601.31 seconds with zero native/reference mismatches. It uses mutation,
truncation, extension, random, near-valid and maximum-shape residual families.
Near-valid batches can contain both accepted and rejected proofs. The separate
[rejection-path study](results/rejection-cost-v1.json) uses 3840 all-reject cases
across three fixed paths and five repeated batches each. Native timing includes
debug-build process startup/IPC; it is not production node capacity or a comparison
with release search throughput. Input framing is valid mode 6 during endurance;
malformed framing/rules remain covered by the ordinary corpus.

The endurance executable was preserved unchanged throughout the hour. Only the
non-executed native search sources changed while that run was active; new builds
used a separate artifacts/admission-current directory. The report deliberately
retains source_unchanged=false for the broad recorded set, lists the two changed
files, and verifies all recorded admission/reference sources plus the original
executable fingerprint before rebuilding it for the final gate. Retention through
the run is workflow provenance. The factual last-write timestamp was recorded,
but actual run-start UTC was not: it cannot provide an automated interval guarantee.
`scripts/evidence_metadata.py` consolidates recorded backend binary/license hashes,
hardware and source checks after all reports complete. It requires retained raw
portfolio/soak records and verifies the old fuzz executable before a rebuild.
Source fingerprints describe each measurement run; the later metadata-only
postprocessor is fingerprinted separately. Its recorded hash identifies the
revision actually used to consolidate the evidence. A subsequent review removed
an invalid timestamp inference (postprocessing time minus run duration); the
existing endurance report explicitly records that interval checking is unavailable.

An earlier portfolio/soak attempt incorrectly used legacy MITM's zero nodes field
for shared node budgeting. Those reports were invalidated and remain only as
ignored retracted artifacts. Final results use NAT1 mode 3, which enforces
nodes=left+right+pairs inside native execution. Mode 2 and the historical two-miner
cohort remain unchanged. There is no zero-cost MITM mining claim.

## Block verification evidence

The local gate mines and appends 64 deterministic tiny blocks. Rust independently
matches SHA-256 body/descriptor/block-ID preimages and bound proof admission over
311 requests. Tests cover canonical length/version/body bounds, committed-field
tampering, replay/parent/height, immutable state, median time, future deferral and
retry, zero proof and forbidden profile/target. This is not a second native block
parser or chain implementation. [The exact specification](../../spec/11-experimental-block-chain-v1.md)
states the scope and future engine requirements.

The [selected-profile demo](results/lab-chain-v1.json) separately mines and appends
eight MGB1 blocks with 10 native searches, 14,272 charged proposal/pair nodes and 166
eligible score computations. All records include canonical block bytes and parent
IDs; there are no transactions/balances/rewards or actual wallet addresses.

## What remains before a real network

Larger optimized solvers and hardware/energy/scaling evidence; independent
cryptographic review; portable difficulty/work argument; independent complete
chain engine; retarget/fork/reorg/overload simulation; transaction/state limits;
persistent nodes, peer protocol and restart; GPU miner; wallet and MagnetGate
integration; separate-operator testnet. The implementation work above does not
make these launch gates disappear.
