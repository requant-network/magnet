# Independent fixed-policy Rust chain and local MCP1 adapter

Research implementation of spec 11. It independently decodes MGB1, computes body/
descriptor/block hashes and performs every linear-chain admission/state step.
Rust reuses its existing independent SHA-256, MGH1 and SIS verifier. Python does
not supply trusted verdicts, decoded fields or block IDs to Rust.

## MCP1 trusted initialization (135 bytes)

| Offset | Field |
|---|---|
|0|MCP1, 4 bytes|
|4|network, 32 bytes|
|36|profile, 16 bytes using existing q/n/m/B2 encoding|
|52|target, unsigned 33-byte BE|
|85|anchor ID, 32 bytes|
|117|anchor height, u64 LE|
|125|anchor time, u64 LE|
|133|future tolerance, u16 LE|

Profile bounds as spec 04, q=2 excluded, target strictly in (0, 2^256), future
tolerance 0..3600. Configuration comes from the local caller, never the first
peer block. All commands use u32-LE length frames, bounded to 1756 bytes before
allocation. Empty stdin returns cleanly. Malformed framing/policy/command exits
nonzero with a bounded diagnostic. This is local IPC, not a network protocol.

First frame initializes policy and returns the empty snapshot. Subsequent frames:
1 || u64LE(now) || MGB1 for append; 2 || u64LE(now) || MGB1 for inspect;
single byte 3 for snapshot. At most 8192 commands after initialization.

Each reply is exactly 43 bytes: status u8, height u64LE, tip32, count u16LE.
Codes 0..8: accepted, malformed, wrong-policy, unknown-or-nontip-parent,
wrong-height, past-time, defer-future-time, invalid-proof, storage-limit.
Inspect never appends. Snapshot uses status0 without implying a new block.

Spec11 rejection precedence remains unchanged: canonical decode/commitment,
policy, parent, height, upper median of last 11 (anchor before first), saturated
trusted-now future bound, full proof, then 4096-block storage cap. In particular,
an invalid proof at full capacity returns invalid-proof. No fork rule, variable
target or transaction meaning is added to this independent engine.

The local gate compares full state after every command, malformed/near-valid
corpora, inspect/replay/deferred retries, median time, saturated clock/height and
a reachable complete 4096-block chain with valid/invalid over-cap candidates.
