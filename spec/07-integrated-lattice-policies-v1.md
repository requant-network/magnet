# Integrated practical lattice policy laboratory v1

Research only. MGH1, SIS validity and the external grinding-score predicate stay
unchanged. This neither selects network work/difficulty nor implements a miner.

## Streaming verified discoveries

`enumerate_kernel` additionally accepts `on_proof=None` or a callable. After
canonical SIS verification and retaining each vector, call the visitor in tree
discovery order. Its return value must be exactly bool. False continues; True
returns `visitor-stop`, including the vector that triggered it. This status
does not certify completeness, even if the final vector happens to trigger it.
Without a visitor, the old exact full-domain behavior and sorted results remain.
Callback time is inside the caller's enumeration timer. Callback failure
propagates, and all exits break the recursive closure cycle.

## Explicit practical backend

`PracticalReducer` is instantiated only in the explicitly provisioned isolated
python-flint environment. Package version/installed metadata and a single warmup
are paid once as session setup, outside per-policy timers and recorded separately.
No implicit install, optional import in the ordinary check gate or fallback.
It reuses the same `reduce_case` helper as the bounded subprocess worker:
full RREF kernel construction, native FLINT LLL delta=.75/eta=.5, integer B/U
and a 256-bit output-entry ceiling. Input shape/dimension checks happen during
kernel construction. The adapter audits every certificate with the unchanged
exact verifier; sphere audits again before enumeration. No certificates or
solutions are precomputed for unvisited headers.

Native construction/reduction timers are disjoint. Adapter elapsed includes
them plus its audit/packing; sphere elapsed includes another audit, exact GSO,
tree, verification and any visitor/scoring. These scopes overlap with total
policy elapsed and must not be added together as independent times. Whole
process/interpreter startup is outside setup and per-run timers. The in-process
adapter has no subprocess timeout or per-reduction preemption; an external caller
must terminate an interrupted/stalled experiment, which leaves evidence incomplete.
The session is a controlled local experiment, not a public input service.

## Four paid strategies

Each policy gets at most 64 same-context MGH1 headers, an external target 0..2^256,
a callable reducer and a validated LatticeBudget. Matrices are derived on demand.
No availability oracle or solution list is given to the policy.

| Policy | Behavior |
|---|---|
| first | Reduce each visited matrix; stop sphere on its first vector; score that vector once |
| all | Reduce each visited matrix; score vectors in tree order; stop at hit or explicit cap |
| reuse | Pay first-vector searches until acquisition; subsequently check only that vector against each new matrix; no hidden fallback reduction |
| cache-all | Obtain the complete sorted candidate pool before scoring; retain complete pools under exact-instance LRU keys; verify and score current-header vectors on every read |

Different score ordering is explicit: first/all/reuse use discovery order, while
cache-all uses canonical sorted pools. Equal hit rates do not imply equal winners
or identical effort. Cache-all pays full preparation even when an earlier vector
might have hit; this is intentionally different from streaming all.

Default aggregate budgets: 100000 sphere coefficient edges, 64 reducer calls,
4096 score hashes; per instance 256 retained proofs and 4096 checked fraction bits.
Maximums: 1000000 nodes, 64 reductions, 100000 scores, 256 proofs and 4096 bits.
Exact positive integers only; bool excluded. Before a new reduction, require
remaining reduction/node budgets. Cached pools and acquired-vector checks do
not need new sphere nodes. Matrix expansion already performed before that
decision remains charged. Hit on the last allowed score wins; otherwise reaching
the score limit stops immediately, without claiming full enumeration/family
completion. A final completed search can exhaust the family at an exactly
sufficient node/reduction budget. Never weaken a profile or substitute an oracle.

Policy reasons: score-hit, family-exhausted, node-limit, reduction-limit, score-limit,
and sphere-node-limit/proof-limit/arithmetic-limit. Successful first-vector
discovery uses a sphere visitor-stop inside the raw instance record; this is
separate from overall hit status. A cache miss reaching a sphere cap stops
without caching or scoring the incomplete pool. Streaming all can score verified
partial discoveries before a later cap. All such work remains in totals.

Counters cover visited/expanded matrices, reducer/sphere calls, sphere
nodes/leaves/canonical SIS checks, reused-vector checks, cache-fill/read checks,
scores/bytes and cache lookups/hits/evictions. They do not count every integer
arithmetic operation or bytes allocated. Native internal LLL counts are absent;
logical calls are not calibrated energy, hardware-independent work or chainweight.
Reuse acquisition records all work through the first score, including the search
that found the vector. Failed acquisition stays in whole-run totals.

## Exact-instance preparation cache

Keys are the complete immutable Profile(q,n,m,B2) plus canonical matrix entries,
not a header, seed, syndrome, digest or claimed similar matrix. Headers with the
same exact matrix can reuse a pool; header-dependent scores never enter the cache.
A changed profile, bound or matrix cannot hit the old entry. Cache instance
fingerprints in evidence are descriptive hashes; actual key equality is exact.

At most 32 entries, at most 256 canonical vectors per entry, dimension 16. LRU
eviction is explicit; empty tuple is a complete cached empty domain, None a miss.
Store only internally generated sphere results with domain-exhausted status,
verify all vectors again, deduplicate and copy into immutable tuples. Invalid,
duplicate, partial or oversized results reject. Cache read revalidates every
vector before the current header's proof hash. Completeness relies on trusted
internal enumeration/results; this is not an authenticated external cache
protocol. Public mutation/caller-supplied fake completeness is outside that trust
boundary. Internal corrupted vectors still cannot become accepted proofs.

## Study design and evidence

Use four profiles, two seeded bases each and two 16-header family types: nonce 16
and joint 2x2x4, at targets 2^256/8 and 2^256/32. This gives 16 families, 256 header
occurrences and 128 initial policy runs. Cache-all additionally runs warm replay
and cleared-cache replay of the identical schedule at each target, giving 192
main run occurrences. These are replay experiments, not fresh ledger work.
Initial cache capacity 32 fits each visited family. For complete/hit cold runs,
warm/reset score streams and stop reasons must match; fitting warm replay must
perform zero additional reductions. Initial cold costs remain recorded and
cannot be discarded when pricing the cold-plus-warm experiment.

Separately repeat four nonce families at target 0 with capacity 1: eight diagnostic
runs. This exposes eviction/churn without conditioning on early hits. It has no
eligible score target and does not enter the 192-run win denominator. Full native
MITM independently audits every header's availability/set. All scored vectors
and digests are audited outside policy timers; every actual hit passes Python
score and independent Rust bound verification. Oracle data never enters decisions.

Summaries retain every failed/capped run's work, exact component numerator/hit
denominator and null when no hits. Native oracle caps/invalid outputs abort rather
than imply availability. Raw and compact local evidence become incomplete before
building; only successful full audits mark passed. Fingerprints cover source,
lock, executable and backend; raw evidence retains headers/seeds, certificates,
complete/partial vectors, scores, caps and the deterministic schedule.

~~~sh
python scripts/check.py
artifacts/flint-env/Scripts/python.exe scripts/integrated_survey.py
python scripts/sphere_survey.py --python artifacts/flint-env/Scripts/python.exe
python scripts/flint_survey.py --python artifacts/flint-env/Scripts/python.exe
~~~

Default checks use stdlib/injected exact reducers; explicit surveys exercise
the pinned native backend. Budgets and arithmetic limits remain cooperative,
not OS enforcement. Common component ceilings do not give equal elapsed time
or prove fairness against unknown optimized/BKZ/GPU/sieve strategies. No source
review substitutes for independent cryptographic assessment.
