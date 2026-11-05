"""Replay captured numerical requests only; collecting a failure is not qualification."""
import argparse
import json
from pathlib import Path
import sys
import time
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'native/tests')]
from native_build_provenance import sha256,source_hashes,verify_sources
from replay_fem_contact import replay as endpoint
from replay_fem_trajectory import replay as trajectory

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--motion',type=int,required=True)
parser.add_argument('--request',type=int,default=None)
args=parser.parse_args()
case_path=ROOT/f'docs/assets/operative-motion{args.motion}-native-case-2026-11-05.json'
case=json.loads(case_path.read_text(encoding='utf-8'))
library=ROOT/'.tools/native/membrane_fem.dll'
manifest=json.loads(library.with_suffix('.build.json').read_text())
assert sha256(library)==manifest['artifact_sha256'];verify_sources(manifest['sources'])
inputs=source_hashes([case_path,Path(__file__),ROOT/'native/tests/replay_fem_contact.py',ROOT/'native/tests/replay_fem_trajectory.py'])
report={'qualified':False,'scope':'Exact captured native request reproduction only, including failed candidates. No whole-step, KKT, path, real-time or release qualification.',
        'inputs':inputs,'build':manifest,'results':[]}
destination=ROOT/'godot/reports'/f'motion{args.motion}-owned-request-replay.json'
rows=enumerate(case['native_history'])
for index,row in rows:
    if args.request is not None and index!=args.request:continue
    p=row['request'];kind=row['kind'];started=time.perf_counter()
    print(f'Replaying owned motion{args.motion} request{index}: {kind}',flush=True)
    if kind in ('static','precise_endpoint','material_points'):
        result=endpoint(p,library,precise=kind=='precise_endpoint',method='membrane_fem_solve_material_points' if kind=='material_points' else None)
    elif kind in ('trajectory','seeded','material_points_trajectory','material_points_trajectory_seeded'):
        extra={}
        if kind in ('seeded','material_points_trajectory_seeded'):extra={'initial':p['initial'],'multiplier_seed':p['multiplier_seed'],'penalty_seed':p['penalty_seed']}
        if kind.startswith('material_points_trajectory'):extra['method']='membrane_fem_solve_'+kind
        result=trajectory(p,p['previous'],p['kinds'],p['packets'],p['times'],library,**extra)
    else:raise ValueError('Unknown captured candidate kind: '+kind)
    status,xyz,reaction,dual,stats=result
    if status!=0:
        np.testing.assert_array_equal(xyz,p['xyz'])
        np.testing.assert_array_equal(reaction,123.);np.testing.assert_array_equal(dual,123.)
    saved=row['response']
    value={'index':index,'kind':kind,'status':status,'stats':stats.tolist(),'elapsed_seconds':time.perf_counter()-started,
           'same_saved_status':status==saved['status'],'same_saved_stats':np.array_equal(stats,saved['stats']),
           'failed_output_atomic':status!=0,'physical_qualified':False}
    report['results'].append(value)
    destination.write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(value),flush=True)
verify_sources(inputs);verify_sources(manifest['sources']);assert sha256(library)==manifest['artifact_sha256']
assert report['results'],'No matching captured request'
report['capture_completed']=True;destination.write_text(json.dumps(report,indent=2),encoding='utf-8')
