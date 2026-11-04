"""A zero PHR update never substitutes for a zero physical contact reaction."""
import ctypes as ct
import math
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[2]
class PhysicalZeroCertificateTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.lib=ct.CDLL(str(ROOT/'.tools/native/contact_activity_probe.dll'));cls.fn=cls.lib.fem_physical_zero_probe
  cls.fn.argtypes=[ct.c_double,ct.c_double,ct.c_int,ct.c_int,ct.c_double,ct.POINTER(ct.c_int),ct.POINTER(ct.c_double)];cls.fn.restype=ct.c_int
 def call(self,height=2.,dual=0.,physical=True,bad=0,radius=.1):
  counts=(ct.c_int*2)(-1,-1);out=(ct.c_double*4)(123.,123.,123.,123.);status=self.fn(height,dual,int(physical),bad,radius,counts,out);return status,list(counts),list(out)
 def test_far_zero_physical_reaction_uses_certificate_after_full_query(self):
  code,count,out=self.call();self.assertEqual(code,0);self.assertEqual(count,[1,0]);self.assertEqual(out[0],0.);self.assertEqual(out[1],0.);self.assertEqual(out[3],0.)
 def test_positive_far_physical_reaction_cannot_use_zero_phr_update(self):
  code,count,out=self.call(dual=.002);self.assertEqual(code,0);self.assertEqual(count,[1,1]);self.assertEqual(out[3],.002);self.assertGreater(out[0],.1);self.assertGreater(out[2],.7)
 def test_zero_physical_reaction_does_not_hide_penetration(self):
  code,count,out=self.call(height=.05);self.assertEqual(code,0);self.assertEqual(count,[1,1]);self.assertEqual(out[0],0.);self.assertGreater(out[1],.049);self.assertEqual(out[3],0.)
 def test_tiny_positive_touch_reaction_stays_active(self):
  code,count,out=self.call(height=.1,dual=1e-17);self.assertEqual(code,0);self.assertEqual(count,[1,1]);self.assertEqual(out[3],1e-17);self.assertGreater(out[0],0.)
 def test_signed_zero_physical_reaction_keeps_its_representation(self):
  code,count,out=self.call(dual=-0.);self.assertEqual(code,0);self.assertEqual(math.copysign(1.,out[3]),-1.)
 def test_existing_phr_far_certificate_keeps_its_query(self):
  code,count,out=self.call(physical=False);self.assertEqual(code,0);self.assertEqual(count,[1,0]);self.assertEqual(out[3],0.)
 def test_invalid_geometry_and_overflow_remain_rejected(self):
  for options in [{'bad':1},{'bad':2},{'radius':1e-160}]:
   code,count,_=self.call(**options);self.assertNotEqual(code,0);self.assertEqual(count[1],0)
class UnroundedFieldRegularityTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.lib=ct.CDLL(str(ROOT/'.tools/native/contact_activity_probe.dll'))
  assert hasattr(cls.lib,'fem_field_regular_probe'),'physical zero certificate requires positive unrounded fine geometry'
  cls.fn=cls.lib.fem_field_regular_probe;cls.fn.argtypes=[ct.POINTER(ct.c_double)]*3+[ct.c_double];cls.fn.restype=ct.c_int
 def call(self,old,end,shape,time):
  return self.fn(*[(ct.c_double*len(v))(*v) for v in [old,end,shape]],time)
 def test_exact_collinear_material_map_is_not_certified(self):
  xyz=[.3183777264711941,.4552728047208582,.469767304940897,.3275560558799335,.4551676272477041,.4637006211618173,.3367343505939624,.4550624536587914,.45763394851565503]
  shape=[.75,.125,.125,.4375,.4375,.125,.125,.75,.125]
  self.assertEqual(self.call(xyz,xyz,shape,.5),0)
 def test_original_control_collapse_is_checked_at_the_actual_time(self):
  old=[0.,0.,0.,1.,0.,0.,0.,0.,1.];end=old.copy();end[-1]=-1.;shape=[1.,0.,0.,0.,1.,0.,0.,0.,1.]
  for time,expected in [(.25,1),(.5,0),(.75,1)]:self.assertEqual(self.call(old,end,shape,time),expected)
 def test_thin_positive_translated_field_can_be_certified(self):
  xyz=[8.,8.,8.,8.1,8.,8.,8.,8.,8.+1e-12];shape=[1.,0.,0.,0.,1.,0.,0.,0.,1.]
  self.assertEqual(self.call(xyz,xyz,shape,.5),1)
if __name__=='__main__':unittest.main()
