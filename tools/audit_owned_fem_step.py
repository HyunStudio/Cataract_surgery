"""Decompose saved diagnostic endpoint trial increments; never qualify a step."""
import ctypes as ct
from decimal import Decimal, localcontext
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
sys.path.insert(0,str(ROOT/'native/tests'))
from native_build_provenance import sha256,source_hashes,verify_sources,compiler_identity
from decimal_distance_reference import contact_merit

trace_path=ROOT/'godot/reports/motion179-request0-stop-trace.json'
trace=json.loads(trace_path.read_text())
line_path=Path(trace['probe'])/'line.jsonl'
assert sha256(line_path)==trace['line_sha256']
case_path=ROOT/'docs/assets/operative-motion179-native-case-2026-11-05.json'
assert sha256(case_path)==trace['fixture_sha256']
p=json.loads(case_path.read_text())['native_history'][0]['request']
inputs=source_hashes([ROOT/'native/tests/contact_step_audit_probe.cpp',ROOT/'native/tests/decimal_distance_reference.py',Path(__file__),trace_path,case_path])
probe=Path(tempfile.mkdtemp(prefix='fem-step179-',dir=ROOT/'.tools'))
source=probe/'source';source.mkdir()
for name in inputs:
    path=ROOT/name
    if path.suffix in ('.h','.inc','.cpp'):
        content=path.read_text().replace('#include "../','#include "')
        (source/path.name).write_text(content)
zig=ROOT/'.tools/zig-x86_64-windows-0.17.0/zig.exe'
compiler=compiler_identity(zig)
library=probe/'audit.dll'
print('Frozen local increment audit: '+str(probe),flush=True)
subprocess.run([str(zig),'c++','-std=c++17','-O3','-Wall','-Wextra','-Werror',
                '-shared','-target','x86_64-windows-gnu',str(source/'contact_step_audit_probe.cpp'),
                '-o',str(library)],check=True)
dll=ct.CDLL(str(library));D=ct.POINTER(ct.c_double)
contact=dll.audit_contact_step;contact.argtypes=[D,D,D,D,D,ct.c_double,ct.c_double,ct.c_double,D]
cell=dll.audit_cell_step;cell.argtypes=[D,D,D,ct.c_double,ct.c_double,ct.c_double,D]
ptr=lambda x:x.ctypes.data_as(D)
predicted=np.array(p['xyz']).reshape(-1,3);inverse=np.array(p['inverse'])
mass=np.zeros_like(inverse);free=inverse>0.;mass[free]=1./(inverse[free]*p['dt']**2)
nodes=np.array(p['nodes']).reshape(-1,3);basis=np.array(p['gradients']).reshape(-1,6)
faces=np.array(p['face_nodes']).reshape(-1,3);shapes=np.array(p['face_weights']).reshape(-1,9)
bodies=np.array(p['capsules']).reshape(-1,7)
lines=[json.loads(x) for x in line_path.read_text().splitlines()]
report={'qualified':False,'scope':'Diagnostic merit/gradient decomposition only; no product change or accepted physical step.',
        'inputs':inputs,'trace_sha256':sha256(trace_path),'line_sha256':sha256(line_path),
        'compiler':compiler,'probe':str(probe),'artifact_sha256':sha256(library),'trials':[]}
for iteration in (0,6,10,16,38):
    z=next(x for x in lines if x['iteration']==iteration)
    x=np.array(z['x']).reshape(-1,3);y=np.array(z['y']).reshape(-1,3);delta=y-x
    cells=[];contacts=[]
    for index,(ids,b,area) in enumerate(zip(nodes,basis,p['areas'])):
        a=x[ids].copy();after=y[ids].copy();out=np.zeros(3)
        status=cell(ptr(a),ptr(after),ptr(b),area,p['mu'],p['lambda'],ptr(out))
        assert status==0,(index,status)
        cells.append({'cell':index,'area':area,'slope':out[1],'change':out[2]})
    for face,(ids,shape) in enumerate(zip(faces,shapes)):
        old=predicted[ids].copy();a=x[ids].copy();after=y[ids].copy()
        for body,capsule in enumerate(bodies):
            out=np.zeros(8);pair=face*len(bodies)+body
            status=contact(ptr(old),ptr(a),ptr(after),ptr(shape),ptr(capsule),capsule[6],z['dual'][pair],z['rho'],ptr(out))
            if status or out[2] or out[5] or out[6] or out[7]:
                contacts.append({'face':face,'body':body,'status':status,'values':out.tolist()})
    inertia_slope=float(np.sum(mass[:,None]*(x-predicted)*delta))
    inertia_change=float(np.sum(mass[:,None]*((x-predicted)*delta+.5*delta*delta)))
    actual_slope=inertia_slope+sum(a['slope'] for a in cells)+sum(a['values'][5] for a in contacts)
    change=inertia_change+sum(a['change'] for a in cells)+sum(a['values'][7] for a in contacts)
    value={'iteration':iteration,'fraction':z['fraction'],'original_slope':z['slope']*z['fraction'],
           'actual_slope':actual_slope,'original_change':z['change'],'summed_change':change,
           'inertia_slope':inertia_slope,'inertia_change':inertia_change,
           'largest_cell_mismatch':sorted(cells,key=lambda a:abs(a['change']-a['slope']),reverse=True)[:8],
           'contacts':contacts,
           'owned_trial':{'x':z['x'],'y':z['y'],'rho':z['rho'],
                          'dual_nonzero':{str(i):v for i,v in enumerate(z['dual']) if v!=0.}},
           'decimal_contact_changes':[]}
    assert abs(change-z['change'])<1e-13,(iteration,change,z['change'])
    assert abs(actual_slope-z['slope']*z['fraction'])<1e-13,(iteration,actual_slope,z['slope'])
    if iteration in (6,10,16):
        for face in (21,22,23):
            np.testing.assert_array_equal(shapes[face],np.eye(3).ravel())
            capsule=bodies[0];ids=faces[face]
            with localcontext() as context:
                context.prec=80
                reference=contact_merit(capsule[:6],y[ids].ravel(),capsule[6],z['dual'][face*len(bodies)],z['rho'])-contact_merit(capsule[:6],x[ids].ravel(),capsule[6],z['dual'][face*len(bodies)],z['rho'])
                v=next(c['values'] for c in contacts if c['face']==face and c['body']==0)
                assert Decimal.from_float(v[6])<=reference<=Decimal.from_float(v[7])
            value['decimal_contact_changes'].append({'face':face,'body':0,'change_80_digits':str(reference),'enclosed':True})
    if iteration==16:
        # Separate a finite feature-crossing increment from the local derivative.
        # Each candidate is rounded to represented binary64 before either oracle.
        face=22;ids=faces[face];shape=shapes[face];capsule=bodies[0]
        old=predicted[ids].copy();a=x[ids].copy();direction=delta[ids].copy()
        value['represented_direction_samples']=[]
        for fraction in (-1.,-.01,-.001,-.0001,.0001,.001,.002,.01,1.):
            after=a+fraction*direction;out=np.zeros(8)
            status=contact(ptr(old),ptr(a),ptr(after),ptr(shape),ptr(capsule),capsule[6],z['dual'][face*len(bodies)],z['rho'],ptr(out))
            with localcontext() as context:
                context.prec=80
                reference=contact_merit(capsule[:6],after.ravel(),capsule[6],z['dual'][face*len(bodies)],z['rho'])-contact_merit(capsule[:6],a.ravel(),capsule[6],z['dual'][face*len(bodies)],z['rho'])
                vertices=[[Decimal.from_float(float(v)) for v in row] for row in after]
                e=[vertices[1][k]-vertices[0][k] for k in range(3)]
                f=[vertices[2][k]-vertices[0][k] for k in range(3)]
                normal=[e[1]*f[2]-e[2]*f[1],e[2]*f[0]-e[0]*f[2],e[0]*f[1]-e[1]*f[0]]
                parallel=sum((Decimal.from_float(float(capsule[k+3]))-Decimal.from_float(float(capsule[k])))*normal[k] for k in range(3))
                if status==0:assert Decimal.from_float(out[6])<=reference<=Decimal.from_float(out[7])
            sample={'fraction':fraction,'status':status,'actual_linear_work':out[5],
                    'change_80_digits':str(reference),'axis_dot_normal_80_digits':str(parallel),
                    'bounds':out[6:8].tolist() if status==0 else None}
            value['represented_direction_samples'].append(sample)
            print(json.dumps({'direction_sample':sample}),flush=True)
    report['trials'].append(value)
    print(json.dumps({k:v for k,v in value.items() if k not in ('contacts','largest_cell_mismatch','owned_trial','decimal_contact_changes','represented_direction_samples')}),flush=True)
verify_sources(inputs)
(ROOT/'godot/reports/motion179-increment-audit.json').write_text(json.dumps(report,indent=2))
