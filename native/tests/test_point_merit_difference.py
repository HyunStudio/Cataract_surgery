"""Moving-point/rigid-face change bounds against independent Decimal geometry."""
import ctypes as ct
from decimal import Decimal,localcontext
import random
from pathlib import Path
import unittest
from decimal_distance_reference import contact_merit,decimal
ROOT=Path(__file__).resolve().parents[2]
A=lambda values:(ct.c_double*len(values))(*values)

class PointMeritTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib=ct.CDLL(str(ROOT/'.tools/native/contact_merit_probe.dll'))
        cls.change=cls.lib.merit_point_contact_change
        cls.change.argtypes=[ct.POINTER(ct.c_double)]*3+[ct.c_double]*3+[ct.POINTER(ct.c_double)]
        cls.change.restype=ct.c_int

    def compare(self,before,after,face,radius=.1,multiplier=.002,penalty=100.):
        out=A([99.,99.])
        code=self.change(A(before),A(after),A(face),radius,multiplier,penalty,out)
        self.assertEqual(code,0,(before,after,face))
        with localcontext() as ctx:
            ctx.prec=80
            exact=contact_merit(after+after,face,radius,multiplier,penalty)-contact_merit(before+before,face,radius,multiplier,penalty)
            self.assertLessEqual(decimal(out[0]),exact+Decimal('1e-60'))
            self.assertGreaterEqual(decimal(out[1]),exact-Decimal('1e-60'))
        return list(out),exact

    def test_tiny_normal_motion_survives_energy_cancellation(self):
        for shift in [0.,8.,-8.]:
            face=[shift,shift,shift,shift+1,shift,shift,shift,shift,shift+1]
            old=[shift+.2,shift+.1,shift+.2]; new=old[:]; new[1]+=1e-12
            out,exact=self.compare(old,new,face)
            self.assertLess(exact,0.)
            self.assertLess(out[1],0.)
            self.assertLess(out[1]-out[0],1e-23)

    def test_noop_transitions_and_finite_feature_changes(self):
        face=[0.,0.,0.,1.,0.,0.,0.,0.,1.]
        self.assertEqual(self.compare([.2,.1,.2],[.2,.1,.2],face)[0],[0.,0.])
        for before,after in [([-.03,.04,.25],[-.03,.05,.25]),([-.03,.04,-.02],[-.01,.05,.01]),([.2,.11,.2],[.2,.09,.2]),([.2,.09,.2],[.2,.11,.2])]:
            self.compare(before,after,face,multiplier=0.)

    def test_independent_random_finite_point_triangle_changes(self):
        rng=random.Random(9016)
        for _ in range(100):
            face=[rng.uniform(-1.,1.) for _ in range(9)]
            before=[rng.uniform(-.5,.5) for _ in range(3)]
            after=[value+rng.uniform(-.01,.01) for value in before]
            self.compare(before,after,face,radius=.3,multiplier=.002,penalty=10.)

    def test_invalid_geometry_does_not_publish_bounds(self):
        out=A([99.,99.])
        self.assertNotEqual(self.change(A([0.,.1,0.]),A([0.,.2,0.]),A([0.]*9),.1,.002,100.,out),0)
        self.assertEqual(list(out),[99.,99.])

if __name__=='__main__': unittest.main()
