"""Numerical recovery must solve unchanged physical temporal contact problems."""
import json
import unittest
import numpy as np
import test_fem_temporal_points as temporal
import test_fp_environment as environment
from replay_fem_trajectory import replay
METHOD=temporal.METHOD+'_seeded'
class WarmPointRecoveryTests(unittest.TestCase):
 def problem(self,b=.005,shift=-.05):
  p,packet=temporal.TemporalPointTests().request();p['budget']=32;old=p['xyz'].copy();times=[.25,.5,1.]
  cold=replay(p,old,[1],packet,times,temporal.LIB,method=temporal.METHOD)
  self.assertEqual(cold[0],0)
  guess=cold[1].reshape(-1,3)+np.array([[.03,b,0.],[-.03,0.,b],[0.,-b,-.03]])+np.array([shift,0.,0.])
  return p,old,packet,times,guess.ravel(),cold[3]
 def call(self,p,old,packet,times,guess,dual):
  return replay(p,old,[1],packet,times,temporal.LIB,initial=guess,multiplier_seed=dual,penalty_seed=1e6,method=METHOD)
 def test_small_family_preserves_original_equilibrium_inside_budget(self):
  for b,shift in [(.005,-.05),(.005,.05),(.02,-.05)]:
   with self.subTest(b=b,shift=shift):
    p,old,packet,times,guess,dual=self.problem(b,shift);before=(guess.tobytes(),dual.tobytes())
    out=self.call(p,old,packet,times,guess,dual)
    temporal.TemporalPointTests().verify_force(p,old,[1],packet,times,out)
    self.assertLessEqual(out[4][2],p['budget'])
    np.testing.assert_allclose(out[1].reshape(-1,3)[:,0],1.15,atol=2e-9,rtol=0.)
    self.assertEqual((guess.tobytes(),dual.tobytes()),before)
 def test_insufficient_budget_never_publishes_recovery_iterate(self):
  p,old,packet,times,guess,dual=self.problem();p['budget']=1
  out=self.call(p,old,packet,times,guess,dual);self.assertNotEqual(out[0],0)
  self.assertLessEqual(out[4][2],1);np.testing.assert_array_equal(out[1],p['xyz'])
  np.testing.assert_array_equal(out[2],123.);np.testing.assert_array_equal(out[3],123.)
 def test_recovery_preserves_all_actual_caller_fp_contexts(self):
  environment.EnvironmentTests.setUpClass();probe=environment.EnvironmentTests.probe
  original=(probe.fem_probe_x87(),probe.fem_probe_mxcsr())
  p,old,packet,times,guess,dual=self.problem()
  def invoke(request):
   r=self.call(request,old,packet,times,guess,dual);return (r[0],*(v.tobytes() for v in r[1:]))
  failed=dict(p,budget=1);expected=[invoke(p),invoke(failed)];self.assertEqual(expected[0][0],0)
  try:
   for cw,mx in environment.EnvironmentTests.contexts(original):
    for i,request in enumerate([p,failed]):
     probe.fem_probe_set_x87(cw);probe.fem_probe_set_mxcsr(mx);actual=invoke(request)
     after=(probe.fem_probe_x87(),probe.fem_probe_mxcsr()&~0x3f)
     probe.fem_probe_set_x87(original[0]);probe.fem_probe_set_mxcsr(original[1])
     self.assertEqual(after,(cw,mx&~0x3f));self.assertEqual(actual,expected[i])
  finally:probe.fem_probe_set_x87(original[0]);probe.fem_probe_set_mxcsr(original[1])
 def test_owned153_subproblems_retain_original_physical_equations(self):
  case=json.loads((temporal.fem.ROOT/'docs/assets/operative-motion153-native-case-2026-11-05.json').read_text(encoding='utf-8'))
  for index in [5,7]:
   p=case['native_history'][index]['request'];frozen=json.dumps(p,sort_keys=True)
   out=replay(p,p['previous'],p['kinds'],p['packets'],p['times'],temporal.LIB,initial=p['initial'],multiplier_seed=p['multiplier_seed'],penalty_seed=p['penalty_seed'],method=METHOD)
   temporal.TemporalPointTests().verify_force(p,p['previous'],p['kinds'],p['packets'],p['times'],out)
   self.assertLessEqual(out[4][2],p['budget']);self.assertEqual(json.dumps(p,sort_keys=True),frozen)
if __name__=='__main__':unittest.main()
