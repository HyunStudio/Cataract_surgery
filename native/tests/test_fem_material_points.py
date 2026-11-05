"""Multiple physical normal reactions for parallel finite-axis contact."""
import ctypes as ct
import unittest
import numpy as np
import test_membrane_fem as fem
from replay_fem_contact import replay
import test_fp_environment as environment

class MaterialPointContactTests(unittest.TestCase):
    def request(self):
        rest=np.array([[-.6,.009,-.3],[.6,.009,-.3],[0.,.009,.6]])
        nodes=np.array([[0,1,2]],dtype=np.int32)
        basis,areas=fem.MembraneFEMTests.reference_cells(rest,nodes)
        # Endpoints project inside the triangle at these material coordinates.
        points=np.array([[.5,1/6,1/3],[1/6,.5,1/3]])
        return {'xyz':rest.ravel().tolist(),'inverse':[1.,1.,1.],
                'nodes':nodes.ravel().tolist(),'gradients':basis.ravel().tolist(),'areas':areas.tolist(),
                'mu':2.,'lambda':3.,'dt':.1,'budget':250,'force_tolerance':1e-8,
                'gap_tolerance':1e-9,'complementarity_tolerance':1e-11,
                'grip_nodes':[],'grip_weights':[],'targets':[],
                'face_nodes':np.tile(nodes,(2,1)).ravel().tolist(),
                'face_weights':np.repeat(points[:,None,:],3,axis=1).ravel().tolist(),
                'capsules':[-.2,0.,0.,.2,0.,0.,.01]}
    def run_point(self,p):
        lib=ct.CDLL(str(fem.ROOT/'.tools/native/membrane_fem.dll'))
        self.assertTrue(hasattr(lib,'membrane_fem_solve_material_points'),
                        'parallel finite-axis contact needs independently weighted material reactions')
        # Reuse the identical typed ABI, with twice-repeated point shape rows.
        return replay(p,fem.ROOT/'.tools/native/membrane_fem.dll',method='membrane_fem_solve_material_points')
    def test_parallel_line_has_distributed_normal_equilibrium(self):
        p=self.request();status,x,reaction,dual,stats=self.run_point(p)
        self.assertEqual(status,0,stats)
        q=x.reshape(-1,3);pred=np.array(p['xyz']).reshape(-1,3)
        np.testing.assert_allclose(q[:,1],.01,atol=2e-10,rtol=0.)
        np.testing.assert_allclose(q[:,[0,2]],pred[:,[0,2]],atol=2e-9,rtol=0.)
        force=(q-pred)/(p['dt']**2)
        shapes=np.array(p['face_weights']).reshape(-1,3,3)
        for w,u in zip(shapes[:,0,:],dual):
            point=w@q;t=np.clip((point[0]+.2)/.4,0.,1.)
            delta=point-np.array([-.2+.4*t,0.,0.])
            force-=u*2.*w[:,None]*delta/(.01**2)
            self.assertGreaterEqual(u,0.)
            self.assertGreaterEqual(np.linalg.norm(delta)-.01,-1e-9)
            self.assertLessEqual(abs(u*(delta@delta/.01**2-1.)),1e-11)
        # Uniform translation has zero original membrane stress.
        self.assertLessEqual(np.max(abs(force)),1e-8)
        self.assertLessEqual(stats[1],1e-8);self.assertLessEqual(stats[12],1e-9)
        self.assertLessEqual(stats[13],1e-11)
        self.assertLessEqual(stats[2],250)
    def test_failure_and_invalid_point_shape_preserve_outputs(self):
        p=self.request();p['budget']=0
        code,x,reaction,dual,stats=self.run_point(p);self.assertNotEqual(code,0)
        np.testing.assert_array_equal(x,p['xyz']);np.testing.assert_array_equal(dual,123.)
        p=self.request();p['face_weights'][3:6]=[1.,0.,0.]
        code,x,reaction,dual,stats=self.run_point(p);self.assertEqual(code,-1)
        np.testing.assert_array_equal(x,p['xyz']);np.testing.assert_array_equal(dual,123.)

    def test_actual_api_fp_contexts_restore_valid_and_failed_calls(self):
        environment.EnvironmentTests.setUpClass();probe=environment.EnvironmentTests.probe
        original=(probe.fem_probe_x87(),probe.fem_probe_mxcsr())
        p=self.request();failed=dict(p,budget=0)
        def call(request):
            answer=self.run_point(request);return (answer[0],*(x.tobytes() for x in answer[1:]))
        expected=[call(p),call(failed)]
        try:
            for cw,mx in environment.EnvironmentTests.contexts(original):
                for i,request in enumerate((p,failed)):
                    probe.fem_probe_set_x87(cw);probe.fem_probe_set_mxcsr(mx);answer=call(request)
                    after=(probe.fem_probe_x87(),probe.fem_probe_mxcsr()&~0x3f)
                    probe.fem_probe_set_x87(original[0]);probe.fem_probe_set_mxcsr(original[1])
                    self.assertEqual(after,(cw,mx&~0x3f));self.assertEqual(answer,expected[i])
        finally:probe.fem_probe_set_x87(original[0]);probe.fem_probe_set_mxcsr(original[1])
    def test_no_contact_retains_original_candidate_bitwise(self):
        p=self.request();p['capsules']=[]
        original=replay(p,fem.ROOT/'.tools/native/membrane_fem.dll')
        current=self.run_point(p);self.assertEqual(current[0],original[0])
        for a,b in zip(current[1:],original[1:]):np.testing.assert_array_equal(a,b)

if __name__=='__main__':unittest.main()
