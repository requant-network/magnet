# ADR 0003: do not price SIS work by box enumeration

Date: 2026-10-08. Status: accepted research constraint.

## Evidence

The [MITM experiment](../research/meet-in-the-middle-v1.md) compares complete
solvers on 64 generated toy instances, three score conditions and repeated local
timings. The exact accepted sets and score-hit existence agree. A split-table
algorithm takes approximately 1.5 to 204 times less elapsed time than the current
box-enumeration baseline on this host, at higher traced allocation in representative
memory probes. Its preprocessing is included in timing and component counters.

## Decision

Do not use box size, enumeration runtime or verifier arithmetic as the intrinsic
cost of producing an SIS proof. A work model must allow alternative algorithms,
preprocessing, memory tradeoffs, unsuccessful search and solution reuse.
Do not assign difficulty or accumulated chainwork from these local time ratios.

Preserve the current acceptance predicate and expose search limits explicitly;
do not change the mathematical task to conceal a cheaper search strategy.

## Limitations and next gate

These instrumented Python toy baselines are not an optimized miner or a hardness
assessment. Selected allocation peaks are not process memory or worst-case bounds.
The result neither proves all SIS-PoW constructions insecure nor selects MITM
as a production solver. Next compare incremental ball enumeration, MITM and reuse
under declared time/memory budgets before proposing a calibrated work model.
