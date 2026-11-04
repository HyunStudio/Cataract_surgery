"""Build isolated calling-thread control diagnostics; never linked to product."""
from pathlib import Path
import subprocess
from native_build_provenance import compiler_identity,source_hashes,write_manifest
ROOT = Path(__file__).resolve().parents[1]
zig = ROOT/'.tools/zig-x86_64-windows-0.17.0/zig.exe'
compiler = compiler_identity(zig)
sources = source_hashes([ROOT/'native/tests/fp_environment_probe.cpp',ROOT/'native/contact_guard.h',ROOT/'native/contact_distance.h',Path(__file__).resolve(),ROOT/'tools/native_build_provenance.py'])
flags = ['-std=c++17','-O3','-Wall','-Wextra','-Werror','-shared','-target','x86_64-windows-gnu']
artifact = ROOT/'.tools/native/fp_environment_probe.dll'
subprocess.run([str(zig),'c++',*flags,str(ROOT/'native/tests/fp_environment_probe.cpp'),'-o',str(artifact)],check=True)
write_manifest(artifact.with_suffix('.build.json'),artifact,sources,compiler,{},flags)
