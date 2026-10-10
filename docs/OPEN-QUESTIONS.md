# Open questions

Date: 2026-10-10. This page complements the working task ordering in
`docs/CRITICAL-PATH.md`; it is not another parallel roadmap.

1. **D2: Can any explicitly defined credit price adversarial work?** The
   [critical path §8](CRITICAL-PATH.md)
   now defines A-unit, A-density and B-score with their assumptions and falsifiers.
   None is selected as a consensus weight. The remaining gap is acquisition/reuse
   cost and adversarial monotonicity, not another local counter or timer.
2. **D3: What screening attacks remain?** The selected2.75x signal does not
   reproduce in the precommitted24-stream cohort (576 runs). A and B now have
   sufficient successes for every policy; neither >2x diagnostic triggers.
   This specific replication is complete, not a claim that arbitrary screening
   cannot win. Keep the earlier288-run evidence separate and do not pool/tune it
   retrospectively. See [findings](FINDINGS.md).
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

Next implementation batch should precommit the D4 first/subsequent acquisition
comparison, defining the externally bound instance and paid setup/reuse scopes.
The [CPPminer/Tensor Core option](research/gpu-readiness-v1.md) is parked for D5
until it advances a specified work hypothesis. Keep negative findings in the central
[findings page](FINDINGS.md). Wallets, payments and production retarget remain
parked while the work-weight question is unresolved.
