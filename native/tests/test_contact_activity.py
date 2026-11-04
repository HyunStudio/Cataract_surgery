"""Reuse validated inactive states without dropping queries or active curvature."""
import ctypes as ct
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]
array=lambda values:(ct.c_double*len(values))(*values)

class ContactActivityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib=ct.CDLL(str(ROOT/'.tools/native/contact_activity_probe.dll'))
        cls.fn=cls.lib.fem_activity_probe
        cls.fn.argtypes=[ct.POINTER(ct.c_double)]*4+[ct.c_double]*2+[ct.POINTER(ct.c_double)]
        cls.fn.restype=ct.c_int

    def call(self,height=2.,dual=0.,shape=None,bad=False,dy=.001,radius=.1):
        x=[0.,0.,0.,1.,0.,0.,0.,0.,1.];y=x.copy()
        for index in [1,4,7]:y[index]+=dy
        if bad:x[0]=float('nan')
        body=[.3,height,.3,.3,height,.3,radius]
        shape=shape or [1.,0.,0.,0.,1.,0.,0.,0.,1.]
        output=array([123.]*6)
        code=self.fn(array(x),array(y),array(body),array(shape),dual,1.,output)
        return code,list(output)

    def test_far_inactive_pair_reuses_both_validated_queries(self):
        code,out=self.call()
        self.assertEqual(code,0)
        self.assertEqual(out[:2],[2.,0.])
        self.assertEqual(out[3:5], [0.,0.])
        self.assertGreaterEqual(out[2],1.5e-6)

    def test_close_and_positive_multiplier_pairs_keep_exact_path(self):
        for height,dual in [(.05,0.),(.2,10.)]:
            code,out=self.call(height,dual)
            self.assertEqual(code,0)
            self.assertEqual(out[:2],[2.,1.])
            self.assertGreater(out[3],0.)

    def test_a_newly_active_trial_cannot_reuse_old_inactivity(self):
        code,out=self.call(dy=1.95)
        self.assertEqual(code,0)
        self.assertEqual(out[:2],[2.,1.])
        self.assertGreater(out[2],1.5*1.95**2)

    def test_inactive_nonzero_multiplier_reuses_validated_queries(self):
        code,out=self.call(dual=.02)
        self.assertEqual(code,0)
        self.assertEqual(out[:2],[2.,0.])
        self.assertEqual(out[3],0.)

    def test_degenerate_fine_geometry_and_nan_still_reject(self):
        for options in [{'shape':[1.,0.,0.]*3},{'bad':True}]:
            code,_=self.call(**options)
            self.assertNotEqual(code,0)

    def test_tiny_radius_preserves_normalized_gap_overflow_rejection(self):
        code,_=self.call(radius=1e-160)
        self.assertNotEqual(code,0)

    def test_rounded_touch_retains_tiny_positive_multiplier(self):
        code,out=self.call(height=.07,radius=.07,dual=1e-17,dy=0.)
        self.assertEqual(code,0)
        self.assertEqual(out[3],1e-17)
        self.assertEqual(out[:2],[2.,1.])
        self.assertGreater(out[5],1.)

if __name__=='__main__':unittest.main()
