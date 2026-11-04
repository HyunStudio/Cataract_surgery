"""Accurate end fields preserve original inertia and do not assert path clearance."""
import ctypes as ct
import json
from pathlib import Path
import unittest
import numpy as np
import test_fem_trajectory as trajectory
import test_fp_environment as environment
from replay_fem_contact import replay
from test_contact_guard import linear
ROOT=Path(__file__).resolve().parents[2]
class PreciseEndpointTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.lib=ROOT/'.tools/native/membrane_fem.dll'
  assert hasattr(ct.CDLL(str(cls.lib)),'membrane_fem_solve_precise_contact'),'accurate endpoint needs a separate ABI without changing the legacy static candidate'
 def problem(self):
  p=trajectory.FEMTrajectoryTests().request();motion=linear([1.,0.,0.],[1.,0.,0.],.1);p['capsules']=motion[:6]+[motion[12]];return p,motion
 def verify(self,p,old,kinds,packets,result):trajectory.FEMTrajectoryTests().verify(p,old,kinds,packets,[1.],result)
 def test_actual156_and167_end_fields_satisfy_original_kkt(self):
  for number in [156,167]:
   case=json.loads((ROOT/f'docs/assets/operative-motion{number}-native-case-2026-11-05.json').read_text());p=case['fem_request'];saved=np.array(p['xyz'])
   result=replay(p,self.lib,precise=True);self.verify(p,case['previous_controls'],case['motion']['kinds'],case['motion']['packets'],result)
   np.testing.assert_array_equal(p['xyz'],saved);self.assertLessEqual(result[4][2],p['budget'])
 def test_simple_endpoint_has_no_history_or_midpoint_dependency(self):
  p,motion=self.problem();result=replay(p,self.lib,precise=True);self.verify(p,p['xyz'],[0],motion,result)
  self.assertGreater(np.max(abs(result[1]-p['xyz'])),.01)
 def test_invalid_and_exhausted_candidates_are_atomic(self):
  p,_=self.problem();bad=dict(p,capsules=p['capsules'][:-1]+[-1.])
  for request,status in [(dict(p,budget=0),1),(bad,-1)]:
   result=replay(request,self.lib,precise=True);self.assertEqual(result[0],status);np.testing.assert_array_equal(result[1],request['xyz']);np.testing.assert_array_equal(result[3],123.)
 def test_no_contact_retains_legacy_grasp_candidate_bitwise(self):
  p,_=self.problem();p['capsules']=[];old=replay(p,self.lib);new=replay(p,self.lib,precise=True)
  self.assertEqual(old[0],new[0])
  for a,b in zip(old[1:],new[1:]):np.testing.assert_array_equal(a,b)
 def test_actual_api_restores_all_caller_fp_contexts(self):
  environment.EnvironmentTests.setUpClass();probe=environment.EnvironmentTests.probe;p,_=self.problem();bad=dict(p,capsules=p['capsules'][:-1]+[-1.]);cases=[(p,0),(dict(p,budget=0),1),(bad,-1)]
  def call(request):
   r=replay(request,self.lib,precise=True);return (r[0],*(x.tobytes() for x in r[1:]))
  expected=[call(p) for p,_ in cases];original=(probe.fem_probe_x87(),probe.fem_probe_mxcsr())
  try:
   for cw,mx in environment.EnvironmentTests.contexts(original):
    for index,(request,status) in enumerate(cases):
     probe.fem_probe_set_x87(cw);probe.fem_probe_set_mxcsr(mx);result=call(request);after=(probe.fem_probe_x87(),probe.fem_probe_mxcsr()&~0x3f);probe.fem_probe_set_x87(original[0]);probe.fem_probe_set_mxcsr(original[1]);self.assertEqual(after,(cw,mx&~0x3f));self.assertEqual(result[0],status);self.assertEqual(result,expected[index])
  finally:probe.fem_probe_set_x87(original[0]);probe.fem_probe_set_mxcsr(original[1])
if __name__=='__main__':unittest.main()
