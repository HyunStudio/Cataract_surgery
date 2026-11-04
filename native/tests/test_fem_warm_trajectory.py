"""Numerical seeds never replace the physical inertial predictor."""
import ctypes as ct
import math
import json
import unittest
import numpy as np
import test_fem_trajectory as trajectory
import test_fp_environment as environment
from replay_fem_trajectory import replay
from replay_seeded_trajectory import extend
from test_contact_guard import linear

class WarmTrajectoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib=trajectory.LIB
        assert hasattr(ct.CDLL(str(cls.lib)),'membrane_fem_solve_trajectory_seeded'),'separate numerical seed API required'

    def problem(self):
        p=trajectory.FEMTrajectoryTests().request();motion=linear([1.,0.,0.],[1.,0.,0.],.1)
        return p,motion

    def verify(self,p,motion,result):
        trajectory.FEMTrajectoryTests().verify(p,p['xyz'],[0],motion,[.5,1.],result)

    def test_different_guesses_preserve_original_physical_objective(self):
        p,motion=self.problem();cold=replay(p,p['xyz'],[0],motion,[.5,1.],self.lib)
        for offset in [np.array([.15,.02,0.]),np.array([.03,-.01,.02])]:
            guess=(np.array(p['xyz']).reshape(-1,3)+offset).ravel();saved=guess.copy();seed=np.zeros(2)
            result=replay(p,p['xyz'],[0],motion,[.5,1.],self.lib,initial=guess,multiplier_seed=seed)
            self.verify(p,motion,result);np.testing.assert_allclose(result[1],cold[1],atol=2e-9,rtol=0.)
            np.testing.assert_array_equal(guess,saved);np.testing.assert_array_equal(seed,0.)

    def test_equilibrated_seed_needs_no_newton_step_but_keeps_original_inertia(self):
        p,motion=self.problem();cold=replay(p,p['xyz'],[0],motion,[.5,1.],self.lib)
        request=dict(p,budget=0);result=replay(request,p['xyz'],[0],motion,[.5,1.],self.lib,initial=cold[1],multiplier_seed=cold[3])
        self.verify(request,motion,result);self.assertEqual(result[4][2],0.)
        self.assertGreater(np.max(abs(result[1]-p['xyz'])),.01)

    def test_invalid_seed_or_pin_is_atomic(self):
        p,motion=self.problem();initial=np.array(p['xyz']);cases=[]
        for value in [math.nan,math.inf,17.]:
            guess=initial.copy();guess[0]=value;cases.append((p,guess,np.zeros(2)))
        for value in [-1.,math.nan,math.inf]:cases.append((p,initial,np.array([value,0.])))
        cases.append((p,None,np.zeros(2)));cases.append((p,initial,None))
        pinned=dict(p,inverse=[0.,1.,1.]);guess=initial.copy();guess[0]+=.01;cases.append((pinned,guess,np.zeros(2)))
        for request,guess,seed in cases:
            result=replay(request,p['xyz'],[0],motion,[.5,1.],self.lib,initial=guess,multiplier_seed=seed)
            self.assertEqual(result[0],-1);np.testing.assert_array_equal(result[1],p['xyz'])
            np.testing.assert_array_equal(result[2],123.);np.testing.assert_array_equal(result[3],123.)

    def test_insufficient_work_does_not_publish_numerical_guess(self):
        p,motion=self.problem();request=dict(p,budget=0);guess=np.array(p['xyz'])+np.tile([.15,.02,0.],3)
        result=replay(request,p['xyz'],[0],motion,[.5,1.],self.lib,initial=guess,multiplier_seed=np.zeros(2))
        self.assertNotEqual(result[0],0);np.testing.assert_array_equal(result[1],p['xyz'])
        np.testing.assert_array_equal(result[2],123.);np.testing.assert_array_equal(result[3],123.)

    def test_initial_guess_projects_exact_hold_without_changing_predictor(self):
        p,motion=self.problem();p.update(grip_nodes=[0,1,2],grip_weights=[0.,0.,1.],targets=p['xyz'][6:9])
        guess=np.array(p['xyz'])+np.tile([.15,.02,0.],3)
        result=replay(p,p['xyz'],[0],motion,[.5,1.],self.lib,initial=guess,multiplier_seed=np.zeros(2))
        self.verify(p,motion,result)

    def test_penalty_seed_is_numerical_only_and_invalid_values_are_atomic(self):
        p,motion=self.problem();guess=np.array(p['xyz'])+np.tile([.15,.02,0.],3)
        result=replay(p,p['xyz'],[0],motion,[.5,1.],self.lib,initial=guess,multiplier_seed=np.zeros(2),penalty_seed=1e4)
        self.verify(p,motion,result);self.assertGreaterEqual(result[4][15],1e4)
        for penalty in [0.,math.nan,math.inf,1e13]:
            bad=replay(p,p['xyz'],[0],motion,[.5,1.],self.lib,initial=guess,multiplier_seed=np.zeros(2),penalty_seed=penalty)
            self.assertEqual(bad[0],-1);np.testing.assert_array_equal(bad[1],p['xyz']);np.testing.assert_array_equal(bad[3],123.)

    def test_seeded_api_preserves_actual_caller_fp_modes(self):
        environment.EnvironmentTests.setUpClass();probe=environment.EnvironmentTests.probe
        p,motion=self.problem();guess=np.array(p['xyz'])+np.tile([.15,.02,0.],3);bad=guess.copy();bad[0]=math.nan
        cases=[(p,guess,0,1.),(dict(p,budget=0),guess,1,1.),(p,bad,-1,1.),(p,guess,0,1e4),(p,guess,-1,0.)]
        def call(request,initial,penalty):
            r=replay(request,p['xyz'],[0],motion,[.5,1.],self.lib,initial=initial,multiplier_seed=np.zeros(2),penalty_seed=penalty)
            return (r[0],*(a.tobytes() for a in r[1:]))
        baseline=[call(request,initial,penalty) for request,initial,_,penalty in cases]
        original=(probe.fem_probe_x87(),probe.fem_probe_mxcsr())
        try:
            for cw,mx in environment.EnvironmentTests.contexts(original):
                for index,(request,initial,status,penalty) in enumerate(cases):
                    probe.fem_probe_set_x87(cw);probe.fem_probe_set_mxcsr(mx)
                    result=call(request,initial,penalty);after=(probe.fem_probe_x87(),probe.fem_probe_mxcsr()&~0x3f)
                    probe.fem_probe_set_x87(original[0]);probe.fem_probe_set_mxcsr(original[1])
                    self.assertEqual(after,(cw,mx&~0x3f));self.assertEqual(result[0],status);self.assertEqual(result,baseline[index])
        finally:probe.fem_probe_set_x87(original[0]);probe.fem_probe_set_mxcsr(original[1])

    def test_actual150_extends_captured_equilibrium_inside_original_budget(self):
        root=trajectory.fem.ROOT
        fixture=json.loads((root/'docs/assets/operative-motion150-budget-case-2026-11-05.json').read_text())
        verifier=trajectory.FEMTrajectoryTests().verify
        qualified,history,_=extend(fixture,self.lib,root/'.tools/native/contact_guard.dll',verifier)
        self.assertTrue(qualified,history);self.assertLessEqual(history[-1]['total_iterations'],250)
        self.assertEqual(history[-1]['guard_status'],0)

if __name__=='__main__':unittest.main()
