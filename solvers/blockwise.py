"""Bounded exact projected-SVP BKZ tours with audited unimodular insertion.

Research dimensions <=16; this is not an optimized fplll implementation.
All projected enumeration is exact rational arithmetic. Node limits mean the
result is a partially improved LLL basis, never a certificate of BKZ reducedness.
"""

from fractions import Fraction
import math

from solvers.sphere import coefficient_interval


def multiply(left, right):
    return tuple(tuple(sum(a*b for a, b in zip(row, col)) for col in zip(*right)) for row in left)


def gram_schmidt(basis):
    mu, norms, orthogonal = [], [], []
    for row in basis:
        vector = list(map(Fraction, row))
        coefficients = []
        for previous, norm in zip(orthogonal, norms):
            value = sum(a*b for a, b in zip(row, previous))/norm
            coefficients.append(value)
            vector = [a-value*b for a, b in zip(vector, previous)]
        norm = sum(x*x for x in vector)
        if norm <= 0:
            raise ValueError("singular basis")
        if any(max(abs(x.numerator).bit_length(), x.denominator.bit_length()) > 4096
               for x in (*vector, *coefficients, norm)):
            raise ValueError("BKZ rational arithmetic bound")
        orthogonal.append(vector)
        mu.append(coefficients)
        norms.append(norm)
    return mu, norms


def projected_shortest(basis, start, end, node_limit):
    """Enumerate pi_start(span(rows[start:end])) below its first GS norm."""
    if (type(node_limit) is not int or not 1 <= node_limit <= 1_000_000
            or not 0 <= start < end <= len(basis) <= 16):
        raise ValueError("projected SVP bounds")
    mu, norms = gram_schmidt(basis)
    best_norm, best = norms[start], None
    coefficients = [0]*len(basis)
    nodes, exhausted = 0, True

    def walk(level, remaining):
        nonlocal nodes, exhausted, best_norm, best
        if level < start:
            candidate = tuple(coefficients[start:end])
            if next((x for x in candidate if x), 0) <= 0:
                return
            norm = sum((norms[i]*(coefficients[i]+sum(mu[j][i]*coefficients[j]
                                                    for j in range(i+1, end)))**2
                        for i in range(start, end)), Fraction(0))
            if 0 < norm < best_norm:
                best_norm, best = norm, candidate
            return
        center = -sum((mu[j][level]*coefficients[j] for j in range(level+1, end)), Fraction(0))
        lower, upper = coefficient_interval(center, remaining/norms[level])
        for value in range(lower, upper+1):
            if nodes == node_limit:
                exhausted = False
                return
            nodes += 1
            coefficients[level] = value
            walk(level-1, remaining-(value-center)**2*norms[level])
            if not exhausted:
                return
    try:
        walk(end-1, best_norm)
    finally:
        # The recursive closure otherwise retains coefficients/GSO until cyclic
        # GC, making many paid BKZ blocks accumulate hidden committed memory.
        walk = None
    if best is not None:
        divisor = math.gcd(*best)
        best = tuple(x//divisor for x in best)
    return {"coefficients": best, "nodes": nodes, "complete": exhausted}


def primitive_completion(coefficients):
    """Integer unimodular U with its first row equal to a primitive coefficient row."""
    if (type(coefficients) not in (tuple, list) or not 1 <= len(coefficients) <= 16
            or any(type(x) is not int or abs(x).bit_length() > 256 for x in coefficients)
            or math.gcd(*coefficients) != 1):
        raise ValueError("bounded primitive integer row required")
    size = len(coefficients)
    current = list(coefficients)
    transform = [[int(i == j) for j in range(size)] for i in range(size)]
    for j in range(1, size):
        a, b = current[0], current[j]
        if not b:
            continue
        old_r, r, old_s, s, old_t, t = a, b, 1, 0, 0, 1
        while r:
            quotient = old_r//r
            old_r, r = r, old_r-quotient*r
            old_s, s = s, old_s-quotient*s
            old_t, t = t, old_t-quotient*t
        if old_r < 0:
            old_r, old_s, old_t = -old_r, -old_s, -old_t
        for row in transform:
            left, right = row[0], row[j]
            row[0], row[j] = old_s*left+old_t*right, -(b//old_r)*left+(a//old_r)*right
        current[0], current[j] = old_r, 0
    if current[0] == -1:
        for row in transform:
            row[0] *= -1
    # Invert the column transform exactly; unimodularity makes the inverse integral.
    augmented = [list(map(Fraction, row))+[Fraction(i == j) for j in range(size)]
                 for i, row in enumerate(transform)]
    for k in range(size):
        pivot = next(i for i in range(k, size) if augmented[i][k])
        augmented[k], augmented[pivot] = augmented[pivot], augmented[k]
        value = augmented[k][k]
        augmented[k] = [x/value for x in augmented[k]]
        for i in range(size):
            if i != k:
                value = augmented[i][k]
                augmented[i] = [a-value*b for a, b in zip(augmented[i], augmented[k])]
    inverse = [row[size:] for row in augmented]
    if any(x.denominator != 1 for row in inverse for x in row):
        raise RuntimeError("nonintegral primitive completion")
    result = tuple(tuple(int(x) for x in row) for row in inverse)
    if result[0] != tuple(coefficients):
        raise RuntimeError("primitive completion row mismatch")
    return result


def bkz_tours(basis, transform, lll, *, block_size=4, tours=1, node_limit=10_000):
    if (type(block_size) is not int or not 2 <= block_size <= 16
            or type(tours) is not int or not 1 <= tours <= 4
            or type(node_limit) is not int or not 1 <= node_limit <= 1_000_000):
        raise ValueError("BKZ budgets")
    nodes, insertions, blocks, complete = 0, 0, 0, True
    for _ in range(tours):
        for k in range(len(basis)-1):
            if nodes == node_limit:
                complete = False
                break
            end = min(len(basis), k+block_size)
            svp = projected_shortest(basis, k, end, node_limit-nodes)
            nodes += svp["nodes"]
            blocks += 1
            complete &= svp["complete"]
            if svp["coefficients"] is not None:
                local = primitive_completion(svp["coefficients"])
                operation = [[int(i == j) for j in range(len(basis))] for i in range(len(basis))]
                for i, row in enumerate(local, k):
                    operation[i][k:end] = row
                basis, transform = multiply(operation, basis), multiply(operation, transform)
                basis, update = lll(basis)
                transform = multiply(update, transform)
                insertions += 1
            if not complete:
                break
        if not complete:
            break
    return basis, transform, {"bkz_nodes": nodes, "bkz_insertions": insertions,
                              "bkz_blocks": blocks, "bkz_tours_complete": complete}
