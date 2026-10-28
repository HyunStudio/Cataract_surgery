"""Frozen-input static coupled diagnostic; never whole-world/CCD/realtime qualification."""
import argparse
import ctypes as ct
import hashlib
import json
import math
from pathlib import Path
import statistics
import time

from native_build_provenance import sha256, verify_sources

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT/"native/tests/fixtures/local_jaw_contact.json")
    parser.add_argument("--full-export", action="store_true", help="Explicitly parse an exported actual substep instead of the reduced fixture")
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    if not 1 <= args.repeats <= 16:
        parser.error("repeats must be in1..16")
    report = ROOT/("godot/reports/coupled-full-static-diagnostic.json" if args.full_export else "godot/reports/coupled-local-static-diagnostic.json")
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps({"qualified": False, "state": "preparing"}))
    raw = args.input.read_bytes()
    p = json.loads(raw)
    if args.full_export:
        data, first = p, p["first"]
        p = {"initial": data["positions"], "predicted": first["xyz"], "inverse": first["inverse"],
             "a": first["a"], "b": first["b"], "rest": first["rest"], "alpha": first["alpha"],
             "triangles": [data["faces"][i:i+3] for i in range(0, len(data["faces"]), 3)],
             "capsules": [{"a": b["segment"][6:9], "b": b["segment"][9:12], "radius": b["radius"]} for b in data["body"]]}
    artifacts = [ROOT/".tools/native/membrane_contact.dll", ROOT/".tools/native/contact_distance.dll"]
    builds = [json.loads(dll.with_suffix(".build.json").read_text()) for dll in artifacts]
    for dll, build in zip(artifacts, builds):
        verify_sources(build["sources"])
        if sha256(dll) != build["artifact_sha256"]:
            raise SystemExit("Native artifact differs from its source manifest")
    inputs = {str(path.resolve()): sha256(path) for path in artifacts+[Path(__file__).resolve()]}
    inputs[str(args.input.resolve())] = hashlib.sha256(raw).hexdigest()
    lib = ct.CDLL(str(artifacts[0])); geometry = ct.CDLL(str(artifacts[1]))
    solve = lib.membrane_solve_contact
    solve.argtypes = [ct.c_int, ct.POINTER(ct.c_double), ct.POINTER(ct.c_double), ct.POINTER(ct.c_double),
                      ct.c_int, ct.POINTER(ct.c_int), ct.POINTER(ct.c_int), ct.POINTER(ct.c_double), ct.c_double,
                      ct.c_int, ct.POINTER(ct.c_int), ct.c_int, ct.POINTER(ct.c_double), ct.c_int,
                      ct.c_double, ct.c_double, ct.c_double, ct.POINTER(ct.c_double), ct.POINTER(ct.c_double)]
    solve.restype = ct.c_int
    distance = geometry.membrane_contact_distance
    distance.argtypes = [ct.POINTER(ct.c_double), ct.POINTER(ct.c_double), ct.c_double, ct.POINTER(ct.c_double)]
    distance.restype = ct.c_int
    doubles = lambda values: (ct.c_double*len(values))(*values)
    integers = lambda values: (ct.c_int*len(values))(*values)
    triangles = integers([v for face in p["triangles"] for v in face])
    bodies = doubles([v for body in p["capsules"] for v in body["a"]+body["b"]+[body["radius"]]])
    samples, statuses = [], []
    for _ in range(args.repeats):
        x = doubles(p["initial"]); dual = doubles([0.]*(len(p["triangles"])*len(p["capsules"])))
        stats = doubles([0.]*12)
        started = time.perf_counter()
        status = solve(len(p["inverse"]), doubles(p["predicted"]), x, doubles(p["inverse"]),
                       len(p["a"]), integers(p["a"]), integers(p["b"]), doubles(p["rest"]), p["alpha"],
                       len(p["triangles"]), triangles, len(p["capsules"]), bodies, 100, 1e-8, 1e-9, 1e-11, dual, stats)
        samples.append(1000*(time.perf_counter()-started)); statuses.append(status)
    x, dual, stats = list(x), list(dual), list(stats)
    # Independently assemble material forces in Python and contact reactions
    # through the separately IPC-checked geometry ABI, rather than trusting stats.
    force = [0.]*len(x); energy = 0.; failures = []
    if not all(math.isfinite(value) for value in x+dual+stats[:9]):
        failures.append("nonfinite native result")
    for i, inverse in enumerate(p["inverse"]):
        if inverse == 0:
            if x[3*i:3*i+3] != p["initial"][3*i:3*i+3]: failures.append("prescribed point moved")
        else:
            for k in range(3):
                delta = x[3*i+k]-p["predicted"][3*i+k]
                energy += .5*delta*delta/inverse; force[3*i+k] = delta/inverse
    for a, b, rest in zip(p["a"], p["b"], p["rest"]):
        delta = [x[3*a+k]-x[3*b+k] for k in range(3)]
        length = math.sqrt(sum(v*v for v in delta))
        if length == 0:
            failures.append("collapsed edge"); continue
        energy += .5*(length-rest)**2/p["alpha"]
        for k in range(3):
            f = (length-rest)*delta[k]/(length*p["alpha"])
            force[3*a+k] += f; force[3*b+k] -= f
    penetration = 0.; complementarity = 0.
    for face, triangle in enumerate(p["triangles"]):
        for b, body in enumerate(p["capsules"]):
            result = doubles([0.]*22)
            code = distance(doubles(body["a"]+body["b"]), doubles([x[3*v+k] for v in triangle for k in range(3)]), body["radius"], result)
            multiplier = dual[face*len(p["capsules"])+b]
            if code in (-1, 1, 2) or (code == 3 and multiplier > 0): failures.append("unresolved final contact")
            penetration = max(penetration, body["radius"]-math.sqrt(max(0., result[0])))
            complementarity = max(complementarity, abs(multiplier*(result[0]/body["radius"]**2-1)))
            if multiplier < 0: failures.append("negative unilateral reaction")
            for j, v in enumerate(triangle):
                for k in range(3): force[3*v+k] -= multiplier*result[11+3*j+k]/body["radius"]**2
    stationarity = max((abs(force[3*i+k]) for i, w in enumerate(p["inverse"]) if w > 0 for k in range(3)), default=0.)
    if (not all(math.isfinite(value) for value in [energy, stationarity, penetration, complementarity])
            or stationarity > 1e-8 or penetration > 1e-9 or complementarity > 1e-11 or abs(energy-stats[0]) > 1e-12):
        failures.append("recomputed coupled acceptance residual")
    for build in builds: verify_sources(build["sources"])
    if any(sha256(Path(name)) != digest for name, digest in inputs.items()):
        raise SystemExit("Diagnostic inputs changed during execution")
    proof = {"qualified": all(code == 0 for code in statuses) and not failures,
             "scope": "static captured material/contact energy only; no anatomical boundary, CCD, complete operation, realtime or clinical qualification",
             "full_export": args.full_export, "vertices": len(p["inverse"]), "free_vertices": sum(w > 0 for w in p["inverse"]),
             "statuses": statuses, "samples_ms": samples, "median_ms": statistics.median(samples), "stats": stats,
             "recomputed_energy": energy, "recomputed_stationarity": stationarity, "recomputed_penetration": penetration,
             "recomputed_complementarity": complementarity, "failures": sorted(set(failures)),
             "positions": x, "dual": dual, "inputs": inputs, "builds": builds}
    report.write_text(json.dumps(proof, indent=2))
    print(json.dumps({k: v for k, v in proof.items() if k not in ["positions", "dual", "inputs", "builds"]}, indent=2))
    return 0 if proof["qualified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
