# MGB1 blocks and fixed-policy linear laboratory chain

This is an executable research envelope, not production consensus. The MGH1/SIS
predicate and score domain remain unchanged. Opaque body bytes carry no transaction
meaning. Recipient is an opaque32-byte commitment; there are no balances/rewards.

## Encoding and binding

All concatenation below is exact; domains include the terminating NUL byte.

| Field | Encoding |
|---|---|
| Magic/version | ASCII MGB1,4 bytes |
| Target | canonical unsigned33-byte big endian,0..2^256 |
| Recipient |32 opaque bytes |
| Body length |u16 little endian,0..1024 |
| Body |exact declared byte count |
| Proof |MGH1 header140 bytes plus m signed-i32 LE coordinates |

Prefix71 bytes, maximum block1747 bytes. No padding/trailing data. Unknown version,
oversized body, malformed profile/header/proof length or noncanonical target rejects.

body_root = SHA256(`MagnetNetwork/block-body/v1\0` || u16LE(body_len) || body).

header.payload = SHA256(`MagnetNetwork/block-commit/v1\0` || `MGB1` || target33BE ||
recipient32 || body_root32).

block_id = SHA256(`MagnetNetwork/block-id/v1\0` || entire canonical encoded block).

Body, target, recipient and envelope version thereby affect the SIS challenge and
score. Proof malleability can give distinct block IDs for distinct valid vectors;
that is permitted, with no assumed anti-reuse or priced work property.
Header network/parent/height/timestamp/nonce/profile use spec04; proof score spec09.

## Trusted chain policy and admission

Externally configured anchor ID/height/time, network, one fixed profile and one
fixed target strictly in (0,2^256). q=2 is ineligible. Future tolerance0..3600 seconds.
All values are typed/bounded before execution. This configuration is not inferred
from the first peer-supplied block. Anchor is a trusted research checkpoint, not
a generated monetary genesis. Maximum4096 appended blocks prevents unbounded RAM.

Admission in order: canonical decoding/commitment; network/profile/target;
parent equals current tip; height exactly tip+1 without u64 overflow; timestamp
strictly above median of last11 appended timestamps (upper median for even short
prefix), using anchor time before the first block; timestamp <= trusted local now
+future tolerance with saturated u64 arithmetic; full bound SIS+outer-score proof;
storage cap. All before-matrix header checks reject without challenge expansion.
Body commitment hashing is bounded but precedes header-surface checks.

Future-time status is deferred and can be retried. Unknown/non-tip parent is a
separate status, not a assertion that another branch is intrinsically invalid.
There is no orphan buffer, fork choice, reorg, retarget, peer clock or network I/O.
Append mutates state only after full acceptance. Returned block history is a tuple
of immutable objects; nominal chain weight is accepted-block count only under
identical fixed policy. It is not calibrated SIS work and must not price competing
targets/profiles. Chain rules are Python-only at this milestone; existing Rust
independently checks hashing preimages and bound proof admission, not MGB1 parsing
or the chain state machine. Add an independent full engine before node deployment.
