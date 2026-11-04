"""Freeze the original solver and trace exact motion156 without publishing it."""
import ctypes as ct
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
root=Path(__file__).resolve().parents[1];sys.path[:0]=[str(root/'tools'),str(root/'native/tests')]
from native_build_provenance import sha256,compiler_identity,verify_sources
from replay_fem_trajectory import replay,publish,guard
from replay_seeded_trajectory import exchange
from test_fem_trajectory import FEMTrajectoryTests
eigen=root/'.tools/eigen-5.0.1';pin=subprocess.check_output(['git','-C',str(eigen),'rev-parse','HEAD'],text=True).strip()
if pin!='bc3b39870ecb690a623a3f49149a358b95c5781d' or subprocess.check_output(['git','-C',str(eigen),'status','--porcelain'],text=True).strip():raise SystemExit('Unpinned Eigen')
baseline_manifest=json.loads((root/'.tools/native/membrane_fem.build.json').read_text());verify_sources(baseline_manifest['sources'])
if sha256(root/'.tools/native/membrane_fem.dll')!=baseline_manifest['artifact_sha256']:raise SystemExit('Baseline differs from manifest')
probe=Path(tempfile.mkdtemp(prefix='fem-trace156-',dir=root/'.tools'));source_dir=probe/'source';source_dir.mkdir()
source_inputs={str(p.relative_to(root)):sha256(p) for p in (root/'native').iterdir() if p.is_file() and p.suffix in ['.h','.inc','.cpp']}
for name in source_inputs:shutil.copyfile(root/name,source_dir/Path(name).name)
shutil.copyfile(root/'.tools/native/membrane_fem.dll',probe/'baseline.dll')
log=probe/'line.jsonl';meta=probe/'decisions.jsonl'
observer=(root/'native/tests/fem_contact_trace_probe.cpp').read_text();observer=observer.replace('../membrane_fem.cpp','membrane_fem.cpp').replace('".tools/native/fem-contact-trace.json"',json.dumps(log.as_posix()))
# These observers change no original predicate, input, work accounting or output.
prefix='''static void trace_decision(int kind,int iteration,int outer,double force,double proposed,int active,bool valid) {
 std::ofstream out(TRACE_DECISIONS,std::ios::app);out<<std::setprecision(17)<<"{\\"kind\\":"<<kind<<",\\"iteration\\":"<<iteration<<",\\"outer\\":"<<outer<<",\\"force\\":"<<force<<",\\"proposed_force\\":"<<proposed<<",\\"active\\":"<<active<<",\\"valid\\":"<<(valid?"true":"false")<<"}\\n";
}
'''.replace('TRACE_DECISIONS',json.dumps(meta.as_posix()))
observer=observer.replace('#define FEM_CONTACT_TRACE',prefix+'\n#define FEM_CONTACT_TRACE')
(source_dir/'trace.cpp').write_text(observer)
inc=(source_dir/'membrane_fem_contact.inc').read_text()
inc=inc.replace('polish_tried=true;std::vector<int> active;','polish_tried=true;trace_decision(1,iterations,outer,force,0.,0,true);std::vector<int> active;')
inc=inc.replace('if(std::isfinite(pf) && ph.allFinite() && pf<=tolerance &&','trace_decision(2,iterations,outer,force,pf,static_cast<int>(active.size()),valid);\n                            if(std::isfinite(pf) && ph.allFinite() && pf<=tolerance &&')
inc=inc.replace('if(!solved) {status=2;break;}','if(!solved) {trace_decision(3,iterations,outer,force,0.,0,polish_tried);status=2;break;}')
inc=inc.replace('if(!(slope<0.) || !std::isfinite(slope)) {status=2;break;}','if(!(slope<0.) || !std::isfinite(slope)) {trace_decision(4,iterations,outer,force,slope,0,polish_tried);status=2;break;}')
inc=inc.replace('if(!accepted) {status=2;break;}','if(!accepted) {trace_decision(5,iterations,outer,force,0.,0,polish_tried);status=2;break;}')
(source_dir/'membrane_fem_contact.inc').write_text(inc)
compiler=compiler_identity(root/'.tools/zig-x86_64-windows-0.17.0/zig.exe')
library=probe/'trace.dll';print('Frozen motion156 trace sources: '+str(probe),flush=True)
subprocess.run([str(root/'.tools/zig-x86_64-windows-0.17.0/zig.exe'),'c++','-std=c++17','-O3','-Wall','-Wextra','-Werror','-DEIGEN_MPL2_ONLY','-isystem',str(root/'.tools/eigen-5.0.1'),'-shared','-target','x86_64-windows-gnu',str(source_dir/'trace.cpp'),'-o',str(library)],check=True)
fixture=root/'docs/assets/operative-motion156-native-case-2026-11-05.json';data=json.loads(fixture.read_text());p=data['fem_request'];old=data['previous_controls'];motion=data['motion'];spent=int(data['failure']['stats'][2]);times=[.5,1.];initial=None;seed=None;penalty=1.;rows=[]
for _ in range(2):
 request=dict(p,budget=p['budget']-spent);result=replay(request,old,motion['kinds'],motion['packets'],times,probe/'baseline.dll',initial=initial,multiplier_seed=seed,penalty_seed=penalty);FEMTrajectoryTests().verify(request,old,motion['kinds'],motion['packets'],times,result);spent+=int(result[4][2]);checked=guard(motion,publish(result[1],request,motion['triangles']),root/'.tools/native/contact_guard.dll');assert checked[0]==1
 rows.append({'times':times[:],'stats':result[4].tolist(),'witness':checked[2]});times,seed=exchange(times,result[3],len(p['face_nodes'])//3*len(motion['kinds']),checked[2]);initial=result[1];penalty=result[4][15]
request=dict(p,budget=p['budget']-spent);case={'request':request,'previous':old,'motion':motion,'times':times,'initial':initial.tolist(),'multiplier_seed':seed.tolist(),'penalty_seed':penalty,'prior_iterations':spent}
(probe/'seeded-case.json').write_text(json.dumps(case,separators=(',',':')));print('Saved exact four-layer numerical seed',flush=True)
dll=ct.CDLL(str(library));dll.fem_trace_configure.argtypes=[ct.c_int,ct.c_int];assert dll.fem_trace_configure(18,1)==0
result=replay(request,old,motion['kinds'],motion['packets'],times,library,initial=initial,multiplier_seed=seed,penalty_seed=penalty)
report={'scope':'Isolated source-bound motion156 stop/line/polish diagnosis; no product change or qualification.','probe':str(probe),'compiler':compiler,'eigen_pin':pin,'baseline_manifest':baseline_manifest,'tool_sha256':sha256(Path(__file__)),'original_sources':source_inputs,'instrumented_sources':{p.name:sha256(p) for p in source_dir.iterdir()},'fixture_sha256':sha256(fixture),'baseline_sha256':sha256(probe/'baseline.dll'),'trace_sha256':sha256(library),'prefix':rows,'seed_sha256':sha256(probe/'seeded-case.json'),'status':result[0],'stats':result[4].tolist(),'line_sha256':sha256(log),'decisions': [json.loads(x) for x in meta.read_text().splitlines()]}
(root/'godot/reports/motion156-stop-trace.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k not in ['original_sources','instrumented_sources','prefix','compiler']}),flush=True)
