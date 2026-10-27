"""Native kernel contract. Build with tools/build_membrane_kernel.py first."""
import ctypes as ct
import json
import math
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]


class KernelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib = ct.CDLL(str(ROOT / ".tools/native/membrane_kernel.dll"))
        cls.solve = cls.lib.membrane_solve
        cls.solve.argtypes = [ct.c_int, ct.POINTER(ct.c_double), ct.POINTER(ct.c_double),
                              ct.c_int, ct.POINTER(ct.c_int), ct.POINTER(ct.c_int),
                              ct.POINTER(ct.c_double), ct.c_double, ct.c_int,
                              ct.c_double, ct.POINTER(ct.c_double)]
        cls.solve.restype = ct.c_int

    def run_kernel(self, positions, inverse, a, b, rest, alpha=.1, budget=100, tol=1e-10):
        flat = [v for point in positions for v in point]
        x = (ct.c_double * len(flat))(*flat)
        w = (ct.c_double * len(inverse))(*inverse)
        aa = (ct.c_int * len(a))(*a)
        bb = (ct.c_int * len(b))(*b)
        rr = (ct.c_double * len(rest))(*rest)
        stats = (ct.c_double * 8)()
        code = self.solve(len(inverse), x, w, len(a), aa, bb, rr, alpha, budget, tol, stats)
        return code, [list(x[i:i + 3]) for i in range(0, len(x), 3)], list(stats)

    def test_unequal_masses_analytic_solution(self):
        code, x, stats = self.run_kernel([[0, 0, 0], [2, 0, 0]], [1, 2], [0], [1], [1])
        self.assertEqual(code, 0)
        self.assertAlmostEqual(x[0][0], 1 / 3.1, places=8)
        self.assertAlmostEqual(x[1][0], 2 - 2 / 3.1, places=8)
        self.assertLessEqual(stats[1], 1e-10)

    def test_pin_is_exact(self):
        code, x, _ = self.run_kernel([[0, 0, 0], [2, 0, 0]], [0, 2], [0], [1], [1])
        self.assertEqual(code, 0)
        self.assertEqual(x[0], [0, 0, 0])
        self.assertAlmostEqual(x[1][0], 2 - 2 / 2.1, places=8)

    def test_invalid_inputs_are_atomic(self):
        original = [[0, 0, 0], [2, 0, 0]]
        for inverse, a, rest, alpha in [([1, -1], [0], [1], .1),
                                        ([1, 2], [2], [1], .1),
                                        ([1, 2], [0], [0], .1),
                                        ([1, 2], [0], [1], 0),
                                        ([1, 2], [0], [math.nan], .1)]:
            code, x, _ = self.run_kernel(original, inverse, a, [1], rest, alpha)
            self.assertEqual(code, -1)
            self.assertEqual(x, original)

    def test_work_exhaustion_is_not_convergence(self):
        code, x, stats = self.run_kernel([[0, 0, 0], [2, 0, 0]], [1, 2], [0], [1], [1], budget=0)
        self.assertEqual(code, 1)
        self.assertEqual(x, [[0, 0, 0], [2, 0, 0]])
        self.assertGreater(stats[1], 1e-10)

    def test_undefined_collapsed_edge_reports_numeric_failure(self):
        original = [[0, 0, 0], [0, 0, 0]]
        code, x, stats = self.run_kernel(original, [1, 2], [0], [1], [1])
        self.assertEqual(code, 2)
        self.assertEqual(x, original)
        self.assertTrue(math.isinf(stats[0]))
        self.assertTrue(math.isinf(stats[1]))

    def test_compressed_stationary_saddle_is_not_accepted(self):
        original = [[0, 0, 0], [-.5, 0, 0], [.5, 0, 0]]
        code, x, stats = self.run_kernel(original, [1, 0, 0], [0, 0], [1, 2], [1, 1])
        self.assertEqual(code, 3)
        self.assertEqual(x, original)
        self.assertEqual(stats[1], 0)
        # Independent physical counterexample: transverse movement lowers the objective.
        displaced_energy = .5*.5**2 + (math.sqrt(.5)-1)**2/.1
        self.assertLess(displaced_energy, stats[0])

    def test_nonfinite_geometric_stiffness_is_numeric_failure(self):
        original = [[0, 0, 0], [1e-308, 0, 0]]
        code, x, stats = self.run_kernel(original, [1, 1], [0], [1], [1e308], alpha=1e308)
        self.assertEqual(code, 2)
        self.assertEqual(x, original)
        self.assertTrue(math.isinf(stats[1]))
        # Finite C/length alone is insufficient if multiplying it by stiffness overflows.
        original = [[0, 0, 0], [-1e-200, 0, 0], [1e-200, 0, 0]]
        code, x, _ = self.run_kernel(original, [1, 0, 0], [0, 0], [1, 2], [1, 1], alpha=1e-200)
        self.assertEqual(code, 2)
        self.assertEqual(x, original)

    def test_collective_buckling_with_positive_coordinate_diagonals_is_rejected(self):
        original = [[-.25, 0, 0], [.25, 0, 0], [-1.25, 0, 0], [1.25, 0, 0]]
        code, x, stats = self.run_kernel(original, [.05, .05, 0, 0],
                                          [0, 0, 1], [1, 2, 3], [1, 1.5, 1.5])
        self.assertEqual(code, 3)
        self.assertEqual(x, original)
        self.assertEqual(stats[1], 0)
        # Each free Y diagonal is+5, but the relative Y mode has eigenvalue-5.
        displaced_energy = 20*.01**2 + (math.hypot(.5,.02)-1)**2/.2
        displaced_energy += 2*(math.hypot(1,.01)-1.5)**2/.2
        self.assertLess(displaced_energy, stats[0])

    def test_small_edge_uses_its_actual_rest_length(self):
        code, x, stats = self.run_kernel([[0, 0, 0], [2e-8, 0, 0]], [0, 1e12],
                                          [0], [1], [1e-8], tol=1e-16)
        self.assertEqual(code, 0, stats)
        self.assertAlmostEqual(x[1][0], 1e-8, delta=1e-15)

    def test_overflowing_linear_norm_does_not_report_zero_residual(self):
        original = [[i*10., 0, 0] for i in range(4)]+[[i*10.+1, 0, 0] for i in range(4)]
        code, x, stats = self.run_kernel(original, [1]*4+[0]*4,
                                          [0, 1, 2, 3], [4, 5, 6, 7], [.3]*4, alpha=1/1.7e308)
        self.assertEqual(code, 2)
        self.assertEqual(x, original)
        self.assertTrue(math.isinf(stats[5]))

    def test_rotated_spring_and_empty_edge_set(self):
        code, x, _ = self.run_kernel([[3, -2, 1], [3, 0, 1]], [1, 2], [0], [1], [1])
        self.assertEqual(code, 0)
        self.assertAlmostEqual(x[0][1], -2 + 1/3.1, places=8)
        self.assertAlmostEqual(x[1][1], -2/3.1, places=8)
        code, x, _ = self.run_kernel([[3, -2, 1]], [1], [], [], [])
        self.assertEqual(code, 0)
        self.assertEqual(x, [[3, -2, 1]])

    def test_refined_flap_against_independent_energy_reference(self):
        data = json.loads((ROOT / "native/tests/fixtures/refined_flap.json").read_text())
        edges = [i for i, active in enumerate(data["active"]) if active]
        a, b, rest = ([data[key][i] for i in edges] for key in ("a", "b", "rest"))
        code, x, stats = self.run_kernel(data["positions"], data["inverse"], a, b, rest,
                                          data["alpha"], budget=100, tol=1e-8)
        self.assertEqual(code, 0, stats)
        energy = 0.
        gradient = [[0., 0., 0.] for _ in x]
        for i, w in enumerate(data["inverse"]):
            if w == 0:
                self.assertEqual(x[i], data["positions"][i])
            else:
                energy += sum((u-v)**2 for u, v in zip(x[i], data["positions"][i])) / (2*w)
                gradient[i] = [(u-v)/w for u, v in zip(x[i], data["positions"][i])]
        strains = []
        for ia, ib, r in zip(a, b, rest):
            length = math.dist(x[ia], x[ib])
            energy += (length-r)**2 / (2*data["alpha"])
            for axis in range(3):
                force = (length-r)*(x[ia][axis]-x[ib][axis])/(data["alpha"]*length)
                gradient[ia][axis] += force
                gradient[ib][axis] -= force
            strains.append(length/r-1)
        self.assertLessEqual(energy, 3.8194e-8)
        self.assertAlmostEqual(energy, stats[0], delta=1e-17)
        self.assertLess(max(strains), .01)
        independent_norm = max(abs(v) for i, g in enumerate(gradient) if data["inverse"][i] > 0 for v in g)
        self.assertLessEqual(independent_norm, 1e-8)
        self.assertAlmostEqual(independent_norm, stats[1], delta=1e-14)


if __name__ == "__main__":
    unittest.main()
