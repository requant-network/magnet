# Bounded search strategies: experiment v1

Date: 2026-10-08. Status: completed toy component-accounting study.

## Result

Charging for initial acquisition does not remove solution reuse. In the
(q=17,n=2,m=3,B2=64) batch, first-reuse performs 181 unique score hashes versus
128 for first-restart, with 364451 versus 364280 candidate proposals. This is
53 additional score trials for 171 additional proposals plus the recorded
derivation and scoring operations. It is not a measured mining speedup.

Sparse screening has a tradeoff: it can reduce proposals while increasing matrix
arithmetic. None of these component counts is a calibrated consensus work unit.

## Reproduction and policies

Run python scripts/strategy_survey.py. The full, ignored report is
artifacts/strategy-survey.json; the committed [summary](results/strategy-survey-v1.json)
omits per-seed records and preserves configuration and source SHA256 hashes.

The 448 seeds are SHA256 of the ASCII string
magnet-sis-strategies-v1/{q}/{n}/{m}/{b2}/{index}, with index starting at zero in
each batch. Every strategy independently expands its own matrix and starts with
no known vectors. No exhaustive oracle supplies solutions to a policy.

| Policy | Search and stopping rule |
|---|---|
| first-restart | Lexicographic box search; score the first valid vector, then stop |
| first-reuse | Same acquisition; divide by coordinate gcd and score admissible positive multiples, then stop |
| full-search | Continue lexicographic box search, scoring every distinct valid vector |
| sparse-reuse-full | Try support-one/two vectors first, then the full box; reuse the first valid vector once |

Every policy stops immediately at its first successful score. Otherwise it ends
at a policy restart, complete domain exhaustion or the 100000-proposal cap.
Restart means advancing to the next externally scheduled seed; this is not an
adaptive racing miner, a fixed-time competition or a search for the optimal
restart threshold. Every policy receives the same seeds, not the same CPU budget.
The cap is a safety bound. If exactly reached, cap status takes precedence over
discovering that the iterator has also ended. No cap was reached in this survey.

Sparse candidates are single positive coordinates, followed by coordinate pairs
i<j with the first positive and the second nonzero. Out-of-ball pairs are charged
before rejection. Full search visits the entire integer box with radius floor
sqrt(B2), including zero and negative-sign vectors before rejecting them. These
are simple baselines, not efficient lattice solvers. Reuse tests only multiples
of the first vector's primitive direction; two-vector combinations are absent.

## Score experiment

The score is SHA256 of the concatenation of:

1. ASCII MagnetNetwork/SIS-LAB/strategy-score/v1 followed by a zero byte;
2. profile q,n,m,B2 encoded as little-endian u32,u16,u16,u64;
3. the 32-byte public matrix seed;
4. the sign-canonical vector encoded as m little-endian signed i32 values.

Interpret the digest as an unsigned big-endian integer and require it to be
strictly less than 2^252. This corresponds to a nominal 1/16 target for a uniform
digest; measured hit counts are small-sample outcomes, not expected rates.
The matrix is determined by the bound profile and seed. There is no independent
score nonce. Unique proofs are hashed once per instance; duplicate proposals
still incur validation cost. The public seed is not a wallet or server secret.

This experiment binds a generated instance to its score, but has no block header,
parent, transactions, network identifier, retarget or consensus acceptance rule.
It must not be presented as a completed network PoW binding.

## Counters and scope

Total work includes unsuccessful searches. first_solution_work is a snapshot
before scoring the first valid vector and is aggregated only over instances
where one was found; it excludes every unsolved instance. It is a conditional
acquisition subtotal and must never replace the all-instance total.

- matrix_expansions and shake_output_bytes charge each call and the entire
  SHAKE output requested by the current generator, including unused bytes.
- proposals counts every evaluated vector, including duplicates and rejections.
- norm_terms counts coordinate squares for validation and reuse setup.
- sign_terms counts visited coordinates during canonical-sign checks.
- matrix_terms counts dot-product terms; row_reductions counts final modular
  reductions. All rows are evaluated after passing norm/sign checks.
- reuse_setups, gcd_inputs and reuse_coordinate_ops count setup calls, gcd
  inputs, coordinate divisions and multiplications during derivation.
- score_hashes and score_input_bytes count unique proof hashes and their input.

These are selected logical components, not all machine instructions. They omit
generation rejection-loop operations, allocation, iteration, tuple/set lookup,
serialization overhead and interpreter overhead. SHAKE bytes and gcd inputs
are not constant-cost CPU instructions. No clocks, watts, throughput, unified
weighted work or cost-per-win ranking are reported. Independent acceptance
audits regenerate A and verify each emitted proof outside the policy counters.

## Observations

Numbers below are totals across the specified batch. Score hits count instances
with at least one hit; domain exhaustion can mean valid proofs existed but all
their scores missed, rather than that the SIS instance had no solution.

| q,n,m,B2; instances | Policy | Proposals | Matrix terms | Score hashes | Score hits |
|---|---|---:|---:|---:|---:|
| 17,2,3,8; 128 | first-restart | 15482 | 33312 | 15 | 0 |
| same | first-reuse | 15504 | 33444 | 22 | 1 |
| same | full-search | 15986 | 35280 | 22 | 1 |
| same | sparse-reuse-full | 19723 | 58140 | 22 | 1 |
| 17,2,3,64; 128 | first-restart | 364280 | 199254 | 128 | 10 |
| same | first-reuse | 364451 | 200280 | 181 | 12 |
| same | full-search | 589460 | 730812 | 391 | 25 |
| same | sparse-reuse-full | 629102 | 920346 | 391 | 25 |
| 17,2,4,32; 128 | first-restart | 982164 | 237136 | 128 | 14 |
| same | first-reuse | 982301 | 238232 | 151 | 16 |
| same | full-search | 1557329 | 1862128 | 812 | 59 |
| same | sparse-reuse-full | 1532994 | 2095376 | 832 | 59 |
| 31,2,4,64; 64 | first-restart | 2774288 | 376832 | 64 | 5 |
| same | first-reuse | 2774363 | 377432 | 80 | 5 |
| same | full-search | 4397635 | 3826016 | 530 | 33 |
| same | sparse-reuse-full | 4381318 | 4019936 | 533 | 33 |

In the B2=8 batch, 113 of 128 matrices have no accepted vector; their failed
searches are retained in the totals. At the larger bounds every sampled matrix
has at least one vector. These batches use different seeds and generation
profiles, so this table is not a controlled fixed-matrix B2 comparison.

At (17,2,4,32), sparse-reuse-full visits fewer candidates than full-search but
uses more matrix terms and score hashes. At (31,2,4,64), first-reuse creates
16 additional score trials without an additional hit. Reporting just proposals
or successful outcomes would conceal part of the cost or sampling variation.
Full-search and sparse-reuse-full have the same hit count because they cover
the same valid domain without hitting the cap; their traversal order changes
the cost of reaching a hit.

## Decision and next gate

[ADR 0002](../decisions/0002-solution-reuse.md) remains in force. There is still
no justified mapping from accepted vectors or score trials to independent SIS
solves, nor a calibrated chainwork formula. No consensus rule has changed.

Next implement a bounded meet-in-the-middle CPU baseline and compare its
memory/time tradeoff with enumeration across several seed batches and score
targets. Include preprocessing, unsuccessful work and amortization. Calibrate
component costs before comparing restart versus continued search under a common
resource budget. Large-parameter hardness, GPU suitability and external
cryptographic review remain separate gates before network consensus work.
