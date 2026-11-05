"""Build an isolated normal-contact derivative/merit test probe."""
from pathlib import Path
import subprocess
from native_build_provenance import compiler_identity,source_hashes,write_manifest

ROOT=Path(__file__).resolve().parents[1]
zig=ROOT/'.tools/zig-x86_64-windows-0.17.0/zig.exe'
compiler=compiler_identity(zig)
source=ROOT/'native/tests/material_point_probe.cpp'
inputs=source_hashes([source,Path(__file__),ROOT/'tools/native_build_provenance.py'])
artifact=ROOT/'.tools/native/material_point_probe.dll'
flags=['-std=c++17','-O3','-Wall','-Wextra','-Wpedantic','-Werror','-shared','-target','x86_64-windows-gnu']
subprocess.run([str(zig),'c++',*flags,str(source),'-o',str(artifact)],check=True)
write_manifest(artifact.with_suffix('.build.json'),artifact,inputs,compiler,{},flags)
