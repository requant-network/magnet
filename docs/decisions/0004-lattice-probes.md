# ADR 0004: lattice reduction misses do not certify SIS nonexistence

Date: 2026-10-08. Status: accepted research constraint.

## Evidence

The [exact LLL experiment](../research/lattice-reduction-v1.md) audits full kernel
bases and unimodular transformations on 1100 deterministic toy matrices. A
finite reduced-row/two-row probe finds a solution on 457 of 458 solvable
instances, compared with exhaustive native enumeration. One completed,
independently LLL-certified basis still misses an existing norm-12 vector.
The frozen regression preserves the counterexample.

## Decision

- Treat reducedness, lattice equivalence, accepted-vector validity and discovery
  success as separate properties. None is a certificate of runtime/work spent.
- Use an empty bounded probe only as a failed discovery attempt, including when
  LLL has completed. Claim bounded-domain nonexistence only from complete exact
  enumeration or another independently justified nonexistence argument.
- Keep capped reduction/oracle statuses and conditional comparison denominators.
- Do not calibrate difficulty or chainwork from exact-reference reduction time,
  basis determinant, proof count or failure of this particular candidate family.

## Limitations and next gate

The probe is deliberately small and LLL is exact-rational reference code.
This does not measure practical LLL/BKZ/sieving, mainnet hardness, parallel speed,
quantum security or network service delivery. The result neither rejects every
SIS-PoW candidate nor closes E2/E3. Header binding, independent generation and
stronger solver/reuse comparisons precede work/consensus selection.
