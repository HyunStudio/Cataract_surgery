"""Build the test-only stable merit interval probe, never a product API."""
from pathlib import Path
import subprocess
from native_build_provenance import compiler_identity,source_hashes,write_manifest
ROOT=Path(__file__).resolve().parents[1]
artifact=ROOT/".tools/native/contact_merit_probe.dll"
artifact.parent.mkdir(parents=True,exist_ok=True)
zig=ROOT/".tools/zig-x86_64-windows-0.17.0/zig.exe"
compiler=compiler_identity(zig)
sources=source_hashes([ROOT/name for name in ["native/contact_merit_difference.h","native/contact_guard.h","native/contact_distance.h",
    "native/tests/merit_difference_probe.cpp","tools/build_contact_merit_probe.py","tools/native_build_provenance.py"]])
flags=["-std=c++17","-O3","-Wall","-Wextra","-Wpedantic","-Werror","-shared","-target","x86_64-windows-gnu"]
subprocess.run([str(zig),"c++",*flags,str(ROOT/"native/tests/merit_difference_probe.cpp"),"-o",str(artifact)],check=True)
write_manifest(artifact.with_suffix(".build.json"),artifact,sources,compiler,{},flags)
