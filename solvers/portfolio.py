"""Paid optional solver portfolio, intended only inside a resource-limited worker."""

from dataclasses import asdict, dataclass
import math
import random
import time

from reference.reuse import canonical
from reference.sis import Profile, verify
from scripts.native_driver import encode_request, run_requests
from solvers.blockwise import bkz_tours
from solvers.flint_worker import backend_metadata
from solvers.lattice import LatticeWork, Reduction, kernel_basis
from solvers.lattice_audit import audit_certificate
from solvers.sphere import enumerate_kernel

BACKENDS = ("mitm", "sparse-first", "lll75", "lll99", "bkz4", "bkz8", "sieve")


@dataclass(frozen=True)
class PreparedLattice:
    """Owned local preparation; its immutable matrix key is not a proof cache."""
    profile: Profile
    matrix: tuple
    reduction: Reduction
    work: dict
    timers: dict
    certificate: dict


class Portfolio:
    def __init__(self, backend, native, seed):
        if backend not in BACKENDS or type(seed) is not int or not 0 <= seed < 2**64:
            raise ValueError("portfolio configuration")
        begin = time.perf_counter_ns()
        self.backend, self.native, self.seed = backend, native, seed
        self.calls = 0
        self.metadata = {"backend": backend, "seed": seed}
        if backend not in ("mitm", "sparse-first"):
            import flint
            self.metadata["flint"] = backend_metadata()
            flint.fmpz_mat([[1]]).lll()
        self.setup_ns = time.perf_counter_ns()-begin

    def acquire(self, profile, matrix, nodes, proofs):
        self.calls += 1
        begin = time.perf_counter_ns()
        if self.backend == "sparse-first":
            sample = sparse_probe(profile, matrix, nodes, proofs)
            vectors, reason = sample["proofs"], sample["reason"]
            work, timers, certificate = sample["work"], {}, None
        elif self.backend == "mitm":
            sample = run_requests(self.native, [encode_request(profile, matrix, "mitm-budgeted", nodes=nodes,
                                  proofs=proofs, table=100_000, pairs=1_000_000)])[0]
            vectors = sample["proofs"]
            work = {"nodes": sample["work"]["nodes"], "native": sample["work"]}
            reason = sample["stop"]
            timers = {"native_inner_ns": sample["elapsed_ns"][0]}
            certificate = None
        else:
            prepared = self.prepare(profile, matrix, nodes)
            extra = prepared.work
            remaining = nodes-extra["bkz_nodes"]
            sample = self.search_prepared(prepared, remaining, proofs, seed=self.seed+self.calls)
            vectors, reason = sample["proofs"], sample["reason"]
            work = {"nodes": sample["work"]["nodes"]+extra["bkz_nodes"],
                    "search": sample["work"], **extra}
            timers, certificate = prepared.timers, prepared.certificate
        unique = tuple(dict.fromkeys(map(tuple, vectors)))
        if len(unique) != len(vectors) or not all(verify(profile, matrix, x) for x in unique):
            raise RuntimeError("portfolio returned invalid/duplicate proof")
        return {"proofs": unique, "reason": reason, "work": work, "timers": timers,
                "certificate": certificate, "elapsed_ns": time.perf_counter_ns()-begin,
                "profile": asdict(profile)}

    def prepare(self, profile, matrix, nodes):
        """Separate existing lattice preparation for the D4 paid-reuse experiment."""
        if self.backend in ("mitm", "sparse-first") or type(nodes) is not int or not 1 <= nodes <= 1_000_000:
            raise ValueError("lattice preparation backend/nodes")
        import flint
        start = time.perf_counter_ns()
        initial, rank = kernel_basis(profile, matrix)
        construction_ns = time.perf_counter_ns()-start

        def lll(basis):
            b, t = flint.fmpz_mat(basis).lll(transform=True, delta=0.75 if self.backend == "lll75" else 0.99,
                                          eta=0.5, rep="zbasis", gram="exact")
            return tuple(tuple(int(x) for x in row) for row in b.tolist()), tuple(tuple(int(x) for x in row) for row in t.tolist())
        start = time.perf_counter_ns()
        basis, transform = lll(initial)
        extra = {"bkz_nodes": 0}
        if self.backend in ("bkz4", "bkz8") and nodes >= 2:
            basis, transform, extra = bkz_tours(basis, transform, lll, block_size=int(self.backend[-1]),
                                               node_limit=max(1, nodes//2))
        reduction_ns = time.perf_counter_ns()-start
        reduction = Reduction(initial, basis, transform, rank, "lll-reduced", LatticeWork())
        start = time.perf_counter_ns()
        certificate = audit_certificate(profile, matrix, reduction)
        audit_ns = time.perf_counter_ns()-start
        return PreparedLattice(profile, tuple(map(tuple, matrix)), reduction, extra,
                               {"construction_ns": construction_ns, "reduction_ns": reduction_ns, "audit_ns": audit_ns}, certificate)

    def search_prepared(self, prepared, nodes, proofs, *, seed):
        """Search only; caller pays preparation and enforces the current matrix key."""
        if (not isinstance(prepared, PreparedLattice) or type(nodes) is not int or not 1 <= nodes <= 1_000_000
                or type(proofs) is not int or not 1 <= proofs <= 100_000
                or type(seed) is not int or seed < 0):
            raise ValueError("prepared search bounds")
        if self.backend == "sieve":
            return gauss_sieve(prepared.profile, prepared.matrix, prepared.reduction.basis, nodes, proofs, seed)
        if self.backend not in ("lll75", "lll99", "bkz4", "bkz8"):
            raise ValueError("prepared search backend")
        return enumerate_kernel(prepared.profile, prepared.matrix, prepared.reduction,
                                node_limit=nodes, proof_limit=proofs)


def gauss_sieve(profile, matrix, basis, node_limit, proof_limit, seed):
    """Finite seeded pair-reduction sieve: no completeness or high-dimensional claim."""
    rng = random.Random(seed)
    pool, solutions, seen = [], [], set()
    nodes, samples, checks = 0, 0, 0
    def norm(x):
        return sum(v*v for v in x)
    while nodes < node_limit and len(solutions) < proof_limit:
        samples += 1
        coefficients = [rng.randrange(-1, 2) for _ in basis]
        vector = canonical(tuple(sum(c*row[j] for c, row in zip(coefficients, basis)) for j in range(profile.m)))
        nodes += 1
        changed = True
        while changed and nodes < node_limit:
            changed = False
            for previous in pool:
                for sign in (-1, 1):
                    if nodes == node_limit:
                        break
                    candidate = canonical(tuple(a+sign*b for a, b in zip(vector, previous)))
                    nodes += 1
                    if any(candidate) and norm(candidate) < norm(vector):
                        vector, changed = candidate, True
                if nodes == node_limit:
                    break
        if any(vector) and vector not in pool:
            pool.append(vector)
            pool.sort(key=norm)
            del pool[64:]
        checks += 1
        if vector not in seen and verify(profile, matrix, vector):
            seen.add(vector)
            solutions.append(vector)
    return {"proofs": solutions, "reason": "proof-limit" if len(solutions) == proof_limit else "node-limit",
            "work": {"nodes": nodes, "samples": samples, "sis_checks": checks}, "complete": False}


def sparse_probe(profile, matrix, node_limit, proof_limit):
    """Paid support<=2 screening for easy instances; never a full-space oracle."""
    nodes, vectors = 0, []
    radius = math.isqrt(profile.b2)
    for i in range(profile.m):
        for first in range(1, radius+1):
            vector = [0]*profile.m
            vector[i] = first
            proposals = [tuple(vector)]
            # Yield the unit-supported candidate before the pairs. Pair signs
            # are canonical because i<j and the first coordinate is positive.
            def pairs():
                yield from proposals
                remaining = math.isqrt(profile.b2-first*first)
                for j in range(i+1, profile.m):
                    for second in range(-remaining, remaining+1):
                        if second:
                            vector[j] = second
                            yield tuple(vector)
                    vector[j] = 0
            for candidate in pairs():
                if nodes == node_limit:
                    return {"proofs": vectors, "reason": "node-limit", "work": {"nodes": nodes, "sparse_checks": nodes}}
                nodes += 1
                if verify(profile, matrix, candidate):
                    vectors.append(candidate)
                    if len(vectors) == proof_limit:
                        return {"proofs": vectors, "reason": "proof-limit", "work": {"nodes": nodes, "sparse_checks": nodes}}
    return {"proofs": vectors, "reason": "sparse-support-exhausted", "work": {"nodes": nodes, "sparse_checks": nodes}}
