"""Generate material normal constraints for owned179; complete geometry gates remain."""
import ctypes as ct
import argparse
from decimal import Decimal,localcontext
import json
from pathlib import Path
import sys
import time
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--require-qualified',action='store_true',help='Fail unless all owned endpoint/force/full-motion checks pass')
options=parser.parse_args()
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'native/tests')]
from native_build_provenance import sha256,source_hashes,verify_sources
from replay_fem_contact import replay
from replay_fem_trajectory import publish,guard

fixture=ROOT/'docs/assets/operative-motion179-native-case-2026-11-05.json'
case=json.loads(fixture.read_text());p=case['native_history'][0]['request']
assert not p['targets'],'This owned independent stress audit has no grasp reactions'
inputs=source_hashes([fixture,Path(__file__),ROOT/'native/tests/replay_fem_contact.py',ROOT/'native/tests/replay_fem_trajectory.py'])
builds={}
for name in ('membrane_fem','contact_distance','contact_guard'):
    artifact=ROOT/f'.tools/native/{name}.dll';manifest=json.loads(artifact.with_suffix('.build.json').read_text())
    verify_sources(manifest['sources']);assert sha256(artifact)==manifest['artifact_sha256'];builds[name]=manifest
library=ROOT/'.tools/native/membrane_fem.dll'
dll=ct.CDLL(str(ROOT/'.tools/native/contact_distance.dll'));D=ct.POINTER(ct.c_double)
witness=dll.membrane_material_witness;witness.argtypes=[D,D,D,ct.c_double,D];witness.restype=ct.c_int
ptr=lambda a:a.ctypes.data_as(D)
nodes=np.array(p['face_nodes']).reshape(-1,3);shapes=np.array(p['face_weights']).reshape(-1,3,3)
bodies=np.array(p['capsules']).reshape(-1,7)
points=[];keys=set()
def add(face,bary):
    with localcontext() as context:
        context.prec=80;d=lambda a:Decimal.from_float(float(a))
        b=list(map(d,bary));total=sum(b);b=[x/total for x in b]
        rows=[[d(v) for v in row] for row in shapes[face]]
        w=[float(sum(b[j]*rows[j][k]/sum(rows[j]) for j in range(3))) for k in range(3)]
    key=tuple(sorted((int(node),float(weight).hex()) for node,weight in zip(nodes[face],w) if weight>0.))
    if key in keys:return False
    keys.add(key);points.append({'face':face,'bary':list(map(float,bary)),'nodes':nodes[face].tolist(),'weights':w});return True
def geometry(x,seed=False):
    q=np.array(x).reshape(-1,3);violations=[];minimum=float('inf');invalid=[]
    for face,(ids,shape) in enumerate(zip(nodes,shapes)):
        controls=q[ids].copy()
        for body,capsule in enumerate(bodies):
            out=np.full(13,123.);status=witness(ptr(capsule),ptr(controls),ptr(shape),capsule[6],ptr(out))
            if status not in (0,1,3):invalid.append([face,body,status]);continue
            minimum=min(minimum,float(out[1]))
            if seed and out[1]<.02:
                for j in range(3):add(face,np.eye(3)[j])
                add(face,out[8:11])
            if out[1]<-p['gap_tolerance']:violations.append({'face':face,'body':body,'gap':out[1],'bary':out[8:11].tolist()})
    return {'minimum_gap':minimum,'invalid':invalid,'violations':violations}
initial_geometry=geometry(p['xyz'],True)
report={'qualified':False,'scope':'Owned endpoint distributed material-point candidate and independent checks only; no engine state, full surgery, real-time or release qualification.',
        'inputs':inputs,'builds':builds,'initial_geometry':initial_geometry,'history':[],'spent_iterations':0}
destination=ROOT/'godot/reports/motion179-material-points.json'
for exchange in range(16):
    if report['spent_iterations']>=p['budget']:break
    request=dict(p,budget=p['budget']-report['spent_iterations'],
                 face_nodes=[n for point in points for n in point['nodes']],
                 face_weights=[w for point in points for _ in range(3) for w in point['weights']])
    assert len(points)<=8192 and len(points)*len(bodies)<=65536
    print(f'Owned179 material point exchange{exchange}: {len(points)} points, remaining {request["budget"]}',flush=True)
    started=time.perf_counter();result=replay(request,library,method='membrane_fem_solve_material_points')
    status,x,reaction,dual,stats=result;report['spent_iterations']+=int(stats[2])
    row={'exchange':exchange,'points':len(points),'status':status,'stats':stats.tolist(),'elapsed_seconds':time.perf_counter()-started}
    report['history'].append(row)
    if status!=0:
        np.testing.assert_array_equal(x,p['xyz']);np.testing.assert_array_equal(dual,123.)
        row['failed_output_atomic']=True;destination.write_text(json.dumps(report,indent=2));print(json.dumps(row),flush=True);break
    checked=geometry(x);row['geometry']=checked
    print(json.dumps({k:v for k,v in row.items() if k!='geometry'}),flush=True)
    print(f'Complete endpoint geometry: gap={checked["minimum_gap"]}, violations={len(checked["violations"])}, invalid={len(checked["invalid"])}',flush=True)
    if not checked['violations'] and not checked['invalid']:
        # Independent original membrane stress plus actual distributed normal forces.
        q=x.reshape(-1,3);pred=np.array(p['xyz']).reshape(-1,3);force=np.zeros_like(q)
        for ids,basis,area in zip(np.array(p['nodes']).reshape(-1,3),np.array(p['gradients']).reshape(-1,2,3),p['areas']):
            f=(q[ids[1:]]-q[ids[0]]).T@basis[:,1:].T;c=f.T@f
            stress=p['mu']*f+(p['lambda']*.5*np.linalg.slogdet(c)[1]-p['mu'])*f@np.linalg.inv(c)
            force[ids]+=(area*stress@basis).T
        inverse=np.array(p['inverse']);free=inverse>0.;force[free]+=(q[free]-pred[free])/(inverse[free,None]*p['dt']**2)
        maximum_comp=0.
        for point,multipliers in zip(points,dual.reshape(len(points),len(bodies))):
            ids=point['nodes'];w=np.array(point['weights']);w=w/sum(w);value=w@q[ids]
            for capsule,u in zip(bodies,multipliers):
                axis=capsule[3:6]-capsule[:3];length=axis@axis
                t=np.clip((value-capsule[:3])@axis/length,0.,1.) if length else 0.
                delta=value-capsule[:3]-t*axis;gap=delta@delta/capsule[6]**2-1.
                assert u>=0.;maximum_comp=max(maximum_comp,abs(u*gap))
                force[ids]-=u*2.*w[:,None]*delta/capsule[6]**2
        residual=float(np.max(abs(force[free])));row['independent_force_inf']=residual;row['independent_complementarity']=maximum_comp
        row['endpoint_physical_qualified']=bool(residual<=p['force_tolerance'] and maximum_comp<=p['complementarity_tolerance'])
        # This full original guard is mandatory even after every sampled row passes.
        clearance=guard(case['motion'],publish(x,p,case['motion']['triangles']),ROOT/'.tools/native/contact_guard.dll')
        row.update({'guard_status':clearance[0],'guard_stats':clearance[1].tolist(),'guard_witness_t':clearance[2]})
        report['owned_step_qualified']=bool(row['endpoint_physical_qualified'] and clearance[0]==0)
        report['result']={'xyz':x.tolist(),'dual':dual.tolist(),'reaction':reaction.tolist(),'points':points}
        destination.write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in row.items() if k!='geometry'}),flush=True);break
    added=0
    for violation in checked['violations']:added+=int(add(violation['face'],violation['bary']))
    row['added_points']=added;destination.write_text(json.dumps(report,indent=2))
    if not added or checked['invalid']:break
verify_sources(inputs)
for name,manifest in builds.items():
    verify_sources(manifest['sources']);assert sha256(ROOT/f'.tools/native/{name}.dll')==manifest['artifact_sha256']
report['capture_completed']=True;destination.write_text(json.dumps(report,indent=2))
print(json.dumps({'report':str(destination),'owned_step_qualified':report.get('owned_step_qualified',False),'spent_iterations':report['spent_iterations']}),flush=True)
raise SystemExit(1 if options.require_qualified and not report.get('owned_step_qualified',False) else 0)
