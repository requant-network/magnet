# Open questions

Date: 2026-10-09. This page complements the working task ordering in
`docs/CRITICAL-PATH.md`; it is not another parallel roadmap.

1. **D2: What exact weight is under attack?** Define the candidate's inputs,
   difficulty knob, permitted miner choices, chargeable preparation/reuse, and
   verifier-computable weight. The answer must distinguish A (pure SIS) from
   B (fixed profile with outer score). Local timers and reported operation
   counters cannot be trusted consensus inputs.
2. **D3: Can screening inflate that weight cheaply?** Commit a common paid
   budget, a baseline, header-selection policy, minimally meaningful larger
   profiles, denominators, and a stop threshold before running. The critical
   path's >2x screening criterion is an experimental kill rule for the stated
   construction, not a theorem about all SIS-PoW.
3. **D4: Does preprocessing/reuse break monotonicity?** Charge first and later
   acquisitions under the same budget. Existing reuse counterexamples already
   rule out fresh-solve counting. A revised weight needs a sharper falsifier;
   more accepted proof occurrences cannot substitute for this argument.
4. **D5: What must the hardware comparison establish?** The current matched
   small-family pilot fixes timer/domain ambiguity. Energy, memory trade-offs,
   stronger CPU baselines and a smallest relevant non-toy profile remain absent.
   Proceed only if a specific candidate weight makes those measurements decisive.
5. **D6: Who independently reviews the argument?** External cryptographic review
   of the framing/weight is still needed. Local source review checks implementation
   and evidence, not economic or cryptographic security.

Next implementation batch should formalize D2 and the D3 falsification experiment,
not add another solver/GPU interface. Keep negative findings in the central
[findings page](FINDINGS.md). Wallets, payments and production retarget remain
parked while the work-weight question is unresolved.
