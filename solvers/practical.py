"""Optional in-process FLINT adapter, explicitly run inside the isolated environment."""

import time

from solvers.flint_worker import backend_metadata, reduce_case
from solvers.lattice import LatticeWork, Reduction
from solvers.lattice_audit import audit_certificate


class PracticalReducer:
    def __init__(self):
        start = time.perf_counter_ns()
        self.backend = backend_metadata()  # Enforces the same pinned package version.
        import flint
        flint.fmpz_mat([[1]]).lll(transform=True, delta=0.75, eta=0.5)
        self.setup_ns = time.perf_counter_ns()-start

    def __call__(self, profile, matrix):
        entry = reduce_case(profile, matrix)
        reduction = Reduction(entry["initial_basis"], entry["basis"], entry["transform"],
                              entry["rank"], entry["reason"], LatticeWork())
        start = time.perf_counter_ns()
        certificate = audit_certificate(profile, matrix, reduction)
        return {"reduction": reduction, "audit": certificate,
                "construction_ns": entry["construction_ns"], "reduction_ns": entry["reduction_ns"],
                "audit_ns": time.perf_counter_ns()-start}
