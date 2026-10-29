"""Build the test-only unilateral step model; does not promote a backend."""
from pathlib import Path
import subprocess
from native_build_provenance import compiler_identity,source_hashes,write_manifest
ROOT=Path(__file__).resolve().parents[1]
artifact=ROOT/'.tools/native/contact_step_probe.dll'
artifact.parent.mkdir(parents=True,exist_ok=True)
zig=ROOT/'.tools/zig-x86_64-windows-0.17.0/zig.exe'
eigen=ROOT/'.tools/eigen-5.0.1'
revision=subprocess.check_output(['git','-C',str(eigen),'rev-parse','HEAD'],text=True).strip()
dirty=subprocess.check_output(['git','-C',str(eigen),'status','--porcelain'],text=True).strip()
if revision!='bc3b39870ecb690a623a3f49149a358b95c5781d' or dirty: raise SystemExit('Unexpected Eigen dependency')
compiler=compiler_identity(zig)
names=['native/contact_step_model.h','native/contact_merit_difference.h','native/contact_guard.h','native/contact_distance.h',
       'native/tests/contact_step_probe.cpp','tools/build_contact_step_probe.py','tools/native_build_provenance.py']
sources=source_hashes([ROOT/name for name in names])
flags=['-std=c++17','-O3','-Wall','-Wextra','-Wpedantic','-Werror','-DEIGEN_MPL2_ONLY',
       '-isystem',str(eigen),'-shared','-target','x86_64-windows-gnu']
subprocess.run([str(zig),'c++',*flags,str(ROOT/'native/tests/contact_step_probe.cpp'),'-o',str(artifact)],check=True)
write_manifest(artifact.with_suffix('.build.json'),artifact,sources,compiler,{str(eigen.relative_to(ROOT)):revision},flags)
