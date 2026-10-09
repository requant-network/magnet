"""Bounded local native adapter; every reply reconciled before consumption."""

import struct
import itertools
import subprocess
import threading
import time

from reference.small_coefficients import search, validate

REQUEST = struct.Struct('<4sIHHQB3xII')
HEADER = struct.Struct('<4sBBHHHIIQ')
PATTERN = struct.Struct('<B3bQQQ')
MAX_REQUEST, MAX_RESPONSE, MAX_BATCH = 4128, 17764, 4096
WORK = ('template_visits', 'template_norm_terms', 'generated', 'screened', 'matrix_terms',
        'row_reductions', 'returned', 'vector_entries', 'gcd_terms', 'primitive_returned',
        'nonprimitive_returned', 'validation_matrix_entries', 'validation_vector_entries')
REASONS = {1: 'proof-limit', 2: 'candidate-limit', 3: 'domain-exhausted'}


def encode_request(profile, matrix, *, bound, candidate_limit=20000, proof_limit=256):
    validate(profile, matrix, bound, candidate_limit, proof_limit)
    return REQUEST.pack(b'SCP1', profile.q, profile.n, profile.m, profile.b2, bound, candidate_limit, proof_limit)+\
        struct.pack('<'+'I'*(profile.n*profile.m), *(x for row in matrix for x in row))


def decode_response(packet, profile, matrix, *, bound, candidate_limit=20000, proof_limit=256):
    validate(profile, matrix, bound, candidate_limit, proof_limit)
    if type(packet) is not bytes or not 204 <= len(packet) <= MAX_RESPONSE:
        raise RuntimeError('SCR1 response size')
    magic, reason, exhausted, reserved, width, patterns, count, domain, elapsed = HEADER.unpack_from(packet)
    if (magic != b'SCR1' or reason not in REASONS or exhausted not in (0, 1) or reserved
            or width != profile.m or patterns > 42 or count > proof_limit or elapsed <= 0
            or len(packet) != 204+PATTERN.size*patterns+4*count*width):
        raise RuntimeError('SCR1 header/length')
    work = dict(zip(WORK, struct.unpack_from('<13Q', packet, 28)))
    weights = {}
    for w in range(1, 4):
        values = struct.unpack_from('<3Q', packet, 132+24*(w-1))
        if w <= min(3, profile.m):
            weights[str(w)] = dict(zip(('domain', 'tested', 'accepted'), values))
        elif values != (0, 0, 0):
            raise RuntimeError('unused SCR1 weight census')
    coefficients = {}
    for i in range(patterns):
        w, a, b, c, d, t, accepted = PATTERN.unpack_from(packet, 204+PATTERN.size*i)
        values = (a, b, c)
        if not 1 <= w <= min(3, profile.m) or any(values[w:]) or a <= 0:
            raise RuntimeError('invalid SCR1 coefficient pattern')
        key = ','.join(map(str, values[:w]))
        if key in coefficients:
            raise RuntimeError('duplicate SCR1 pattern')
        coefficients[key] = dict(domain=d, tested=t, accepted=accepted)
    offset = 204+patterns*PATTERN.size
    proofs = [struct.unpack_from('<'+'i'*width, packet, offset+4*width*i) for i in range(count)]
    checked = work['screened']
    result = dict(bound=bound, domain=domain, proofs=proofs, work=work, weights=weights, coefficients=coefficients,
        reason=REASONS[reason], checked_interval=[0, checked], unchecked_domain_suffix=domain-checked,
        domain_exhausted=bool(exhausted), proof_cap_hit=count == proof_limit,
        candidate_cap_truncates_domain=candidate_limit < domain, candidate_censored=reason == 2,
        all_proofs_returned=bool(exhausted), accepted_tail_discarded=0)
    expected = search(profile, matrix, bound=bound, candidate_limit=candidate_limit, proof_limit=proof_limit)
    if result != expected or list(coefficients) != list(expected['coefficients']):
        raise RuntimeError('SCR1 independent ordered prefix/ledger mismatch')
    return dict(result=result, elapsed_ns=elapsed)


def exchange(executable, wire, response_limit, *, timeout=30):
    """Drain bounded pipes concurrently, including while stdin is being written."""
    if type(timeout) not in (int, float) or not 0 < timeout <= 60:
        raise ValueError('native timeout outside range')
    if type(wire) is not bytes or len(wire) > MAX_BATCH*(4+MAX_REQUEST):
        raise ValueError('native input exceeds bound')
    if type(response_limit) is not int or not 0 <= response_limit <= MAX_BATCH*(4+MAX_RESPONSE):
        raise ValueError('native response limit outside range')
    process = subprocess.Popen([str(executable)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    buffers, errors = {'stdout': bytearray(), 'stderr': bytearray()}, []

    def read(name, stream, maximum):
        try:
            while chunk := stream.read(min(65536, maximum-len(buffers[name])+1)):
                if len(buffers[name])+len(chunk) > maximum:
                    errors.append('native '+name+' exceeds bound')
                    process.kill()
                    break
                buffers[name].extend(chunk)
        except OSError:
            errors.append('native pipe read failed')
        finally:
            stream.close()

    def write():
        try:
            process.stdin.write(wire)
            process.stdin.close()
        except (OSError, ValueError):
            errors.append('native stdin failed')
            try:
                process.stdin.close()
            except (OSError, ValueError):
                pass

    threads = [threading.Thread(target=read, args=('stdout', process.stdout, response_limit)),
               threading.Thread(target=read, args=('stderr', process.stderr, 4096)), threading.Thread(target=write)]
    try:
        for thread in threads:
            thread.start()
        process.wait(timeout=timeout)
    finally:
        if process.poll() is None:
            process.kill()
        process.wait()
        for thread in threads:
            if thread.ident is not None:
                thread.join()
    if errors or process.returncode or buffers['stderr']:
        raise RuntimeError('native exchange failed: '+('; '.join(errors) or 'exit/diagnostics'))
    return bytes(buffers['stdout'])


def search_many(executable, cases):
    cases = list(itertools.islice(cases, MAX_BATCH+1))
    if len(cases) > MAX_BATCH:
        raise ValueError('native batch exceeds cap')
    requests = [encode_request(p, matrix, **settings) for p, matrix, settings in cases]
    wire = b''.join(struct.pack('<I', len(packet))+packet for packet in requests)
    start = time.perf_counter_ns()
    data = exchange(executable, wire, len(cases)*(4+MAX_RESPONSE))
    wall = time.perf_counter_ns()-start
    cursor, outputs = 0, []
    for p, matrix, settings in cases:
        if len(data)-cursor < 4:
            raise RuntimeError('missing SCR1 response frame')
        size, = struct.unpack_from('<I', data, cursor)
        cursor += 4
        if not 204 <= size <= MAX_RESPONSE or cursor+size > len(data):
            raise RuntimeError('invalid SCR1 response frame size')
        outputs.append(decode_response(data[cursor:cursor+size], p, matrix, **settings))
        cursor += size
    if cursor != len(data):
        raise RuntimeError('extra SCR1 response bytes')
    return outputs, wall
