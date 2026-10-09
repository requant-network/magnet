# Cooperative acquisition: five-task research block

Date: 2026-10-09. Local component-model experiment, not production work pricing.

All five tasks are implemented and exercised:

| Task | Implementation |
| --- | --- |
| Common cooperative budget and monotonic snapshots | [Component meter](../../reference/component_meter.py) |
| Streaming unit/non-unit acquisition | [Sparse adapters](../../reference/cooperative_solvers.py) |
| Whole-ball and meet-in-the-middle integration | Same owned adapter, existing BallSearch/MitmSearch |
| Paid exact-vector/direction retention | [Campaign transactions](../../reference/cooperative_campaign.py) |
| Frozen fresh/control schedule and budget response | [Survey](../../scripts/cooperative_survey.py), [evidence](results/cooperative-acquisition-v1.json) |

See [spec 22](../../spec/22-cooperative-acquisition.md),
[ADR 0018](../decisions/0018-cooperative-component-budgets.md) and the
[secondary Russian report](../ru/cooperative-acquisition-v1.md).

The study completes all 576 planned steps, 12 separate complete-domain audits,
48 budget-response series and 3661 independent native positive/negative verdict
checks. The local gate passes 295 Python tests, 21 Rust tests, rustfmt/clippy
and all prior differential corpora. No consensus, SIS1 validity or earlier GPU
interface changes were made.

## Budget model and scope

`cooperative-components-v1` gives one unit to each named logical operation
counter. `matrix.shake_output_bytes` is informational with weight zero; legacy
`table_buckets` inventory is excluded, while `table_entries` counts insertions.
The exact model definition/hash is committed in configuration. Raw phase vectors
are preserved alongside totals. This model is an explicit hypothesis; equal
weights do not establish equivalent cycles, economic costs or secure chainwork.

Common preparation counts matrix expansion/entries and shape checks. Constructor
checks are additionally counted when a solver performs them. Sparse search
records candidate generation/screening and early-rejected row products. Existing
ball/MITM engines supply their operation counters through synchronized snapshots.
Output materialization, dense proof/carry checks, sign/norm terms, direction
gcd/key construction, dedup comparisons and retained entries are separately paid.
Python allocator/bookkeeping instructions are not exhaustively priced.

Snapshots reject booleans, negative values, regression and missing counters
atomically. Checks occur at cooperative boundaries. Completed work always remains
charged; there is no hard operation, wall-time or memory ceiling. The report
retains used units, observed overshoot, first boundary and subsequently charged
units as a subset of the final total. Maximum observed excess is 67 units at a
750-unit limit: used 817, first boundary 759 and post-boundary work 58.

A produced proof is densely verified and merged in a transaction before its
post-operation stop. Unchecked carry proofs are excluded from the current pool.
Emission, verified acquisition and retention remain separate fields. Direction
policy uses vector/gcd only as a key and retains the original verified vector;
it does not manufacture a normalized proof. Acquisition continues after pool
capacity is reached, so this fixed policy does not claim adaptive saved work.

All iterators close in finally and flush final counters. Budget, output cap and
observed solver exhaustion have separate flags. Sparse search knows its final
ordinal; closed ball/MITM yields can leave exhaustion unobserved even if an
external oracle knows the last solution was emitted. False exhaustion means
unobserved completion, not proof that another solution remains.

## Schedule and observed response

Profiles (q,n,m,B2) are (7,1,4,8), (17,2,5,8), (257,2,6,12). For each profile,
cross budgets 750/5000/50000, four algorithms, two retention policies and fresh/
control cohorts, each with four sequential steps and an empty initial pool.
Pool cap 8 and acquisition cap 64 apply throughout. Label seed 2026100916 and exact
label derivation/order were frozen before outcomes. Controls repeat fresh step 0;
all methods share each labelled matrix. Matrix preparation is performed inside
each step, not supplied as a free cached solver input.

| Budget per step | Steps | Acquired proof occurrences | Retained direction occurrences | Budget reached | Observed exhausted | Empty acquisition |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 750 | 192 | 364 | 398 | 144 | 48 | 88 |
| 5000 | 192 | 1044 | 508 | 48 | 144 | 82 |
| 50000 | 192 | 1044 | 508 | 0 | 192 | 82 |

There are 384 domain-exhausted primary stops and 192 budget stops; no configured
64-proof cap is reached in this schedule. Retained direction counts include valid
carry, so they need not equal current acquired counts. These totals sum repeated
pool observations, not globally unique discoveries. Same-instance controls,
sequential inventories and scalar copies are correlated.

At 5000 some ball/MITM attempts still stop early, while increasing to 50000 exhausts
all declared solver domains. The equal aggregate acquisition counts at those
budgets are a result of this finite schedule, not a general saturation theorem.
Raw records and 48 response series retain every budget/profile/algorithm/policy/
cohort combination; no result selection or portable winner is published.

Exact retention produces 772 retained-vector occurrences representing 670 direction
occurrences. Direction retention produces 744 occurrences representing 744
directions. This exposes scalar-copy occupancy of finite pools. Different carried
inventories also change subsequent paid work; these totals do not prove a universal
optimal retention policy or independent per-proof acquisition.

## Independent verification and limitations

The Cartesian norm-ball oracle is separate from each solver. Sparse comparisons
filter to support<=3 and coefficient bound1/2. Ball/MITM comparisons use the whole
norm ball, including coefficient3 where B2 permits it. Complete sets are compared
only when observed exhausted; partial acquisitions must be subsets of the
appropriate oracle. Capped absence is never treated as full SIS nonexistence.

For the first labelled matrix of each profile, complete accepted counts are:

| Profile | Sparse ±1 | Sparse ±2 | Ball | MITM |
| --- | ---: | ---: | ---: | ---: |
| (7,1,4,8) | 4 | 14 | 20 | 20 |
| (17,2,5,8) | 0 | 1 | 3 | 3 |
| (257,2,6,12) | 0 | 0 | 0 | 0 |

The oracle checks all runtime complete/subset results. Rust independently checks
acquired proofs and paid carry verdicts, including rejection. Independent ledger
audits reconstruct common/solver preparation, dense verification and retention,
output materialization, direction histograms, totals and stop metadata. Legacy
search counters originate in the existing engines; this is not an independent
reimplementation of their instruction cost. Oracle/native audit work and
report-only direction histograms are outside the component model.

Sixteen new tests cover atomic snapshots, invalid caps, complete domains, negative
verification, partial carry exclusion, proof transactions, direction keys,
simultaneous stops, conservative exhaustion, iterator closure, self-reconciled
counter/histogram/boundary tampering and failed-build invalidation.

Evidence freezes 197 source files and the current Cargo-selected verifier, and
binds exact UTF8/LF raw bytes. Failed publication invalidates success summaries
and preserves completed records with unknown unfinished work. Run:

```sh
python scripts/check.py
python scripts/cooperative_survey.py
```

No new dependencies, GPU/miner changes, paid cloud or GitHub Actions were used.
The next block should carry a selected broader family into an independent native
implementation, compare paid acquisition under clearer hardware scopes and
test policy robustness across more fresh challenge schedules. Portable adversarial
work pricing and production security/chainwork remain open.
