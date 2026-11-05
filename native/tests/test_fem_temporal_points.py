"""Time-weighted material point normals; collocation never replaces whole-motion guard."""
import ctypes as ct
import math
import unittest
import numpy as np
import test_membrane_fem as fem
import test_fp_environment as environment
import test_fem_material_points as static_points
import test_fem_trajectory as temporal_faces
from test_trajectory_contact import sample
from replay_fem_contact import replay as static_replay
from replay_fem_trajectory import replay
LIB=fem.ROOT/'.tools/native/membrane_fem.dll'
METHOD='membrane_fem_solve_material_points_trajectory'
class TemporalPointTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.lib=ct.CDLL(str(LIB));assert hasattr(cls.lib,METHOD),'missing time-weighted material point candidate API'
 def request(self):
  p=temporal_faces.FEMTrajectoryTests().request();p['budget']=250
  p['face_weights']=np.tile([1/3,1/3,1/3],(3,1)).ravel().tolist()
  h=math.sqrt(.5)
  packet=[0.,-1.,0.]*2+[0.,1.,0.]*2+[.1]+[0.]*6+[0.,0.,-h,h,0.,0.,h,h]+[1.,0.,0.]*4+[0.,1.]
  return p,packet
 def run_point(self,p,old,kinds,packets,times):
  return replay(p,old,kinds,packets,times,LIB,method=METHOD)
 def verify_force(self,p,old,kinds,packets,times,result):
  status,x,_,dual,stats=result;self.assertEqual(status,0,stats)
  q=x.reshape(-1,3);pred=np.array(p['xyz']).reshape(-1,3);old=np.array(old).reshape(-1,3)
  force=np.zeros_like(q)
  for ids,basis,area in zip(np.array(p['nodes']).reshape(-1,3),np.array(p['gradients']).reshape(-1,2,3),p['areas']):
   f=q[ids].T@basis.T;c=f.T@f;log_j=.5*np.linalg.slogdet(c)[1]
   stress=p['mu']*f+(p['lambda']*log_j-p['mu'])*f@np.linalg.inv(c);force[ids]+=(area*stress@basis).T
  free=np.array(p['inverse'])>0
  force[free]+=(q[free]-pred[free])/(np.array(p['inverse'])[free,None]*p['dt']**2)
  rows=np.array(p['face_nodes']).reshape(-1,3);shapes=np.array(p['face_weights']).reshape(-1,3,3)
  packets=np.array(packets).reshape(-1,41)
  for layer,t in enumerate(times):
   posed=(1-t)*old+t*q
   for row,(ids,shape) in enumerate(zip(rows,shapes)):
    w=shape[0]/sum(shape[0]);point=w@posed[ids]
    for body,packet in enumerate(packets):
     axis=sample(packet,t) if kinds[body] else ((1-t)*packet[:6]+t*packet[6:12]).reshape(2,3)
     direction=axis[1]-axis[0];length=direction@direction
     parameter=np.clip((point-axis[0])@direction/length,0.,1.) if length else 0.
     delta=point-axis[0]-parameter*direction;squared=delta@delta;r=packet[12]
     u=dual[(layer*len(rows)+row)*len(kinds)+body]
     self.assertGreaterEqual(u,0.);self.assertGreaterEqual(math.sqrt(squared)-r,-1e-9)
     self.assertLessEqual(abs(u*(squared/(r*r)-1.)),1e-11)
     force[ids]-=u*t*2.*w[:,None]*delta/(r*r)
  self.assertLessEqual(np.max(abs(force[free])),1e-8)
  self.assertLessEqual(stats[1],1e-8);self.assertLessEqual(stats[12],1e-9);self.assertLessEqual(stats[13],1e-11);self.assertLessEqual(stats[2],250)
 def test_mid_arc_has_analytic_time_scaled_normal_reaction(self):
  p,packet=self.request();old=p['xyz'].copy()
  result=self.run_point(p,old,[1],packet,[.5,1.]);self.verify_force(p,old,[1],packet,[.5,1.],result)
  q=result[1].reshape(-1,3)
  np.testing.assert_allclose(q[:,0],1.15,atol=2e-9,rtol=0.)
  np.testing.assert_allclose(q[:,1:],np.array(old).reshape(-1,3)[:,1:],atol=2e-9,rtol=0.)
  self.assertAlmostEqual(result[3][0],3.,delta=2e-8);self.assertEqual(result[3][1],0.)
 def test_endpoint_only_matches_existing_point_api_bits(self):
  p=static_points.MaterialPointContactTests().request();segment=p['capsules'][:6];packet=segment+segment+[p['capsules'][6]]+[0.]*28
  before=static_replay(p,LIB,method='membrane_fem_solve_material_points')
  after=self.run_point(p,p['xyz'],[0],packet,[1.]);self.assertEqual(before[0],after[0])
  for a,b in zip(before[1:],after[1:]):self.assertEqual(a.tobytes(),b.tobytes())
 def test_invalid_time_shape_and_budget_are_atomic(self):
  p,packet=self.request();old=p['xyz'].copy()
  for times in ([.5,.5,1.],[0.,1.],[.5]):
   result=self.run_point(p,old,[1],packet,times);self.assertEqual(result[0],-1)
   np.testing.assert_array_equal(result[1],p['xyz']);np.testing.assert_array_equal(result[3],123.)
  p['budget']=0;result=self.run_point(p,old,[1],packet,[.5,1.]);self.assertNotEqual(result[0],0)
  np.testing.assert_array_equal(result[1],p['xyz']);np.testing.assert_array_equal(result[3],123.)
  p,packet=self.request();p['face_weights'][3:6]=[1.,0.,0.]
  result=self.run_point(p,p['xyz'],[1],packet,[.5,1.]);self.assertEqual(result[0],-1)
  np.testing.assert_array_equal(result[1],p['xyz']);np.testing.assert_array_equal(result[3],123.)
 def test_no_body_keeps_original_trajectory_bits(self):
  p,_=self.request();before=replay(p,p['xyz'],[],[],[.5,1.],LIB)
  after=self.run_point(p,p['xyz'],[],[],[.5,1.]);self.assertEqual(before[0],after[0])
  for a,b in zip(before[1:],after[1:]):self.assertEqual(a.tobytes(),b.tobytes())
 def test_separate_point_seed_preserves_physics_and_reduces_work(self):
  method='membrane_fem_solve_material_points_trajectory_seeded'
  self.assertTrue(hasattr(self.lib,method),'temporal points need their own seed ABI, never ordinary face multipliers')
  p,packet=self.request();old=p['xyz'].copy();cold=self.run_point(p,old,[1],packet,[.5,1.])
  self.assertEqual(cold[0],0)
  seeded=replay(p,old,[1],packet,[.25,.5,1.],LIB,initial=cold[1],multiplier_seed=[0.,cold[3][0],cold[3][1]],penalty_seed=float(cold[4][15]),method=method)
  self.verify_force(p,old,[1],packet,[.25,.5,1.],seeded)
  self.assertLess(seeded[4][2],cold[4][2]);self.assertEqual(seeded[1].tobytes(),cold[1].tobytes())
 def test_bad_point_seed_is_atomic(self):
  method='membrane_fem_solve_material_points_trajectory_seeded';self.assertTrue(hasattr(self.lib,method))
  p,packet=self.request();old=p['xyz'].copy();bad=old.copy();bad[-1]=float('nan')
  for initial,multipliers,penalty in [(bad,[0.,0.],1.),(old,[-1.,0.],1.),(old,[0.,0.],.1)]:
   result=replay(p,old,[1],packet,[.5,1.],LIB,initial=initial,multiplier_seed=multipliers,penalty_seed=penalty,method=method)
   self.assertEqual(result[0],-1);np.testing.assert_array_equal(result[1],p['xyz']);np.testing.assert_array_equal(result[3],123.)
 def test_point_time_gradient_and_hessian(self):
  dll=ct.CDLL(str(fem.ROOT/'.tools/native/contact_activity_probe.dll'))
  self.assertTrue(hasattr(dll,'fem_time_point_contact_probe'))
  probe=dll.fem_time_point_contact_probe;probe.argtypes=[fem.D]*4+[ct.c_double]*3+[fem.D]*2;probe.restype=ct.c_int
  old=np.array([[0.,0.,0.],[1.,0.,0.],[0.,0.,1.]])
  end=old.copy();end[0,0]+=.01;end[1,1]+=.04;end[2,2]-=.01
  body=np.array([.3,.075,.3,.3,.075,.3,.12]);w=np.array([.5,.2,.3]);shape=np.tile(w,(3,1))
  def call(x,t):
   arrays=[np.ascontiguousarray(a,dtype=np.float64) for a in (old,x,body,shape)];g=np.full(9,123.);h=np.full((9,9),123.)
   code=probe(*(a.ctypes.data_as(fem.D) for a in arrays),t,.17,.8,g.ctypes.data_as(fem.D),h.ctypes.data_as(fem.D));self.assertEqual(code,0)
   return g,h
  def merit(x,t):
   point=w@((1-t)*old+t*x);g=np.sum((point-body[:3])**2)/body[6]**2-1.;u=max(0.,.17-.8*g)
   return (u*u-.17**2)/(2*.8)
  for t in [.2,.5,1.]:
   gradient,hessian=call(end,t);finite_g=np.empty(9);finite_h=np.empty((9,9))
   for k in range(9):
    plus=end.copy();minus=end.copy();plus.flat[k]+=1e-6;minus.flat[k]-=1e-6
    finite_g[k]=(merit(plus,t)-merit(minus,t))/2e-6;finite_h[:,k]=(call(plus,t)[0]-call(minus,t)[0])/2e-6
   np.testing.assert_allclose(gradient,finite_g,atol=2e-9,rtol=2e-7)
   np.testing.assert_allclose(hessian,finite_h,atol=2e-7,rtol=2e-7)
 def test_point_seeded_api_fp_contexts_restore(self):
  method='membrane_fem_solve_material_points_trajectory_seeded'
  environment.EnvironmentTests.setUpClass();probe=environment.EnvironmentTests.probe;original=(probe.fem_probe_x87(),probe.fem_probe_mxcsr())
  p,packet=self.request();cold=self.run_point(p,p['xyz'],[1],packet,[.5,1.]);self.assertEqual(cold[0],0)
  failed=dict(p,budget=0)
  def call(request):
   out=replay(request,request['xyz'],[1],packet,[.25,.5,1.],LIB,initial=cold[1],multiplier_seed=[0.,cold[3][0],cold[3][1]],penalty_seed=float(cold[4][15]),method=method)
   return out[0],*(a.tobytes() for a in out[1:])
  expected=[call(p),call(failed)]
  try:
   for cw,mx in environment.EnvironmentTests.contexts(original):
    for i,request in enumerate([p,failed]):
     probe.fem_probe_set_x87(cw);probe.fem_probe_set_mxcsr(mx);actual=call(request)
     after=(probe.fem_probe_x87(),probe.fem_probe_mxcsr()&~0x3f);probe.fem_probe_set_x87(original[0]);probe.fem_probe_set_mxcsr(original[1])
     self.assertEqual(after,(cw,mx&~0x3f));self.assertEqual(actual,expected[i])
  finally:probe.fem_probe_set_x87(original[0]);probe.fem_probe_set_mxcsr(original[1])
 def test_actual_api_fp_contexts_restore(self):
  environment.EnvironmentTests.setUpClass();probe=environment.EnvironmentTests.probe;original=(probe.fem_probe_x87(),probe.fem_probe_mxcsr())
  p,packet=self.request();failed=dict(p,budget=0)
  def call(request):
   out=self.run_point(request,request['xyz'],[1],packet,[.5,1.]);return out[0],*(a.tobytes() for a in out[1:])
  expected=[call(p),call(failed)]
  try:
   for cw,mx in environment.EnvironmentTests.contexts(original):
    for i,request in enumerate([p,failed]):
     probe.fem_probe_set_x87(cw);probe.fem_probe_set_mxcsr(mx);actual=call(request)
     after=(probe.fem_probe_x87(),probe.fem_probe_mxcsr()&~0x3f);probe.fem_probe_set_x87(original[0]);probe.fem_probe_set_mxcsr(original[1])
     self.assertEqual(after,(cw,mx&~0x3f));self.assertEqual(actual,expected[i])
  finally:probe.fem_probe_set_x87(original[0]);probe.fem_probe_set_mxcsr(original[1])
if __name__=='__main__':unittest.main()
