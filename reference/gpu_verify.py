"""Optional exact CUDA screening; host validation is dependency-free (spec/16)."""

from collections import defaultdict

from reference.sis import MAX_PACKET, decode_case

MAX_BATCH = 256
MAX_INPUT_BYTES = MAX_BATCH * MAX_PACKET
MAX_DEVICE_BYTES = 64 * 1024 * 1024
CHUNK = 32


def prepare(packets):
    """Reject malformed cases before transfer, using overflow-safe host integers."""
    if type(packets) not in (tuple, list) or not 1 <= len(packets) <= MAX_BATCH:
        raise ValueError('require a bounded nonempty packet sequence')
    if sum(len(p) for p in packets if type(p) is bytes) > MAX_INPUT_BYTES:
        raise ValueError('input byte budget')
    groups = defaultdict(list)
    for index, packet in enumerate(packets):
        try:
            profile, matrix, vector = decode_case(packet)
        except ValueError:
            continue
        first = next((x for x in vector if x), 0)
        if first <= 0 or sum(x*x for x in vector) > profile.b2:
            continue
        groups[(profile.q, profile.n, profile.m)].append((index, matrix, vector))
    for (_, n, m), cases in groups.items():
        # Conservative logical tensor allowance; not a measured allocator limit.
        needed = min(CHUNK, len(cases)) * 8 * (3*n*m + 2*m + n)
        if needed > MAX_DEVICE_BYTES:
            raise ValueError('device tensor budget')
    return dict(groups)


def verify_batch(packets):
    """Return exact SIS verdicts using CUDA int64 modular products, never floats."""
    groups = prepare(packets)
    import torch  # Explicit optional runtime; ordinary tests do not require torch.
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA device required; no silent CPU fallback')
    results = [False] * len(packets)
    with torch.no_grad():
        for (q, _, _), cases in groups.items():
            for offset in range(0, len(cases), CHUNK):
                batch = cases[offset:offset+CHUNK]
                matrix = torch.tensor([c[1] for c in batch], dtype=torch.int64, device='cuda')
                vector = torch.tensor([c[2] for c in batch], dtype=torch.int64, device='cuda')
                valid = ((matrix * vector[:, None, :]).sum(dim=2).remainder(q) == 0).all(dim=1)
                for case, verdict in zip(batch, valid.tolist()):
                    results[case[0]] = bool(verdict)
                del matrix, vector, valid
    return results
