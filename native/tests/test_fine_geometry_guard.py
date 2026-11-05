"""Separate bounded fine geometry; mechanical and legacy limits are unchanged."""
import ctypes as ct
import unittest
import numpy as np
import test_contact_guard as guard
import test_fp_environment as environment

D=ct.POINTER(ct.c_double);I=ct.POINTER(ct.c_int)
class FineGeometryGuardTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.lib=ct.CDLL(str(guard.ROOT/'.tools/native/contact_guard.dll'))
  assert hasattr(cls.lib,'membrane_guard_fine_motion_witness'),'fine geometry needs a separate bounded guard ABI'
  cls.extended=cls.lib.membrane_guard_fine_motion_witness;cls.legacy=cls.lib.membrane_guard_motion_witness
  for fn in (cls.extended,cls.legacy):
   fn.argtypes=[ct.c_int,D,D,ct.c_int,I,ct.c_int,I,D,ct.c_int,ct.c_double,D,D];fn.restype=ct.c_int
 def mesh(self):
  q=np.empty((8192,3));faces=[]
  for i in range(2729):
   x=2.+(i%64)*.01;z=2.+(i//64)*.01
   q[i*3:i*3+3]=[[x,1.,z],[x+.002,1.,z],[x,1.,z+.002]];faces.append([i*3,i*3+1,i*3+2])
  q[8187:8189]=[[2.8,1.,2.8],[2.81,1.,2.8]];faces.append([8187,8188,0])
  q[8189:]=[[-.05,0.,-.05],[.05,0.,-.05],[0.,0.,.05]];faces.append([8189,8190,8191])
  self.assertEqual(len(set(np.array(faces).ravel())),8192)
  return q,np.array(faces,dtype=np.int32)
 def call(self,q,faces,packet,legacy=False,budget=128):
  q=np.ascontiguousarray(q,dtype=np.float64);faces=np.ascontiguousarray(faces,dtype=np.int32)
  packets=np.ascontiguousarray(packet,dtype=np.float64);kinds=np.array([0],dtype=np.int32)
  out=np.full(8,99.);witness=ct.c_double(-99.);saved=[x.copy() for x in (q,faces,packets)]
  fn=self.legacy if legacy else self.extended
  status=fn(len(q),q.ctypes.data_as(D),q.ctypes.data_as(D),len(faces),faces.ctypes.data_as(I),1,kinds.ctypes.data_as(I),packets.ctypes.data_as(D),budget,1e-9,out.ctypes.data_as(D),ct.byref(witness))
  for a,b in zip((q,faces,packets),saved):np.testing.assert_array_equal(a,b)
  return status,out,witness.value
 def test_all8192_points_and_every_face_are_checked(self):
  q,faces=self.mesh();code,stats,w=self.call(q,faces,guard.linear([4.,4.,4.],[4.,4.,4.],.01))
  self.assertEqual(code,0);self.assertEqual(stats[1],len(faces));self.assertEqual(w,-1.)
  code,stats,w=self.call(q,faces,guard.linear([0.,.1,0.],[0.,-.1,0.],.01))
  self.assertEqual(code,1);self.assertEqual(stats[2],len(faces)-1);self.assertTrue(0.<=w<=1.);self.assertLessEqual(stats[0],128)
 def test_legacy_and_extended_capacity_failures_are_atomic(self):
  q,faces=self.mesh();packet=guard.linear([4.,4.,4.],[4.,4.,4.],.01)
  for points,legacy in ((q,True),(np.r_[q,[[0.,0.,0.]]],False)):
   code,stats,w=self.call(points,faces,packet,legacy);self.assertEqual(code,-1);np.testing.assert_array_equal(stats,99.);self.assertEqual(w,-99.)
  bad=q.copy();bad[-1,0]=np.nan
  code,stats,w=self.call(bad,faces,packet);self.assertEqual(code,-1);np.testing.assert_array_equal(stats,99.);self.assertEqual(w,-99.)
 def test_small_inputs_retain_legacy_results_bitwise(self):
  q=np.array([[-1.,0.,-1.],[1.,0.,-1.],[0.,0.,1.]]);f=np.array([[0,1,2]],dtype=np.int32)
  for packet,budget in ((guard.linear([0.,.1,0.],[0.,-.1,0.],.01),128),(guard.linear([3.,3.,3.],[3.,3.,3.],.01),128),(guard.linear([0.,.1,0.],[0.,-.1,0.],.01),0)):
   a=self.call(q,f,packet,True,budget);b=self.call(q,f,packet,False,budget)
   self.assertEqual(a[0],b[0]);self.assertEqual(a[1].tobytes(),b[1].tobytes());self.assertEqual(a[2],b[2])
 def test_actual_extended_api_restores_caller_fp_contexts(self):
  environment.EnvironmentTests.setUpClass();probe=environment.EnvironmentTests.probe
  q,faces=self.mesh();packet=guard.linear([0.,.1,0.],[0.,-.1,0.],.01)
  original=(probe.fem_probe_x87(),probe.fem_probe_mxcsr())
  expected=self.call(q,faces,packet)
  try:
   for cw,mx in environment.EnvironmentTests.contexts(original):
    probe.fem_probe_set_x87(cw);probe.fem_probe_set_mxcsr(mx);answer=self.call(q,faces,packet)
    after=(probe.fem_probe_x87(),probe.fem_probe_mxcsr()&~0x3f)
    probe.fem_probe_set_x87(original[0]);probe.fem_probe_set_mxcsr(original[1])
    self.assertEqual(after,(cw,mx&~0x3f));self.assertEqual(answer[0],expected[0]);self.assertEqual(answer[1].tobytes(),expected[1].tobytes());self.assertEqual(answer[2],expected[2])
  finally:probe.fem_probe_set_x87(original[0]);probe.fem_probe_set_mxcsr(original[1])

if __name__=='__main__':unittest.main()
