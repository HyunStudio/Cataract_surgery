"""Build isolated helper-count qualification; never linked into the app."""
from pathlib import Path
import subprocess
from native_build_provenance import compiler_identity,source_hashes,write_manifest
ROOT=Path(__file__).resolve().parents[1]
zig=ROOT/'.tools/zig-x86_64-windows-0.17.0/zig.exe'
eigen=ROOT/'.tools/eigen-5.0.1'
revision=subprocess.check_output(['git','-C',str(eigen),'rev-parse','HEAD'],text=True).strip()
if revision!='bc3b39870ecb690a623a3f49149a358b95c5781d' or subprocess.check_output(['git','-C',str(eigen),'status','--porcelain'],text=True).strip():
    raise SystemExit('Unpinned Eigen')
compiler=compiler_identity(zig)
sources=source_hashes([ROOT/'native/tests/fem_activity_probe.cpp',Path(__file__).resolve(),ROOT/'tools/native_build_provenance.py'])
flags=['-std=c++17','-O3','-Wall','-Wextra','-Werror','-DEIGEN_MPL2_ONLY','-isystem',str(eigen),'-shared','-target','x86_64-windows-gnu']
artifact=ROOT/'.tools/native/contact_activity_probe.dll'
subprocess.run([str(zig),'c++',*flags,str(ROOT/'native/tests/fem_activity_probe.cpp'),'-o',str(artifact)],check=True)
write_manifest(artifact.with_suffix('.build.json'),artifact,sources,compiler,{str(eigen.relative_to(ROOT)):revision},flags)
