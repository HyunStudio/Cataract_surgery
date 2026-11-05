"""Observe an owned failed request in a frozen diagnostic DLL; no product changes."""
import argparse
import ctypes as ct
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'tools'), str(ROOT/'native/tests')]
from native_build_provenance import sha256, compiler_identity, verify_sources
from replay_fem_contact import replay as endpoint
from replay_fem_trajectory import replay as trajectory

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--motion', type=int, required=True)
parser.add_argument('--request', type=int, default=0)
args = parser.parse_args()
fixture = ROOT/f'docs/assets/operative-motion{args.motion}-native-case-2026-11-05.json'
case = json.loads(fixture.read_text())
row = case['native_history'][args.request]
manifest = json.loads((ROOT/'.tools/native/membrane_fem.build.json').read_text())
verify_sources(manifest['sources'])
assert sha256(ROOT/'.tools/native/membrane_fem.dll') == manifest['artifact_sha256']
eigen = ROOT/'.tools/eigen-5.0.1'
pin = subprocess.check_output(['git','-C',str(eigen),'rev-parse','HEAD'],text=True).strip()
assert pin == 'bc3b39870ecb690a623a3f49149a358b95c5781d'
assert not subprocess.check_output(['git','-C',str(eigen),'status','--porcelain'],text=True).strip()
probe = Path(tempfile.mkdtemp(prefix=f'fem-trace{args.motion}-',dir=ROOT/'.tools'))
source = probe/'source'
source.mkdir()
originals = {str(p.relative_to(ROOT)):sha256(p) for p in (ROOT/'native').iterdir()
             if p.is_file() and p.suffix in ('.h','.inc','.cpp')}
for name in originals:
    shutil.copyfile(ROOT/name,source/Path(name).name)
shutil.copyfile(fixture,probe/'case.json')
line_log = probe/'line.jsonl'
decision_log = probe/'decisions.jsonl'
observer = (ROOT/'native/tests/fem_contact_trace_probe.cpp').read_text()
observer = observer.replace('../membrane_fem.cpp','membrane_fem.cpp')
observer = observer.replace('".tools/native/fem-contact-trace.json"',json.dumps(line_log.as_posix()))
prefix = r'''
static void decision(int kind,int iteration,int outer,int attempt,double force,double damping,double linear,bool ok) {
 std::ofstream out(DECISIONS,std::ios::app);
 out<<std::setprecision(17)<<"{\"kind\":"<<kind<<",\"iteration\":"<<iteration<<",\"outer\":"<<outer
 <<",\"attempt\":"<<attempt<<",\"force\":"<<force<<",\"damping\":"<<damping<<",\"linear\":"<<linear
 <<",\"ok\":"<<(ok?"true":"false")<<"}\n";
}
'''.replace('DECISIONS',json.dumps(decision_log.as_posix()))
observer = observer.replace('#define FEM_CONTACT_TRACE',prefix+'\n#define FEM_CONTACT_TRACE')
(source/'trace.cpp').write_text(observer)
inc = (source/'membrane_fem_contact.inc').read_text()
def insert(old,new):
    global inc
    assert inc.count(old) == 1, old
    inc = inc.replace(old,new)
insert('if(!solved) {status=2;break;}',
       'if(!solved) {decision(3,iterations,outer,0,force,damping,linear,false);status=2;break;}')
insert('if(!(slope<0.) || !std::isfinite(slope)) {status=2;break;}',
       'if(!(slope<0.) || !std::isfinite(slope)) {decision(4,iterations,outer,0,force,damping,slope,false);status=2;break;}')
insert('if(!accepted) {status=2;break;}',
       'if(!accepted) {decision(5,iterations,outer,0,force,damping,linear,false);status=2;break;}')
insert('if(curvature==2) break;',
       'decision(10,iterations,outer,attempt,force,damping,double(curvature),curvature==0);if(curvature==2) break;')
insert('if(solved) break;',
       'decision(11,iterations,outer,attempt,force,damping,linear,solved);if(solved) break;')
insert('x.swap(trial);std::swap(state,next);++iterations;',
       'decision(12,iterations,outer,0,force,damping,fraction,true);x.swap(trial);std::swap(state,next);++iterations;')
(source/'membrane_fem_contact.inc').write_text(inc)
zig = ROOT/'.tools/zig-x86_64-windows-0.17.0/zig.exe'
compiler = compiler_identity(zig)
library = probe/'trace.dll'
print('Frozen diagnostic probe: '+str(probe),flush=True)
subprocess.run([str(zig),'c++','-std=c++17','-O3','-Wall','-Wextra','-Werror',
                '-DEIGEN_MPL2_ONLY','-isystem',str(eigen),'-shared','-target',
                'x86_64-windows-gnu',str(source/'trace.cpp'),'-o',str(library)],check=True)
dll = ct.CDLL(str(library))
dll.fem_trace_configure.argtypes = [ct.c_int,ct.c_int]
assert dll.fem_trace_configure(0,1) == 0
p = row['request']
if row['kind'] in ('static','precise_endpoint'):
    result = endpoint(p,library,precise=row['kind']=='precise_endpoint')
else:
    extra = {k:p[k] for k in ('initial','multiplier_seed','penalty_seed')} if row['kind']=='seeded' else {}
    result = trajectory(p,p['previous'],p['kinds'],p['packets'],p['times'],library,**extra)
assert result[0] == row['response']['status']
np.testing.assert_array_equal(result[4],row['response']['stats'])
assert result[0] != 0
np.testing.assert_array_equal(result[1],p['xyz'])
np.testing.assert_array_equal(result[2],123.)
np.testing.assert_array_equal(result[3],123.)
verify_sources(originals)
verify_sources(manifest['sources'])
report = {'qualified':False,'scope':'Frozen diagnostic observation only; no product DLL promotion or physical acceptance.',
          'motion':args.motion,'request':args.request,'probe':str(probe),'compiler':compiler,
          'eigen_pin':pin,'baseline_build':manifest,'original_sources':originals,
          'tool_sha256':sha256(Path(__file__)),'fixture_sha256':sha256(fixture),
          'instrumented_sources':{p.name:sha256(p) for p in source.iterdir()},
          'trace_sha256':sha256(library),'status':result[0],'stats':result[4].tolist(),
          'same_saved_stats':True,'failed_output_atomic':True,
          'line_sha256':sha256(line_log),'decisions_sha256':sha256(decision_log),
          'decisions':[json.loads(x) for x in decision_log.read_text().splitlines()]}
destination = ROOT/f'godot/reports/motion{args.motion}-request{args.request}-stop-trace.json'
destination.write_text(json.dumps(report,indent=2))
print(json.dumps({'report':str(destination),'status':result[0],'stats':result[4].tolist(),
                  'terminal_decisions':report['decisions'][-5:]}),flush=True)
