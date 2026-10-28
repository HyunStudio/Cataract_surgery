"""Build the isolated double trajectory guard; no product promotion."""
from pathlib import Path
import subprocess
from native_build_provenance import compiler_identity,source_hashes,write_manifest
ROOT=Path(__file__).resolve().parents[1]
out=ROOT/".tools/native"; out.mkdir(parents=True,exist_ok=True)
zig=ROOT/".tools/zig-x86_64-windows-0.17.0/zig.exe"
compiler=compiler_identity(zig)
sources=source_hashes([ROOT/"native/contact_guard.cpp",ROOT/"native/contact_guard.h",ROOT/"native/contact_distance.h",
                       Path(__file__).resolve(),ROOT/"tools/native_build_provenance.py"])
flags=["-std=c++17","-O3","-Wall","-Wextra","-Wpedantic","-Werror","-shared","-target","x86_64-windows-gnu"]
artifact=out/"contact_guard.dll"
subprocess.run([str(zig),"c++",*flags,str(ROOT/"native/contact_guard.cpp"),"-o",str(artifact)],check=True)
write_manifest(out/"contact_guard.build.json",artifact,sources,compiler,{},flags)
