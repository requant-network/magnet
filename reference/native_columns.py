"""Strict bounded CPS1/CSR1 bridge; native timing excludes pipe transport."""

import struct
import subprocess
import time

from reference.sis import Profile, encode_case, verify

REQUEST = struct.Struct('<4sIHHQIII')
RESPONSE = struct.Struct('<4sBBBBHHII5Q')
MAX_RESPONSE = RESPONSE.size + 256*128*4
REASONS = {1: 'proof-limit', 2: 'candidate-limit', 3: 'domain-exhausted'}


def validate(profile, matrix, candidate_limit, proof_limit, batch_size):
    if not isinstance(profile, Profile):
        raise ValueError('expected Profile')
    encode_case(profile, matrix, [1]+[0]*(profile.m-1))
    for value, cap in ((candidate_limit, 16384), (proof_limit, 256), (batch_size, 4096)):
        if type(value) is not int or not 1 <= value <= cap:
            raise ValueError('column cap outside laboratory range')


def encode_request(profile, matrix, *, candidate_limit=16384, proof_limit=256, batch_size=256):
    validate(profile, matrix, candidate_limit, proof_limit, batch_size)
    return REQUEST.pack(b'CPS1', profile.q, profile.n, profile.m, profile.b2,
                        candidate_limit, proof_limit, batch_size) + struct.pack(
                            '<'+'I'*(profile.n*profile.m), *(a for row in matrix for a in row))


def decode_response(packet, profile, matrix, *, candidate_limit=16384, proof_limit=256, batch_size=256):
    validate(profile, matrix, candidate_limit, proof_limit, batch_size)
    if type(packet) is not bytes or not RESPONSE.size <= len(packet) <= MAX_RESPONSE:
        raise ValueError('CSR1 response size')
    (magic, reason, exhausted, complete, reserved, m, reserved16, returned, domain,
     elapsed, checked, batches, accepted, rows) = RESPONSE.unpack_from(packet)
    expected_domain = profile.m if profile.b2 == 1 else profile.m**2
    end = min(expected_domain, candidate_limit)
    if (magic != b'CSR1' or reason not in REASONS or exhausted not in (0, 1) or complete not in (0, 1)
            or reserved or reserved16 or m != profile.m or domain != expected_domain
            or not 0 < checked <= end or not 0 < batches <= (end+batch_size-1)//batch_size
            or checked != min(batches*batch_size, end)
            or not 0 <= returned <= min(proof_limit, accepted) or accepted > checked
            or returned != min(proof_limit, accepted)
            or not checked+accepted*(profile.n-1) <= rows <= checked*profile.n
            or len(packet) != RESPONSE.size+4*m*returned):
        raise ValueError('CSR1 inconsistent header/counters')
    expected_reason = 1 if returned == proof_limit else 2 if checked < domain else 3
    if (reason != expected_reason or exhausted != (checked == domain)
            or complete != (exhausted and returned == accepted)
            or (reason != 1 and checked != end)):
        raise ValueError('CSR1 inconsistent stop flags')
    values = struct.unpack_from('<'+'i'*(m*returned), packet, RESPONSE.size)
    proofs = [values[i*m:(i+1)*m] for i in range(returned)]
    # This protects the transport boundary; the survey also compares exact order
    # and uses a second native verifier. Do not treat this as an independent census.
    if len(set(proofs)) != returned or any(not verify(profile, matrix, v) or
            sum(x != 0 for x in v) > 2 or any(x not in (-1, 0, 1) for x in v) for v in proofs):
        raise ValueError('CSR1 invalid unit-sparse witness')
    ordinals = []
    for vector in proofs:
        nonzero = [(i, x) for i, x in enumerate(vector) if x]
        if len(nonzero) == 1:
            ordinal = nonzero[0][0]
        else:
            first, second = nonzero[0][0], nonzero[1][0]
            pair_rank = first*(2*m-first-1)//2 + second-first-1
            ordinal = m+2*pair_rank+int(nonzero[1][1] == -1)
        ordinals.append(ordinal)
    if any(ordinal >= checked for ordinal in ordinals) or any(a >= b for a, b in zip(ordinals, ordinals[1:])):
        raise ValueError('CSR1 proof outside charged prefix/order')
    work = dict(generated=checked, screened=checked, vector_entries=returned*m,
                matrix_grid_slots=checked*profile.n*m, matrix_entries=profile.n*m,
                batches=batches, accepted_seen=accepted, returned=returned,
                support_entries=3*checked, scheduled_column_reads=2*checked*profile.n,
                host_prefix_entries=0, device_prefix_entries=0, column_table_entries=profile.n*m,
                explicit_h2d_bytes=0, explicit_d2h_bytes=0, actual_row_checks=rows)
    return dict(backend='rust-columns', domain=domain, reason=REASONS[reason],
                domain_exhausted=bool(exhausted), all_proofs_returned=bool(complete),
                proofs=proofs, work=work, elapsed_ns=elapsed)


def search_many(executable, requests):
    """At most 256 validated requests per process; errors never return partial evidence."""
    begin = time.perf_counter_ns()
    if not 1 <= len(requests) <= 256:
        raise ValueError('native request batch outside range')
    wire = bytearray()
    for profile, matrix, settings in requests:
        packet = encode_request(profile, matrix, **settings)
        wire.extend(struct.pack('<I', len(packet)))
        wire.extend(packet)
    result = subprocess.run([str(executable)], input=bytes(wire), capture_output=True, timeout=60, check=True)
    if result.stderr:
        raise RuntimeError('unexpected native column diagnostics')
    data, offset, outputs = result.stdout, 0, []
    if len(data) > len(requests)*(MAX_RESPONSE+4):
        raise ValueError('native output exceeds response allowance')
    for profile, matrix, settings in requests:
        if offset+4 > len(data):
            raise ValueError('missing native response frame')
        size, = struct.unpack_from('<I', data, offset)
        offset += 4
        if not RESPONSE.size <= size <= MAX_RESPONSE or offset+size > len(data):
            raise ValueError('invalid native response frame')
        outputs.append(decode_response(data[offset:offset+size], profile, matrix, **settings))
        offset += size
    if offset != len(data):
        raise ValueError('extra native response bytes')
    return outputs, time.perf_counter_ns()-begin
