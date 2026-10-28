"""Finite rigid anatomy and moving tissue points in the same physical solve."""
import ctypes as ct
import math
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]
D=lambda x:(ct.c_double*len(x))(*x)
I=lambda x:(ct.c_int*len(x))(*x)
PLANE=[-1.,0.,-1.,1.,0.,-1.,0.,0.,1.]

class AnatomicalContactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib=ct.CDLL(str(ROOT/'.tools/native/membrane_contact.dll'))
        cls.solve=cls.lib.membrane_solve_trajectory_anatomy
        cls.solve.argtypes=[ct.c_int,ct.POINTER(ct.c_double),ct.POINTER(ct.c_double),ct.POINTER(ct.c_double),ct.c_int,
            ct.POINTER(ct.c_int),ct.POINTER(ct.c_int),ct.POINTER(ct.c_double),ct.c_double,ct.c_int,ct.POINTER(ct.c_int),
            ct.c_int,ct.POINTER(ct.c_int),ct.POINTER(ct.c_double),ct.POINTER(ct.c_double),ct.c_int,ct.POINTER(ct.c_double),
            ct.c_int,ct.POINTER(ct.c_int),ct.POINTER(ct.c_double),ct.c_int,ct.c_double,ct.c_double,ct.c_double,
            ct.POINTER(ct.c_double),ct.POINTER(ct.c_double)]
        cls.solve.restype=ct.c_int

    def query(self,point,face=PLANE,radius=.1,time=1.,old=None,inverse=None,budget=100,vertex=0):
        before=point[:]; x=D(point); previous=D(old if old is not None else point)
        rigid=face+[radius,time]; record=D(rigid); record_bytes=bytes(record)
        dual=D([99.]); stats=D([99.]*12)
        code=self.solve(len(point)//3,D(point),x,D(inverse if inverse is not None else [1.]*(len(point)//3)),
            0,I([]),I([]),D([]),.1,0,I([]),0,I([]),D([]),previous,1,D([1.]),1,I([vertex]),record,
            budget,1e-8,1e-9,1e-11,dual,stats)
        self.assertEqual(bytes(record),record_bytes)
        self.assertEqual(list(previous),old if old is not None else before)
        return code,list(x),list(dual),list(stats)

    def test_plane_reaction_balances_original_inertia(self):
        code,x,dual,stats=self.query([0.,.05,0.])
        self.assertEqual(code,0,stats)
        self.assertAlmostEqual(x[1],.1,delta=1e-9)
        self.assertAlmostEqual(x[0],0.,delta=1e-12); self.assertAlmostEqual(x[2],0.,delta=1e-12)
        self.assertAlmostEqual(dual[0],.0025,delta=1e-9)
        self.assertLessEqual(stats[1],1e-8); self.assertLessEqual(stats[2],1e-9); self.assertLessEqual(stats[3],1e-11)

    def test_finite_edge_reaction_is_not_an_infinite_plane(self):
        face=[0.,0.,0.,1.,0.,0.,0.,0.,1.]
        code,x,dual,stats=self.query([-.03,.04,.25],face)
        self.assertEqual(code,0,stats)
        for actual,expected in zip(x,[-.06,.08,.25]): self.assertAlmostEqual(actual,expected,delta=2e-9)
        self.assertAlmostEqual(dual[0],.0025,delta=1e-9)

    def test_finite_vertex_reaction_is_radial(self):
        point=[-.03,.04,-.02]; length=math.sqrt(sum(v*v for v in point))
        code,x,dual,stats=self.query(point,[0.,0.,0.,1.,0.,0.,0.,0.,1.])
        self.assertEqual(code,0,stats)
        for actual,value in zip(x,point): self.assertAlmostEqual(actual,value*.1/length,delta=2e-9)
        self.assertAlmostEqual(dual[0],(.1-length)*.1/2,delta=1e-9)

    def test_time_weighted_anatomy_reaction_uses_fixed_history(self):
        code,x,dual,stats=self.query([0.,0.,0.],time=.5,old=[0.,.15,0.])
        self.assertEqual(code,0,stats)
        self.assertAlmostEqual(x[1],.05,delta=2e-9)
        self.assertAlmostEqual(dual[0],.005,delta=1e-9)

    def test_clear_anatomy_keeps_predictor_and_zero_reaction(self):
        point=[0.,.2,0.]; code,x,dual,stats=self.query(point)
        self.assertEqual(code,0,stats); self.assertEqual(x,point); self.assertEqual(dual,[0.])

    def test_prescribed_penetration_rejects_without_publication(self):
        point=[0.,.05,0.]; code,x,dual,_=self.query(point,inverse=[0.])
        self.assertEqual(code,3); self.assertEqual(x,point); self.assertEqual(dual,[99.])

    def test_exhaustion_rejects_without_publication(self):
        point=[0.,.05,0.]; code,x,dual,_=self.query(point,budget=0)
        self.assertEqual(code,1); self.assertEqual(x,point); self.assertEqual(dual,[99.])

    def test_invalid_constraint_domain_is_atomic(self):
        point=[0.,.05,0.]
        for kwargs in [{'radius':0.},{'radius':1e-9},{'radius':.31},{'time':0.},{'time':1.01},{'time':math.nan},{'vertex':1},{'vertex':-1},{'face':[17.]+PLANE[1:]}]:
            code,x,dual,_=self.query(point,**kwargs)
            self.assertEqual(code,-1,kwargs); self.assertEqual(x,point); self.assertEqual(dual,[99.])

    def test_degenerate_nearby_anatomy_is_not_a_regular_contact(self):
        point=[0.,.05,0.]; code,x,dual,_=self.query(point,[0.]*9)
        self.assertEqual(code,4); self.assertEqual(x,point); self.assertEqual(dual,[99.])

    def test_rotation_translation_preserve_equilibrium(self):
        def move(p): return [p[1]+.3,-p[0]-.2,p[2]+.4]
        point=move([0.,.05,0.]); face=sum((move(PLANE[i:i+3]) for i in range(0,9,3)),[])
        code,x,dual,stats=self.query(point,face)
        self.assertEqual(code,0,stats)
        for actual,expected in zip(x,move([0.,.1,0.])): self.assertAlmostEqual(actual,expected,delta=2e-9)
        self.assertAlmostEqual(dual[0],.0025,delta=1e-9)

    def test_simultaneous_tool_and_anatomy_reactions_balance_inertia(self):
        point=[0.,.05,0.,-1.,.1,0.,0.,.1,-1.]
        capsule=[.05,.1,.05]*4+[.1]+[0.]*28
        x=D(point); dual=D([99.,99.]); stats=D([99.]*12)
        code=self.solve(3,D(point),x,D([1.,0.,0.]),0,I([]),I([]),D([]),.1,1,I([0,1,2]),
            1,I([0]),D(capsule),D(point),1,D([1.]),1,I([0]),D(PLANE+[.1,1.]),
            100,1e-8,1e-9,1e-11,dual,stats)
        self.assertEqual(code,0,list(stats))
        lateral=.05-.1/math.sqrt(2.)
        for actual,expected in zip(list(x)[:3],[lateral,.1,lateral]): self.assertAlmostEqual(actual,expected,delta=2e-8)
        self.assertEqual(list(x)[3:],point[3:])
        self.assertGreater(dual[0],0.); self.assertAlmostEqual(dual[1],.0025,delta=2e-9)
        # Independent known finite-vertex normal and rigid-plane normal.
        displacement=[x[k]-point[k] for k in range(3)]
        tool_gradient=[2*(x[k]-[.05,.1,.05][k])/.01 for k in range(3)]
        anatomy_gradient=[0.,2*x[1]/.01,0.]
        residual=[displacement[k]-dual[0]*tool_gradient[k]-dual[1]*anatomy_gradient[k] for k in range(3)]
        self.assertLessEqual(max(map(abs,residual)),1e-8)
        self.assertLessEqual(stats[2],1e-9); self.assertLessEqual(stats[3],1e-11)

    def test_anatomy_balances_elastic_spring_and_inertial_force(self):
        point=[0.,.05,0.,0.,-.2,0.]
        x=D(point); dual=D([99.]); stats=D([99.]*12)
        code=self.solve(2,D(point),x,D([1.,0.]),1,I([0]),I([1]),D([.2]),.1,0,I([]),0,I([]),D([]),
            D(point),1,D([1.]),1,I([0]),D(PLANE+[.1,1.]),100,1e-8,1e-9,1e-11,dual,stats)
        self.assertEqual(code,0,list(stats)); self.assertAlmostEqual(x[1],.1,delta=1e-9)
        self.assertEqual(list(x)[3:],point[3:])
        inertial=x[1]-.05; elastic=(x[1]+.2-.2)/.1
        self.assertAlmostEqual(dual[0],.0525,delta=1e-9)
        self.assertLessEqual(abs(inertial+elastic-dual[0]*2*x[1]/.01),1e-8)

    def test_constraint_selects_the_named_vertex_only(self):
        point=[0.,.2,0.,.1,.05,0.]
        code,x,dual,stats=self.query(point,vertex=1)
        self.assertEqual(code,0,stats); self.assertEqual(x[:3],point[:3])
        self.assertAlmostEqual(x[4],.1,delta=1e-9); self.assertAlmostEqual(dual[0],.0025,delta=1e-9)

    def test_no_anatomy_matches_original_trajectory_abi_exactly(self):
        old=self.lib.membrane_solve_trajectory
        old.argtypes=self.solve.argtypes[:17]+self.solve.argtypes[20:]; old.restype=ct.c_int
        point=[0.,0.,0.,1.2,0.,0.]
        common=[2,D(point),None,D([0.,1.]),1,I([0]),I([1]),D([1.]),.1,0,I([]),0,I([]),D([]),D(point),1,D([1.])]
        observed=[]
        for anatomy in [False,True]:
            x=D(point); stats=D([99.]*12); dual=D([])
            args=common[:]; args[2]=x
            if anatomy: args += [0,I([]),D([])]
            args += [100,1e-8,1e-9,1e-11,dual,stats]
            code=(self.solve if anatomy else old)(*args)
            observed.append((code,list(x),list(stats)))
        self.assertEqual(observed[0][0],0,observed)
        self.assertEqual(observed[0],observed[1])

if __name__=='__main__': unittest.main()
