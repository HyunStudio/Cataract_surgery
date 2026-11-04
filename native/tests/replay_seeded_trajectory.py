"""Extend a sampled equilibrium without changing its original physical problem."""
import numpy as np
from replay_fem_trajectory import replay,publish,guard

def exchange(times,dual,pairs,witness):
    rows=np.asarray(dual,dtype=np.float64).reshape(len(times),pairs)
    if not np.all(np.isfinite(rows)) or np.any(rows<0.):raise ValueError('invalid physical multiplier')
    if not np.isfinite(witness) or not 0.<witness<1. or witness in times:raise ValueError('invalid new witness')
    next_times=sorted([*times,witness])
    if len(next_times)*pairs>65536 or len(next_times)>16:
        active=[t for t,row in zip(times,rows) if t==1. or np.any(row>0.)]
        next_times=sorted(set([*active,witness]))
    seed=np.zeros((len(next_times),pairs))
    for i,t in enumerate(next_times):
        if t in times:seed[i]=rows[times.index(t)]
    return next_times,seed.ravel()

def extend(fixture,library,guard_library,verify):
    request=fixture['fem_request'];previous=fixture['previous_controls'];motion=fixture['motion'];last=fixture['last_candidate']
    times=last['times'];xyz=np.array(last['xyz']);dual=np.zeros(last['dual_count'])
    for index,value in last['dual_nonzero']:dual[index]=value
    penalty=last['stats'][15];spent=int(fixture['total_iterations']);witness=fixture['history'][-1]['witness_t'];history=[]
    pairs=(len(request['face_nodes'])//3)*len(motion['kinds'])
    for _ in range(16-len(fixture['history'])):
        times,seed=exchange(times,dual,pairs,witness)
        if pairs*len(times)>65536 or spent>=request['budget']:return False,history,None
        attempt=dict(request,budget=request['budget']-spent)
        result=replay(attempt,previous,motion['kinds'],motion['packets'],times,library,initial=xyz,multiplier_seed=seed,penalty_seed=penalty)
        spent+=int(result[4][2]);row={'times':times[:],'status':result[0],'stats':result[4].tolist(),'total_iterations':spent};history.append(row)
        if result[0]!=0:return False,history,result
        verify(attempt,previous,motion['kinds'],motion['packets'],times,result)
        checked=guard(motion,publish(result[1],request,motion['triangles']),guard_library)
        row.update(guard_status=checked[0],guard_stats=checked[1].tolist(),witness_t=checked[2])
        if checked[0]==0:return True,history,result
        if checked[0]!=1 or checked[2]<=0. or checked[2] in times:return False,history,result
        xyz=result[1];dual=result[3];penalty=result[4][15];witness=checked[2]
    return False,history,result
