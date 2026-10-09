"""Sparse column arithmetic without dense candidate tensors (spec/18)."""

import bisect
import itertools
import time

from reference.sis import Profile, encode_case

MAX_BATCH = 4096
MAX_LOGICAL_DEVICE_BYTES = 64 * 1024 * 1024


def supports(profile):
    """Independent host support order; a singleton reads its column twice, sign 0."""
    for first in range(profile.m):
        yield first, first, 0
    if profile.b2 >= 2:
        for first, second in itertools.combinations(range(profile.m), 2):
            for sign in (1, -1):
                yield first, second, sign


def support_at(m, ordinal, starts):
    if ordinal < m:
        return ordinal, ordinal, 0
    rank = (ordinal-m)//2
    first = bisect.bisect_right(starts, rank)-1
    return first, first+1+rank-starts[first], 1-2*((ordinal-m) % 2)


def vector_for(m, support):
    first, second, sign = support
    vector = [0]*m
    vector[first] = 1
    if sign:
        vector[second] = sign
    return tuple(vector)


def device_supports(torch, offset, count, m, starts):
    """Device ordinal decode with host-known chunk boundaries; no scalar readback."""
    ids = torch.arange(offset, offset+count, dtype=torch.int64, device='cuda')
    singles = max(0, min(m-offset, count))
    unit = ids[:singles]
    if singles == count:
        return unit, unit, torch.zeros_like(unit)
    pairs = ids[singles:]
    rank = (pairs-m)//2
    first = torch.searchsorted(starts, rank, right=True)-1
    second = first+1+rank-starts[first]
    sign = 1-2*((pairs-m) % 2)
    return (torch.cat((unit, first)), torch.cat((unit, second)),
            torch.cat((torch.zeros_like(unit), sign)))


def search(profile, matrix, *, backend, candidate_limit=16384, proof_limit=256, batch_size=256):
    begin = time.perf_counter_ns()
    if not isinstance(profile, Profile):
        raise ValueError('expected Profile')
    encode_case(profile, matrix, [1]+[0]*(profile.m-1))
    for value, limit in ((candidate_limit, 16384), (proof_limit, 256), (batch_size, MAX_BATCH)):
        if type(value) is not int or not 1 <= value <= limit:
            raise ValueError('column search cap outside laboratory range')
    if backend not in ('python-columns', 'cuda-columns'):
        raise ValueError('unknown column backend')
    logical_bytes = 8*(10*batch_size*profile.n + 20*batch_size + 2*profile.n*profile.m)
    if logical_bytes > MAX_LOGICAL_DEVICE_BYTES:
        raise ValueError('logical tensor allowance')
    domain = profile.m if profile.b2 == 1 else profile.m**2
    work = {'generated': 0, 'screened': 0, 'vector_entries': 0, 'matrix_grid_slots': 0,
            'matrix_entries': profile.n*profile.m, 'batches': 0, 'accepted_seen': 0, 'returned': 0,
            'support_entries': 0, 'scheduled_column_reads': 0, 'host_prefix_entries': 0,
            'device_prefix_entries': 0, 'column_table_entries': 0,
            'explicit_h2d_bytes': 0, 'explicit_d2h_bytes': 0}
    proofs = []
    if backend == 'cuda-columns':
        import torch
        if not torch.cuda.is_available():
            raise RuntimeError('CUDA required; no silent CPU fallback')
        gpu_matrix = torch.tensor(matrix, dtype=torch.int64, device='cuda')
        positions = torch.arange(profile.m, dtype=torch.int64, device='cuda')
        gpu_starts = positions*(2*profile.m-positions-1)//2
        host_starts = tuple(i*(2*profile.m-i-1)//2 for i in range(profile.m))
        work['host_prefix_entries'] = work['device_prefix_entries'] = profile.m
        work['explicit_h2d_bytes'] = profile.n*profile.m*8
    else:
        iterator = supports(profile)
        columns = tuple(tuple(row[i] for row in matrix) for i in range(profile.m))
        work['column_table_entries'] = profile.n*profile.m
    reason = 'domain-exhausted'
    end = min(domain, candidate_limit)
    for offset in range(0, end, batch_size):
        count = min(batch_size, end-offset)
        remaining = proof_limit-len(proofs)
        if backend == 'cuda-columns':
            first, second, sign = device_supports(torch, offset, count, profile.m, gpu_starts)
            mask = ((gpu_matrix[:, first].T + sign[:, None]*gpu_matrix[:, second].T)
                    .remainder(profile.q) == 0).all(dim=1)
            flags = mask.cpu().tolist()
            accepted = sum(flags)
            ordinals = [offset+i for i, valid in enumerate(flags) if valid][:remaining]
            output = [vector_for(profile.m, support_at(profile.m, i, host_starts)) for i in ordinals]
            work['explicit_d2h_bytes'] += count  # One boolean tensor; no scalar/vector reads.
            del first, second, sign, mask
        else:
            batch = list(itertools.islice(iterator, count))
            valid = [s for s in batch if all((a+s[2]*b) % profile.q == 0
                     for a, b in zip(columns[s[0]], columns[s[1]]))]
            accepted = len(valid)
            output = [vector_for(profile.m, s) for s in valid[:remaining]]
        proofs.extend(output)
        work['generated'] += count
        work['screened'] += count
        work['vector_entries'] += len(output)*profile.m
        work['matrix_grid_slots'] += count*profile.n*profile.m
        work['scheduled_column_reads'] += 2*count*profile.n
        work['support_entries'] += 3*count
        work['batches'] += 1
        work['accepted_seen'] += accepted
        work['returned'] = len(proofs)
        if len(proofs) == proof_limit:
            reason = 'proof-limit'
            break
    if reason != 'proof-limit' and work['screened'] < domain:
        reason = 'candidate-limit'
    if backend == 'cuda-columns':
        torch.cuda.synchronize()
        del gpu_matrix, positions, gpu_starts
    exhausted = work['screened'] == domain
    return {'backend': backend, 'domain': domain, 'reason': reason, 'domain_exhausted': exhausted,
            'all_proofs_returned': exhausted and len(proofs) == work['accepted_seen'],
            'proofs': proofs, 'work': work, 'elapsed_ns': time.perf_counter_ns()-begin}
