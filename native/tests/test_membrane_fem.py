"""Embedded membrane mechanics: independent derivative and implicit-solve gates."""
import ctypes as ct
from decimal import Decimal, localcontext
import math
import json
from pathlib import Path
import unittest
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
D = ct.POINTER(ct.c_double)
I = ct.POINTER(ct.c_int)


class MembraneFEMTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib = ct.CDLL(str(ROOT / '.tools/native/membrane_fem.dll'))
        cls.evaluate = cls.lib.membrane_fem_evaluate
        cls.evaluate.argtypes = [ct.c_int, D, ct.c_int, I, D, D, ct.c_double, ct.c_double, D, D, D]
        cls.evaluate.restype = ct.c_int
        cls.solve = cls.lib.membrane_fem_solve
        cls.solve.argtypes = [ct.c_int, D, D, ct.c_int, I, D, D, ct.c_double, ct.c_double,
                              ct.c_double, ct.c_int, ct.c_double, D]
        cls.solve.restype = ct.c_int

    def data(self):
        points = np.array([[0., 0., 0.], [1., 0., 0.], [0., 0., 1.]])
        # Reference tangent axes X,Z; order A,B,C, both gradients sum to zero.
        nodes = np.array([[0, 1, 2]], dtype=np.int32)
        gradients = np.array([[[-1., 1., 0.], [-1., 0., 1.]]])
        return points, nodes, gradients, np.array([.5])

    def call_evaluate(self, points, nodes, gradients, areas, mu=2., lam=3.):
        x = np.ascontiguousarray(points, dtype=np.float64)
        nodes = np.ascontiguousarray(nodes, dtype=np.int32)
        gradients = np.ascontiguousarray(gradients, dtype=np.float64)
        areas = np.ascontiguousarray(areas, dtype=np.float64)
        energy = ct.c_double(123.)
        force = np.full(x.size, 123.)
        blocks = np.full((len(areas), 9, 9), 123.)
        code = self.evaluate(len(x), x.ctypes.data_as(D), len(areas), nodes.ctypes.data_as(I),
                             gradients.ctypes.data_as(D), areas.ctypes.data_as(D), mu, lam,
                             ct.byref(energy), force.ctypes.data_as(D), blocks.ctypes.data_as(D))
        return code, energy.value, force.reshape(x.shape), blocks

    @staticmethod
    def oracle(x, nodes, gradients, areas, mu=2., lam=3.):
        total = 0.
        for ids, basis, area in zip(nodes, gradients, areas):
            f = x[ids].T @ basis.T
            c = f.T @ f
            sign, determinant_log = np.linalg.slogdet(c)
            if sign <= 0:
                return math.inf
            logarithm = .5 * determinant_log
            total += area * (.5 * mu * (np.trace(c) - 2 - 2 * logarithm) + .5 * lam * logarithm**2)
        return total

    def test_rest_objectivity_and_exact_hessian(self):
        x, nodes, basis, areas = self.data()
        code, energy, gradient, hessian = self.call_evaluate(x, nodes, basis, areas)
        self.assertEqual(code, 0)
        self.assertLess(abs(energy), 1e-13)
        self.assertLess(np.max(np.abs(gradient)), 1e-13)
        x[1] = [1.12, .08, .04]
        x[2] = [.09, -.03, .91]
        code, energy, gradient, hessian = self.call_evaluate(x, nodes, basis, areas)
        self.assertEqual(code, 0)
        self.assertAlmostEqual(energy, self.oracle(x, nodes, basis, areas), places=13)
        finite_hessian = np.zeros((9, 9))
        for k in range(9):
            plus, minus = x.copy(), x.copy()
            plus.flat[k] += 1e-6
            minus.flat[k] -= 1e-6
            finite_gradient = (self.oracle(plus, nodes, basis, areas) - self.oracle(minus, nodes, basis, areas)) / 2e-6
            self.assertAlmostEqual(gradient.flat[k], finite_gradient, places=8)
            finite_hessian[:, k] = (self.call_evaluate(plus, nodes, basis, areas)[2].ravel()
                                    - self.call_evaluate(minus, nodes, basis, areas)[2].ravel()) / 2e-6
        np.testing.assert_allclose(hessian[0], finite_hessian, rtol=2e-7, atol=2e-8)
        np.testing.assert_allclose(hessian[0], hessian[0].T, rtol=1e-12, atol=1e-12)
        a, b = .63, -.37
        ry = np.array([[math.cos(a), 0, math.sin(a)], [0, 1, 0], [-math.sin(a), 0, math.cos(a)]])
        rx = np.array([[1, 0, 0], [0, math.cos(b), -math.sin(b)], [0, math.sin(b), math.cos(b)]])
        rotation = rx @ ry
        transformed = self.call_evaluate(x @ rotation.T + [.2, -.3, .1], nodes, basis, areas)
        self.assertEqual(transformed[0], 0)
        self.assertAlmostEqual(transformed[1], energy, places=12)
        np.testing.assert_allclose(transformed[2], gradient @ rotation.T, atol=2e-12)

    def run_solve(self, predicted, inverse, nodes, basis, areas, dt=1/60, budget=100, tol=1e-8, mu=2., lam=3.):
        x = np.ascontiguousarray(predicted, dtype=np.float64).copy()
        inverse = np.ascontiguousarray(inverse, dtype=np.float64)
        nodes = np.ascontiguousarray(nodes, dtype=np.int32)
        basis = np.ascontiguousarray(basis, dtype=np.float64)
        areas = np.ascontiguousarray(areas, dtype=np.float64)
        stats = np.zeros(8)
        code = self.solve(len(x), x.ctypes.data_as(D), inverse.ctypes.data_as(D), len(areas),
                          nodes.ctypes.data_as(I), basis.ctypes.data_as(D), areas.ctypes.data_as(D),
                          mu, lam, dt, budget, tol, stats.ctypes.data_as(D))
        return code, x, stats

    def test_curved_godot_reference_and_implicit_step(self):
        fixture = json.loads((ROOT/'native/tests/fixtures/embedded_membrane_reference.json').read_text())
        x = np.array(fixture['xyz']).reshape(-1, 3)
        nodes = np.array([cell['nodes'] for cell in fixture['cells']], dtype=np.int32)
        basis = np.array([cell['gradients'] for cell in fixture['cells']]).reshape(-1, 2, 3)
        areas = np.array([cell['area'] for cell in fixture['cells']])
        code, energy, gradient, _ = self.call_evaluate(x, nodes, basis, areas)
        self.assertEqual(code, 0)
        self.assertAlmostEqual(energy, fixture['energy'], places=11)
        np.testing.assert_allclose(gradient.ravel(), fixture['gradient'], atol=2e-11, rtol=2e-10)
        predicted = np.array(fixture['rest']).reshape(-1, 3)
        predicted[0, 1] += .0005
        inverse = 1/np.array(fixture['mass'])
        self.assertIsInstance(fixture['fixed'], list)
        self.assertEqual(len(fixture['fixed']), len(x))
        self.assertEqual(fixture['fixed'].count(1), 36)
        inverse[np.array(fixture['fixed'], dtype=bool)] = 0.
        for stiffness in [2., 1e4]:
            code, result, stats = self.run_solve(predicted, inverse, nodes, basis, areas, mu=stiffness, lam=1.5*stiffness)
            self.assertEqual(code, 0, stats)
            independent = np.zeros_like(result)
            for ids, shape, area in zip(nodes, basis, areas):
                f = result[ids].T @ shape.T
                c = f.T @ f
                log_j = .5*np.linalg.slogdet(c)[1]
                p = stiffness*f + (1.5*stiffness*log_j-stiffness)*f@np.linalg.inv(c)
                independent[ids] += (area*p@shape).T
            for i, weight in enumerate(inverse):
                if weight:independent[i] += (result[i]-predicted[i])/(weight*(1/60)**2)
            self.assertLessEqual(np.max(np.abs(independent[inverse>0])), 1e-8)
            np.testing.assert_array_equal(result[inverse==0], predicted[inverse==0])

    @staticmethod
    def reference_cells(rest, nodes):
        bases, areas = [], []
        for ids in nodes:
            a, b, c = rest[ids]
            first, last = b-a, c-a
            e1 = first / np.linalg.norm(first)
            normal = np.cross(first, last)
            areas.append(np.linalg.norm(normal) / 2)
            e2 = np.cross(normal / np.linalg.norm(normal), e1)
            dm = np.array([[np.dot(first, e1), np.dot(last, e1)],
                           [np.dot(first, e2), np.dot(last, e2)]])
            bases.append(np.linalg.inv(dm).T @ np.array([[-1., 1., 0.], [-1., 0., 1.]]))
        return np.array(bases), np.array(areas)

    def test_shared_nodes_and_permuted_cells(self):
        rest = np.array([[-1., 0., -1.], [1., 0., -1.], [1., 0., 1.], [-1., 0., 1.]])
        nodes = np.array([[0, 1, 2], [3, 0, 2]], dtype=np.int32)
        basis, areas = self.reference_cells(rest, nodes)
        x = rest.copy()
        x[1] += [.04, .07, -.02]
        x[2] += [-.03, -.02, .06]
        code, energy, gradient, blocks = self.call_evaluate(x, nodes, basis, areas)
        self.assertEqual(code, 0)
        self.assertAlmostEqual(energy, self.oracle(x, nodes, basis, areas), places=12)
        assembled = np.zeros((12, 12))
        for ids, block in zip(nodes, blocks):
            coordinates = (ids[:, None]*3 + np.arange(3)).ravel()
            assembled[np.ix_(coordinates, coordinates)] += block
        for k in range(12):
            plus, minus = x.copy(), x.copy()
            plus.flat[k] += 1e-6
            minus.flat[k] -= 1e-6
            finite_g = (self.oracle(plus, nodes, basis, areas)-self.oracle(minus, nodes, basis, areas))/2e-6
            self.assertAlmostEqual(finite_g, gradient.flat[k], places=8)
            finite_h = (self.call_evaluate(plus, nodes, basis, areas)[2].ravel()
                        - self.call_evaluate(minus, nodes, basis, areas)[2].ravel())/2e-6
            np.testing.assert_allclose(assembled[:, k], finite_h, rtol=2e-7, atol=2e-8)
        code, result, stats = self.run_solve(x, [0., 2., 3., 4.], nodes, basis, areas)
        self.assertEqual(code, 0, stats)
        residual = self.call_evaluate(result, nodes, basis, areas)[2]
        for i, inverse in enumerate([0., 2., 3., 4.]):
            if inverse:residual[i] += (result[i]-x[i])/(inverse*(1/60)**2)
        self.assertLessEqual(np.max(np.abs(residual[1:])), 1e-8)
        np.testing.assert_array_equal(result[0], x[0])

    def test_stationary_compressed_saddle_is_not_convergence(self):
        rest = np.array([[0., 0., 0.], [-1., 0., -1.], [1., 0., -1.], [1., 0., 1.], [-1., 0., 1.]])
        nodes = np.array([[0, 2, 1], [0, 3, 2], [0, 4, 3], [0, 1, 4]], dtype=np.int32)
        basis, areas = self.reference_cells(rest, nodes)
        predicted = rest*.5
        code, result, stats = self.run_solve(predicted, [1e10, 0., 0., 0., 0.], nodes, basis, areas)
        self.assertLessEqual(stats[1], 1e-8)
        self.assertEqual(code, 3, stats)
        np.testing.assert_array_equal(result, predicted)

    def test_small_energy_change_matches_high_precision_subtraction(self):
        difference = self.lib.membrane_fem_difference
        difference.argtypes = [ct.c_int, D, D, ct.c_int, I, D, D, ct.c_double, ct.c_double, D]
        difference.restype = ct.c_int
        x, nodes, basis, areas = self.data()
        x[1] = [1.12, .08, .04]
        x[2] = [.09, -.03, .91]
        trial = x + 1e-10*np.sin(np.arange(9).reshape(3, 3)*.7)
        def decimal_energy(values):
            q = [[Decimal.from_float(float(v)) for v in row] for row in values]
            fx = [q[1][j]-q[0][j] for j in range(3)]
            fy = [q[2][j]-q[0][j] for j in range(3)]
            c00, c01, c11 = sum(v*v for v in fx), sum(a*b for a, b in zip(fx, fy)), sum(v*v for v in fy)
            logarithm = (c00*c11-c01*c01).ln()/2
            return (c00+c11-2-2*logarithm+Decimal('1.5')*logarithm**2)/2
        with localcontext() as context:
            context.prec = 80
            expected = float(decimal_energy(trial)-decimal_energy(x))
        result = ct.c_double(123.)
        code = difference(len(x), x.ctypes.data_as(D), trial.ctypes.data_as(D), len(areas),
                          nodes.ctypes.data_as(I), basis.ctypes.data_as(D), areas.ctypes.data_as(D),
                          2., 3., ct.byref(result))
        self.assertEqual(code, 0)
        self.assertLess(abs(result.value-expected), 1e-24)

    def test_implicit_equilibrium_and_exact_pin(self):
        x, nodes, basis, areas = self.data()
        x[1] += [.06, .03, 0]
        inverse = np.array([0., 4., 7.])
        code, result, stats = self.run_solve(x, inverse, nodes, basis, areas)
        self.assertEqual(code, 0, stats)
        np.testing.assert_array_equal(result[0], x[0])
        residual = self.call_evaluate(result, nodes, basis, areas)[2]
        for i in [1, 2]:
            residual[i] += (result[i] - x[i]) / (inverse[i] * (1/60)**2)
        self.assertLessEqual(np.max(np.abs(residual[1:])), 1e-8)
        self.assertLessEqual(stats[1], 1e-8)
        self.assertGreater(stats[4], 0)
        h = self.call_evaluate(result, nodes, basis, areas)[3][0][3:, 3:]
        h += np.diag(np.repeat(1 / inverse[1:] / (1/60)**2, 3))
        self.assertGreater(np.linalg.eigvalsh(h).min(), 0.)

    def test_rigid_prediction_has_no_internal_impulse(self):
        x, nodes, basis, areas = self.data()
        x += [.03, .02, -.01]
        code, result, stats = self.run_solve(x, [3., 4., 7.], nodes, basis, areas)
        self.assertEqual(code, 0, stats)
        np.testing.assert_array_equal(result, x)

    def test_positive_micro_material_preserves_nonlinear_equilibrium(self):
        x, nodes, basis, areas = self.data()
        x[1] += [.06, .03, 0.]
        inverse = np.array([0., 4., 7.])
        base_code, expected, _ = self.run_solve(x, inverse, nodes, basis, areas)
        self.assertEqual(base_code, 0)
        for scale in [1e-12, 1e-13, 1e-16]:
            with self.subTest(scale=scale):
                code, result, stats = self.run_solve(x, inverse/scale, nodes, basis, areas*scale, tol=1e-8*scale)
                self.assertEqual(code, 0, stats)
                # Both physical stiffness and inertia scale, so the minimizer
                # must be unchanged. No mass floors or relaxed force target.
                np.testing.assert_allclose(result, expected, atol=2e-9, rtol=0.)
                gradient = self.call_evaluate(result, nodes, basis, areas)[2]
                gradient[1:] += (result[1:]-x[1:])/(inverse[1:,None]*(1/60)**2)
                self.assertLessEqual(np.max(np.abs(gradient[1:])), 1e-8)
                self.assertLessEqual(stats[1], 1e-8*scale)
                np.testing.assert_array_equal(result[0], x[0])

    def test_mixed_macro_and_micro_components_keep_distinct_mass(self):
        rest, nodes, basis, areas = self.data()
        x = np.concatenate([rest, rest+[2., 0., 0.]])
        x[4] += [.06, .03, 0.]
        joined_nodes = np.concatenate([nodes, nodes+3])
        joined_basis = np.concatenate([basis, basis])
        scale = 1e-13
        inverse = np.array([0., 4., 7., 0., 4./scale, 7./scale])
        code, result, stats = self.run_solve(x, inverse, joined_nodes, joined_basis, np.array([areas[0], areas[0]*scale]), tol=1e-21)
        self.assertEqual(code, 0, stats)
        np.testing.assert_array_equal(result[:3], rest)
        base_code, expected, _ = self.run_solve(x[3:]-[2.,0.,0.], [0.,4.,7.], nodes,basis,areas)
        self.assertEqual(base_code, 0)
        np.testing.assert_allclose(result[3:]-[2.,0.,0.], expected, atol=2e-9, rtol=0.)

    def test_extreme_finite_inertia_without_elastic_scale_is_retained(self):
        predicted=np.array([[.1,.2,.3]])
        for inverse in [1e13,1e100,1e308]:
            with self.subTest(inverse=inverse):
                code,result,stats=self.run_solve(predicted,[inverse],np.empty((0,3),dtype=np.int32),np.empty((0,2,3)),np.empty(0))
                self.assertEqual(code,0,stats)
                np.testing.assert_array_equal(result,predicted)

    def test_failures_do_not_publish_unaccepted_iterates(self):
        x, nodes, basis, areas = self.data()
        x[1, 0] += .1
        code, result, stats = self.run_solve(x, [0., 4., 7.], nodes, basis, areas, budget=0)
        self.assertEqual(code, 1)
        self.assertGreater(stats[1], 1e-8)
        np.testing.assert_array_equal(result, x)
        for inverse, bad_nodes, bad_basis, bad_areas in [
            ([0., math.inf, 7.], nodes, basis, areas),
            ([0., math.nan, 7.], nodes, basis, areas),
            ([0., -1., 7.], nodes, basis, areas),
            ([0., 1e-320, 7.], nodes, basis, areas),
            ([0., 4., 7.], [[0, 1, 9]], basis, areas),
            ([0., 4., 7.], nodes, basis * math.nan, areas),
            ([0., 4., 7.], nodes, basis + 1., areas),
            ([0., 4., 7.], nodes, basis, [-.5]),
        ]:
            code, result, _ = self.run_solve(x, inverse, bad_nodes, bad_basis, bad_areas)
            self.assertEqual(code, -1)
            np.testing.assert_array_equal(result, x)
        collapsed = np.zeros_like(x)
        code, result, _ = self.run_solve(collapsed, [0., 4., 7.], nodes, basis, areas)
        self.assertEqual(code, 2)
        np.testing.assert_array_equal(result, collapsed)


if __name__ == '__main__':
    unittest.main()
