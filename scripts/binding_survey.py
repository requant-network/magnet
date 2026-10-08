"""Nonce families: availability, cheap screening and cross-header proof reuse."""

from dataclasses import asdict
import hashlib
import itertools
import json
import math
from pathlib import Path
import platform
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from reference.header import ExpectedContext, LabHeader, encode_proof
from reference.sis import Profile, verify
from scripts.lab_driver import build_lab, exchange, matrix_bytes, request
from scripts.native_driver import build_native, encode_request, run_requests

SETUPS = [(7, 1, 3, 8), (17, 2, 4, 8), (17, 2, 4, 3), (257, 2, 4, 8)]
INSTANCES = 256


def candidates(profile):
    radius = math.isqrt(profile.b2)
    box_size = (2 * radius + 1) ** profile.m
    if box_size > 100_000:
        raise ValueError("binding survey oracle space exceeds cap")
    result = [x for x in itertools.product(range(-radius, radius + 1), repeat=profile.m)
              if next((v for v in x if v), 0) > 0 and sum(v*v for v in x) <= profile.b2]
    return box_size, result


def run_study(lab, native, profile, count):
    if type(count) is not int or not 1 <= count <= 512:
        raise ValueError("binding survey count bound")
    box_size, domain = candidates(profile)
    label = f"magnet-header-binding-v1/{profile.q}/{profile.n}/{profile.m}/{profile.b2}"
    blobs = [hashlib.sha256((label + suffix).encode("ascii")).digest()
             for suffix in ("/network", "/parent", "/payload")]
    headers = [LabHeader(*blobs, 1, 20261008, nonce, profile) for nonce in range(count)]
    matrices = [h.matrix() for h in headers]
    expected_generation = [h.seed() + matrix_bytes(a) for h, a in zip(headers, matrices, strict=True)]
    if exchange(lab, [request(2, h.encode()) for h in headers]) != expected_generation:
        raise RuntimeError("header generation mismatch in survey")
    proofs = [tuple(x for x in domain if verify(profile, a, x)) for a in matrices]
    native_results = run_requests(native, [encode_request(profile, a, "mitm") for a in matrices])
    for vectors, result in zip(proofs, native_results, strict=True):
        if result["stop"] != "domain-exhausted" or set(vectors) != set(result["proofs"]):
            raise RuntimeError("native oracle incomplete or mismatched")

    acquired_index = next((i for i, vectors in enumerate(proofs) if vectors), None)
    acquired = proofs[acquired_index][0] if acquired_index is not None else None
    # Charge all unsuccessful preceding domains and the successful first-match prefix.
    acquisition_checks = (acquired_index * len(domain) + domain.index(acquired) + 1
                          if acquired is not None else count * len(domain))
    records, verify_requests, verify_expected = [], [], []
    for index, (h, a, vectors) in enumerate(zip(headers, matrices, proofs, strict=True)):
        unit = (1,) + (0,) * (profile.m - 1)
        probes = {"unit": unit}
        if vectors:
            probes["first_oracle"] = vectors[0]
        if acquired is not None and index > acquired_index:
            probes["fixed_acquired"] = acquired
        if index > 0 and proofs[index - 1]:
            probes["adjacent_first"] = proofs[index - 1][0]
        outcomes = {}
        context = ExpectedContext(h.network, h.parent, h.height, profile)
        for name, vector in probes.items():
            accepted = verify(profile, a, vector)
            outcomes[name] = accepted
            verify_requests.append(request(3, context.encode() + encode_proof(h, vector)))
            verify_expected.append(bytes([accepted]))
        encoded_solutions = b"".join(struct.pack(f"<{len(x)}i", *x) for x in sorted(vectors))
        records.append({"nonce": h.nonce, "header_hex": h.encode().hex(), "seed": h.seed().hex(),
                        "matrix_sha256": hashlib.sha256(matrix_bytes(a)).hexdigest(),
                        "proof_count": len(vectors), "proof_set_sha256": hashlib.sha256(encoded_solutions).hexdigest(),
                        "first_solution": vectors[0] if vectors else None, "probes": outcomes})
    if exchange(lab, verify_requests) != verify_expected:
        raise RuntimeError("native header verifier mismatch in survey")
    aggregate = {
        "instances": count, "oracle_complete": count,
        "with_solution": sum(bool(vectors) for vectors in proofs),
        "without_solution": sum(not vectors for vectors in proofs),
        "oracle_vectors": sum(map(len, proofs)), "unique_seeds": len({r["seed"] for r in records}),
        "unique_matrices": len({r["matrix_sha256"] for r in records}),
        "box_candidates_prepared_once": box_size, "canonical_norm_candidates": len(domain),
        "oracle_vector_checks": count * len(domain), "python_family_matrix_generations": count,
        "native_derivation_requests": count,
        "native_oracle_instances": count, "native_bound_verifications": len(verify_requests),
        "acquisition": {"nonce": acquired_index, "vector": acquired,
                        "search_vector_checks_including_empty_headers": acquisition_checks,
                        "matrix_generations_through_acquisition": acquired_index + 1
                        if acquired is not None else count},
        "probes": {name: {"attempts": sum(name in r["probes"] for r in records),
                          "accepted": sum(r["probes"].get(name, False) for r in records)}
                   for name in ("unit", "fixed_acquired", "adjacent_first")},
    }
    return {"profile": asdict(profile), "header_label": label, "aggregate": aggregate, "records": records}


def main():
    destination = ROOT / "artifacts/header-binding-v1.json"
    summary_path = destination.parent / "header-binding-summary-v1.json"
    destination.parent.mkdir(exist_ok=True)
    for path in (destination, summary_path):
        path.write_text('{"status":"running-or-incomplete"}\n', encoding="utf-8", newline="\n")
    lab, native = build_lab(), build_native(release=True)
    studies = []
    for setup in SETUPS:
        study = run_study(lab, native, Profile(*setup), INSTANCES)
        studies.append(study)
        print(setup, study["aggregate"], flush=True)
    paths = [ROOT / "Cargo.toml", ROOT / "Cargo.lock"]
    for folder, pattern in (("reference", "*.py"), ("solvers", "*.py"), ("crates", "*.rs"),
                            ("scripts", "*.py"), ("tests", "*.py"), ("tests/vectors", "*.json"), ("spec", "*.md")):
        paths.extend((ROOT / folder).rglob(pattern))
    report = {"status": "passed", "experiment": "header-binding-v1", "setups": SETUPS,
              "instances_per_setup": INSTANCES, "python": platform.python_version(),
              "platform": platform.platform(), "executable_sha256": {
                  "sis-lab-debug": hashlib.sha256(lab.read_bytes()).hexdigest(),
                  "sis-search-release": hashlib.sha256(native.read_bytes()).hexdigest()},
              "source_sha256": {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                                for path in sorted(paths)}, "studies": studies}
    destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    summary = {**report, "studies": [{k: v for k, v in study.items() if k != "records"} for study in studies]}
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8", newline="\n")
    print("Saved raw and compact header-binding evidence", flush=True)


if __name__ == "__main__":
    main()
