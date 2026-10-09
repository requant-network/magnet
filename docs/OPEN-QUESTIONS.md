# Open questions

Date: 2026-10-09. This page complements the working task ordering in
`docs/CRITICAL-PATH.md`; it is not another parallel roadmap.

1. **D2: Can any explicitly defined credit price adversarial work?** The
   [critical path §8](CRITICAL-PATH.md)
   now defines A-unit, A-density and B-score with their assumptions and falsifiers.
   None is selected as a consensus weight. The remaining gap is acquisition/reuse
   cost and adversarial monotonicity, not another local counter or timer.
2. **D3: Does the screening signal reproduce on fresh streams?** The frozen
   campaign completed 288 runs. A `(17,3,16,12)` shows about 2.75x against all
   controls, but controls each have four successes, below the declared floor of
   five. Five of six primary comparisons are insufficient; one is not triggered.
   A separately precommitted fresh-stream replication must establish sufficient
   controls before D3 can resolve. Do not lower the threshold or reinterpret the
   existing run as a kill/pass. This remains a scoped experimental rule, not a
   theorem about all SIS-PoW. See [findings](FINDINGS.md).
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

Next implementation batch should resolve the D3 screening signal with an explicit
fresh-stream protocol, not add another solver/GPU interface. Keep negative findings in the central
[findings page](FINDINGS.md). Wallets, payments and production retarget remain
parked while the work-weight question is unresolved.
