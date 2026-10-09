# Native small-coefficient search

Status: local research only. Separate API; SIS1, spec21 and consensus unchanged.

Five tasks: bounded wire/engine contract; independent Rust implementation;
strict Python adapter; differential/boundary corpus; fresh-seed robustness and
explicitly scoped local measurements.

## Domain and input

Exactly spec21 order/validity: support<=3, coefficient bound1/2, first nonzero
positive, norm<=B2, nonprimitive vectors included. Existing prime profiles are
restricted to m<=16,B2<=12; n<=64. Candidate cap1..20000, proof cap1..256.
Validate profile, dimensions, exact length, bound, caps, reserved fields and
matrix residues before matrix/search allocations. Rust uses safe owned buffers,
integer arithmetic and the existing unsafe-code prohibition.

SCP1 is little-endian `<4sIHHQB3xII`: magic,q,n,m,B2,bound,three reserved zero
bytes,candidate cap,proof cap. Follow with n*m uint32 row-major matrix entries.
A uint32 frame length precedes each request; accepted size32..4128. Invalid
frames/requests terminate with nonzero exit; batch clients cannot use partial
outputs after failure. Empty stream succeeds with empty output.

## Response

Each SCR1 response is uint32-length-framed. Fixed header `<4sBBHHHIIQ` is28
bytes: magic,reason,exhausted,reserved zero,width,pattern count,proof count,domain,
native elapsed nanoseconds. Reason1=proof-limit,2=candidate-limit,3=domain-exhausted.
Then13 uint64 work counters in order: template_visits,template_norm_terms,
generated,screened,matrix_terms,row_reductions,returned,vector_entries,gcd_terms,
primitive_returned,nonprimitive_returned,validation_matrix_entries,
validation_vector_entries. These are spec21 logical counters, not instructions.

Then three `<QQQ` weight records (domain,tested,accepted), including zero records
for weights exceeding m; then pattern_count `<B3bQQQ` records: weight,three signed
coefficients zero-padded,domain,tested,accepted. Norm-filtered patterns occur in
spec21 order. Follow with proof_count*m int32 coordinates. Maximum response17764
bytes: fixed204,42 patterns*28,256 proofs*16*4. Reject unknown/reserved fields,
noncanonical patterns, duplicates, impossible counts and inconsistent flags.

The sequential cap-triggering proof is paid. Proof-limit takes stop precedence,
with an independent exhausted flag. Exactly sufficient candidate cap exhausts
the domain. Every accepted tested candidate is returned; unseen suffix acceptance
is unknown. No accepted chunk tail exists. Full native/Python proof order,
work/census and stopping results must match in differential studies.

## Client validation and evidence

Strict integer settings reject booleans before narrowing. Bound batch size4096
requests and total response bytes accordingly. Timeout, native exit, diagnostics,
truncation, extra frames or semantic corruption invalidate the entire exchange.
The decoder validates returned proofs with independent Python SIS validity and
prefix membership/order. Structural counter/census checks precede consumption;
full differential reconciliation and independent tiny box audits validate the
remaining search completeness/operation hypotheses. Never accept a native miss
as general SIS nonexistence, or silently fall back to Python.

Native timer starts after reading the frame, before request validation, and ends
after search/censuses but before SCR1 serialization. Python search timing covers
its existing validation/enumeration/result assembly. Batch roundtrip covers fresh
process launch and transport; request encode and host decode/audits are outside.
Scopes differ; report them separately, retain all repetitions and require strict
positive elapsed samples. No mixed-scope speedup or portable winner is claimed.

Frozen comparison: profiles(7,1,5,8),(17,2,12,12),(257,2,16,12),(65521,64,16,12),
seed labels2026100917/2026100918, bounds1/2, settings(cap,proofs)=(1,1),(31,3),
(4096,32),(20000,256),three repetitions. Include zero,triple-only,nonunit-only,
scalar-copy and singleton fixtures, both bounds and cap settings. A separate
fresh/control refresh cohort uses seeds2026100919/2026100920/2026100921, four
steps, the same profiles, both bounds, pool32 and acquisition cap4096/proofs32.
Public ASCII labels commit version,cohort,profile,seed,step; SHA256 seeds SIS1
SHAKE. Controls repeat fresh step0; sequential pools/repeated seeds are correlated.

Capture Cargo-selected release search and verifier hashes before all experiments,
freeze sources/configuration and exact raw UTF8/LF digest through publication.
Invalidate old evidence before builds; failures preserve completed records and
unknown current work, never successful timing summaries. Local checks and affected
survey pass before commit. No new dependencies/cloud/GPU/Actions are needed.
