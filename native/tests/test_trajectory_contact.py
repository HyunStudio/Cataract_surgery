"""Time-weighted physical contact constraints; complete CCD remains separate."""
import ctypes as ct
import json
import math
from pathlib import Path
import unittest
import numpy as np
from scipy.spatial.transform import Rotation,Slerp

ROOT=Path(__file__).resolve().parents[2]
D=lambda x:(ct.c_double*len(x))(*x)
I=lambda x:(ct.c_int*len(x))(*x)

def sample(packet,t):
    p=np.asarray(packet)
    rotation=Slerp([0,1],Rotation.from_quat(p[19:27].reshape(2,4)))
    def ideal(s):
        local=p[27:33].reshape(2,3)*(1-s)+p[33:39].reshape(2,3)*s
        return p[13:16]*(1-s)+p[16:19]*s+rotation(s).apply(local)
    return ideal(p[39]+t*(p[40]-p[39]))+(1-t)*(p[:6].reshape(2,3)-ideal(p[39]))+t*(p[6:12].reshape(2,3)-ideal(p[40]))

class TrajectoryContactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib=ct.CDLL(str(ROOT/'.tools/native/membrane_contact.dll'))
        cls.solve=cls.lib.membrane_solve_trajectory
        cls.solve.argtypes=[ct.c_int,ct.POINTER(ct.c_double),ct.POINTER(ct.c_double),ct.POINTER(ct.c_double),ct.c_int,
                           ct.POINTER(ct.c_int),ct.POINTER(ct.c_int),ct.POINTER(ct.c_double),ct.c_double,ct.c_int,
                           ct.POINTER(ct.c_int),ct.c_int,ct.POINTER(ct.c_int),ct.POINTER(ct.c_double),ct.POINTER(ct.c_double),
                           ct.c_int,ct.POINTER(ct.c_double),ct.c_int,ct.c_double,ct.c_double,ct.c_double,
                           ct.POINTER(ct.c_double),ct.POINTER(ct.c_double)]
        cls.solve.restype=ct.c_int
        cls.geometry=ct.CDLL(str(ROOT/'.tools/native/contact_distance.dll')).membrane_contact_distance
        cls.geometry.argtypes=[ct.POINTER(ct.c_double),ct.POINTER(ct.c_double),ct.c_double,ct.POINTER(ct.c_double)]

    def run_problem(self,p,old,packets,kinds,times,budget=100):
        x=D(p['initial']); predicted=D(p['predicted']); previous=D(old); motion=D(packets)
        count=len(p['triangles'])//3*len(kinds)*len(times)
        dual=D([99.]*count); stats=D([99.]*12)
        code=self.solve(len(old)//3,predicted,x,D(p['inverse']),len(p['a']),I(p['a']),I(p['b']),D(p['rest']),p['alpha'],
                        len(p['triangles'])//3,I(p['triangles']),len(kinds),I(kinds),motion,previous,len(times),D(times),
                        budget,1e-8,1e-9,1e-11,dual,stats)
        self.assertEqual(list(previous),old); self.assertEqual(list(predicted),p['predicted']); self.assertEqual(list(motion),packets)
        return code,list(x),list(dual),list(stats)

    def arc_problem(self):
        old=[1.05,-1.,-1.,1.05,1.,-1.,1.05,0.,2.]
        p={'initial':old[:],'predicted':old[:],'inverse':[1.,1.,1.],'a':[],'b':[],'rest':[],'alpha':.1,'triangles':[0,1,2]}
        h=math.sqrt(.5)
        packet=[0.,-1.,0.]*2+[0.,1.,0.]*2+[.1]+[0.]*6+[0.,0.,-h,h,0.,0.,h,h]+[1.,0.,0.]*4+[0.,1.]
        return p,old,packet

    def assert_kkt(self,p,old,packets,kinds,times,x,dual):
        xyz=np.array(x).reshape(-1,3); previous=np.array(old).reshape(-1,3)
        inverse=np.array(p['inverse']); free=inverse>0
        mass=np.divide(1.,inverse,out=np.zeros_like(inverse),where=free)
        force=mass[:,None]*(xyz-np.array(p['predicted']).reshape(-1,3))
        for a,b,rest in zip(p['a'],p['b'],p['rest']):
            delta=xyz[a]-xyz[b]; length=np.linalg.norm(delta)
            value=(length-rest)/p['alpha']*delta/length
            force[a]+=value; force[b]-=value
        faces=np.array(p['triangles']).reshape(-1,3); bodies=len(kinds)
        packets=np.array(packets).reshape(-1,41); max_pen=max_comp=0.
        for layer,t in enumerate(times):
            tissue=previous*(1-t)+xyz*t
            for face,ids in enumerate(faces):
                for body,packet in enumerate(packets):
                    segment=sample(packet,t) if kinds[body] else (packet[:6]*(1-t)+packet[6:12]*t).reshape(2,3)
                    out=D([0.]*22)
                    code=self.geometry(D(segment.flatten()),D(tissue[ids].flatten()),packet[12],out)
                    self.assertIn(code,[0,3])
                    g=out[0]/packet[12]**2-1
                    reaction=dual[(layer*len(faces)+face)*bodies+body]
                    self.assertGreaterEqual(reaction,0.)
                    max_pen=max(max_pen,packet[12]-math.sqrt(max(out[0],0.)))
                    max_comp=max(max_comp,abs(reaction*g))
                    gradient=np.array(list(out)[11:20]).reshape(3,3)/packet[12]**2
                    force[ids]-=reaction*t*gradient
        self.assertLessEqual(max_pen,1.001e-9); self.assertLessEqual(max_comp,1.001e-11)
        self.assertLessEqual(np.max(np.abs(force[free])),1.01e-8)
        self.assertEqual(xyz[~free].flatten().tolist(),np.array(p['initial']).reshape(-1,3)[~free].flatten().tolist())

    def test_midpoint_arc_constraint_has_time_weighted_reaction(self):
        p,old,packet=self.arc_problem()
        code,x,dual,stats=self.run_problem(p,old,packet,[1],[.5,1.])
        self.assertEqual(code,0,stats)
        self.assert_kkt(p,old,packet,[1],[.5,1.],x,dual)
        for vertex in range(3): self.assertAlmostEqual(x[3*vertex],1.15,delta=2e-7)
        self.assertAlmostEqual(dual[0],.03,delta=2e-7)
        self.assertAlmostEqual(stats[0],.015,delta=2e-7)

    def test_actual262_midpoint_and_endpoint_constraints_reach_physical_gates(self):
        p=json.loads((ROOT/'native/tests/fixtures/joint_static262.json').read_text())
        motion=json.loads((ROOT/'native/tests/fixtures/joint_motion262.json').read_text())
        code,x,dual,stats=self.run_problem(p,motion['previous'],motion['packets'],motion['kinds'],[.5,1.])
        self.assertEqual(code,0,stats)
        self.assert_kkt(p,motion['previous'],motion['packets'],motion['kinds'],[.5,1.],x,dual)

    def test_saved_four_layer_problem_balances_all_time_reactions(self):
        p=json.loads((ROOT/'native/tests/fixtures/joint_trajectory263.json').read_text())
        code,x,dual,stats=self.run_problem(p,p['previous'],p['packets'],p['kinds'],p['times'])
        self.assertEqual(code,0,stats)
        self.assert_kkt(p,p['previous'],p['packets'],p['kinds'],p['times'],x,dual)

    def test_actual264_three_layer_force_stagnation_reaches_original_gates(self):
        p=json.loads((ROOT/'native/tests/fixtures/joint_trajectory264_second.json').read_text())
        code,x,dual,stats=self.run_problem(p,p['previous'],p['packets'],p['kinds'],p['times'])
        self.assertEqual(code,0,stats)
        self.assert_kkt(p,p['previous'],p['packets'],p['kinds'],p['times'],x,dual)

    def test_exhaustion_preserves_positions_and_all_layer_reactions(self):
        p,old,packet=self.arc_problem()
        code,x,dual,_=self.run_problem(p,old,packet,[1],[.5,1.],budget=0)
        self.assertEqual(code,1); self.assertEqual(x,p['initial']); self.assertEqual(dual,[99.,99.])

    def test_endpoint_only_trajectory_matches_unchanged_static_abi(self):
        p=json.loads((ROOT/'native/tests/fixtures/joint_static262.json').read_text())
        motion=json.loads((ROOT/'native/tests/fixtures/joint_motion262.json').read_text())
        trajectory=self.run_problem(p,motion['previous'],motion['packets'],motion['kinds'],[1.])
        static=self.lib.membrane_solve_contact
        static.argtypes=[ct.c_int,ct.POINTER(ct.c_double),ct.POINTER(ct.c_double),ct.POINTER(ct.c_double),ct.c_int,
                         ct.POINTER(ct.c_int),ct.POINTER(ct.c_int),ct.POINTER(ct.c_double),ct.c_double,ct.c_int,
                         ct.POINTER(ct.c_int),ct.c_int,ct.POINTER(ct.c_double),ct.c_int,ct.c_double,ct.c_double,ct.c_double,
                         ct.POINTER(ct.c_double),ct.POINTER(ct.c_double)]
        x=D(p['initial']); dual=D([99.]*(len(p['triangles'])//3*len(motion['kinds']))); stats=D([99.]*12)
        status=static(len(p['inverse']),D(p['predicted']),x,D(p['inverse']),len(p['a']),I(p['a']),I(p['b']),D(p['rest']),p['alpha'],
                      len(p['triangles'])//3,I(p['triangles']),len(motion['kinds']),D(p['capsules']),100,1e-8,1e-9,1e-11,dual,stats)
        self.assertEqual(trajectory,(status,list(x),list(dual),list(stats)))

    def test_invalid_times_and_motion_reject_atomically(self):
        p,old,packet=self.arc_problem()
        for times in [[],[0.,1.],[.5,.5,1.],[1.,.5],[.5],[math.nan,1.],list(np.linspace(.01,1.,17))]:
            code,x,dual,_=self.run_problem(p,old,packet,[1],times)
            self.assertEqual(code,-1); self.assertEqual(x,p['initial']); self.assertTrue(all(v==99. for v in dual))
        packet[19:23]=[0.]*4
        code,x,dual,_=self.run_problem(p,old,packet,[1],[.5,1.])
        self.assertEqual(code,-1); self.assertEqual(x,p['initial']); self.assertEqual(dual,[99.,99.])

if __name__=='__main__': unittest.main()
