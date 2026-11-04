"""Cached outward certificates must equal the original, uncached arithmetic."""
import ctypes as ct
import math
from pathlib import Path
import random
import unittest
import test_fp_environment as environment
ROOT=Path(__file__).resolve().parents[2]
D=ct.POINTER(ct.c_double)
array=lambda values:(ct.c_double*len(values))(*values)
class TemporalHullTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.lib=ct.CDLL(str(ROOT/'.tools/native/contact_merit_probe.dll'))
  assert hasattr(cls.lib,'merit_temporal_hull_compare'),'temporal inactive certificates need an immutable original-control hull cache'
  cls.fn=cls.lib.merit_temporal_hull_compare;cls.fn.argtypes=[D,D,D,ct.c_double,D,ct.c_double,ct.c_double,ct.c_double,D];cls.fn.restype=ct.c_int
 def call(self,previous,before,after,time,axis,radius,dual,rho):
  out=array([123.]*12);code=self.fn(array(previous),array(before),array(after),time,array(axis),radius,dual,rho,out)
  self.assertIn(code,[0,3],'cached hull changed the original strict inactive certificate')
  return code,bytes(out)
 def test_body_dual_penalty_and_time_remain_pair_specific(self):
  old=[0.,0.,0.,1.,0.,0.,0.,0.,1.];end=old.copy()
  for j in [1,4,7]:end[j]=.2
  self.assertEqual(self.call(old,end,end,.25,[.3,2.,.3]*2,.1,0.,1.)[0],3)
  self.assertEqual(self.call(old,end,end,.25,[.3,.05,.3]*2,.1,0.,1.)[0],0)
  self.assertEqual(self.call(old,end,end,.25,[.3,2.,.3]*2,.1,1e10,1.)[0],0)
  self.assertEqual(self.call(old,end,end,1.,[.3,.2,.3]*2,.1,0.,1.)[0],0)
 def test_random_controls_translations_and_numerical_seeds(self):
  rng=random.Random(156)
  for i in range(500):
   offset=rng.choice([-8.,0.,8.]);previous=[offset+rng.uniform(-1,1) for _ in range(9)];before=[x+rng.uniform(-.2,.2) for x in previous];after=[x+rng.uniform(-.2,.2) for x in before]
   axis=[offset+rng.uniform(-3,3) for _ in range(6)];self.call(previous,before,after,rng.choice([math.nextafter(0.,1.),.001953125,.4697265625,.5,1.]),axis,rng.uniform(.001,.3),rng.choice([0.,1e-300,.002,1000.]),rng.choice([1.,1e4,1e7,1e12]))
 def test_near_threshold_keeps_outward_strictness(self):
  old=[0.,0.,0.,1.,0.,0.,0.,0.,1.]
  for height in [math.nextafter(.1,0.),.1,math.nextafter(.1,1.),.100000000001]:
   for dual in [0.,1e-300,1e-17]:self.call(old,old,old,1.,[.3,height,.3]*2,.1,dual,1e7)
 def test_cache_restores_all_caller_fp_contexts(self):
  environment.EnvironmentTests.setUpClass();probe=environment.EnvironmentTests.probe
  old=[-.2,0.,.1,1.,0.,0.,0.,0.,1.];before=[x+.001 for x in old];after=[x+.003 for x in old];args=(old,before,after,.4697265625,[.3,2.,.3]*2,.07,.002,1e7)
  expected=self.call(*args);original=(probe.fem_probe_x87(),probe.fem_probe_mxcsr())
  try:
   for cw,mx in environment.EnvironmentTests.contexts(original):
    probe.fem_probe_set_x87(cw);probe.fem_probe_set_mxcsr(mx);result=self.call(*args);got=(probe.fem_probe_x87(),probe.fem_probe_mxcsr()&~0x3f);probe.fem_probe_set_x87(original[0]);probe.fem_probe_set_mxcsr(original[1]);self.assertEqual(got,(cw,mx&~0x3f));self.assertEqual(result,expected)
  finally:probe.fem_probe_set_x87(original[0]);probe.fem_probe_set_mxcsr(original[1])
if __name__=='__main__':unittest.main()
