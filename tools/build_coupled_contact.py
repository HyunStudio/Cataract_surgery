"""Build the isolated coupled solver; does not promote a Godot backend."""
from pathlib import Path
import subprocess
from native_build_provenance import compiler_identity, source_hashes, write_manifest

ROOT = Path(__file__).resolve().parents[1]
out = ROOT/".tools/native"
out.mkdir(parents=True, exist_ok=True)
eigen = ROOT/".tools/eigen-5.0.1"
revision = subprocess.check_output(["git", "-C", str(eigen), "rev-parse", "HEAD"], text=True).strip()
dirty = subprocess.check_output(["git", "-C", str(eigen), "status", "--porcelain"], text=True).strip()
if revision != "bc3b39870ecb690a623a3f49149a358b95c5781d" or dirty:
    raise SystemExit("Unexpected Eigen dependency; run setup_native_dependencies.py")
zig = ROOT/".tools/zig-x86_64-windows-0.17.0/zig.exe"
compiler = compiler_identity(zig)
sources = source_hashes([ROOT/"native/membrane_contact_solver.cpp", ROOT/"native/membrane_contact_solver.h",
                         ROOT/"native/contact_distance.h",ROOT/"native/contact_guard.h",ROOT/"native/contact_merit_difference.h",
                         ROOT/"native/contact_step_model.h", Path(__file__).resolve(), ROOT/"tools/native_build_provenance.py"])
flags = ["-std=c++17", "-O3", "-Wall", "-Wextra", "-Wpedantic", "-Werror", "-DEIGEN_MPL2_ONLY",
         "-isystem", str(eigen), "-shared", "-target", "x86_64-windows-gnu"]
artifact = out/"membrane_contact.dll"
subprocess.run([str(zig), "c++", *flags, str(ROOT/"native/membrane_contact_solver.cpp"), "-o", str(artifact)], check=True)
write_manifest(out/"membrane_contact.build.json", artifact, sources, compiler, {str(eigen.relative_to(ROOT)): revision}, flags)
