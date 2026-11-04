"""Independent original KKT for simultaneous retained contact and exact grasps."""
import ctypes as ct
import itertools
import json
import unittest
import numpy as np
import test_membrane_fem as fem
import test_membrane_grasp as grasp
from replay_fem_contact import replay


class FEMContactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fem.MembraneFEMTests.setUpClass();grasp.GraspTests.setUpClass()
        cls.base = fem.MembraneFEMTests()
        cls.solve = cls.base.lib.membrane_fem_solve_contact
        cls.solve.argtypes = [ct.c_int,fem.D,fem.D,ct.c_int,fem.I,fem.D,fem.D,
            ct.c_double,ct.c_double,ct.c_double,ct.c_int,ct.c_double,ct.c_double,ct.c_double,
            ct.c_int,fem.I,fem.D,fem.D,fem.D,ct.c_int,fem.I,fem.D,ct.c_int,fem.D,fem.D,fem.D]
        cls.solve.restype = ct.c_int

    def run_case(self, grips=(), targets=None, bodies=None, shape=None, budget=250, predicted=None, specimen=None, inverse=None, grasp_nodes=None, grasp_weights=None):
        rest,nodes,basis,areas = self.base.data() if specimen is None else specimen
        predicted = rest if predicted is None else np.array(predicted,dtype=np.float64)
        inverse = np.ones(len(rest)) if inverse is None else np.array(inverse)
        face_nodes = nodes.copy();shape = np.tile(np.eye(3),(len(nodes),1,1)) if shape is None else np.array(shape).reshape(-1,3,3)
        bodies = np.array([[.3,.05,.3,.3,.05,.3,.1]]) if bodies is None else np.array(bodies).reshape(-1,7)
        grip_nodes = np.array([[i,i,i] for i in grips] if grasp_nodes is None else grasp_nodes, dtype=np.int32).reshape(-1,3)
        weights = np.array([[1.,0.,0.] for _ in grips] if grasp_weights is None else grasp_weights).reshape(-1,3)
        targets = np.array([w@predicted[ids] for ids,w in zip(grip_nodes,weights)]).reshape(-1,3) if targets is None else np.array(targets)
        reaction = np.full((len(grip_nodes),3),123.);dual = np.full(len(bodies)*len(face_nodes),123.);stats = np.full(16,123.)
        x = predicted.copy()
        doubles = [np.ascontiguousarray(a,dtype=np.float64) for a in (inverse,basis,areas,weights,targets,shape,bodies)]
        inverse,basis,areas,weights,targets,shape,bodies = doubles
        d = lambda a:a.ctypes.data_as(fem.D)
        i = lambda a:a.ctypes.data_as(fem.I)
        code = self.solve(len(x),d(x),d(inverse),len(areas),i(nodes),d(basis),d(areas),2.,3.,1/60,budget,1e-8,1e-9,1e-11,
                          len(grip_nodes),i(grip_nodes),d(weights),d(targets),d(reaction),len(face_nodes),i(face_nodes),d(shape),
                          len(bodies),d(bodies),d(dual),d(stats))
        return code,x,reaction,dual,stats,(predicted,nodes,basis,areas,inverse,grips,targets,bodies,shape,grip_nodes,weights)

    @staticmethod
    def closest(body,triangle):
        # Independent NumPy active-simplex enumeration, no native query oracle.
        best = None;u = body[3:6]-body[:3]
        for count in (1,2,3):
            for ids in itertools.combinations(range(3),count):
                for axis in (0.,1.,None):
                    columns = [triangle[j]-triangle[ids[0]] for j in ids[1:]]
                    origin = triangle[ids[0]]-body[:3]
                    if axis is None:columns.append(-u)
                    else:origin -= axis*u
                    z = np.linalg.lstsq(np.array(columns).T,-origin,rcond=None)[0] if columns else np.array([])
                    w = np.zeros(3);w[list(ids[1:])] = z[:count-1];w[ids[0]] = 1.-sum(z[:count-1])
                    t = z[-1] if axis is None else axis
                    if np.min(w)<-1e-12 or t < -1e-12 or t > 1.+1e-12:continue
                    w = np.maximum(w,0.);w /= sum(w);t = np.clip(t,0.,1.)
                    delta = w@triangle-(body[:3]+t*u);squared = float(delta@delta)
                    if best is None or squared<best[0]:best = squared,w,delta
        assert best is not None
        return best

    def verify(self, answer):
        code,x,reaction,dual,stats,data = answer
        self.assertEqual(code,0,msg=str(stats))
        predicted,nodes,basis,areas,inverse,grips,targets,bodies,shape,grip_nodes,grip_weights = data
        g = self.base.call_evaluate(x,nodes,basis,areas)[2]
        free = inverse>0.;g[free] += (x[free]-predicted[free])/(inverse[free,None]*(1/60)**2)
        np.testing.assert_array_equal(x[~free],predicted[~free])
        for slot,(ids,w) in enumerate(zip(grip_nodes,grip_weights)):
            np.testing.assert_allclose(w@x[ids],targets[slot],atol=1e-9,rtol=0.)
            for node,weight in zip(ids,w):g[node] += weight*reaction[slot]
        for p,u in enumerate(dual):
            body = bodies[p%len(bodies)];face = p//len(bodies);ids = nodes[face]
            self.assertGreaterEqual(u,0.)
            normalized = shape[face]/shape[face].sum(axis=1)[:,None]
            squared,w,delta = self.closest(body,normalized@x[ids])
            self.assertGreaterEqual(np.sqrt(squared)-body[6],-1e-9)
            c = squared/body[6]**2-1.
            self.assertLessEqual(abs(u*c),1e-11)
            row = normalized.T@(2*w[:,None]*delta)
            g[ids] -= u*row/body[6]**2
        self.assertLessEqual(np.max(np.abs(g[free])),1e-8)
        return x

    def test_unheld_body_reaction(self):self.verify(self.run_case())

    def test_finite_micro_inertia_with_active_and_inactive_contact(self):
        for bodies in (None, [[.3,1.,.3,.3,1.,.3,.1]]):
            with self.subTest(active=bodies is None):
                answer=self.run_case(inverse=[1e13,0.,0.],bodies=bodies)
                self.verify(answer)
                if bodies is None:self.assertGreater(float(np.max(answer[3])),0.)

    def test_finite_micro_inertia_with_exact_hold_and_contact(self):
        expected=self.verify(self.run_case((0,)))
        for inverse in [1e6,1e12,1e13]:
            with self.subTest(inverse=inverse):
                actual=self.verify(self.run_case((0,),inverse=[inverse,1.,1.]))
                # A nodally fixed coordinate's inertia cannot change the
                # minimizer of the remaining constrained material coordinates.
                np.testing.assert_allclose(actual,expected,atol=2e-9,rtol=0.)

    def test_unrepresentable_inertia_rejects_without_contact_publication(self):
        for inverse in [-1.,float('nan'),float('inf'),1e-320]:
            with self.subTest(inverse=inverse):
                code,x,reaction,dual,_,data=self.run_case((0,),inverse=[inverse,1.,1.])
                self.assertEqual(code,-1)
                np.testing.assert_array_equal(x,data[0]);np.testing.assert_array_equal(reaction,123.);np.testing.assert_array_equal(dual,123.)

    def test_one_and_two_hands_with_contact(self):
        for grips in ((0,),(0,1)):self.verify(self.run_case(grips))

    def test_two_bodies_and_held_corner(self):
        self.verify(self.run_case((0,),bodies=[[.25,.05,.25,.25,.05,.25,.1],[.5,.07,.25,.5,.07,.25,.1]]))

    def test_empty_parent_material_is_not_constrained(self):
        shape = [[.8,.1,.1],[.3,.6,.1],[.3,.1,.6]]
        answer = self.run_case(shape=shape,bodies=[[.82,.03,.08,.82,.03,.08,.1]])
        x = self.verify(answer)
        np.testing.assert_array_equal(x,answer[-1][0]);self.assertTrue(np.all(answer[3]==0.))

    def test_no_body_preserves_old_grasp_result(self):
        predicted = [[0.,0.,0.],[1.06,.03,0.],[0.,0.,1.]]
        answer = self.run_case((0,),bodies=[],predicted=predicted)
        self.verify(answer)
        p,n,b,a,inverse,_,targets,_,_,_,_ = answer[-1]
        old = grasp.GraspTests().run_grasp(p,inverse,n,b,a,[[0,0,0]],[[1.,0.,0.]],targets,budget=250)
        self.assertEqual(old[0],0)
        for actual,expected in zip(answer[1:3],old[1:3]):np.testing.assert_array_equal(actual,expected)
        np.testing.assert_array_equal(answer[4][:12],old[3])
        self.assertTrue(np.all(np.isfinite(answer[4])))

    def test_finite_capsule_endpoint(self):
        self.verify(self.run_case((0,),bodies=[[.3,.05,.3,.3,.25,.3,.1]]))

    def test_interior_material_hold_with_partially_fixed_controls(self):
        self.verify(self.run_case(inverse=[0.,1.,2.],grasp_nodes=[[0,1,2]],grasp_weights=[[.7,.2,.1]]))

    def test_actual_curved_retained_two_hands_two_bodies(self):
        request = json.loads((fem.ROOT/'native/tests/fixtures/curved_coupled_two_hands.json').read_text(encoding='utf-8'))['request']
        self.verify_curved_request(request,replay(request,fem.ROOT/'.tools/native/membrane_fem.dll'))

    def verify_curved_request(self,request,result):
        status,x,reaction,dual,stats = result
        self.assertEqual(status,0,msg=str(stats))
        q = x.reshape(-1,3);predicted = np.array(request['xyz']).reshape(-1,3)
        inverse = np.array(request['inverse']);free = inverse>0.
        np.testing.assert_array_equal(q[~free],predicted[~free])
        force = np.zeros_like(q)
        for ids,basis,area in zip(np.array(request['nodes']).reshape(-1,3),np.array(request['gradients']).reshape(-1,2,3),request['areas']):
            f = q[ids].T@basis.T;c = f.T@f;log_j = .5*np.linalg.slogdet(c)[1]
            p = request['mu']*f+(request['lambda']*log_j-request['mu'])*f@np.linalg.inv(c)
            force[ids] += (area*p@basis).T
        force[free] += (q[free]-predicted[free])/(inverse[free,None]*request['dt']**2)
        for ids,w,target,r in zip(np.array(request['grip_nodes']).reshape(-1,3),np.array(request['grip_weights']).reshape(-1,3),np.array(request['targets']).reshape(-1,3),reaction.reshape(-1,3)):
            w = w/sum(w);np.testing.assert_allclose(w@q[ids],target,atol=1e-9,rtol=0.)
            for node,weight in zip(ids,w):force[node] += weight*r
        bodies = np.array(request['capsules']).reshape(-1,7)
        for ids,shape,multipliers in zip(np.array(request['face_nodes']).reshape(-1,3),np.array(request['face_weights']).reshape(-1,3,3),dual.reshape(-1,len(bodies))):
            shape = shape/shape.sum(axis=1)[:,None]
            for body,u in zip(bodies,multipliers):
                self.assertGreaterEqual(u,0.)
                sq,w,delta = self.closest(body,shape@q[ids])
                self.assertGreaterEqual(np.sqrt(sq)-body[6],-1e-9)
                self.assertLessEqual(abs(u*(sq/body[6]**2-1.)),1e-11)
                force[ids] -= u*(shape.T@(2*w[:,None]*delta))/body[6]**2
        self.assertLessEqual(np.max(np.abs(force[free])),1e-8)

    def test_actual_curved_under_extended_x87(self):
        probe = ct.CDLL(str(fem.ROOT/'.tools/native/fp_environment_probe.dll'))
        probe.fem_probe_x87.restype = ct.c_uint;probe.fem_probe_set_x87.argtypes = [ct.c_uint]
        saved = probe.fem_probe_x87()
        request = json.loads((fem.ROOT/'native/tests/fixtures/curved_coupled_two_hands.json').read_text(encoding='utf-8'))['request']
        try:
            probe.fem_probe_set_x87((saved&~0xf00)|0x300)
            result = replay(request,fem.ROOT/'.tools/native/membrane_fem.dll')
        finally:probe.fem_probe_set_x87(saved)
        self.assertEqual(probe.fem_probe_x87(),saved)
        self.verify_curved_request(request,result)

    def test_redundant_contact_rows_remain_nonnegative_and_balanced(self):
        body = [.3,.05,.3,.3,.05,.3,.1]
        answer = self.run_case((0,),bodies=[body,body]);self.verify(answer)
        self.assertTrue(np.all(answer[3]>0.))

    def test_inactive_contact_cannot_hide_negative_free_tangent(self):
        rest = np.array([[0.,0.,0.],[-1.,0.,-1.],[1.,0.,-1.],[1.,0.,1.],[-1.,0.,1.]])
        nodes = np.array([[0,2,1],[0,3,2],[0,4,3],[0,1,4]],dtype=np.int32)
        basis,areas = self.base.reference_cells(rest,nodes)
        answer = self.run_case(specimen=(rest,nodes,basis,areas),predicted=rest*.5,inverse=[1e10,0.,0.,0.,0.],bodies=[[.1,2.,.1,.1,2.,.1,.1]])
        self.assertEqual(answer[0],3)
        np.testing.assert_array_equal(answer[1],answer[-1][0]);self.assertTrue(np.all(answer[3]==123.))

    def test_invalid_geometry_is_atomic(self):
        for answer in (self.run_case(shape=np.eye(3)*2),self.run_case(bodies=[[0.,0.,0.,0.,0.,0.,0.]]),self.run_case(bodies=[[np.nan,0.,0.,0.,0.,0.,.1]])):
            self.assertEqual(answer[0],-1)
            np.testing.assert_array_equal(answer[1],answer[-1][0]);self.assertTrue(np.all(answer[2]==123.));self.assertTrue(np.all(answer[3]==123.))

    def test_budget_and_impossible_targets_are_atomic(self):
        for answer in (self.run_case(budget=0),self.run_case((0,),targets=[[.3,0.,.3]],budget=5),self.run_case((0,1,2),budget=5)):
            self.assertNotEqual(answer[0],0)
            np.testing.assert_array_equal(answer[1],answer[-1][0])
            self.assertTrue(np.all(answer[2]==123.));self.assertTrue(np.all(answer[3]==123.))


if __name__=='__main__':unittest.main()
