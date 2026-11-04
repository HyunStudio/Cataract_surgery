"""Retained fine-face contact chain rule, independently differenced in control space."""
import ctypes as ct
from pathlib import Path
import unittest
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
D = ct.POINTER(ct.c_double)
Q = np.array([[0., 0., 0.], [1., 0., 0.], [0., 0., 1.]])
B = np.array([[.8, .1, .1], [.3, .6, .1], [.3, .1, .6]])


class EmbeddedContactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib = ct.CDLL(str(ROOT/'.tools/native/contact_distance.dll'))
        cls.query_native = cls.lib.membrane_embedded_contact_distance
        cls.query_native.argtypes = [D, D, D, ct.c_double, D, D, D]
        cls.query_native.restype = ct.c_int

    def query(self, segment, q=Q, b=B, radius=.1):
        segment = np.ascontiguousarray(segment, dtype=np.float64)
        q = np.ascontiguousarray(q, dtype=np.float64)
        b = np.ascontiguousarray(b, dtype=np.float64)
        saved = [x.copy() for x in (segment, q, b)]
        out, gradient, hessian = np.full(22, 123.), np.full(9, 123.), np.full((9, 9), 123.)
        status = self.query_native(*(x.ctypes.data_as(D) for x in (segment, q, b)), radius,
                                   *(x.ctypes.data_as(D) for x in (out, gradient, hessian)))
        for x, old in zip((segment, q, b), saved):np.testing.assert_array_equal(x, old)
        return status, out, gradient, hessian

    def finite_difference(self, segment, q=Q, b=B, epsilon=2e-6):
        code, out, g, h = self.query(segment, q, b)
        self.assertEqual(code, 0)
        fdg, fdh = np.zeros(9), np.zeros((9, 9))
        for k in range(9):
            step = np.zeros((3, 3));step.flat[k] = epsilon
            cp, op, gp, _ = self.query(segment, q+step, b)
            cm, om, gm, _ = self.query(segment, q-step, b)
            self.assertEqual((cp, cm), (0, 0))
            fdg[k] = (op[0]-om[0])/(2*epsilon)
            fdh[:, k] = (gp-gm)/(2*epsilon)
        np.testing.assert_allclose(g, fdg, atol=2e-10, rtol=2e-8)
        np.testing.assert_allclose(h, fdh, atol=2e-8, rtol=2e-7)
        np.testing.assert_allclose(h, h.T, atol=2e-14, rtol=0.)
        # A rigid translation of all controls moves the fine witness equally.
        np.testing.assert_allclose(g.reshape(3, 3).sum(0),
                                   2*(out[5:8]-out[2:5]), atol=1e-14, rtol=0.)
        return out, g, h

    def test_sphere_face_with_affine_control_map(self):
        out, _, _ = self.finite_difference([.25, .3, .25]*2)
        self.assertAlmostEqual(out[0], .09, places=14)
        self.assertAlmostEqual(out[1], .2, places=14)
        np.testing.assert_allclose(out[8:11], [.4, .3, .3], atol=1e-14)

    def test_sphere_edge_curvature(self):
        self.finite_difference([.35, .3, -.2]*2)

    def test_sphere_vertex_curvature(self):
        self.finite_difference([-.3, .3, -.2]*2)

    def test_finite_capsule_endpoint_and_interior_edge(self):
        self.finite_difference([.25, .3, .25, .25, .6, .25])
        # Skew interior axis / edge witness, away from feature switches.
        self.finite_difference([.35, -.2, .6, .35, .8, -.4])

    def test_absent_parent_material_does_not_collide(self):
        segment = [.82, .03, .08]*2
        status, fine, _, _ = self.query(segment)
        self.assertEqual(status, 0)
        self.assertGreater(fine[1], .1)
        status, coarse, _, _ = self.query(segment, b=np.eye(3))
        self.assertEqual(status, 0)
        self.assertLess(coarse[1], 0.)

    def test_permutations_and_axis_reversal(self):
        segment = np.array([[.35, -.2, .6], [.35, .8, -.4]])
        status, out, g, h = self.query(segment)
        self.assertEqual(status, 0)
        for order in ([1, 2, 0], [2, 1, 0]):
            code, other, og, oh = self.query(segment[::-1], q=Q[order], b=B[:, order])
            self.assertEqual(code, 0)
            self.assertAlmostEqual(other[0], out[0], places=14)
            np.testing.assert_allclose(og.reshape(3, 3), g.reshape(3, 3)[order], atol=1e-14)
            ix = np.array([[3*i+j for j in range(3)] for i in order]).ravel()
            np.testing.assert_allclose(oh, h[np.ix_(ix, ix)], atol=1e-13)
        code, other, og, oh = self.query(segment, b=B[[2, 0, 1]])
        self.assertEqual(code, 0)
        np.testing.assert_allclose(og, g, atol=1e-14)
        np.testing.assert_allclose(oh, h, atol=1e-13)

    def test_invalid_or_undefined_is_atomic(self):
        segment = [.25, .3, .25]*2
        for b in (B*np.nan, B-1, B*2, np.zeros((3, 3))):
            code, out, g, h = self.query(segment, b=b)
            self.assertEqual(code, -1)
            for x in (out, g, h):self.assertTrue(np.all(x == 123.))
        # Axis crossing and collapsed fine face have no smooth positive-distance Hessian.
        for seg, b in (([.25, 1., .25, .25, -1., .25], B),
                       (segment, np.array([B[0]]*3))):
            code, out, g, h = self.query(seg, b=b)
            self.assertNotEqual(code, 0)
            for x in (out, g, h):self.assertTrue(np.all(x == 123.))

    def test_tiny_retained_face_and_deformed_controls(self):
        tiny = np.array([[1., 0., 0.], [1.-1e-5, 1e-5, 0.], [1.-1e-5, 0., 1e-5]])
        self.finite_difference([2e-6, 3e-6, 3e-6]*2, b=tiny, epsilon=1e-9)
        deformed = Q+np.array([[.12, -.03, .2], [-.05, .13, .01], [.02, -.06, .05]])
        self.finite_difference([.3, .5, .3]*2, q=deformed)

    def test_c1_feature_switch_and_parallel_tie_are_not_c2(self):
        # Projection exactly on the first edge: face and edge Hessians differ.
        cases = [([.35, .3, .1]*2, 4),
                 ([.2, .3, .2, .3, .3, .2], 3)]
        for segment, expected in cases:
            code, out, g, h = self.query(segment)
            self.assertEqual(code, expected)
            for x in (out, g, h):self.assertTrue(np.all(x == 123.))

    def test_nonfinite_coordinates_and_null_outputs(self):
        segment = [.25, .3, .25]*2
        for bad in (np.nan, np.inf, 17.):
            q = Q.copy();q[0, 0] = bad
            code, out, g, h = self.query(segment, q=q)
            self.assertEqual(code, -1)
            for x in (out, g, h):self.assertTrue(np.all(x == 123.))
        arrays = [np.ascontiguousarray(x, dtype=np.float64) for x in (segment, Q, B)]
        out, g, h = np.full(22, 123.), np.full(9, 123.), np.full(81, 123.)
        args = [x.ctypes.data_as(D) for x in arrays]+[.1]+[x.ctypes.data_as(D) for x in (out, g, h)]
        for index in (0, 1, 2, 4, 5, 6):
            bad = args.copy();bad[index] = None
            self.assertEqual(self.query_native(*bad), -1)
            for x in (out, g, h):self.assertTrue(np.all(x == 123.))


if __name__ == '__main__':unittest.main()
