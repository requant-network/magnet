# 0015: Keep native and fused search as measured laboratory baselines

Date: 2026-10-09. Status: accepted for research; production work remains open.

The independent native and fused implementations preserve spec/18's restricted
domain and full paid-chunk semantics. The 600-attempt study has no disagreements
and verifies every returned occurrence independently. It is appropriate to keep
both implementations as correctness/optimization baselines.

Fusing reduces measured wrapper overhead compared with the same-run PyTorch
implementation. Native engine time is also very short. Their measured scopes
and transport/verification boundaries differ, so no portable CPU/GPU winner,
energy price, ASIC resistance or production chainwork follows. Cheap search in
a restricted sparse domain is not a secure work function.

Do not change accepted profiles, block scores, retarget or fork weights based
on these timings. Preserve failed search, caps, setup and cold/runtime costs in
future comparisons. Next compare matched in-process integration and competing
solver families before revisiting production work pricing. The local CUDA FFI
is an owned trusted-process boundary, not an exposed service or sandbox.

Evidence: [report](../research/native-fused-column-v1.md),
[contract](../../spec/19-native-fused-column-search.md),
[compact results](../research/results/native-fused-column-v1.json).
