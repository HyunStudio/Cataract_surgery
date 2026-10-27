"""Build an isolated Godot test extension; never modifies the product project."""
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from native_build_provenance import compiler_identity, source_hashes, write_manifest

ROOT = Path(__file__).resolve().parents[1]
CPP = ROOT / ".tools/godot-cpp-4.5"
EIGEN = ROOT / ".tools/eigen-5.0.1"
WORK = ROOT / ".tools/membrane-extension"
PROJECT = ROOT / ".tools/native-godot"
PINS = {CPP: "e83fd0904c13356ed1d4c3d09f8bb9132bdc6b77",
        EIGEN: "bc3b39870ecb690a623a3f49149a358b95c5781d"}
for path, expected in PINS.items():
    actual = subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD"], text=True).strip()
    dirty = subprocess.check_output(["git", "-C", str(path), "status", "--porcelain"], text=True).strip()
    if actual != expected or dirty:
        raise SystemExit(f"Refusing modified/unpinned native dependency: {path}")
WORK.mkdir(parents=True, exist_ok=True)
(WORK / "obj").mkdir(exist_ok=True)
(PROJECT / "bin").mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(CPP))
from build_profile import generate_trimmed_api
from binding_generator import generate_bindings

api = generate_trimmed_api(str(CPP / "gdextension/extension_api.json"), str(ROOT / "native/godot_build_profile.json"))
api_path = WORK / "extension_api.json"
api_path.write_text(json.dumps(api), encoding="utf-8")
generate_bindings(str(api_path), False, "64", "single", str(WORK))
zig = str(ROOT / ".tools/zig-x86_64-windows-0.17.0/zig.exe")
compiler = compiler_identity(Path(zig))
tracked_inputs = [ROOT/"native/membrane_kernel.cpp",ROOT/"native/membrane_sparse.h",ROOT/"native/godot_membrane.cpp",
                  ROOT/"native/godot_build_profile.json",ROOT/"native/test_project.godot",ROOT/"native/membrane.gdextension",
                  ROOT/"tools/native_build_provenance.py",Path(__file__).resolve()]
input_hashes = source_hashes(tracked_inputs)
flags = ["-std=c++17", "-O3", "-DNDEBUG", "-DGDEXTENSION", "-DTHREADS_ENABLED", "-DEIGEN_MPL2_ONLY",
         "-target", "x86_64-windows-gnu"]
for include in [CPP / "include", CPP / "gdextension", WORK / "gen/include", EIGEN]:
    flags += ["-isystem", str(include)]
sources = sorted((CPP / "src").rglob("*.cpp"))+sorted((WORK / "gen/src").rglob("*.cpp"))
sources += [ROOT / "native/membrane_kernel.cpp", ROOT / "native/godot_membrane.cpp"]
base_key = repr(flags)+repr(PINS)+repr(compiler)+api_path.read_text(encoding="utf-8")

def compile_one(source):
    key = base_key.encode()+source.read_bytes()
    if source.parent == ROOT / "native":
        key += (ROOT / "native/membrane_sparse.h").read_bytes()
    digest = hashlib.sha256(key).hexdigest()
    obj = WORK / "obj" / f"{source.stem}-{digest[:20]}.o"
    if not obj.exists():
        completed = subprocess.run([zig,"c++",*flags,"-c",str(source),"-o",str(obj)], capture_output=True, text=True)
        if completed.returncode:
            raise RuntimeError(f"{source}\n{completed.stdout}\n{completed.stderr}")
    return obj

print(f"Building isolated extension: {len(sources)} translation units,4 workers", flush=True)
objects = []
with ThreadPoolExecutor(max_workers=4) as pool:
    futures = [pool.submit(compile_one, source) for source in sources]
    for number, future in enumerate(as_completed(futures),1):
        objects.append(future.result())
        if number%10 == 0 or number == len(sources): print(f"Compiled/cached {number}/{len(sources)}", flush=True)
# A response file avoids Windows command-line length limits; paths are literal compiler arguments.
response = WORK / "objects.rsp"
response.write_text("\n".join('"'+str(path).replace('\\','/')+'"' for path in sorted(objects)), encoding="utf-8")
subprocess.run([zig,"c++","-shared","-target","x86_64-windows-gnu","@"+str(response),
                "-o",str(PROJECT / "bin/membrane.dll")], check=True)
write_manifest(PROJECT/"bin/membrane.build.json",PROJECT/"bin/membrane.dll",input_hashes,compiler,
               {str(path.relative_to(ROOT)):revision for path,revision in PINS.items()},flags)
shutil.copyfile(ROOT/"native/test_project.godot",PROJECT/"project.godot")
shutil.copyfile(ROOT/"native/membrane.gdextension",PROJECT/"bin/membrane.gdextension")
shutil.copyfile(ROOT / "native/tests/test_godot_bridge.gd", PROJECT / "test_bridge.gd")
shutil.copyfile(ROOT / "native/tests/fixtures/refined_flap.json", PROJECT / "refined_flap.json")
print(f"Built test project at {PROJECT}", flush=True)
