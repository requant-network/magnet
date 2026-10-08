# Native score and trusted-rule transport v1

Status: implemented laboratory acceptance, independently in Python and Rust.
No production consensus, block-body validity, chain-derived target or work weight
is selected. MGH1, its instance seed and the existing score remain unchanged.

## SHA-256 and score

`sha256::digest` implements bounded SHA-256 according to [FIPS 180-4](https://csrc.nist.gov/pubs/fips/180-4/upd1/final),
using big-endian words/bit length, wrapping u32 compression arithmetic and a
maximum message length of 2048 bytes. The cap precedes padding/allocation. Tests
include fixed known answers and differential messages at padding transitions and
the maximum length. This handwritten laboratory implementation is not certified
or a replacement for audited production cryptography.

`score::digest(packet)` computes the existing Python predicate:

~~~text
SHA256("MagnetNetwork/SIS-LAB/grinding-score/v1\0" || canonical_MGH1_proof)
~~~

The domain terminates with an actual zero byte. A proof has a 140-byte MGH1 header
and exactly m signed-i32 little-endian coordinates. `score::digest` bounds input
to 652 bytes; hashing alone does not prove validity. `verify_scored_proof` first
rejects target zero, then independently checks bound SIS validity/context and
strictly compares the score as a big-endian integer to the external target.

Targets use **33 big-endian bytes**, permitting exactly 0 through 2^256. High
byte 0 permits any following 32 bytes; high byte 1 requires all remaining bytes
zero. Other encodings are rejected. This represents the full inclusive domain
of external thresholds while keeping the score predicate strict: score = T
rejects; T=0 accepts none; T=2^256 accepts all otherwise valid proofs. Target bytes
are local adapter transport, not a miner-selected field in a block.

## Canonical LabRules wire

Python `reference.admission_wire` and Rust `rules::LabRules::decode` implement:

| Offset | Bytes | Field |
|---:|---:|---|
| 0 | 88 | ExpectedContext from spec 04: network, parent, height, profile |
| 88 | 33 | External target, big-endian |
| 121 | 8 | Earliest timestamp, u64 little-endian |
| 129 | 8 | Latest timestamp, u64 little-endian |
| 137 | 1 | Allowed payload count k, 1–8 |
| 138 | 32k | Distinct allowed payload commitments, in configured order |

Exact total length is 138+32k, 170–394 bytes. Earliest must not exceed latest;
profile/context and target must validate; duplicate payloads, truncation and
trailing data are rejected. Configuration order is preserved, not sorted. Rust
keeps decoded fields private so a constructed object cannot bypass validation.

Admission rejects a zero target, malformed proof, forbidden timestamp/payload,
context/profile mismatch, length/sign/norm violations before matrix derivation.
It then regenerates A, checks SIS and the current-header score. The parent/time/
payload limits have the same scope as LabRules in spec 08: they do not validate
an actual parent chain, body or consensus clock. Trusted rules must originate
outside the proof. The local framed stream is not an authenticated remote API;
an attacker choosing its whole request also chooses its asserted policy.

## MGL1 extension

Existing modes 0–3 and framing limits are unchanged. New modes:

| Mode | Request after `MGL1` + mode byte | Response |
|---:|---|---|
| 4 | Raw message, 0–2048 bytes | 32-byte SHA-256 |
| 5 | Context(88) + target(33) + proof | One byte 0/1, scored bound validity |
| 6 | Rules length(u16 LE) + rules + proof | One byte 0/1, full lab admission |

Malformed trusted configuration/commands cause adapter failure; a well-configured
invalid proof returns 0. Mode 6 uses checked slicing for its declared rules length
before decoding. Unknown command 7 is retained as a rejection regression; mode 4
is now intentionally supported. No mode permits a supplied matrix to stand in
for a bound proof. Request cap remains 2057 bytes; response limits and empty-stream
semantics remain from spec 04. These helpers run only as caller-controlled local
processes with external timeout, not listeners.

## Regression gate

`tests/vectors/admission-v1.json` freezes one existing MGH1 proof, vector, digest,
rule bytes and targets 0, 1, digest, digest+1, 2^256−1 and 2^256. It is not rebuilt
during checks. The Python gate reads it and executes both native score and
admission through independently implemented adapters, preserving strict equality.

`scripts.admission_checks.differential_admission` uses seed 2026100809, 568 raw
SHA-256 messages and 512 structured header families, with profiles q7/q17/q257,
n1/m3/B²8. Canonical valid vectors are selected by an independent tiny exhaustive
oracle when one exists; otherwise a candidate remains invalid. These oracles
are test-corpus preparation, never a source of free mining acquisition.
The corpus checks 10814 cases and 13 malformed requests: padding transitions,
strict thresholds, sign changes, mutations, nonce/time/payload/context changes,
malformed rules and maximum payload lists. Mutations may remain mathematically
valid; expected acceptance is recomputed rather than assumed false.

This gate complements existing SIS/generation/binding corpora. It is neither
long-running fuzzing nor a cryptographic audit. The lab's original specification
had Python-only score/admission; this extension closes that implementation gap
without calibrating difficulty or selecting network consensus.
