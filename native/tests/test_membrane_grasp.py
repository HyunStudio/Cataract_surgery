"""Exact embedded attachment constraints: independent KKT and atomicity gates."""
import ctypes as ct
import unittest
import numpy as np
import test_membrane_fem as reference


class GraspTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        reference.MembraneFEMTests.setUpClass()
        cls.base = reference.MembraneFEMTests()
        cls.solve = cls.base.lib.membrane_fem_solve_grasp
        cls.solve.argtypes = [ct.c_int, reference.D, reference.D, ct.c_int, reference.I, reference.D, reference.D,
                              ct.c_double, ct.c_double, ct.c_double, ct.c_int, ct.c_double, ct.c_double,
                              ct.c_int, reference.I, reference.D, reference.D, reference.D, reference.D]
        cls.solve.restype = ct.c_int

    def run_grasp(self, predicted, inverse, nodes, basis, areas, grasp_nodes, weights, targets, budget=100):
        x = np.ascontiguousarray(predicted, dtype=np.float64).copy()
        inverse = np.ascontiguousarray(inverse, dtype=np.float64)
        nodes = np.ascontiguousarray(nodes, dtype=np.int32)
        basis = np.ascontiguousarray(basis, dtype=np.float64)
        areas = np.ascontiguousarray(areas, dtype=np.float64)
        grasp_nodes = np.ascontiguousarray(grasp_nodes, dtype=np.int32).reshape(-1, 3)
        weights = np.ascontiguousarray(weights, dtype=np.float64).reshape(-1, 3)
        targets = np.ascontiguousarray(targets, dtype=np.float64).reshape(-1, 3)
        reaction = np.full(targets.shape, 123.)
        stats = np.zeros(12)
        code = self.solve(len(x), x.ctypes.data_as(reference.D), inverse.ctypes.data_as(reference.D), len(areas),
                          nodes.ctypes.data_as(reference.I), basis.ctypes.data_as(reference.D), areas.ctypes.data_as(reference.D),
                          2., 3., 1/60, budget, 1e-8, 1e-9, len(targets), grasp_nodes.ctypes.data_as(reference.I),
                          weights.ctypes.data_as(reference.D), targets.ctypes.data_as(reference.D),
                          reaction.ctypes.data_as(reference.D), stats.ctypes.data_as(reference.D))
        return code, x, reaction, stats

    def verify_kkt(self, predicted, inverse, nodes, basis, areas, grips, weights, targets, result, reaction):
        g = self.base.call_evaluate(result, nodes, basis, areas)[2]
        inverse = np.array(inverse)
        for i in range(len(inverse)):
            if inverse[i]:g[i] += (result[i]-predicted[i])/(inverse[i]*(1/60)**2)
        for ids, row, target, dual in zip(grips, weights, targets, reaction):
            np.testing.assert_allclose(row@result[ids], target, atol=1e-9, rtol=0.)
            for node, value in zip(ids, row):g[node] += value*dual
        self.assertLessEqual(np.max(np.abs(g[inverse>0])), 1e-8)
        np.testing.assert_array_equal(result[inverse==0], predicted[inverse==0])

    def test_interior_material_point_and_reaction(self):
        x, nodes, basis, areas = self.base.data()
        grips = np.array([[0, 1, 2]], dtype=np.int32)
        weights = np.array([[.2, .3, .5]])
        targets = weights@x + [0., .005, 0.]
        inverse = [0., 4., 7.]
        code, result, reaction, stats = self.run_grasp(x, inverse, nodes, basis, areas, grips, weights, targets)
        self.assertEqual(code, 0, stats)
        self.verify_kkt(x, inverse, nodes, basis, areas, grips, weights, targets, result, reaction)
        self.assertGreater(np.linalg.norm(reaction), 0.)

    def test_finite_micro_inertia_keeps_exact_attachment(self):
        x,nodes,basis,areas=self.base.data()
        grips=np.array([[0,1,2]],dtype=np.int32);weights=np.array([[.2,.3,.5]])
        targets=weights@x+[0.,.005,0.];inverse=[0.,1e13,7.]
        code,result,reaction,stats=self.run_grasp(x,inverse,nodes,basis,areas,grips,weights,targets)
        self.assertEqual(code,0,stats)
        self.verify_kkt(x,inverse,nodes,basis,areas,grips,weights,targets,result,reaction)

    def test_two_distinct_grips_on_shared_cells(self):
        x = np.array([[-1., 0., -1.], [1., 0., -1.], [1., 0., 1.], [-1., 0., 1.]])
        nodes = np.array([[0, 1, 2], [3, 0, 2]], np.int32)
        basis, areas = self.base.reference_cells(x, nodes)
        grips = np.array([[0, 1, 2], [0, 2, 3]], np.int32)
        weights = np.array([[.2, .3, .5], [.2, .4, .4]])
        targets = np.array([row@x[ids] for row, ids in zip(weights, grips)]) + [[0., .005, 0.], [.001, .003, 0.]]
        inverse = [0., 2., 3., 4.]
        code, result, reaction, stats = self.run_grasp(x, inverse, nodes, basis, areas, grips, weights, targets)
        self.assertEqual(code, 0, stats)
        self.verify_kkt(x, inverse, nodes, basis, areas, grips, weights, targets, result, reaction)

    def test_nodal_hold_with_repeated_zero_weight_slots(self):
        x, nodes, basis, areas = self.base.data()
        grips = np.array([[1, 1, 1]], np.int32);weights = np.array([[1., 0., 0.]])
        targets = np.array([[1., .005, 0.]])
        code, result, reaction, stats = self.run_grasp(x, [0., 4., 7.], nodes, basis, areas, grips, weights, targets)
        self.assertEqual(code, 0, stats)
        self.verify_kkt(x, [0., 4., 7.], nodes, basis, areas, grips, weights, targets, result, reaction)

    def test_invalid_rank_and_exhaustion_are_atomic(self):
        x, nodes, basis, areas = self.base.data()
        grips = np.array([[0, 1, 2]], np.int32);weights = np.array([[.2, .3, .5]])
        targets = weights@x + [0., .005, 0.]
        code, result, reaction, _ = self.run_grasp(x, [0., 4., 7.], nodes, basis, areas, grips, weights, targets, budget=0)
        self.assertEqual(code, 1)
        np.testing.assert_array_equal(result, x);np.testing.assert_array_equal(reaction, 123.)
        for g, w, target in [(np.repeat(grips, 2, axis=0), np.repeat(weights, 2, axis=0), np.repeat(targets, 2, axis=0)),
                              (np.array([[0, 1, 9]]), weights, targets),
                              (grips, np.array([[-.2, .3, .9]]), targets),
                              (grips, weights*2, targets),
                              (grips, weights, targets*np.nan)]:
            code, result, reaction, _ = self.run_grasp(x, [0., 4., 7.], nodes, basis, areas, g, w, target)
            self.assertNotEqual(code, 0)
            np.testing.assert_array_equal(result, x);np.testing.assert_array_equal(reaction, 123.)

    def test_zero_grips_preserve_existing_unconstrained_contract(self):
        x, nodes, basis, areas = self.base.data();x[1, 0]+=.03
        old = self.base.run_solve(x, [0., 4., 7.], nodes, basis, areas)
        code, result, _, stats = self.run_grasp(x, [0., 4., 7.], nodes, basis, areas, [], [], [])
        self.assertEqual(code, old[0]);np.testing.assert_array_equal(result, old[1]);np.testing.assert_array_equal(stats[:8], old[2])

    def test_constraints_stabilize_only_the_constrained_curvature(self):
        rest = np.array([[0., 0., 0.], [-1., 0., -1.], [1., 0., -1.], [1., 0., 1.], [-1., 0., 1.]])
        nodes = np.array([[0, 2, 1], [0, 3, 2], [0, 4, 3], [0, 1, 4]], np.int32)
        basis, areas = self.base.reference_cells(rest, nodes)
        x = rest*.5
        code, result, reaction, stats = self.run_grasp(x, [1e10, 0., 0., 0., 0.], nodes, basis, areas, [[0, 0, 0]], [[1., 0., 0.]], [[0., 0., 0.]])
        self.assertEqual(code, 0, stats)
        np.testing.assert_array_equal(result, x)
        self.assertLessEqual(np.max(np.abs(reaction)), 1e-8)

    def test_unheld_negative_tangent_cannot_be_hidden_by_augmentation(self):
        # Two independent compressed patches: holding the first center must not
        # turn the second patch's unstable free tangent into a successful solve.
        patch = np.array([[0., 0., 0.], [-1., 0., -1.], [1., 0., -1.], [1., 0., 1.], [-1., 0., 1.]])
        rest = np.vstack([patch, patch + [3., 0., 0.]])
        first = np.array([[0, 2, 1], [0, 3, 2], [0, 4, 3], [0, 1, 4]], np.int32)
        nodes = np.vstack([first, first+5])
        basis, areas = self.base.reference_cells(rest, nodes)
        x = rest.copy();x[:5] *= .5;x[5:] = (x[5:]-[3., 0., 0.])*.5+[3., 0., 0.]
        code, result, reaction, _ = self.run_grasp(x, [1e10, 0., 0., 0., 0., 1e10, 0., 0., 0., 0.], nodes, basis, areas,
                                                   [[0, 0, 0]], [[1., 0., 0.]], [[0., 0., 0.]])
        self.assertNotEqual(code, 0)
        np.testing.assert_array_equal(result, x);np.testing.assert_array_equal(reaction, 123.)


if __name__ == '__main__':
    unittest.main()
