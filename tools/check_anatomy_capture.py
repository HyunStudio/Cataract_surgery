"""Explicit heavy KKT gate for one capture; rejection is NOT qualification."""
import ctypes as ct
import hashlib
import json
import math
from pathlib import Path
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'native/tests'))
from test_anatomical_contact import AnatomicalContactTests,D,I
from test_trajectory_contact import sample

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

fixture=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else ROOT/'native/tests/fixtures/joint_anatomy264.json'
artifact=ROOT/'.tools/native/membrane_contact.dll'
manifest_path=artifact.with_name('membrane_contact.build.json')
manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
def verify():
    assert sha(artifact)==manifest['artifact_sha256'],'DLL differs from build manifest'
    for name,digest in manifest['sources'].items(): assert sha(ROOT/name)==digest,name
verify()
fixture_hash=sha(fixture)
p=json.loads(fixture.read_text(encoding='utf-8'))
report=ROOT/'godot/reports/native-anatomy-capture-check.json'; report.parent.mkdir(parents=True,exist_ok=True)
proof={'qualified':False,'scope':'one captured selected-time mechanical solve; not a continuous timestep or extraction',
       'fixture':str(fixture),'fixture_sha256':fixture_hash,'dll_sha256':sha(artifact),'script_sha256':sha(Path(__file__)),
       'build':manifest,'state':'running'}
report.write_text(json.dumps(proof,indent=2),encoding='utf-8')
AnatomicalContactTests.setUpClass()
point=D(p['initial']); previous=D(p['previous']); predicted=D(p['predicted']); packets=D(p['packets']); records=D(p['anatomy'])
tool_count=len(p['triangles'])//3*len(p['kinds'])*len(p['times'])
count=tool_count+len(p['anatomy_vertices']); reactions=D([99.]*count); stats=D([99.]*12)
immutable=[previous,predicted,packets,records]; preserved=[bytes(value) for value in immutable]
status=AnatomicalContactTests.solve(len(p['inverse']),predicted,point,D(p['inverse']),len(p['a']),I(p['a']),I(p['b']),D(p['rest']),p['alpha'],
    len(p['triangles'])//3,I(p['triangles']),len(p['kinds']),I(p['kinds']),packets,previous,len(p['times']),D(p['times']),
    len(p['anatomy_vertices']),I(p['anatomy_vertices']),records,p['budget'],p['force_tolerance'],p['gap_tolerance'],p['complementarity_tolerance'],reactions,stats)
verify(); assert sha(fixture)==fixture_hash
assert [bytes(value) for value in immutable]==preserved
proof.update(state='terminal',status=status,stats=list(stats))
if status:
    proof['atomic_rejection']=list(point)==p['initial'] and list(reactions)==[99.]*count
    assert proof['atomic_rejection'],'failed solve published positions/reactions'
else:
    xyz=np.asarray(list(point)).reshape(-1,3); old=np.asarray(p['previous']).reshape(-1,3)
    inv=np.asarray(p['inverse']); free=inv>0
    mass=np.divide(1.,inv,out=np.zeros_like(inv),where=free)
    force=mass[:,None]*(xyz-np.asarray(p['predicted']).reshape(-1,3))
    energy=float(np.sum(.5*mass[:,None]*(xyz-np.asarray(p['predicted']).reshape(-1,3))**2))
    for a,b,rest in zip(p['a'],p['b'],p['rest']):
        delta=xyz[a]-xyz[b]; length=float(np.linalg.norm(delta))
        value=(length-rest)/p['alpha']*delta/length
        force[a]+=value; force[b]-=value; energy+=.5*(length-rest)**2/p['alpha']
    geometry=ct.CDLL(str(ROOT/'.tools/native/contact_distance.dll')).membrane_contact_distance
    geometry.argtypes=[ct.POINTER(ct.c_double),ct.POINTER(ct.c_double),ct.c_double,ct.POINTER(ct.c_double)]
    geometry.restype=ct.c_int
    faces=np.asarray(p['triangles']).reshape(-1,3); max_gap=0.; max_comp=0.
    def distance(axis,face,radius,mu):
        global max_gap,max_comp
        out=D([0.]*22); code=geometry(D(axis),D(face),radius,out)
        assert code in [0,3] and (mu==0 or code==0),(code,mu)
        g=out[0]/radius**2-1
        max_gap=max(max_gap,radius-math.sqrt(max(0.,out[0])))
        max_comp=max(max_comp,abs(mu*g)); assert math.isfinite(mu) and mu>=0
        return out
    for layer,t in enumerate(p['times']):
        tissue=old*(1-t)+xyz*t
        for f,ids in enumerate(faces):
            for b,packet in enumerate(np.asarray(p['packets']).reshape(-1,41)):
                axis=sample(packet,t) if p['kinds'][b] else (packet[:6]*(1-t)+packet[6:12]*t).reshape(2,3)
                mu=reactions[(layer*len(faces)+f)*len(p['kinds'])+b]
                out=distance(axis.flatten(),tissue[ids].flatten(),packet[12],mu)
                force[ids]-=mu*t*np.asarray(list(out)[11:20]).reshape(3,3)/packet[12]**2
    for c,v in enumerate(p['anatomy_vertices']):
        record=p['anatomy'][11*c:11*c+11]; radius,t=record[9:11]
        tissue=old[v]*(1-t)+xyz[v]*t; mu=reactions[tool_count+c]
        out=distance(np.tile(tissue,2),record[:9],radius,mu)
        # Independently use the point-to-witness vector rather than summing
        # the triangle gradients as the production point Jacobian does.
        force[v]-=mu*t*2*(tissue-np.asarray(list(out)[5:8]))/radius**2
    residual=float(np.max(np.abs(force[free]))) if free.any() else 0.
    assert np.array_equal(xyz[~free],np.asarray(p['initial']).reshape(-1,3)[~free])
    proof['independent']={'force':residual,'gap':max_gap,'complementarity':max_comp,'energy':energy}
    assert stats[1]<=1e-8 and stats[2]<=1e-9 and stats[3]<=1e-11
    assert residual<=1.01e-8 and max_gap<=1.001e-9 and max_comp<=1.001e-11
    assert math.isclose(energy,stats[0],rel_tol=1e-9,abs_tol=1e-16)
    proof['qualified']=True
report.write_text(json.dumps(proof,indent=2),encoding='utf-8')
print(json.dumps({key:proof[key] for key in ['qualified','scope','status','stats']},indent=2),flush=True)
raise SystemExit(0 if proof['qualified'] else 1)
