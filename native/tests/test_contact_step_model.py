"""Independent small unilateral models; none is a physical timestep clearance."""
import ctypes as ct
import math
from pathlib import Path
import unittest
import itertools
from decimal import Decimal,localcontext
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
D=lambda a:(ct.c_double*len(a))(*a)
I=lambda a:(ct.c_int*len(a))(*a)

class ContactStepModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib=ct.CDLL(str(ROOT/'.tools/native/contact_step_probe.dll'))
        cls.fn=cls.lib.contact_step_probe
        cls.fn.argtypes=[ct.c_int,ct.c_int]+[ct.POINTER(ct.c_double)]*5+[ct.c_double,ct.POINTER(ct.c_int),ct.c_int]+[ct.POINTER(ct.c_double)]*2
        cls.fn.restype=ct.c_int

    def run_model(self,h,rows,force,gaps,dual=None,rho=100.,regular=None,budget=12,proposal=False):
        n=len(force); pairs=len(gaps)
        arrays=[D(np.asarray(h).flatten()),D(np.asarray(rows).flatten()),D(force),D(gaps),D(dual if dual is not None else [0.]*pairs)]
        saved=[bytes(a) for a in arrays]; flags=I(regular if regular is not None else [1]*pairs)
        output=D([99.]*n); stats=D([99.]*4)
        fn=self.fn
        if proposal:
            fn=self.lib.contact_step_proposal; fn.argtypes=self.fn.argtypes; fn.restype=ct.c_int
        code=fn(n,pairs,*arrays,rho,flags,budget,output,stats)
        self.assertEqual([bytes(a) for a in arrays],saved)
        self.assertLessEqual(stats[0],max(0,budget))
        if code not in (0,6,7,8): self.assertEqual(list(output),[99.]*n)
        elif code==8: self.assertEqual(stats[2],math.inf)
        else: self.assertLess(stats[2],0.)
        return code,np.array(output),list(stats)

    def test_inactive_plane_activates_and_changes_affine_rhs(self):
        code,d,stats=self.run_model([[1.]],[[1.]],[1.],[.01])
        self.assertEqual(code,0,stats)
        self.assertAlmostEqual(d[0],-2/(101+1e-8),delta=1e-12)
        self.assertLessEqual(abs(d[0]+1-100*max(0.,-.01-d[0])),1e-8)

    def test_active_plane_releases_and_removes_affine_rhs(self):
        code,d,stats=self.run_model([[1.]],[[1.]],[-3.],[-.1],rho=10.)
        self.assertEqual(code,0,stats)
        self.assertAlmostEqual(d[0],3/(1+11e-8),delta=1e-12)

    def test_opposing_shared_constraints_remain_in_the_model(self):
        code,d,stats=self.run_model([[1.]],[[1.],[-1.]],[.3],[-.02,-.01])
        self.assertEqual(code,0,stats)
        self.assertAlmostEqual(d[0],.7/(201+201e-8),delta=1e-12)

    def test_one_contact_can_couple_multiple_free_coordinates(self):
        code,d,stats=self.run_model([[2.,0.],[0.,3.]],[[1.,1.]],[1.,2.],[.01],rho=30.)
        self.assertEqual(code,0,stats)
        expected=np.linalg.solve(np.array([[32.+2e-8,30.],[30.,33.+3e-8]]),[-1.3,-2.3])
        np.testing.assert_allclose(d,expected,atol=1e-12,rtol=0)

    def test_an_ambiguous_newly_active_normal_cannot_be_used(self):
        code,_,stats=self.run_model([[1.]],[[1.]],[1.],[.01],regular=[0])
        self.assertEqual(code,4,stats)

    def test_unavailable_inactive_gradient_is_an_explicit_unmodelled_proposal(self):
        for normal in [1.,math.inf]:
            code,d,stats=self.run_model([[1.]],[[normal]],[1.],[.01],regular=[0],proposal=True)
            self.assertEqual(code,7,stats)
            self.assertAlmostEqual(d[0],-1/(1+1e-8),delta=1e-12)

    def test_unavailable_active_gradient_never_produces_a_direction(self):
        for proposal in [False,True]:
            code,_,stats=self.run_model([[1.]],[[1.]],[1.],[-.01],regular=[0],proposal=proposal)
            self.assertEqual(code,4,stats)

    def test_known_nonfinite_gradient_is_invalid(self):
        code,_,stats=self.run_model([[1.]],[[math.inf]],[1.],[.01],proposal=True)
        self.assertEqual(code,-1,stats)

    def test_negative_overflow_is_provably_inactive_and_unmodelled(self):
        code,d,stats=self.run_model([[1.]],[[1.]],[1.],[1e308],rho=16.,proposal=True)
        self.assertEqual(code,7,stats)
        self.assertAlmostEqual(d[0],-1/(1+1e-8),delta=1e-12)

    def test_positive_overflow_cannot_be_clipped_to_an_inactive_contact(self):
        code,_,stats=self.run_model([[1.]],[[1.]],[1.],[-1e308],rho=16.,proposal=True)
        self.assertEqual(code,2,stats)

    def test_working_set_changes_share_the_factor_budget(self):
        code,_,stats=self.run_model([[1.]],[[1.]],[1.],[.01],budget=1)
        self.assertEqual(code,1,stats); self.assertEqual(stats[0],1.)

    def test_budget_exhaustion_preserves_raw_newton_seed_without_model_certificate(self):
        # The full step crosses an inactive plane and increases the model.
        # A small step on this ray descends, so the physical line search may
        # still use it, with no second search or claimed model convergence.
        code,d,stats=self.run_model([[1.]],[[1.]],[1.],[.01],budget=1,proposal=True)
        self.assertEqual(code,8,stats)
        self.assertAlmostEqual(d[0],-1/(1+1e-8),delta=1e-12)
        self.assertLess(stats[1],1e-5)
        self.assertEqual(stats[0],1.)
        self.assertGreater(d[0]+.5*(1+1e-8)*d[0]**2+50*max(0.,-.01-d[0])**2,0.)

    def test_proposal_zero_budget_has_no_seed_to_publish(self):
        code,_,stats=self.run_model([[1.]],[],[1.],[],budget=0,proposal=True)
        self.assertEqual(code,1,stats)

    def test_zero_budget_is_atomic(self):
        code,_,stats=self.run_model([[1.]],[],[1.],[],budget=0)
        self.assertEqual(code,1,stats); self.assertEqual(stats[0],0.)

    def test_invalid_model_is_atomic(self):
        code,_,_=self.run_model([[1.]],[[1.]],[1.],[.01],rho=math.nan)
        self.assertEqual(code,-1)

    def test_overflowing_force_norm_never_reports_zero_residual(self):
        code,_,stats=self.run_model(np.eye(2),[],[1.7e308,1.7e308],[])
        self.assertNotEqual(code,0); self.assertTrue(math.isinf(stats[1]))

    def test_symmetrizing_finite_large_inertia_does_not_overflow(self):
        code,d,stats=self.run_model([[1e308]],[],[1.],[])
        self.assertEqual(code,0,stats); self.assertTrue(math.isfinite(d[0]))
        self.assertLess(d[0],0.)

    def test_stationary_saddle_is_not_qualified_by_inactive_rows(self):
        code,_,stats=self.run_model([[-1.]],[[1.]],[0.],[10.])
        self.assertNotEqual(code,0,stats)

    def test_indefinite_retry_cannot_reset_the_factor_budget(self):
        code,d,stats=self.run_model([[-.5]],[[1.]],[-1.],[-.1],rho=1.,budget=2)
        self.assertEqual(code,1,stats); self.assertEqual(stats[0],2.)

    def test_released_set_survives_indefinite_damping_retries(self):
        # The active matrix is SPD, but releasing its plane reveals the
        # negative Lagrangian curvature. Repeating the same active-set change
        # at every damping level wastes the aggregate factorization budget.
        code,d,stats=self.run_model([[-10.]],[[14.]],[.02],[-.5],rho=.11)
        self.assertEqual(code,0,stats)
        self.assertAlmostEqual(d[0],.75/(1.56+21.56),delta=1e-12)

    def test_deep_simultaneous_contacts_get_a_coercive_model_in_budget(self):
        # Exact initial local coefficients of the existing plane plus finite
        # tool-vertex physical regression. Contact curvature makes H_L
        # indefinite; only12factor attempts are available for all retries.
        h=np.diag([-4.5,-21.,-4.5]); rows=[[-10.,-10.,-10.],[0.,10.,0.]]
        code,d,stats=self.run_model(h,rows,[0.,0.,0.],[-.25,-.75],rho=.11)
        self.assertEqual(code,0,stats)
        self.assertLess(np.dot([.275,-.55,.275],d),0.)

    def test_proposal_release_reports_descent_without_claiming_model_optimum(self):
        code,d,stats=self.run_model([[1.]],[[1.]],[-3.],[-.1],rho=10.,proposal=True)
        self.assertEqual(code,6,stats)
        # Initial active RHS is -force + J*(dual-rho*g) = 3+1.
        self.assertAlmostEqual(d[0],4/(11+11e-8),delta=1e-12)
        self.assertGreater(abs(d[0]-3.),1.)

    def test_proposal_still_models_a_new_activation(self):
        code,d,stats=self.run_model([[1.]],[[1.]],[1.],[.01],proposal=True)
        self.assertEqual(code,0,stats)
        self.assertAlmostEqual(d[0],-2/(101+1e-8),delta=1e-12)

    def test_proposal_preserves_gradual_damping_for_deep_contacts(self):
        h=np.diag([-4.5,-21.,-4.5]); rows=np.array([[-10.,-10.,-10.],[0.,10.,0.]])
        code,d,stats=self.run_model(h,rows,[0.,0.,0.],[-.25,-.75],rho=.11,proposal=True)
        self.assertIn(code,(0,6),stats)
        base=h+.11*rows.T@rows; scale=np.maximum(1.,np.abs(np.diag(base)))
        expected=np.linalg.solve(base+np.diag(10*scale),rows.T@np.array([.0275,.0825]))
        np.testing.assert_allclose(d,expected,atol=1e-12,rtol=0)

    def test_small_convex_models_match_exhaustive_active_set_oracle(self):
        # Enumerate every set independently rather than reproducing the
        # production working-set iteration or accepting its reported residual.
        rng=np.random.default_rng(64129)
        for case in range(40):
            a=rng.normal(size=(2,2)); h=a.T@a+np.eye(2)
            rows=rng.normal(size=(3,2)); force=rng.normal(size=2)
            gaps=rng.uniform(-.2,.2,3); dual=rng.uniform(0,.1,3); rho=30.
            intercept=dual-rho*gaps; initial=intercept>0
            scale=np.maximum(1.,np.abs(np.diag(h+rho*rows[initial].T@rows[initial])))
            expected=None
            for bits in itertools.product([False,True],repeat=3):
                active=np.asarray(bits)
                matrix=h+np.diag(1e-8*scale)+rho*rows[active].T@rows[active]
                rhs=-force+rows[active].T@intercept[active]
                candidate=np.linalg.solve(matrix,rhs)
                if np.array_equal(intercept-rho*rows@candidate>0,active): expected=candidate; break
            self.assertIsNotNone(expected,case)
            code,d,stats=self.run_model(h,rows,force,gaps,dual=dual,rho=rho)
            self.assertEqual(code,0,(case,stats))
            np.testing.assert_allclose(d,expected,atol=1e-9,rtol=0,err_msg=str(case))

    def test_reported_change_is_an_outward_upper_bound(self):
        with localcontext() as context:
            context.prec=80
            dec=Decimal.from_float
            for h in [1.,1.3,2.,7.]:
                for force in [.1,.7,1.,3.]:
                    code,d,stats=self.run_model([[h]],[],[force],[])
                    self.assertEqual(code,0,stats)
                    diagonal=1e-8*max(1.,h)
                    exact=dec(force)*dec(float(d[0]))+(dec(h)+dec(diagonal))*dec(float(d[0]))**2/2
                    self.assertGreaterEqual(dec(stats[2]),exact,(h,force,stats[2],str(exact)))
