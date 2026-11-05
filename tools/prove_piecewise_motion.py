"""Geometric path-family counterexample only; never a physical integrator pass."""
import json
from fractions import Fraction
from pathlib import Path
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'native/tests'))
from replay_fem_trajectory import guard
from native_build_provenance import sha256,source_hashes,verify_sources
library=ROOT/'.tools/native/contact_guard.dll'
manifest=json.loads(library.with_suffix('.build.json').read_text())
verify_sources(manifest['sources']);assert sha256(library)==manifest['artifact_sha256']
inputs=source_hashes([Path(__file__),ROOT/'native/tests/replay_fem_trajectory.py',ROOT/'tools/native_build_provenance.py'])
triangle=np.array([-.01,0.,-.01,.01,0.,-.01,0.,0.,.01])
peak=triangle.copy();peak[1::3]=.25
# Kind0: exact recorded linear point-axis motion; no rotation approximation.
def request(previous,start,end):
    packet=[start,0.,0.,start,0.,0.,end,0.,0.,end,0.,0.,.1]+[0.]*28
    return {'previous':previous.tolist(),'triangles':[0,1,2],'kinds':[0],'packets':packet,'budget':128,'gap_tolerance':1e-9}
records=[]
for name,previous,current,start,end,expected in [('affine',triangle,triangle,1.,-1.,1),('piece0',triangle,peak,1.,0.,0),('piece1',peak,triangle,0.,-1.,0)]:
    motion=request(previous,start,end);status,stats,time=guard(motion,current,library)
    records.append({'path':name,'status':status,'stats':stats.tolist(),'witness_t':time,'expected':expected})
    assert status==expected,(name,status,stats,time)
# Exact rational separation proof on each half: global t<=2/5 implies x
# separation>=1/5-width; t in[2/5,1/2] implies y>=1/5. Reflect second half.
width=Fraction.from_float(.01);radius=Fraction.from_float(.1)
assert Fraction(1,5)-width>radius and Fraction(1,5)>radius
# For the patch center, complete the square in (1-2t)^2+(t/2)^2.
minimum_time=Fraction(8,17);minimum_squared=(1-2*minimum_time)**2+(minimum_time/2)**2
assert minimum_squared==Fraction(1,17) and minimum_squared>radius*radius
verify_sources(inputs);verify_sources(manifest['sources']);assert sha256(library)==manifest['artifact_sha256']
report={'qualified':False,'geometric_proof_verified':True,'scope':'Same tissue endpoints and same recorded linear obstacle path: affine tissue motion collides, two-piece motion is certified clear. No equilibrium, momentum, energy, physical integration, owned153 feasibility, full surgery, real-time or release qualification.','inputs':inputs,'build':manifest,'patch_half_width_exact':str(width),'radius_exact':str(radius),'center_min_squared':'1/17','triangle_separation_lower_bound':str(Fraction(1,5)-width),'guards':records}
destination=ROOT/'godot/reports/piecewise-motion-family-proof.json';destination.write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'geometric_proof_verified':True,'qualified':False,'guards':[(r['path'],r['status']) for r in records],'report':str(destination)}))
