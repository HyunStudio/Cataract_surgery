"""Original-material FEM collocation candidate; complete motion guard is separate."""
import ctypes as ct
from pathlib import Path
import numpy as np
from test_membrane_fem import D,I

def replay(request,previous,kinds,packets,times,library,initial=None,multiplier_seed=None,penalty_seed=1.,method=None):
    seeded=initial is not None or multiplier_seed is not None
    lib=ct.CDLL(str(Path(library).resolve()));fn=getattr(lib,method or ('membrane_fem_solve_trajectory_seeded' if seeded else 'membrane_fem_solve_trajectory'))
    if method and seeded and method!='membrane_fem_solve_material_points_trajectory_seeded':raise ValueError('Explicit candidate API does not accept ordinary trajectory seeds')
    fn.argtypes=[ct.c_int,D,D,ct.c_int,I,D,D,ct.c_double,ct.c_double,ct.c_double,ct.c_int,
                 ct.c_double,ct.c_double,ct.c_double,ct.c_int,I,D,D,D,ct.c_int,I,D,
                 ct.c_int,I,D,D,ct.c_int,D,D,D]
    if seeded:fn.argtypes += [D,D,ct.c_double]
    fn.restype=ct.c_int
    fields={k:np.ascontiguousarray(v,dtype=np.int32 if k in ('nodes','grip_nodes','face_nodes') else np.float64)
            for k,v in request.items() if isinstance(v,list)}
    for k,v in [('old',previous),('packets',packets),('times',times)]:fields[k]=np.ascontiguousarray(v,dtype=np.float64)
    fields['kinds']=np.ascontiguousarray(kinds,dtype=np.int32)
    extra=[]
    if seeded:
        for name,value in [('initial',initial),('multiplier_seed',multiplier_seed)]:
            fields[name]=np.ascontiguousarray(value,dtype=np.float64) if value is not None else None
            extra.append(fields[name].ctypes.data_as(D) if fields[name] is not None else None)
        extra.append(penalty_seed)
    x=fields['xyz'].copy();reaction=np.full(len(fields['targets']),123.)
    dual=np.full(len(times)*(len(fields['face_nodes'])//3)*len(kinds),123.);stats=np.full(16,123.)
    d=lambda k:fields[k].ctypes.data_as(D);i=lambda k:fields[k].ctypes.data_as(I)
    code=fn(len(x)//3,x.ctypes.data_as(D),d('inverse'),len(fields['areas']),i('nodes'),d('gradients'),d('areas'),
            request['mu'],request['lambda'],request['dt'],request['budget'],request['force_tolerance'],request['gap_tolerance'],request['complementarity_tolerance'],
            len(fields['targets'])//3,i('grip_nodes'),d('grip_weights'),d('targets'),reaction.ctypes.data_as(D),
            len(fields['face_nodes'])//3,i('face_nodes'),d('face_weights'),len(kinds),i('kinds'),d('packets'),d('old'),len(times),d('times'),
            dual.ctypes.data_as(D),stats.ctypes.data_as(D),*extra)
    return code,x,reaction,dual,stats

def publish(controls,request,triangles):
    """Same canonical sparse B and summation order as the owned engine state."""
    q=np.asarray(controls).reshape(-1,3);faces=np.asarray(triangles).reshape(-1,3)
    nodes=np.array(request['face_nodes']).reshape(-1,3);weights=np.array(request['face_weights']).reshape(-1,3,3)
    output=np.empty((int(np.max(faces))+1,3));seen=set()
    for ids,material,shape in zip(faces,nodes,weights):
        for corner,vertex in enumerate(ids):
            if vertex in seen:continue
            seen.add(vertex);mapping={int(node):float(weight) for node,weight in zip(material,shape[corner]) if weight>0.}
            for axis in range(3):
                value=0.
                for node in sorted(mapping):value+=mapping[node]*float(q[node,axis])
                output[vertex,axis]=value
    if len(seen)!=len(output):raise ValueError('unmapped fine vertices')
    return output.ravel()

def guard(request,current,library):
    lib=ct.CDLL(str(Path(library).resolve()));fn=lib.membrane_guard_motion_witness
    fn.argtypes=[ct.c_int,D,D,ct.c_int,I,ct.c_int,I,D,ct.c_int,ct.c_double,D,D];fn.restype=ct.c_int
    fields={k:np.ascontiguousarray(request[k],dtype=np.int32 if k in ('triangles','kinds') else np.float64) for k in ('previous','triangles','kinds','packets')}
    end=np.ascontiguousarray(current,dtype=np.float64);stats=np.full(8,123.);time=ct.c_double(-1.)
    d=lambda k:fields[k].ctypes.data_as(D);i=lambda k:fields[k].ctypes.data_as(I)
    code=fn(len(end)//3,d('previous'),end.ctypes.data_as(D),len(fields['triangles'])//3,i('triangles'),len(fields['kinds']),i('kinds'),d('packets'),request['budget'],request['gap_tolerance'],stats.ctypes.data_as(D),ct.byref(time))
    return code,stats,time.value

def resolve(request,previous,motion,library,guard_library):
    """Offline witness generation, same predictor/dt; no accepted-state writes."""
    times=[1.];history=[];iterations=0
    for _ in range(16):
        attempt=dict(request);attempt['budget']=request['budget']-iterations
        if attempt['budget']<0:return False,times,history,None
        result=replay(attempt,previous,motion['kinds'],motion['packets'],times,library)
        iterations+=int(result[4][2]);record={'times':times[:],'status':result[0],'stats':result[4].tolist(),'total_iterations':iterations};history.append(record)
        if result[0]!=0:return False,times,history,result
        clearance=guard(motion,publish(result[1],request,motion['triangles']),guard_library)
        record.update({'guard_status':clearance[0],'guard_stats':clearance[1].tolist(),'witness_t':clearance[2]})
        if clearance[0]==0:return True,times,history,result
        t=clearance[2]
        if clearance[0]!=1 or t<=0. or t in times:return False,times,history,result
        times=sorted([*times,t])
        if len(times)*(len(request['face_nodes'])//3)*len(motion['kinds'])>65536:return False,times,history,result
    return False,times,history,result


if __name__=='__main__':
    import argparse
    import json
    import sys
    root=Path(__file__).resolve().parents[2]
    sys.path.insert(0,str(root/'tools'))
    from native_build_provenance import sha256,source_hashes,verify_sources
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    fixture=root/'native/tests/fixtures/operative_motion144.json'
    controls=root/'native/tests/fixtures/operative_motion144_controls.json'
    library=root/'.tools/native/membrane_fem.dll';guard_library=root/'.tools/native/contact_guard.dll'
    sources=source_hashes([fixture,controls,Path(__file__).resolve(),root/'tools/native_build_provenance.py'])
    builds={}
    for artifact in [library,guard_library]:
        manifest=json.loads(artifact.with_suffix('.build.json').read_text())
        if sha256(artifact)!=manifest['artifact_sha256']:raise SystemExit('Native artifact/manifest mismatch')
        verify_sources(manifest['sources']);builds[str(artifact.relative_to(root))]=manifest
    data=json.loads(fixture.read_text());old=json.loads(controls.read_text())['xyz']
    motion=data['guard_request'];request=data['fem_request']
    exact=np.array_equal(publish(old,request,motion['triangles']),motion['previous'])
    if not exact:raise SystemExit('Old fine state reconstruction differs; refusing a different motion')
    qualified,times,history,result=resolve(request,old,motion,library,guard_library)
    report={'qualified':qualified,'scope':'Exact captured native collocation candidates plus complete interval guard only. No engine, whole-case, GPU or release qualification.',
            'old_fine_bitwise_equal':exact,'sources':sources,'artifacts':builds,'times':times,'history':history,
            'failed_candidate_preserved_predictor':bool(result is not None and result[0]!=0 and np.array_equal(result[1],request['xyz']))}
    verify_sources(sources)
    for name,manifest in builds.items():
        verify_sources(manifest['sources'])
        if sha256(root/name)!=manifest['artifact_sha256'] or json.loads((root/name).with_suffix('.build.json').read_text())!=manifest:
            raise SystemExit('Native artifacts changed during replay')
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'qualified':qualified,'times':times,'report':str(args.output)}))
    raise SystemExit(0 if qualified else 1)
