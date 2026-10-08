# Exact lattice-reduction baseline v1

Research only. SIS-LAB-v1 acceptance and the native search protocol are unchanged.
The solver accepts a supplied lab matrix; it does not bind a block header,
assign work/difficulty or implement consensus. Standard Python libraries only.

## Integer kernel basis

For prime q and A with m columns, define L={x in Z^m : A*x=0 mod q}.
Perform full RREF over F_q, with leftmost pivots and first available pivot row.
Let r be the rank and P the pivot columns. Generate m basis rows:

- q*e_p for each p in P, in ascending pivot order;
- for each free column f, a vector with coordinate f=1, other free coordinates
  zero and pivot coordinate p_i equal to -R[i,f] modulo q.

Choose the centered representative v or v-q, using v if 2*v <= q. Rows are
in original coordinate order. This works with noninitial pivots, rank-deficient
A, zero rank and r=m, not just full-row-rank rectangular matrices.

Every generated row belongs to L. Permuting pivot/free coordinates shows a
triangular basis with absolute determinant q^r. The homomorphism A modulo q
has image of size q^r, so L also has index q^r in Z^m. Membership and equal
index establish that the basis spans the entire integer kernel, rather than
only a sublattice. Coordinates are integers, not field-kernel vectors used
without their q*e_p lifts. There is no divisibility/gcd reduction of a row.

## Exact LLL

Reduce this full-rank square basis using delta=3/4, eta=1/2. Recompute
Gram-Schmidt from scratch with fractions after every size reduction or swap.
Size-reduce k against j=k-1,...,0 when abs(mu[k,j])>1/2; subtract the nearest
integer multiple of row j. Ties round towards +infinity. Coefficients exactly
at abs(mu)=1/2 are already allowed and do not trigger a reduction.

Accept the adjacent Lovasz test iff
`D[k] >= (3/4-mu[k,k-1]^2)*D[k-1]`. Otherwise swap adjacent rows and resume
at max(1,k-1). At all times keep an integer transformation U with B=U*B0.
Swaps and row subtraction are unimodular operations. The basis is never
canonicalized or sorted after LLL; candidate sign normalization is separate.

Completion status `lll-reduced` means the exact reduction loop finishes. Other
statuses are `step-limit`, `reduction-limit` and `arithmetic-limit`. Limits:
m<=16, 1..10000 outer steps, 1..10000 size reductions, 1..4096 checked bits.
Profile/parser limits remain those of SIS-LAB-v1. Invalid API arguments raise
ValueError before the corresponding search. Identity transformation and the
initial basis are returned even if the initial basis exceeds the bit allowance.

Check integer row/U entries before committing a size reduction and fractions
after dot/projection operations. Arithmetic may transiently exceed the allowance
while forming the checked value. This is an arithmetic-growth guard, not a hard
byte/time cap or an arbitrary-precision memory guarantee. A cap can occur after
a committed valid row operation, leaving a nonreduced but equivalent basis.
All returned certificates must pass membership/index/unimodularity audit;
capped bases are not claimed LLL-reduced or evidence of nonexistence.

## Independent certificate audit

The audit uses integer Bareiss determinants and the integer Gram matrix's exact
LDL recurrence, not the solver's orthogonal-vector Gram-Schmidt implementation.
Require bounded square integer matrices, rank equal to independent modular rank,
abs(det(B0))=q^r, B0 rows in the kernel, abs(det(U))=1 and B=U*B0.
For completed reductions, independently require every abs(mu)<=1/2 and every
adjacent Lovasz inequality. This certifies equivalence/reducedness, not shortest
vector optimality, SIS hardness or the amount of computation a prover spent.

## Candidate probe

Inspect each reduced basis row, then every unordered pair i<j with coefficients
a in {1,2}, b in {-2,-1,1,2}, in that order. Canonicalize the vector's sign,
measure squared norm and verify every potentially acceptable vector with the
existing SIS verifier. Deduplicate accepted vectors. Report row-only proofs
separately from pair-derived proofs, proposals and minimum nonzero proposed norm.
At most m+8*choose(m,2)<=976 proposals with an independent 1..4096 cap.

`probe-exhausted` only exhausts this proposal family. It is not exhaustive
enumeration of the lattice or the SIS norm ball. Both capped and completed
reductions may be probed, with their separate reduction status retained.
An empty probe does not prove there is no accepted solution. The experiment's
native exhaustive solver supplies comparison truth only after reduction/probing;
it never supplies a starting solution or modifies the lattice basis.

## Sources and scope

The [CNRS exercise notes](https://apelletm.pages.math.cnrs.fr/page-perso/documents/enseignement/summer_school_Budapest/exercises_1_solutions.pdf)
give the SIS kernel-lattice definition. The basis/index argument above is the
implementation's explicit derivation. [Magma's reduction documentation](https://magma.maths.usyd.edu.au/magma/handbook/text/335)
states the LLL inequalities, classical parameters and unimodular transformation
contract. This code is an independent exact reference, not Magma/fplll/BKZ or a
performance-equivalent implementation. Checked 2026-10-08.
