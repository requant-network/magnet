"""Paid unit-sparse candidate acquisition; optional CUDA backend (spec/17)."""

import itertools
import time

from reference.sis import Profile, encode_case, verify

MAX_CANDIDATES = 16384
MAX_PROOFS = 256
MAX_BATCH = 256
MAX_LOGICAL_DEVICE_BYTES = 64 * 1024 * 1024


def candidates(profile):
    """Independent host ordering: positive units, then pairs with second +1/-1."""
    if not isinstance(profile, Profile):
        raise ValueError('expected Profile')
    for first in range(profile.m):
        vector = [0]*profile.m
        vector[first] = 1
        yield tuple(vector)
    if profile.b2 >= 2:
        for first, second in itertools.combinations(range(profile.m), 2):
            for sign in (1, -1):
                vector = [0]*profile.m
                vector[first], vector[second] = 1, sign
                yield tuple(vector)


def _validate(profile, matrix, candidate_limit, proof_limit, batch_size, backend):
    if not isinstance(profile, Profile):
        raise ValueError('expected Profile')
    encode_case(profile, matrix, [1]+[0]*(profile.m-1))
    for value, limit in ((candidate_limit, MAX_CANDIDATES), (proof_limit, MAX_PROOFS),
                         (batch_size, MAX_BATCH)):
        if type(value) is not int or not 1 <= value <= limit:
            raise ValueError('search cap outside laboratory range')
    if backend not in ('python', 'cuda'):
        raise ValueError('unknown sparse backend')
    logical_bytes = 8 * (2*batch_size*profile.n*profile.m + 3*batch_size*profile.m
                         + 12*batch_size + profile.n*profile.m + profile.m)
    if logical_bytes > MAX_LOGICAL_DEVICE_BYTES:
        raise ValueError('logical tensor allowance')
    return profile.m if profile.b2 == 1 else profile.m**2


def _cuda_candidates(torch, ids, m, starts):
    """Generate the ordinal domain on-device; no host solution/candidate oracle."""
    begin, count = ids[0].item(), ids.numel()
    singles = max(0, min(m-begin, count))
    vectors = torch.zeros((count, m), dtype=torch.int64, device='cuda')
    if singles:
        rows = torch.arange(singles, device='cuda')
        vectors[rows, ids[:singles]] = 1
    if singles < count:
        pair_ids = (ids[singles:]-m)//2
        first = torch.searchsorted(starts, pair_ids, right=True)-1
        second = first+1+pair_ids-starts[first]
        rows = torch.arange(singles, count, device='cuda')
        vectors[rows, first] = 1
        vectors[rows, second] = 1-2*((ids[singles:]-m) % 2)
    return vectors


def search(profile, matrix, *, backend, candidate_limit=MAX_CANDIDATES,
           proof_limit=MAX_PROOFS, batch_size=MAX_BATCH):
    """Bounded sparse-domain search. A proof stop still pays for the full chunk."""
    begin = time.perf_counter_ns()
    domain = _validate(profile, matrix, candidate_limit, proof_limit, batch_size, backend)
    work = {'generated': 0, 'screened': 0, 'vector_entries': 0, 'matrix_grid_slots': 0,
            'matrix_entries': profile.n*profile.m, 'batches': 0, 'accepted_seen': 0,
            'returned': 0, 'support_prefix_entries': 0,
            'explicit_h2d_bytes': 0, 'explicit_d2h_bytes': 0}
    proofs = []
    if backend == 'cuda':
        import torch
        if not torch.cuda.is_available():
            raise RuntimeError('CUDA required; no silent CPU fallback')
        gpu_matrix = torch.tensor(matrix, dtype=torch.int64, device='cuda')
        positions = torch.arange(profile.m, dtype=torch.int64, device='cuda')
        starts = positions*(2*profile.m-positions-1)//2
        work['support_prefix_entries'] = profile.m
        work['explicit_h2d_bytes'] = profile.n*profile.m*8
    else:
        iterator = candidates(profile)
    reason = 'domain-exhausted'
    end = min(domain, candidate_limit)
    for offset in range(0, end, batch_size):
        count = min(batch_size, end-offset)
        remaining = proof_limit-len(proofs)
        if backend == 'cuda':
            ids = torch.arange(offset, offset+count, dtype=torch.int64, device='cuda')
            vectors = _cuda_candidates(torch, ids, profile.m, starts)
            mask = ((gpu_matrix[None, :, :]*vectors[:, None, :]).sum(dim=2).remainder(profile.q) == 0).all(dim=1)
            accepted = int(mask.sum().item())
            indices = torch.nonzero(mask).flatten()[:remaining]
            output = [tuple(x) for x in vectors[indices].tolist()]
            # Explicit tensor payloads only: count + first ordinal + returned vectors.
            work['explicit_d2h_bytes'] += 16+len(output)*profile.m*8
            del ids, vectors, mask, indices
        else:
            batch = list(itertools.islice(iterator, count))
            valid = [v for v in batch if verify(profile, matrix, v)]
            accepted, output = len(valid), valid[:remaining]
        proofs.extend(output)
        work['generated'] += count
        work['screened'] += count
        work['vector_entries'] += count*profile.m
        work['matrix_grid_slots'] += count*profile.n*profile.m
        work['batches'] += 1
        work['accepted_seen'] += accepted
        work['returned'] = len(proofs)
        if len(proofs) == proof_limit:
            reason = 'proof-limit'
            break
    if reason != 'proof-limit' and work['screened'] < domain:
        reason = 'candidate-limit'
    if backend == 'cuda':
        torch.cuda.synchronize()
        del gpu_matrix, positions, starts
    exhausted = work['screened'] == domain
    return {'backend': backend, 'domain': domain, 'reason': reason, 'domain_exhausted': exhausted,
            'all_proofs_returned': exhausted and len(proofs) == work['accepted_seen'],
            'proofs': proofs, 'work': work, 'elapsed_ns': time.perf_counter_ns()-begin}
