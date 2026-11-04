"""Build separate numerical line observer; no product DLL promotion."""
from pathlib import Path
import subprocess
from native_build_provenance import compiler_identity,source_hashes,write_manifest
ROOT=Path(__file__).resolve().parents[1]
zig=ROOT/'.tools/zig-x86_64-windows-0.17.0/zig.exe';eigen=ROOT/'.tools/eigen-5.0.1'
pin=subprocess.check_output(['git','-C',str(eigen),'rev-parse','HEAD'],text=True).strip()
if pin!='bc3b39870ecb690a623a3f49149a358b95c5781d' or subprocess.check_output(['git','-C',str(eigen),'status','--porcelain'],text=True).strip():raise SystemExit('Unpinned Eigen')
compiler=compiler_identity(zig)
sources=source_hashes([ROOT/'native/tests/fem_contact_trace_probe.cpp',ROOT/'native/membrane_fem.cpp',ROOT/'native/membrane_fem.h',ROOT/'native/membrane_fem_contact.inc',ROOT/'native/embedded_contact.h',ROOT/'native/contact_distance.h',ROOT/'native/contact_merit_difference.h',ROOT/'native/contact_guard.h',Path(__file__).resolve(),ROOT/'tools/native_build_provenance.py'])
flags=['-std=c++17','-O3','-Wall','-Wextra','-Werror','-DEIGEN_MPL2_ONLY','-isystem',str(eigen),'-shared','-target','x86_64-windows-gnu']
artifact=ROOT/'.tools/native/fem_contact_trace.dll'
subprocess.run([str(zig),'c++',*flags,str(ROOT/'native/tests/fem_contact_trace_probe.cpp'),'-o',str(artifact)],check=True)
write_manifest(artifact.with_suffix('.build.json'),artifact,sources,compiler,{str(eigen.relative_to(ROOT)):pin},flags)
