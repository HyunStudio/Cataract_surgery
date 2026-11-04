"""Profile an isolated instrumented copy; retain physical KKT/whole-path checks."""
import argparse
import ctypes as ct
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
root=Path(__file__).resolve().parents[1];sys.path[:0]=[str(root/'tools'),str(root/'native/tests')]
from native_build_provenance import sha256,compiler_identity
from replay_fem_trajectory import replay,publish,guard
from test_fem_trajectory import FEMTrajectoryTests
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,default=root/'godot/reports/trajectory-contact-profile.json')
args=parser.parse_args()
compiler=compiler_identity(root/'.tools/zig-x86_64-windows-0.17.0/zig.exe')
eigen=root/'.tools/eigen-5.0.1'
pin=subprocess.check_output(['git','-C',str(eigen),'rev-parse','HEAD'],text=True).strip()
if pin!='bc3b39870ecb690a623a3f49149a358b95c5781d' or subprocess.check_output(['git','-C',str(eigen),'status','--porcelain'],text=True).strip():raise SystemExit('Unpinned Eigen')
probe=Path(tempfile.mkdtemp(prefix='fem-profile-',dir=root/'.tools'))
original={str(p.relative_to(root)):sha256(p) for p in (root/'native').iterdir() if p.is_file() and p.suffix in ['.h','.inc','.cpp']}
for name in original:shutil.copyfile(root/name,probe/Path(name).name)
prefix='''#include <chrono>
static double profile_seconds[7]{},profile_calls[7]{};
struct ProfileScope {
 int index;std::chrono::steady_clock::time_point start;
 explicit ProfileScope(int k):index(k),start(std::chrono::steady_clock::now()){}
 ~ProfileScope(){profile_seconds[index]+=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();profile_calls[index]+=1.;}
};
'''
source=(probe/'membrane_fem.cpp').read_text()
for signature in ['int factor(const Vec& blocks,const Vec& mass,double damping,const Vec& metric,double rho=0.) {',
                  'bool direction(const Vec& gradient,Vec& output,double& residual) {',
                  'bool solve_matrix(const Eigen::MatrixXd& input,Eigen::MatrixXd& output,double& residual) {']:
 assert source.count(signature)==1
 source=source.replace(signature,signature+'ProfileScope timing('+('5' if signature.startswith('int factor') else '6')+');')
source=prefix+source+'\nFEM_EXPORT void fem_profile_stats(double* out){for(int k=0;k<7;++k){out[k*2]=profile_seconds[k];out[k*2+1]=profile_calls[k];}}\n'
(probe/'membrane_fem.cpp').write_text(source)
inc=(probe/'membrane_fem_contact.inc').read_text()
signature='bool evaluate(const Problem& problem,const Vec& x,const Vec& dual,double rho,ContactState& out,bool physical_dual=false) const {'
assert inc.count(signature)==1;inc=inc.replace(signature,signature+'ProfileScope total_timing(0);')
signature='const ContactState& current,const ContactState& candidate,double& upper) const {'
assert inc.count(signature)==1;inc=inc.replace(signature,signature+'ProfileScope total_timing(1);')
for old,index in [('membrane::contact::distance(capsule,triangle,capsule[6])',2),('membrane::embedded_contact::distance(capsule,controls,weights+face*9,capsule[6])',4),('membrane::embedded_contact::distance(body,controls,face_weights+face*9,body[6])',4)]:
 assert inc.count(old)==1
 inc=inc.replace(old,'[&](){ProfileScope timing('+str(index)+');return '+old+';}()')
old='if(previous) {\n                // The full query above'
assert inc.count(old)==1;inc=inc.replace(old,'if(previous) {ProfileScope field_timing(3);\n                // The full query above')
header=(probe/'fem_trajectory_merit.h').read_text();signature='inline Hull hull(const double* previous,const double* end,double time) {'
assert header.count(signature)==1;header=header.replace(signature,signature+'ProfileScope hull_timing(3);')
(probe/'fem_trajectory_merit.h').write_text(header)
(probe/'membrane_fem_contact.inc').write_text(inc)
library=probe/'profile.dll'
subprocess.run([str(root/'.tools/zig-x86_64-windows-0.17.0/zig.exe'),'c++','-std=c++17','-O3','-Wall','-Wextra','-Werror','-DEIGEN_MPL2_ONLY','-isystem',str(root/'.tools/eigen-5.0.1'),'-shared','-target','x86_64-windows-gnu',str(probe/'membrane_fem.cpp'),'-o',str(library)],check=True)
data=json.loads((root/'native/tests/fixtures/operative_motion144.json').read_text());old=json.loads((root/'native/tests/fixtures/operative_motion144_controls.json').read_text())['xyz'];p=data['fem_request'];motion=data['guard_request'];times=[.25,.375,.5,1.]
started=time.perf_counter();result=replay(p,old,motion['kinds'],motion['packets'],times,library);elapsed=time.perf_counter()-started
FEMTrajectoryTests().verify(p,old,motion['kinds'],motion['packets'],times,result)
clearance=guard(motion,publish(result[1],p,motion['triangles']),root/'.tools/native/contact_guard.dll');assert clearance[0]==0
stats=(ct.c_double*14)();dll=ct.CDLL(str(library));dll.fem_profile_stats.argtypes=[ct.POINTER(ct.c_double)];dll.fem_profile_stats.restype=None;dll.fem_profile_stats(stats)
names=['evaluate_inclusive','merit_difference_inclusive','full_geometry_queries','temporal_gap_field_inclusive','embedded_derivatives','sparse_factor','sparse_linear_solve']
report={'scope':'Diagnostic instrumented source copy only; independent captured KKT and full guard checked; no real-time qualification.', 'compiler':compiler,'eigen_pin':pin,'tool_sha256':sha256(Path(__file__)),'instrumented_sources':{Path(name).name:sha256(probe/Path(name).name) for name in original},'artifact_sha256':sha256(library),'source_inputs':original,'probe':str(probe),'status':result[0],'native_stats':result[4].tolist(),'guard_stats':clearance[1].tolist(),'wall_seconds':elapsed,'timings':{name:{'seconds':stats[k*2],'calls':stats[k*2+1]} for k,name in enumerate(names)}}
assert all(sha256(root/name)==value for name,value in original.items())
args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k not in ['source_inputs','instrumented_sources']}),flush=True)
