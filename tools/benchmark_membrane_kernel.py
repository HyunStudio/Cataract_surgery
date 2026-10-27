"""Measure a frozen input and identify the exact experimental native DLL."""
import ctypes as ct
import hashlib
import json
import math
from pathlib import Path
import statistics
import time
from native_build_provenance import sha256, verify_sources

ROOT = Path(__file__).resolve().parents[1]
DLL = ROOT / ".tools/native/membrane_kernel.dll"
FIXTURE = ROOT / "native/tests/fixtures/refined_flap.json"
before = sha256(DLL)
manifest = json.loads((DLL.parent/"membrane_kernel.build.json").read_text())
if manifest["artifact_sha256"] != before: raise SystemExit("DLL does not match its build manifest")
verify_sources(manifest["sources"])
fixture_bytes = FIXTURE.read_bytes()
fixture_hash = hashlib.sha256(fixture_bytes).hexdigest()
data = json.loads(fixture_bytes)
active = [i for i, flag in enumerate(data["active"]) if flag]
xyz = [v for point in data["positions"] for v in point]
inverse = (ct.c_double*len(data["inverse"]))(*data["inverse"])
a, b = ((ct.c_int*len(active))(*(data[key][i] for i in active)) for key in ("a", "b"))
rest = (ct.c_double*len(active))(*(data["rest"][i] for i in active))
lib = ct.CDLL(str(DLL)); solve = lib.membrane_solve
solve.argtypes = [ct.c_int,ct.POINTER(ct.c_double),ct.POINTER(ct.c_double),ct.c_int,
                   ct.POINTER(ct.c_int),ct.POINTER(ct.c_int),ct.POINTER(ct.c_double),
                   ct.c_double,ct.c_int,ct.c_double,ct.POINTER(ct.c_double)]
solve.restype = ct.c_int
times = []
for run in range(11):
    output = (ct.c_double*len(xyz))(*xyz); stats = (ct.c_double*8)()
    started = time.perf_counter()
    status = solve(len(inverse),output,inverse,len(a),a,b,rest,data["alpha"],100,1e-8,stats)
    elapsed = time.perf_counter()-started
    if status != 0 or stats[1] > 1e-8 or stats[0] > 3.8194e-8:
        raise SystemExit(f"Benchmark input failed correctness gate: {status}, {list(stats)}")
    if run: times.append(elapsed)
if sha256(DLL) != before or sha256(FIXTURE) != fixture_hash:
    raise SystemExit("Native DLL changed during measurement")
verify_sources(manifest["sources"])
points = [list(output[i:i+3]) for i in range(0,len(output),3)]
result = {"scope":"standalone captured refined-flap solve; not app/GPU performance",
          "dll_sha256":before,"fixture_sha256":fixture_hash,"build":manifest}
result.update({"samples":len(times),"median_ms":1000*statistics.median(times),
               "min_ms":1000*min(times),"max_ms":1000*max(times),"stats":list(stats),
               "max_strain":max(math.dist(points[ia],points[ib])/r-1 for ia,ib,r in zip(a,b,rest))})
print(json.dumps(result,indent=2))
report = ROOT/"godot/reports/native-membrane-benchmark.json"
report.parent.mkdir(parents=True,exist_ok=True)
report.write_text(json.dumps(result,indent=2),encoding="utf-8")
