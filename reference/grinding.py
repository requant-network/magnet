"""Bounded header-selection policies and a research-only score predicate."""

from dataclasses import replace
import hashlib
import itertools
import math
import struct

from reference.header import ExpectedContext, LabHeader, encode_proof, verify_proof
from reference.sis import verify

SCORE_DOMAIN = b"MagnetNetwork/SIS-LAB/grinding-score/v1\0"
PAYLOAD_DOMAIN = b"MagnetNetwork/SIS-LAB/payload-grind/v1\0"
POLICIES = ("unit", "first", "all", "reuse")
FIELDS = ("nonce", "timestamp", "payload")


def header_family(base, field, count):
    if not isinstance(base, LabHeader) or field not in FIELDS or type(count) is not int or not 1 <= count <= 512:
        raise ValueError("header family bound/type/field")
    if field in ("nonce", "timestamp") and getattr(base, field) + count > 2**64:
        raise ValueError("header family u64 overflow")
    result = [base]
    for index in range(1, count):
        value = (hashlib.sha256(PAYLOAD_DOMAIN + base.payload + struct.pack("<Q", index)).digest()
                 if field == "payload" else getattr(base, field) + index)
        result.append(replace(base, **{field: value}))
    return tuple(result)


def candidate_domain(profile):
    radius = math.isqrt(profile.b2)
    box = (2*radius + 1)**profile.m
    if box > 100_000:
        raise ValueError("grinding oracle space bound")
    vectors = tuple(x for x in itertools.product(range(-radius, radius + 1), repeat=profile.m)
                    if next((v for v in x if v), 0) > 0 and sum(v*v for v in x) <= profile.b2)
    return box, vectors


def _target(target):
    if type(target) is not int or not 0 <= target <= 2**256:
        raise ValueError("research score target must be an integer in 0..2^256")


def score_digest(header, vector):
    return hashlib.sha256(SCORE_DOMAIN + encode_proof(header, vector)).digest()


def verify_scored_proof(packet, context, target):
    _target(target)
    return verify_proof(packet, context) and int.from_bytes(
        hashlib.sha256(SCORE_DOMAIN + packet).digest(), "big") < target


def run_policy(headers, policy, target, *, proposal_limit=100_000):
    _target(target)
    if policy not in POLICIES or type(proposal_limit) is not int or not 1 <= proposal_limit <= 100_000:
        raise ValueError("grinding policy/proposal limit")
    if type(headers) not in (tuple, list) or not 1 <= len(headers) <= 512 or any(
            not isinstance(h, LabHeader) for h in headers):
        raise ValueError("grinding headers bound/type")
    base = headers[0]
    expected = ExpectedContext(base.network, base.parent, base.height, base.profile)
    if any(not expected.matches(h) for h in headers):
        raise ValueError("grinding context mismatch")
    box, domain = candidate_domain(base.profile) if policy in ("first", "all", "reuse") else (0, ())
    work = {"headers_processed": 0, "matrix_entries_expanded": 0, "vector_checks": 0,
            "score_hashes": 0, "score_input_bytes": 0}
    transcript, scored_samples = hashlib.sha256(), []
    acquired, acquisition = None, None
    result = {"policy": policy, "target": str(target), "proposal_limit": proposal_limit,
              "domain_preparation": {"box_vectors": box, "canonical_norm_vectors": len(domain)},
              "work": work, "reason": "family-exhausted", "acquisition": None, "hit": None,
              "score_samples": scored_samples}
    for index, header in enumerate(headers):
        if work["vector_checks"] == proposal_limit:
            result["reason"] = "proposal-limit"
            break
        matrix = header.matrix()
        work["headers_processed"] += 1
        work["matrix_entries_expanded"] += header.profile.n * header.profile.m
        proposals = ((1,) + (0,) * (header.profile.m - 1),)
        if policy in ("first", "all") or (policy == "reuse" and acquired is None):
            proposals = domain
        elif policy == "reuse":
            proposals = (acquired,)
        for vector in proposals:
            if work["vector_checks"] == proposal_limit:
                result["reason"] = "proposal-limit"
                break
            work["vector_checks"] += 1
            if not verify(header.profile, matrix, vector):
                continue
            if policy == "reuse" and acquired is None:
                acquired = vector
                acquisition = {"header_index": index, "vector": vector, "work_through_acquisition": dict(work)}
            packet = encode_proof(header, vector)
            message = SCORE_DOMAIN + packet
            digest = hashlib.sha256(message).digest()
            transcript.update(message)
            work["score_hashes"] += 1
            work["score_input_bytes"] += len(message)
            sample = {"header_index": index, "vector": vector, "digest": digest.hex()}
            if len(scored_samples) < 8:
                scored_samples.append(sample)
            if int.from_bytes(digest, "big") < target:
                result["reason"] = "score-hit"
                result["hit"] = {**sample, "proof_hex": packet.hex()}
                break
            if policy in ("first", "reuse"):
                break
        if result["reason"] in ("score-hit", "proposal-limit"):
            break
    result["acquisition"] = acquisition
    result["score_transcript_sha256"] = transcript.hexdigest()
    return result
