# ADR 0011 — Retain SIS + outer score for the laboratory chain only

Status: accepted laboratory construction and demonstration configuration;
production parameters, calibrated work and monetary launch remain unselected.

## Construction decision (backlog item 6)

Use candidate B: the existing canonical MGH1-derived SIS predicate plus a strict
SHA-256 outer threshold. Keep pure SIS as a competing research hypothesis, but
do not build this prototype around changing the norm bound as the only difficulty
control. Norm changes affect availability, proof multiplicity, solver performance
and possible emptiness together. A single norm bound does not give a portable,
smoothly adjustable work scale. Earlier complete surveys already contain empty
and highly soluble cohorts; this milestone adds paid solver/pool competition.

The outer score supplies an exact, independently checked eligibility predicate
and a simple fixed-target demonstration. It does not repair SIS work pricing by
itself. Candidate B remains lattice-based: removing SIS would be a new construction
decision, not an implementation shortcut. No claim of memory hardness, GPU
fairness, post-quantum network security or paid-SIS-per-score is introduced.

## Parameters (backlog item 7)

Choose q=17,n=2,m=8,B2=8 and T=2^252 for the runnable **demonstration** chain.
These parameters are intentionally toy-sized, cheaply solved by known methods,
and unsuitable for any valuable asset. The choice is for reproducibility and
visible block progress, not security. The portfolio compares them with q=257,
q=769 and q=12289 profiles at dimensions<=16; capped empty outputs do not reject
a profile for mathematical emptiness. q=2 remains an attack-control cohort and
is explicitly excluded from chain policy. The old complete empty cohort remains
negative availability evidence, not a silently replaced successful parameter set.

Production profile selection requires fresh independent seeds, larger-dimensional
optimized/native/GPU baselines, solution-density tails, cheap sparse attacks,
cross-context reuse and an external cryptographic review. This experiment does
not promote its fastest backend or easiest profile to a security parameter.

## Work argument (backlog item 8)

For a positive threshold T, under the explicit uniform-independent *eligible
score-input* assumption, success probability is T/2^256 and mean eligible trials
is 2^256/T. This describes score trials, not SIS solves, seconds, joules or block
weight. Repeating an identical input repeats its digest; it is not a new independent
trial. Distinct proof vectors, cheaply formed combinations and alternate headers
can supply more distinct eligible inputs after shared paid preparation.

The observed campaign cost is a vector: setup, acquisition/search, expansion,
carried/combination checks, score bytes/hashes, eviction and failed attempts.
Backend node units differ. No weighted sum of these host-specific counters is
installed as consensus difficulty. Censored total logical work stays unknown;
completed-only per-hit ratios are conditional statistics, never an unconditional
price or winner comparison. Warm-stage counts retain the campaign's paid cold
setup/acquisition costs rather than pretending the pool was free.

With this prototype's externally fixed profile and target, nominal chain weight
is one per accepted block. This is sufficient to inspect a linear laboratory
history and insufficient to compare forks or changed thresholds. We do **not**
assign inverse-target weight to SIS blocks, multiply it by an arbitrary estimated
SIS constant, trust miner-reported work, or derive validity from measured time.
E3's portable, adversarial work/comparability gate remains open. Next consensus
simulation must confront cheap inflated-weight branches before installing any
retarget or fork-choice rule.

## Block and chain boundary (backlog items 9–10)

MGB1 commits body, recipient, target and version into the SIS challenge, retains
all MGH1 fields and assigns an unambiguous block ID. The trusted anchor provides
one fixed eligible profile/target. Append checks parent, exact height, median
past time, trusted-clock future tolerance, body binding and full proof before
mutating state. Future blocks defer; unknown/non-tip parents are separate from
intrinsically invalid proofs. The body is opaque and bounded; no payment/reward
semantics exist. Chain storage is bounded and immutable to callers.

This is a Python linear-chain engine with independent Rust hash/proof admission
checks. A second complete chain/parser implementation, persisted database,
fork/reorg handling, retarget, transaction/state rules and peer resource control
are required before node deployment. Do not describe the prototype as a monetary
testnet or declare the complete consensus problem solved.

See [block specification](../../spec/11-experimental-block-chain-v1.md),
[portfolio interface](../../spec/10-pool-portfolio-v1.md) and
[milestone report](../research/pool-portfolio-and-blocks-v1.md).
