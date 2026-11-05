"""All-pair scalar parity and atomic bulk geometry; no omitted-pair certificate."""
import ctypes as ct
from pathlib import Path
import unittest
import numpy as np
import test_fp_environment as env
ROOT=Path(__file__).resolve().parents[2]
D=ct.POINTER(ct.c_double);I=ct.POINTER(ct.c_int)
Q=np.array([[0.,0.,0.],[1.,0.,0.],[0.,0.,1.]])
B=np.array([[.8,.1,.1],[.3,.6,.1],[.3,.1,.6]])
class BatchTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.lib=ct.CDLL(str(ROOT/'.tools/native/contact_distance.dll'))
  assert hasattr(cls.lib,'membrane_material_witness_batch'),'missing bounded all-pair witness ABI'
  cls.fn=cls.lib.membrane_material_witness_batch;cls.fn.argtypes=[ct.c_int,D,D,ct.c_int,D,I,D];cls.fn.restype=ct.c_int
  cls.scalar=cls.lib.membrane_material_witness;cls.scalar.argtypes=[D,D,D,ct.c_double,D];cls.scalar.restype=ct.c_int
 def call(self,q,b,c,faces=None,bodies=None):
  q=np.ascontiguousarray(q,dtype=np.float64);b=np.ascontiguousarray(b,dtype=np.float64);c=np.ascontiguousarray(c,dtype=np.float64)
  f=len(q) if faces is None else faces;n=len(c) if bodies is None else bodies
  count=max(1,min(65536,len(q)*len(c)));codes=np.full(count,456,dtype=np.int32);values=np.full(count*13,123.)
  old=(q.tobytes(),b.tobytes(),c.tobytes())
  status=self.fn(f,q.ctypes.data_as(D),b.ctypes.data_as(D),n,c.ctypes.data_as(D),codes.ctypes.data_as(I),values.ctypes.data_as(D))
  self.assertEqual(old,(q.tobytes(),b.tobytes(),c.tobytes()))
  return status,codes,values
 def scalar_call(self,q,b,c):
  out=np.full(13,123.);q=np.ascontiguousarray(q);b=np.ascontiguousarray(b);c=np.ascontiguousarray(c)
  status=self.scalar(c.ctypes.data_as(D),q.ctypes.data_as(D),b.ctypes.data_as(D),float(c[6]),out.ctypes.data_as(D))
  return status,out
 def test_all_pairs_match_scalar_bits_in_rigid_poses(self):
  rng=np.random.default_rng(527);qs=[];bs=[]
  for _ in range(24):
   u,_,v=np.linalg.svd(rng.normal(size=(3,3)));qs.append(Q@(u@v)+rng.uniform(-1.,1.,3));bs.append(B.copy())
  capsules=np.array([[.25,.1,.25,.25,.1,.25,.01],[.25,.1,.25,.5,.2,.25,.02],[-1.,-.2,-1.,-1.,.2,-1.,.03]])
  status,codes,values=self.call(qs,bs,capsules);self.assertEqual(status,0)
  for f in range(len(qs)):
   for body,c in enumerate(capsules):
    code,scalar=self.scalar_call(qs[f],bs[f],c);pair=f*len(capsules)+body
    self.assertEqual(codes[pair],code);self.assertEqual(values[pair*13:pair*13+13].tobytes(),scalar.tobytes())
 def test_intersection_tie_and_degenerate_statuses_preserved(self):
  for capsule in [[.25,0.,.25,.25,0.,.25,.01],[.25,.1,.25,.25,-.1,.25,.01],[.1,.1,.1,.6,.1,.1,.01]]:
   expected,values=self.scalar_call(Q,np.eye(3),np.array(capsule));status,codes,out=self.call([Q],[np.eye(3)],[capsule])
   self.assertEqual(status,0);self.assertEqual(codes[0],expected);self.assertEqual(out.tobytes(),values.tobytes())
  status,codes,out=self.call([Q,Q],[np.eye(3),np.array([[1.,0.,0.]]*3)],[[.2,.1,.2,.2,.1,.2,.01]])
  self.assertEqual(status,2);self.assertTrue(np.all(codes==456));self.assertTrue(np.all(out==123.))
 def test_invalid_late_input_and_limits_are_atomic(self):
  q=np.array([Q,Q]);b=np.array([B,B]);c=np.array([[.2,.1,.2,.2,.1,.2,.01]]*2)
  cases=[]
  bad=q.copy();bad[-1,-1,-1]=np.nan;cases.append((bad,b,c,None,None))
  bad=b.copy();bad[-1,-1,-1]=np.inf;cases.append((q,bad,c,None,None))
  bad=c.copy();bad[-1,-1]=np.nan;cases.append((q,b,bad,None,None))
  cases.extend([(q,b,c,0,1),(q,b,c,8193,1),(q,b,c,1,65),(q,b,c,8192,9)])
  for args in cases:
   status,codes,out=self.call(*args);self.assertEqual(status,-1);self.assertTrue(np.all(codes==456));self.assertTrue(np.all(out==123.))
 def test_maximum_pair_count_is_not_truncated(self):
  q=np.tile(Q,(8192,1,1));b=np.tile(B,(8192,1,1));c=np.array([[.25,.05+.01*i,.25,.25,.05+.01*i,.25,.01] for i in range(8)])
  status,codes,values=self.call(q,b,c);self.assertEqual(status,0);self.assertEqual(len(codes),65536)
  for pair in [0,7,65528,65535]:
   expected,out=self.scalar_call(Q,B,c[pair%8]);self.assertEqual(codes[pair],expected);self.assertEqual(values[pair*13:pair*13+13].tobytes(),out.tobytes())
 def test_caller_fp_contexts_restore_and_match_bits(self):
  env.EnvironmentTests.setUpClass();p=env.EnvironmentTests.probe;original=(p.fem_probe_x87(),p.fem_probe_mxcsr())
  q=np.array([Q]);b=np.array([B]);c=np.array([[.25,.1,.25,.25,.1,.25,.01]])
  def call():
   status,codes,values=self.call(q,b,c);return status,codes.tobytes(),values.tobytes()
  expected=call()
  try:
   for cw,mx in env.EnvironmentTests.contexts(original):
    codes=np.full(1,456,dtype=np.int32);values=np.full(13,123.)
    p.fem_probe_set_x87(cw);p.fem_probe_set_mxcsr(mx)
    status=self.fn(1,q.ctypes.data_as(D),b.ctypes.data_as(D),1,c.ctypes.data_as(D),codes.ctypes.data_as(I),values.ctypes.data_as(D))
    after=(p.fem_probe_x87(),p.fem_probe_mxcsr()&~0x3f);p.fem_probe_set_x87(original[0]);p.fem_probe_set_mxcsr(original[1])
    self.assertEqual(after,(cw,mx&~0x3f));self.assertEqual((status,codes.tobytes(),values.tobytes()),expected)
  finally:p.fem_probe_set_x87(original[0]);p.fem_probe_set_mxcsr(original[1])
if __name__=='__main__':unittest.main()
