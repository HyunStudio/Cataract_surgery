"""Compare the isolated native geometry component against pinned IPC diagnostics.

No Godot/world/clinical qualification. IPC is an optional oracle, not a runtime dependency.
"""
import argparse
import ctypes as ct
import hashlib
from importlib import metadata
import json
from pathlib import Path
import sys

from native_build_provenance import sha256, verify_sources

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ipctk-path", type=Path, default=ROOT/".tools/ipc-probe-python")
    parser.add_argument("--samples", type=int, default=256)
    args = parser.parse_args()
    if not 0 <= args.samples <= 4096:
        parser.error("samples must be between0and4096")
    report = ROOT/"godot/reports/native-contact-distance-comparison.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps({"qualified": False, "state": "preparing"}))
    target = args.ipctk_path.resolve()
    sys.path.insert(0, str(target))
    import ipctk
    import numpy as np

    if not Path(ipctk.__file__).resolve().is_relative_to(target):
        raise SystemExit("Oracle was not loaded from the requested isolated target")
    versions = [d.version for d in metadata.distributions(path=[str(target)])
                if d.metadata["Name"].lower() == "ipctk"]
    if versions != ["1.6.1"]:
        raise SystemExit("Expected the pinned diagnostic IPC1.6.1")

    dll = ROOT/".tools/native/contact_distance.dll"
    manifest = json.loads(dll.with_suffix(".build.json").read_text())
    verify_sources(manifest["sources"])
    if sha256(dll) != manifest["artifact_sha256"]:
        raise SystemExit("Contact artifact differs from its build manifest")
    fixture_path = ROOT/"native/tests/fixtures/local_jaw_contact.json"
    fixture_bytes = fixture_path.read_bytes()
    fixture = json.loads(fixture_bytes)
    inputs = {str(p): sha256(p) for p in [dll, fixture_path, Path(ipctk.__file__), Path(__file__).resolve()]}
    inputs[str(fixture_path)] = hashlib.sha256(fixture_bytes).hexdigest()
    lib = ct.CDLL(str(dll))
    fn = lib.membrane_contact_distance
    fn.argtypes = [ct.POINTER(ct.c_double), ct.POINTER(ct.c_double), ct.c_double, ct.POINTER(ct.c_double)]
    fn.restype = ct.c_int

    def native(a, b, triangle, radius):
        segment = (ct.c_double*6)(*np.r_[a, b])
        face = (ct.c_double*9)(*triangle.ravel())
        output = (ct.c_double*22)()
        return fn(segment, face, radius, output), np.array(output)

    def oracle(a, b, triangle):
        hit, u, v, t = ipctk.edge_triangle_intersection(a, b, *triangle)
        if hit and np.isfinite([u, v, t]).all():
            return 0., np.zeros(9), False, True
        candidates = []
        for endpoint in [a, b]:
            d = ipctk.point_triangle_distance(endpoint, *triangle)
            g = ipctk.point_triangle_distance_gradient(endpoint, *triangle).reshape(4, 3)[1:]
            candidates.append((d, g.ravel()))
        for i, j in [(0, 1), (1, 2), (2, 0)]:
            d = ipctk.edge_edge_distance(a, b, triangle[i], triangle[j])
            g = ipctk.edge_edge_distance_gradient(a, b, triangle[i], triangle[j]).reshape(4, 3)
            gradient = np.zeros((3, 3))
            gradient[i], gradient[j] = g[2], g[3]
            candidates.append((d, gradient.ravel()))
        d, g = min(candidates, key=lambda candidate: candidate[0])
        # Robust predicate deliberately returns conservative true for coplanarity.
        return d, g, hit and not np.isfinite([u, v, t]).all(), False

    points = np.array(fixture["initial"]).reshape(-1, 3)
    cases = []
    for face in fixture["triangles"]:
        for body in fixture["capsules"]:
            cases.append((np.array(body["a"]), np.array(body["b"]), points[face], body["radius"], "actual-local"))
    random = np.random.default_rng(194263)
    for _ in range(args.samples):
        a, b, x, y, z = random.uniform(-1, 1, (5, 3))
        cases.append((a, b, np.array([x, y, z]), .05, "seeded-random"))

    # Status gates prevent universal ambiguity/degeneracy from bypassing gradients.
    face = np.array([[0., 0., 0.], [1., 0., 0.], [0., 0., 1.]])
    analytic = [([.2, .3, .4], [.2, .6, .4], face, 0),
                ([.2, 1., .2], [.2, -1., .2], face, 1),
                ([.2, .1, .2], [.2, .1, .6], face, 3),
                ([.2, 1e-13, .2], [.2, 1e-13, .6], face, 3),
                ([.2, .1, .2], [.2, .1, .2], np.array([[0., 0., 0.], [1., 0., 0.], [2., 0., 0.]]), 2),
                ([.25, 2.**-67, .25], [.25, 2.**-67, .25], np.array([[0., 0., 0.], [1., 0., 1.], [0., 1., 1.]]), 2)]
    expected_status = {}
    for a, b, triangle, status in analytic:
        expected_status[len(cases)] = status
        cases.append((np.array(a), np.array(b), triangle, .1, "analytic-status"))

    failures = []
    statuses = {}
    max_distance_error = 0.
    max_gradient_error = 0.
    oracle_degenerate = 0
    gradient_checks = 0
    for index, (a, b, triangle, radius, kind) in enumerate(cases):
        status, output = native(a, b, triangle, radius)
        statuses[str(status)] = statuses.get(str(status), 0)+1
        if index in expected_status:
            if status != expected_status[index] or not np.isfinite(output).all():
                failures.append({"index": index, "kind": kind, "status": status, "expected_status": expected_status[index]})
            if expected_status[index] == 2:
                continue  # Explicitly inconclusive, not an asserted distance oracle.
        expected, gradient, uncertain, exact_intersection = oracle(a, b, triangle)
        if uncertain:
            oracle_degenerate += 1
            continue
        error = abs(output[0]-expected)
        max_distance_error = max(max_distance_error, error)
        if (status < 0 or not np.isfinite(output).all()
                or (status != 2 and error > 2e-12*max(1e-16, expected))
                or (status in (0, 3) and expected > 0 and output[0] == 0)
                or (status == 1 and not exact_intersection)):
            failures.append({"index": index, "kind": kind, "status": status, "distance_error": error})
        if status == 0:
            gradient_checks += 1
            error = float(np.max(abs(output[11:20]-gradient)))
            max_gradient_error = max(max_gradient_error, error)
            if error > 2e-9:
                failures.append({"index": index, "kind": kind, "gradient_error": error})

    minimum_gradient_checks = int(.6*len(cases))
    if gradient_checks < minimum_gradient_checks:
        failures.append({"gradient_checks": gradient_checks, "minimum_required": minimum_gradient_checks})

    verify_sources(manifest["sources"])
    if any(sha256(Path(name)) != digest for name, digest in inputs.items()):
        raise SystemExit("Comparison inputs changed during execution")
    proof = {"qualified": not failures and oracle_degenerate == 0,
             "scope": "isolated static native distance/gradient comparison, not world/CCD/solver/clinical qualification",
             "cases": len(cases), "statuses": statuses, "gradient_checks": gradient_checks,
             "minimum_gradient_checks": minimum_gradient_checks, "analytic_status_cases": len(analytic),
             "oracle_degenerate_cases": oracle_degenerate, "max_squared_distance_error": max_distance_error,
             "max_gradient_error": max_gradient_error, "failures": failures,
             "oracle_version": versions[0], "numpy_version": np.__version__, "inputs": inputs, "build": manifest}
    report.write_text(json.dumps(proof, indent=2))
    print(json.dumps({k: v for k, v in proof.items() if k not in ["inputs", "build"]}, indent=2))
    return 0 if proof["qualified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
