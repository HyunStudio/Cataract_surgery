"""Read-only geometry at actual material contact, with no force/Hessian claim."""
import ctypes as ct
from pathlib import Path
import unittest
import numpy as np
import test_fp_environment as environment
import test_fem_contact as contact
ROOT=Path(__file__).resolve().parents[2]
D=ct.POINTER(ct.c_double)
Q=np.array([[0.,0.,0.],[1.,0.,0.],[0.,0.,1.]])
B=np.array([[.8,.1,.1],[.3,.6,.1],[.3,.1,.6]])
class MaterialWitnessTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.lib=ct.CDLL(str(ROOT/'.tools/native/contact_distance.dll'))
  assert hasattr(cls.lib,'membrane_material_witness'),'jaw acquisition needs a separate read-only geometry ABI, including exact contact'
  cls.fn=cls.lib.membrane_material_witness;cls.fn.argtypes=[D,D,D,ct.c_double,D];cls.fn.restype=ct.c_int
 def call(self,segment,q=Q,b=B,radius=.01):
  args=[np.ascontiguousarray(x,dtype=np.float64) for x in [segment,q,b]];saved=[x.copy() for x in args];out=np.full(13,123.)
  code=self.fn(*(x.ctypes.data_as(D) for x in args),radius,out.ctypes.data_as(D))
  for x,y in zip(args,saved):np.testing.assert_array_equal(x,y)
  return code,out
 def verify(self,segment,q,b,result,radius=.01):
  code,out=result;self.assertIn(code,[0,1,3]);tri=(b/b.sum(axis=1)[:,None])@q;seg=np.array(segment).reshape(2,3)
  expected,_,_=contact.FEMContactTests.closest(np.r_[seg.ravel(),radius],tri)
  self.assertAlmostEqual(out[0],expected,delta=1e-12);self.assertAlmostEqual(out[1],np.sqrt(expected)-radius,delta=1e-11)
  self.assertTrue(np.all(out[8:11]>=0.));self.assertAlmostEqual(sum(out[8:11]),1.,delta=1e-13);self.assertTrue(0.<=out[11]<=1.)
  np.testing.assert_allclose(out[2:5],seg[0]+out[11]*(seg[1]-seg[0]),atol=1e-13,rtol=0.)
  np.testing.assert_allclose(out[5:8],out[8:11]@tri,atol=1e-13,rtol=0.)
  delta=out[5:8]-out[2:5]
  self.assertTrue(np.all((tri-out[5:8])@delta>=-1e-12));self.assertTrue(np.all((out[2:5]-seg)@delta>=-1e-12))
 def test_exact_point_contact_retains_geometry_without_derivatives(self):
  segment=[.25,0.,.25]*2;result=self.call(segment);self.assertEqual(result[0],1);self.assertEqual(result[1][0],0.);self.verify(segment,Q,B,result)
 def test_finite_crossing_retains_original_intersection_status(self):
  segment=[.25,.1,.25,.25,-.1,.25];result=self.call(segment);self.assertEqual(result[0],1);self.verify(segment,Q,B,result)
 def test_regular_fine_face_uses_nonidentity_material_map(self):
  segment=[.25,.05,.25]*2;result=self.call(segment);self.assertEqual(result[0],0);self.verify(segment,Q,B,result);np.testing.assert_allclose(result[1][8:11],[.4,.3,.3],atol=1e-13)
 def test_independent_closest_and_kkt_in_rigid_poses(self):
  rng=np.random.default_rng(103)
  for _ in range(24):
   u,_,v=np.linalg.svd(rng.normal(size=(3,3)));rotation=u@v;shift=rng.uniform(-2.,2.,3);q=Q@rotation+shift
   seg=np.array([[.25,.03,.25],[.35,.07,.3]])@rotation+shift;self.verify(seg,q,B,self.call(seg,q))
 def test_invalid_arguments_are_atomic(self):
  for segment,q,b,radius in [([.2,.1,.2]*2,Q,B,-1.),([np.nan,0.,0.]*2,Q,B,.01),([.2,.1,.2]*2,Q,np.zeros((3,3)),.01),([.2,.1,.2]*2,Q,np.full((3,3),np.inf),.01)]:
   code,out=self.call(segment,q,b,radius);self.assertEqual(code,-1);np.testing.assert_array_equal(out,123.)
 def test_degenerate_material_face_is_not_a_published_contact(self):
  code,out=self.call([.2,.1,.2]*2,b=np.array([[1.,0.,0.]]*3));self.assertEqual(code,2);np.testing.assert_array_equal(out,123.)
 def test_geometry_tie_is_explicit_not_a_smooth_branch(self):
  segment=[.1,.1,.1,.6,.1,.1];b=np.eye(3);result=self.call(segment,b=b);self.assertEqual(result[0],3);self.verify(segment,Q,b,result)
 def test_caller_fp_contexts_preserve_contact_and_invalid_results(self):
  environment.EnvironmentTests.setUpClass();p=environment.EnvironmentTests.probe;original=(p.fem_probe_x87(),p.fem_probe_mxcsr())
  args=[np.array([.25,0.,.25]*2),Q.copy(),B.copy()];ptr=[x.ctypes.data_as(D) for x in args]
  def call(radius):
   out=np.full(13,123.);code=self.fn(*ptr,radius,out.ctypes.data_as(D));return code,out.tobytes()
  expected=[call(.01),call(-1.)]
  try:
   for cw,mx in environment.EnvironmentTests.contexts(original):
    for index,radius in enumerate([.01,-1.]):
     p.fem_probe_set_x87(cw);p.fem_probe_set_mxcsr(mx);result=call(radius);after=(p.fem_probe_x87(),p.fem_probe_mxcsr()&~0x3f);p.fem_probe_set_x87(original[0]);p.fem_probe_set_mxcsr(original[1]);self.assertEqual(after,(cw,mx&~0x3f));self.assertEqual(result,expected[index])
  finally:p.fem_probe_set_x87(original[0]);p.fem_probe_set_mxcsr(original[1])
if __name__=='__main__':unittest.main()
