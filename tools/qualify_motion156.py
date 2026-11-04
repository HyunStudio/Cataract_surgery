"""Qualify the captured motion156 native path under original work/physical gates."""
import json
from pathlib import Path
import sys
import time
root=Path(__file__).resolve().parents[1];sys.path[:0]=[str(root/'tools'),str(root/'native/tests')]
from native_build_provenance import sha256,source_hashes,verify_sources
from replay_fem_trajectory import replay,publish,guard
from replay_seeded_trajectory import exchange
from test_fem_trajectory import FEMTrajectoryTests
fixture=root/'docs/assets/operative-motion156-native-case-2026-11-05.json'
inputs=source_hashes([fixture,Path(__file__),root/'native/tests/replay_fem_trajectory.py',root/'native/tests/replay_seeded_trajectory.py',root/'native/tests/test_fem_trajectory.py'])
library=root/'.tools/native/membrane_fem.dll';guardlib=root/'.tools/native/contact_guard.dll';builds={}
for lib in [library,guardlib]:
 manifest=json.loads(lib.with_suffix('.build.json').read_text());assert sha256(lib)==manifest['artifact_sha256'];verify_sources(manifest['sources']);builds[str(lib.relative_to(root))]=manifest
case=json.loads(fixture.read_text());p=case['fem_request'];old=case['previous_controls'];motion=case['motion'];spent=int(case['failure']['stats'][2]);times=[.5,1.];initial=None;seed=None;penalty=1.;history=[];qualified=False;pairs=len(p['face_nodes'])//3*len(motion['kinds']);started=time.perf_counter()
for attempt in range(15):
 if spent>=p['budget'] or len(times)*pairs>65536:break
 request=dict(p,budget=p['budget']-spent);begin=time.perf_counter();result=replay(request,old,motion['kinds'],motion['packets'],times,library,initial=initial,multiplier_seed=seed,penalty_seed=penalty);spent+=int(result[4][2]);row={'times':times[:],'status':result[0],'stats':result[4].tolist(),'total_iterations':spent,'elapsed_seconds':time.perf_counter()-begin};history.append(row)
 if result[0]!=0:break
 FEMTrajectoryTests().verify(request,old,motion['kinds'],motion['packets'],times,result);row['independent_kkt_passed']=True;checked=guard(motion,publish(result[1],request,motion['triangles']),guardlib);row.update(guard_status=checked[0],guard_stats=checked[1].tolist(),witness_t=checked[2]);print(json.dumps(row),flush=True)
 if checked[0]==0:qualified=True;break
 if checked[0]!=1:break
 times,seed=exchange(times,result[3],pairs,checked[2]);initial=result[1];penalty=result[4][15]
verify_sources(inputs)
for name,manifest in builds.items():verify_sources(manifest['sources']);assert sha256(root/name)==manifest['artifact_sha256']
report={'qualified':qualified,'scope':'Exact captured motion156 native original KKT and complete interval guard only; not engine, outer anatomy, whole surgery, real-time or release qualification.','inputs':inputs,'builds':builds,'history':history,'total_iterations':spent,'elapsed_seconds':time.perf_counter()-started}
(root/'godot/reports/motion156-fresh-polish-resolve.json').write_text(json.dumps(report,indent=2));print(json.dumps({'qualified':qualified,'iterations':spent,'seconds':report['elapsed_seconds']}),flush=True)
raise SystemExit(0 if qualified else 1)
