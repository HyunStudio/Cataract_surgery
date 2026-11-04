"""Independent time-weighted original-FEM KKT; sampled contact is not CCD."""
import ctypes as ct
import json
import math
import unittest
from decimal import Decimal,localcontext
import numpy as np
import test_membrane_fem as fem
import test_fem_contact as contact
import test_fp_environment as environment
from test_contact_guard import linear
from test_trajectory_contact import sample
from replay_fem_contact import replay as static_replay
from replay_fem_trajectory import replay,publish,guard
from decimal_distance_reference import contact_merit

LIB=fem.ROOT/'.tools/native/membrane_fem.dll'
class FEMTrajectoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib=ct.CDLL(str(LIB))
        assert hasattr(cls.lib,'membrane_fem_solve_trajectory'),'original FEM requires its own time-weighted contact API'

    def request(self):
        rest=np.array([[1.05,-1.,-1.],[1.05,1.,-1.],[1.05,0.,2.]])
        nodes=np.array([[0,1,2]],dtype=np.int32);basis,areas=fem.MembraneFEMTests.reference_cells(rest,nodes)
        return {'xyz':rest.ravel().tolist(),'inverse':[1.,1.,1.],'nodes':nodes.ravel().tolist(),'gradients':basis.ravel().tolist(),'areas':areas.tolist(),
                'mu':2.,'lambda':3.,'dt':.1,'budget':1000,'force_tolerance':1e-8,'gap_tolerance':1e-9,'complementarity_tolerance':1e-11,
                'grip_nodes':[],'grip_weights':[],'targets':[],'face_nodes':[0,1,2],'face_weights':np.eye(3).ravel().tolist(),'capsules':[]}

    def verify(self,p,old,kinds,packets,times,result):
        code,x,reaction,dual,stats=result;self.assertEqual(code,0,stats)
        q=x.reshape(-1,3);predicted=np.array(p['xyz']).reshape(-1,3);old=np.array(old).reshape(-1,3)
        inverse=np.array(p['inverse']);free=inverse>0.;force=np.zeros_like(q)
        for ids,basis,area in zip(np.array(p['nodes']).reshape(-1,3),np.array(p['gradients']).reshape(-1,2,3),p['areas']):
            f=q[ids].T@basis.T;c=f.T@f;log_j=.5*np.linalg.slogdet(c)[1]
            stress=p['mu']*f+(p['lambda']*log_j-p['mu'])*f@np.linalg.inv(c);force[ids]+=(area*stress@basis).T
        force[free]+=(q[free]-predicted[free])/(inverse[free,None]*p['dt']**2)
        np.testing.assert_array_equal(q[~free],predicted[~free])
        for ids,w,target,r in zip(np.array(p['grip_nodes']).reshape(-1,3),np.array(p['grip_weights']).reshape(-1,3),np.array(p['targets']).reshape(-1,3),reaction.reshape(-1,3)):
            w=w/sum(w);np.testing.assert_allclose(w@q[ids],target,atol=1e-9,rtol=0.)
            for node,weight in zip(ids,w):force[node]+=weight*r
        faces=np.array(p['face_nodes']).reshape(-1,3);shapes=np.array(p['face_weights']).reshape(-1,3,3)
        packets=np.array(packets).reshape(-1,41);multipliers=dual.reshape(len(times),len(faces),len(kinds))
        for layer,t in enumerate(times):
            posed=(1-t)*old+t*q
            segments=[sample(packet,t) if kinds[body] else ((1-t)*packet[:6]+t*packet[6:12]).reshape(2,3) for body,packet in enumerate(packets)]
            for face,(ids,shape) in enumerate(zip(faces,shapes)):
                shape=shape/shape.sum(axis=1)[:,None]
                triangle=shape@posed[ids]
                for body,packet in enumerate(packets):
                    segment=segments[body]
                    capsule=np.r_[segment.ravel(),packet[12]];u=multipliers[layer,face,body]
                    # Independent far-pair separation; the generous positive
                    # margin avoids using rounded near-contact AABBs as proof.
                    box=np.maximum(0.,np.maximum(triangle.min(axis=0)-segment.max(axis=0),segment.min(axis=0)-triangle.max(axis=0)))
                    if u==0. and np.linalg.norm(box)>packet[12]+1e-10:continue
                    sq,w,delta=contact.FEMContactTests.closest(capsule,triangle)
                    self.assertGreaterEqual(u,0.);self.assertGreaterEqual(math.sqrt(sq)-packet[12],-1e-9)
                    self.assertLessEqual(abs(u*(sq/packet[12]**2-1.)),1e-11)
                    force[ids]-=u*t*(shape.T@(2*w[:,None]*delta))/packet[12]**2
        self.assertLessEqual(np.max(np.abs(force[free])),1e-8)
        self.assertLessEqual(stats[1],1e-8);self.assertLessEqual(stats[12],1e-9);self.assertLessEqual(stats[13],1e-11)

    def test_mid_arc_obstruction_uses_time_weighted_material_reaction(self):
        p=self.request();old=p['xyz'];h=math.sqrt(.5)
        packet=[0.,-1.,0.]*2+[0.,1.,0.]*2+[.1]+[0.]*6+[0.,0.,-h,h,0.,0.,h,h]+[1.,0.,0.]*4+[0.,1.]
        result=replay(p,old,[1],packet,[.5,1.],LIB);self.verify(p,old,[1],packet,[.5,1.],result)
        self.assertGreater(np.max(abs(result[1]-old)),.01)

    def test_actual_operative144_satisfies_material_kkt_and_complete_motion_guard(self):
        fixture=json.loads((fem.ROOT/'native/tests/fixtures/operative_motion144.json').read_text())
        old=json.loads((fem.ROOT/'native/tests/fixtures/operative_motion144_controls.json').read_text())['xyz']
        p=fixture['fem_request'];motion=fixture['guard_request'];times=[.25,.375,.5,1.]
        result=replay(p,old,motion['kinds'],motion['packets'],times,LIB)
        self.verify(p,old,motion['kinds'],motion['packets'],times,result)
        code,stats,_=guard(motion,publish(result[1],p,motion['triangles']),fem.ROOT/'.tools/native/contact_guard.dll')
        self.assertEqual(code,0,stats)

    def test_contact_time_gradient_and_hessian_match_independent_merit(self):
        probe=ct.CDLL(str(fem.ROOT/'.tools/native/contact_activity_probe.dll')).fem_time_contact_probe
        probe.argtypes=[fem.D]*4+[ct.c_double]*3+[fem.D]*2;probe.restype=ct.c_int
        old=np.array([[0.,0.,0.],[1.,0.,0.],[0.,0.,1.]])
        end=old.copy();end[0,0]+=.01;end[1,1]+=.04;end[2,2]-=.01
        body=np.array([.3,.075,.3,.3,.075,.3,.12]);shape=np.array([[.8,.1,.1],[.3,.6,.1],[.3,.1,.6]])
        def call(x,t):
            g=np.full(9,123.);h=np.full((9,9),123.)
            arrays=[np.ascontiguousarray(a,dtype=np.float64) for a in (old,x,body,shape)]
            self.assertEqual(probe(*(a.ctypes.data_as(fem.D) for a in arrays),t,.17,.8,g.ctypes.data_as(fem.D),h.ctypes.data_as(fem.D)),0)
            return g,h
        def merit(x,t):
            sq,_,_=contact.FEMContactTests.closest(body,shape@((1-t)*old+t*x))
            g=sq/body[6]**2-1.;u=max(0.,.17-.8*g)
            return (u*u-.17**2)/(2*.8)
        for t in [.2,.5,1.]:
            gradient,hessian=call(end,t);finite_g=np.empty(9);finite_h=np.empty((9,9))
            for k in range(9):
                plus=end.copy();minus=end.copy();plus.flat[k]+=1e-6;minus.flat[k]-=1e-6
                finite_g[k]=(merit(plus,t)-merit(minus,t))/2e-6
                finite_h[:,k]=(call(plus,t)[0]-call(minus,t)[0])/2e-6
            np.testing.assert_allclose(gradient,finite_g,atol=2e-9,rtol=2e-7)
            np.testing.assert_allclose(hessian,finite_h,atol=2e-7,rtol=2e-7)

    def test_unrounded_affine_merit_encloses_decimal_change_at_stalled_step(self):
        data=json.loads((fem.ROOT/'native/tests/fixtures/fem_time_merit_stall.json').read_text())
        probe=ct.CDLL(str(fem.ROOT/'.tools/native/contact_activity_probe.dll')).fem_time_merit_probe
        probe.argtypes=[fem.D]*4+[ct.c_double,fem.D]+[ct.c_double]*3+[fem.D];probe.restype=ct.c_int
        for offset in [0.,8.,-8.]:
            for shape in [data['shape'],[.8,.1,.1,.3,.6,.1,.3,.1,.6]]:
                arrays=[np.array(data[name])+offset for name in ['previous','before','after']]
                body=np.array(data['body']);body[:6]+=offset
                args=[np.ascontiguousarray(a,dtype=np.float64) for a in [*arrays,shape,body]];out=np.full(2,123.)
                self.assertEqual(probe(*(a.ctypes.data_as(fem.D) for a in args[:4]),data['time'],args[4].ctypes.data_as(fem.D),body[6],data['dual'],data['rho'],out.ctypes.data_as(fem.D)),0)
                with localcontext() as context:
                    context.prec=80;d=Decimal.from_float;t=d(data['time'])
                    def face(end):
                        controls=[[(1-t)*d(float(arrays[0][j*3+k]))+t*d(float(end[j*3+k])) for k in range(3)] for j in range(3)]
                        result=[]
                        for j in range(3):
                            w=[d(float(v)) for v in shape[j*3:j*3+3]];total=sum(w)
                            for k in range(3):result.append(sum(w[i]*controls[i][k] for i in range(3))/total)
                        return result
                    expected=contact_merit(body[:6],face(arrays[2]),body[6],data['dual'],data['rho'])-contact_merit(body[:6],face(arrays[1]),body[6],data['dual'],data['rho'])
                    self.assertLessEqual(d(float(out[0])),expected);self.assertGreaterEqual(d(float(out[1])),expected)
                self.assertLess(out[1]-out[0],1e-22)

    def test_high_penalty_force_uses_unrounded_intermediate_gap(self):
        probe=ct.CDLL(str(fem.ROOT/'.tools/native/contact_activity_probe.dll')).fem_time_contact_probe
        probe.argtypes=[fem.D]*4+[ct.c_double]*3+[fem.D]*2;probe.restype=ct.c_int
        for t in [.25,.375,.5,1.]:
            old=np.array([[0.,.5,0.],[1.,.5,0.],[0.,.5,1.]])
            end=old.copy();end[:,1]=math.nextafter(.5,1.)
            body=np.array([.3,.6,.3,.3,.6,.3,.1]);shape=np.array([[.8,.1,.1],[.1,.8,.1],[.1,.1,.8]])
            arrays=[np.ascontiguousarray(v,dtype=np.float64) for v in [old,end,body,shape]]
            g=np.full(9,123.);h=np.full(81,123.)
            self.assertEqual(probe(*(v.ctypes.data_as(fem.D) for v in arrays),t,.01,1e7,g.ctypes.data_as(fem.D),h.ctypes.data_as(fem.D)),0)
            with localcontext() as context:
                context.prec=80;d=Decimal.from_float
                height=d(.5)+d(t)*(d(float(end[0,1]))-d(.5));distance=d(.6)-height
                r2=d(.1*.1);gap=distance*distance/r2-1
                multiplier=max(Decimal(0),d(.01)-d(1e7)*gap)
                expected=float(multiplier*d(t)*2*distance/r2)
            self.assertAlmostEqual(float(g.reshape(3,3)[:,1].sum()),expected,delta=2e-12,msg=f't={t}')

    def test_endpoint_only_preserves_static_candidate(self):
        p=self.request();packet=linear([1.,0.,0.],[1.,0.,0.],.1);p['capsules']=packet[6:13]
        expected=static_replay(p,LIB);actual=replay(p,p['xyz'],[0],packet,[1.],LIB)
        self.verify(p,p['xyz'],[0],packet,[1.],actual)
        self.assertEqual(expected[0],actual[0])
        for a,b in zip(actual[1:],expected[1:]):np.testing.assert_array_equal(a,b)

    def test_invalid_times_and_history_are_atomic(self):
        p=self.request();packet=linear([0.,2.,0.],[0.,2.,0.],.1)
        for times in [[],[0.,1.],[.5,.5,1.],[1.,.5],[.5],[math.nan,1.],np.linspace(.01,1.,17).tolist()]:
            with self.subTest(times=times):
                code,x,r,u,_=replay(p,p['xyz'],[0],packet,times,LIB)
                self.assertEqual(code,-1);np.testing.assert_array_equal(x,p['xyz']);np.testing.assert_array_equal(r,123.);np.testing.assert_array_equal(u,123.)

    def test_invalid_history_and_recorded_bodies_are_atomic(self):
        p=self.request();packet=linear([0.,2.,0.],[0.,2.,0.],.1)
        cases=[]
        for value in [math.nan,math.inf,17.]:
            old=p['xyz'][:];old[0]=value;cases.append((p,old,[0],packet))
        pinned=dict(p,inverse=[0.,1.,1.]);old=p['xyz'][:];old[0]+=.01
        cases.append((pinned,old,[0],packet))
        cases.append((p,p['xyz'],[2],packet))
        for index,value in [(0,math.nan),(12,0.),(12,.31)]:
            broken=packet[:];broken[index]=value;cases.append((p,p['xyz'],[0],broken))
        cases.append((p,p['xyz'],[1],packet)) # zero quaternion is invalid
        for request,old,kinds,motion in cases:
            code,x,r,u,_=replay(request,old,kinds,motion,[.5,1.],LIB)
            self.assertEqual(code,-1);np.testing.assert_array_equal(x,p['xyz'])
            np.testing.assert_array_equal(r,123.);np.testing.assert_array_equal(u,123.)

    def test_multiple_bodies_layers_with_exact_hold_and_pin(self):
        for pinned in [False,True]:
            p=self.request();old=p['xyz'][:]
            if pinned:p['inverse'][2]=0.
            else:p.update(grip_nodes=[0,1,2],grip_weights=[0.,0.,1.],targets=old[6:9])
            packets=linear([1.,-.3,0.],[1.,-.3,0.],.1)+linear([1.,.3,0.],[1.,.3,0.],.1)
            times=[.5,.75,1.];result=replay(p,old,[0,0],packets,times,LIB)
            self.verify(p,old,[0,0],packets,times,result)

    def test_budget_exhaustion_preserves_all_candidate_outputs(self):
        p=self.request();p['budget']=0;packet=linear([1.,0.,0.],[1.,0.,0.],.1)
        code,x,r,u,_=replay(p,p['xyz'],[0],packet,[.5,1.],LIB)
        self.assertEqual(code,1);np.testing.assert_array_equal(x,p['xyz'])
        np.testing.assert_array_equal(r,123.);np.testing.assert_array_equal(u,123.)

    def test_real_api_preserves_caller_modes_on_success_invalid_and_exhaustion(self):
        environment.EnvironmentTests.setUpClass();probe=environment.EnvironmentTests.probe
        saved=(probe.fem_probe_x87(),probe.fem_probe_mxcsr())
        p=self.request();packet=linear([1.,0.,0.],[1.,0.,0.],.1)
        cases=[(p,[.5,1.],0),(p,[0.,1.],-1),(dict(p,budget=0),[.5,1.],1)]
        baseline=[replay(request,p['xyz'],[0],packet,times,LIB) for request,times,_ in cases]
        try:
            for cw,mx in environment.EnvironmentTests.contexts(saved):
                for index,(request,times,status) in enumerate(cases):
                    probe.fem_probe_set_x87(cw);probe.fem_probe_set_mxcsr(mx)
                    actual=replay(request,p['xyz'],[0],packet,times,LIB)
                    after=(probe.fem_probe_x87(),probe.fem_probe_mxcsr()&~0x3f)
                    probe.fem_probe_set_x87(saved[0]);probe.fem_probe_set_mxcsr(saved[1])
                    self.assertEqual(after,(cw,mx&~0x3f));self.assertEqual(actual[0],status)
                    for first,last in zip(actual[1:],baseline[index][1:]):np.testing.assert_array_equal(first,last)
        finally:probe.fem_probe_set_x87(saved[0]);probe.fem_probe_set_mxcsr(saved[1])

if __name__=='__main__':unittest.main()
