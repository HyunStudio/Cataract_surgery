"""Independent derivatives and original-field merit for point normal contacts."""
import ctypes as ct
from decimal import Decimal as Dec,localcontext
from pathlib import Path
import unittest
import numpy as np
import test_fp_environment as environment

ROOT=Path(__file__).resolve().parents[2]
D=ct.POINTER(ct.c_double)
class PointDistanceTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  path=ROOT/'.tools/native/material_point_probe.dll'
  assert path.exists(),'build the isolated material-point derivative probe'
  cls.lib=ct.CDLL(str(path));cls.query=cls.lib.point_query
  cls.query.argtypes=[D,D,D,ct.c_double,D,D,D];cls.query.restype=ct.c_int
  cls.change=cls.lib.point_change;cls.change.argtypes=[D,D,D,D,ct.c_double,D,ct.c_double,ct.c_double,ct.c_double,D];cls.change.restype=ct.c_int
 def data(self):
  return np.array([-.3,0.,.1,.4,.1,-.2]),np.array([[.1,.2,.3],[.5,-.1,.2],[-.2,.4,.1]]),np.tile([.2,.3,.5],(3,1))
 def call(self,axis,q,b,r=.01):
  args=[np.ascontiguousarray(v,dtype=np.float64) for v in (axis,q,b)];before=[x.copy() for x in args]
  values=np.full(22,123.);g=np.full(9,123.);h=np.full(81,123.)
  code=self.query(*(x.ctypes.data_as(D) for x in args),r,values.ctypes.data_as(D),g.ctypes.data_as(D),h.ctypes.data_as(D))
  for x,y in zip(args,before):np.testing.assert_array_equal(x,y)
  return code,values,g,h.reshape(9,9)
 @staticmethod
 def squared(axis,q,b):
  w=b[0]/sum(b[0]);p=w@q;u=axis[3:]-axis[:3];t=np.clip((p-axis[:3])@u/(u@u),0.,1.) if u@u else 0.
  return np.sum((p-axis[:3]-t*u)**2)
 def test_gradient_and_hessian_against_independent_finite_differences(self):
  axis,q,b=self.data()
  for axis in (axis,np.r_[axis[:3],axis[:3]],axis+np.tile([1.,-1.,.5],2)):
   code,v,g,h=self.call(axis,q,b);self.assertEqual(code,0)
   self.assertAlmostEqual(v[0],self.squared(axis,q,b),places=14)
   for k in range(9):
    plus=q.copy();minus=q.copy();plus.flat[k]+=1e-6;minus.flat[k]-=1e-6
    derivative=(self.squared(axis,plus,b)-self.squared(axis,minus,b))/2e-6
    self.assertAlmostEqual(g[k],derivative,delta=4e-10)
    finite=(self.call(axis,plus,b)[2]-self.call(axis,minus,b)[2])/2e-6
    np.testing.assert_allclose(h[:,k],finite,atol=3e-10,rtol=2e-8)
   np.testing.assert_allclose(h,h.T,atol=1e-14,rtol=0.)
 def test_rigid_pose_and_endpoint_generalized_hessian(self):
  axis,q,b=self.data();rng=np.random.default_rng(716)
  base=self.call(axis,q,b)
  for _ in range(12):
   rot,_=np.linalg.qr(rng.normal(size=(3,3)));shift=rng.uniform(-1.,1.,3)
   posed_axis=(axis.reshape(2,3)@rot+shift).ravel();posed=self.call(posed_axis,q@rot+shift,b)
   self.assertEqual(posed[0],0);self.assertAlmostEqual(posed[1][0],base[1][0],places=13)
   np.testing.assert_allclose(posed[2].reshape(3,3),base[2].reshape(3,3)@rot,atol=2e-15)
  axis=np.array([0.,0.,0.,1.,0.,0.]);q=np.tile([0.,.1,0.],(3,1));code,_,_,h=self.call(axis,q,b)
  self.assertEqual(code,0);self.assertGreaterEqual(np.linalg.eigvalsh(h).min(),-1e-14)
 @staticmethod
 def merit(old,end,b,time,axis,radius,dual,rho):
  with localcontext() as ctx:
   ctx.prec=80;d=lambda x:Dec.from_float(float(x))
   w=list(map(d,b[0]));total=sum(w);t=d(time)
   controls=[[d(old[j,a])+t*(d(end[j,a])-d(old[j,a])) for a in range(3)] for j in range(3)]
   p=[sum(w[j]*controls[j][a] for j in range(3))/total for a in range(3)]
   u=[d(axis[a+3])-d(axis[a]) for a in range(3)];v=[p[a]-d(axis[a]) for a in range(3)];length=sum(x*x for x in u)
   s=max(Dec(0),min(Dec(1),sum(x*y for x,y in zip(u,v))/length)) if length else Dec(0)
   g=sum((v[a]-s*u[a])**2 for a in range(3))/d(radius*radius)-1
   lam=d(dual);penalty=d(rho);return +(max(Dec(0),lam-penalty*g)**2-lam**2)/(2*penalty)
 def test_interval_merit_contains_independent_80_digit_original_field(self):
  axis,q,b=self.data();rng=np.random.default_rng(18);old=q+rng.normal(size=q.shape)*.01
  for time in (.125,.7,1.):
   for scale in (1e-3,1e-7,1e-11,1e-14):
    after=q+rng.normal(size=q.shape)*scale;out=np.full(2,123.)
    args=[np.ascontiguousarray(x) for x in (old,q,after,b,axis)]
    code=self.change(*(x.ctypes.data_as(D) for x in args[:4]),time,args[4].ctypes.data_as(D),.3,.2,10.,out.ctypes.data_as(D))
    self.assertEqual(code,0)
    with localcontext() as ctx:
     ctx.prec=80;reference=self.merit(old,after,b,time,axis,.3,.2,10.)-self.merit(old,q,b,time,axis,.3,.2,10.)
    self.assertLessEqual(Dec.from_float(out[0]),reference);self.assertGreaterEqual(Dec.from_float(out[1]),reference)
 def test_invalid_point_shape_is_atomic(self):
  axis,q,b=self.data()
  for bad in (np.eye(3),np.full((3,3),np.nan),np.zeros((3,3))):
   code,v,g,h=self.call(axis,q,bad);self.assertEqual(code,-1)
   for out in (v,g,h):np.testing.assert_array_equal(out,123.)
 def test_caller_fp_contexts_and_ownership(self):
  environment.EnvironmentTests.setUpClass();probe=environment.EnvironmentTests.probe
  original=(probe.fem_probe_x87(),probe.fem_probe_mxcsr());axis,q,b=self.data();expected=self.call(axis,q,b)
  try:
   for cw,mx in environment.EnvironmentTests.contexts(original):
    probe.fem_probe_set_x87(cw);probe.fem_probe_set_mxcsr(mx)
    answer=self.call(axis,q,b);actual=(probe.fem_probe_x87(),probe.fem_probe_mxcsr()&~0x3f)
    probe.fem_probe_set_x87(original[0]);probe.fem_probe_set_mxcsr(original[1])
    self.assertEqual(actual,(cw,mx&~0x3f));self.assertEqual(answer[0],expected[0])
    for x,y in zip(answer[1:],expected[1:]):self.assertEqual(x.tobytes(),y.tobytes())
  finally:probe.fem_probe_set_x87(original[0]);probe.fem_probe_set_mxcsr(original[1])

if __name__=='__main__':unittest.main()
