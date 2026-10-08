# Precommitted pool supply model v1

This isolated research model does not change MGH1/MGB1 admission, fork choice or
targets. Existing Profile requires prime q, n<=64, m<=128 and 1<=B2<q^2.

## Contract and mathematical model

Fix 1..6 distinct canonical signed-32 vectors of dimension m and norm squared
<=B2 BEFORE seeing the fresh matrix. They may be proportional modulo q. A has
n independent uniform rows in F_q^m. This is an explicit probability model,
not a proved distribution of deterministic header expansion or an adaptive miner.

For subset S of the pool, let r(S) be its rank over F_q. The linear row map
a -> (a dot x)_(x in S) has q^r equally populated outputs. Thus
P(all vectors in S valid)=q^(-n*r). Each nonzero accepted vector has nonzero
residue modulo q because B2<q^2, giving the marginal q^-n.

Let K be the number of valid vectors and F_r=sum_(|S|=r) P(S all valid), F_0=1.
Then F_r=E[choose(K,r)], and exact binomial inversion gives
P(K=k)=sum_(r>=k) (-1)^(r-k)*choose(r,k)*F_r. The implementation checks
nonnegativity, total mass and E[K]=pool_size*q^-n using exact fractions.

For a separate hypothesis, scores for DISTINCT header/proof inputs are iid uniform
256-bit values CONDITIONAL ON the entire matrix and its valid-vector set. At
strict target T, p=T/2^256. A pool-only header succeeds with model probability
sum_k P(K=k)*(1-(1-p)^k). This includes T=0 and T=2^256. Independence among scores
alone is insufficient. SHAKE/SHA-256 domain separation does not prove this hypothesis.

The independent-vector shortcut 1-(1-p*q^-n)^pool_size is shown only for comparison.
It is exact for a linearly independent pool under both hypotheses, and can fail
for dependent pools even when every PAIR is independent.

## Resource contract

At most 63 nonempty subsets, each with at most 6 rows and 128 columns, are reduced
by modular Gaussian elimination. A caller may lower the shared 250000 arithmetic
unit ceiling; normalization charges one unit/coordinate, elimination two. Charge
before mutating rows; cap throws and returns no partial exact distribution.
Pivot scans, modular inverses, Python allocation and fraction work are not priced
by that counter. All remain bounded by the fixed profile/pool shapes.

Matrix-law exponents are <=384. Since q<2^16, denominators divide q^384 and
use at most 6144 bits. Score mixture adds at most 1536 denominator bits, so its
denominator divides q^384*2^1536, at most 7680 bits. The public score helper
also bounds each supplied fraction numerator/denominator and their least common
denominator to 6144 bits before summing an externally supplied histogram.
These are computational
bounds, not measured time, memory hardness, energy or consensus work.

## Experiment boundary

Full enumeration of bounded tiny matrix spaces is an independent arithmetic oracle.
Fresh real headers are a separate deterministic cohort: setup vectors are acquired
and charged first, then held fixed through fresh parent/height/nonce schedules.
Every supplied vector is checked, every valid vector is scored without early
success stopping, and native generation/validity/score results are compared.
Every setup header and every returned setup proof also receive independent native
generation/validity audits. Setup cost is retained; no free acquisition or
cross-profile work weighting follows. A 16-attempt setup with no returned vector
is recorded with its full costs and stop reasons; three dependent cohorts are
explicitly skipped. No law for a nonexistent pool or absence-of-solutions claim
is fabricated. Native proof-limit output may be a partial pool, not a complete oracle.

Exact law agreement certifies the model arithmetic. Finite header frequencies
neither prove uniformity nor bound adaptive, sparse/LLL/BKZ/GPU miners. No portable
adversarial SIS work argument or production retarget decision is delivered.
