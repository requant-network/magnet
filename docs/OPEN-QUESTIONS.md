# Open questions

Date: 2026-10-10. **The programme is closed** ([NEGATIVE-RESULT.md](NEGATIVE-RESULT.md),
[ADR 0020](decisions/0020-close-sis-pow-programme.md)). The questions below stay unresolved in the
general sense but will not be pursued. The only outstanding request is an external review of the
closing note. The list is kept as it stood at closure.

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
   more accepted proof occurrences cannot substitute for this argument. Exact
   complete-kernel transfer now has a conditional fresh-uniform bound and an
   audited8-worker integration; this route is parked under that assumption.
   Partial bases, donor geometry, same-header solution supply and adaptively
   selected headers remain unresolved. See [findings](FINDINGS.md).
   The proof-independent B-H repair's [section11 test](CRITICAL-PATH.md) is now
   complete: two nonempty primary pairs demonstrate public-gate bypass with
   identical admitted outputs. Its fresh-SIS-per-hash amplification premise is
   rejected; this does not complete D4 partial preparation or reject hash credit.
4. **D5: What must the hardware comparison establish?** The current matched
   small-family pilot fixes timer/domain ambiguity. Energy, memory trade-offs,
   stronger CPU baselines and a smallest relevant non-toy profile remain absent.
   Proceed only if a specific candidate weight makes those measurements decisive.
5. **D6: Who independently reviews the argument?** External cryptographic review
   of the framing/weight is still needed. Local source review checks implementation
   and evidence, not economic or cryptographic security.

Next D4 experiment must name a revised weight and one concrete partial-preparation
or same-header amortization attack whose result can falsify its monotonicity.
Do not rerun the B-H gate demonstration: making the score proof-independent
does not price SIS at every hash trial. A new candidate must state whether SIS
supplies the difficulty itself or is a separate filter of a hash-PoW mechanism.
The full-kernel collision diagnostic should not grow into a low-power timing
survey: its conditional mathematical law already answers that narrow question.
The [CPPminer/Tensor Core option](research/gpu-readiness-v1.md) is parked for D5
until it advances a specified work hypothesis. Keep negative findings in the central
[findings page](FINDINGS.md). Wallets, payments and production retarget remain
parked while the work-weight question is unresolved.
The owner has reserved the GPU for other work; do not use it or stop its miner
until explicitly released. Current work is local CPU-only.
