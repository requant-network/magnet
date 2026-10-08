"""Cross-language exact sets and native caps, including malformed byte boundaries."""
import random
import struct
import subprocess

from reference.ball import BallSearch
from reference.mitm import MitmSearch
from reference.sis import MAX_PACKET, Profile, verify
from scripts.native_driver import encode_request, run_requests


def differential_search(executable):
    rng = random.Random(20261009)
    cases = []
    for q in (2, 7, 17, 65521):
        for width in range(1, 7):
            p = Profile(q, 2, width, min(5, q*q - 1))
            for _ in range(4):
                cases.append((p, [[rng.randrange(q) for _ in range(width)] for _ in range(2)]))
    cases += [(Profile(7, 1, width, 5), [[0] * width]) for width in range(1, 7)]
    cases.append((Profile(7, 1, 3, 5), [[1, 2, 3]]))
    requests = [encode_request(p, matrix, algorithm, repeats=2)
                for p, matrix in cases for algorithm in ("ball", "mitm", "mitm-budgeted")]
    results = run_requests(executable, requests)
    proofs = 0
    for index, (p, matrix) in enumerate(cases):
        expected = set(BallSearch(p, matrix).solutions())
        if expected != set(MitmSearch(p, matrix).solutions()):
            raise RuntimeError("Python reference searches disagree")
        for result in results[3*index:3*index + 3]:
            vectors = result["proofs"]
            if (result["stop"] != "domain-exhausted" or len(vectors) != len(set(vectors))
                    or set(vectors) != expected or not all(verify(p, matrix, x) for x in vectors)):
                raise RuntimeError(f"native search mismatch at instance {index}")
            proofs += len(vectors)
        budgeted = results[3*index+2]["work"]
        if budgeted["nodes"] != budgeted["left"]+budgeted["right"]+budgeted["pairs"]:
            raise RuntimeError("native budgeted MITM lost work")

    p, matrix = Profile(7, 1, 4, 5), [[0] * 4]
    capped = [("ball", {"nodes": 1}, "node-limit"),
              ("ball", {"proofs": 1}, "proof-limit"),
              ("mitm", {"table": 1}, "table-limit"),
              ("mitm", {"pairs": 1}, "pair-limit"),
              ("mitm", {"proofs": 1}, "proof-limit")]
    capped.append(("mitm-budgeted", {"nodes": 1}, "node-limit"))
    for algorithm, limits, reason in capped:
        result = run_requests(executable, [encode_request(p, matrix, algorithm, **limits)])[0]
        if result["stop"] != reason or not all(verify(p, matrix, x) for x in result["proofs"]):
            raise RuntimeError("native cap reporting differs")
    full = run_requests(executable, [encode_request(p, matrix, "mitm-budgeted")])[0]
    total = full["work"]["nodes"]
    for allowance in (1, full["work"]["left"], full["work"]["left"]+1, total-1, total):
        result = run_requests(executable, [encode_request(p, matrix, "mitm-budgeted", nodes=allowance)])[0]
        work = result["work"]
        if work["nodes"] != min(allowance, total) or work["nodes"] != work["left"]+work["right"]+work["pairs"]:
            raise RuntimeError("budgeted MITM aggregate cap mismatch")
        expected_stop = "domain-exhausted" if allowance == total else "node-limit"
        if result["stop"] != expected_stop or not set(result["proofs"]) <= set(full["proofs"]):
            raise RuntimeError("budgeted MITM boundary completion mismatch")
    p = Profile(17, 1, 28, 1)
    matrix = [[0] * 28]
    ball, mitm = run_requests(executable, [encode_request(p, matrix, a) for a in ("ball", "mitm")])
    if (ball["stop"] != "domain-exhausted" or len(ball["proofs"]) != 28
            or mitm["stop"] != "half-box-limit" or mitm["proofs"]):
        raise RuntimeError("huge box/small ball case differs")

    valid = encode_request(Profile(7, 1, 2, 5), [[1, 2]], "ball")
    invalid = [b"", valid[:-1], valid + b"x"]
    for offset, replacement in [(0, b"BAD!"), (4, b"\x04"), (5, b"\x01"), (8, bytes(8)),
                                (32, struct.pack("<I", 10)), (40, struct.pack("<I", 6)),
                                (44, bytes(2)), (48, bytes(8)), (56, struct.pack("<I", 7)),
                                (len(valid)-4, struct.pack("<i", 1))]:
        body = bytearray(valid)
        body[offset:offset + len(replacement)] = replacement
        invalid.append(bytes(body))
    wires = [struct.pack("<I", len(body)) + body for body in invalid]
    wires += [b"\x01", struct.pack("<I", 36 + MAX_PACKET + 1), struct.pack("<I", 10) + b"abc"]
    for wire in wires:
        result = subprocess.run([str(executable)], input=wire, capture_output=True, timeout=5)
        if result.returncode == 0 or result.stdout or not result.stderr:
            raise RuntimeError("malformed native request unexpectedly accepted")
    if run_requests(executable, []) != []:
        raise RuntimeError("native empty stream failed")
    return {"seed": 20261009, "instances": len(cases), "searches": len(results),
            "verified_proofs": proofs, "mismatches": 0, "cap_checks": len(capped) + 7,
            "malformed_rejections": len(wires), "empty_stream_checks": 1}
