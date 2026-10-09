# Unit-sparse column search optimization v1

Preserve spec/17's candidate domain, order, candidate/proof limits, chunk charging,
stop precedence and completeness flags. Dense Python/CUDA implementations remain
available. The optimized backends are python-columns and cuda-columns, supporting
batch widths 1–4096, candidate limits 1–16384 and proof limits 1–256.

Represent a singleton by (first,first,0), or a pair by (first,second,+/-1).
Its SIS residual is A[:,first]+sign*A[:,second]. CUDA generates ordinal/support
arrays itself using exact integer triangular prefixes; it does not receive
host-generated candidate supports or solutions. CPU independently enumerates
supports using itertools. Arithmetic and CUDA tensors use int64 throughout.
Residuals lie within +/-2*(q-1), far below int64 overflow.

Transfer one boolean CUDA mask per checked chunk to the host. The host counts
all accepted candidates and reconstructs only the remaining returned prefix
from its ordinals. This deterministic decoding is not CPU discovery of valid
solutions. There are no explicit CUDA ordinal/count scalar or vector readbacks.
Implicit runtime/shape/command traffic is outside explicit tensor-byte metrics.
Proof-limit tails remain paid; matrix transfer occurs once per invocation.

Common counters preserve domain proposals, checked candidates, batches,
accepted_seen, returned, matrix setup entries and the historical scheduled dense
matrix-grid metric. Materialized vector_entries now count returned*m rather
than checked*m. New support_entries count three coordinates/coefficients per
checked candidate; scheduled_column_reads count 2*n*checked. CPU can short-circuit
rows, so read counters are a schedule/upper-bound metric, not measured CPU
operations. Record host/device prefix tables and CPU column-table setup separately.

Host Profile/matrix validation and strict type/range caps precede optional
runtime allocation. Conservative logical device allowance is
8*(10*batch*n+20*batch+2*n*m) <=64MiB. Context, runtime, cached allocations and
host Python objects are additional; this is not an external memory ceiling.
CUDA failure propagates without CPU fallback. Search timers include setup,
candidate/support generation, screening, transfers and output reconstruction.

Evidence must compare legacy-width jobs across dense and optimized backends,
then compare columns at larger widths under identical cap settings. Do not
require vector materialization or transfer ledgers to equal dense algorithms;
validate each ledger against its algorithm instead. Outside paid search, audit
the entire device-generated support order against independent host vectors,
and independently verify every returned proof with native Rust.

Preserve seeds, configuration, all completed attempt records, source/binary
fingerprints, setup and timing scope. Failed studies invalidate evidence.
Changing batch widths changes paid proof-limit tails; timings across widths
are not automatically equal-work comparisons. Reference Python baselines are
not optimized native CPU competition. No consensus, energy, hardness or portable
GPU advantage claim follows from these local bounded observations.
