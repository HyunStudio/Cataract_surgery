"""Bounded capsule/triangle distance contract; build_contact_distance.py first."""
import ctypes as ct
import itertools
import math
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
FACE = [[0., 0., 0.], [1., 0., 0.], [0., 0., 1.]]


class ContactDistanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib = ct.CDLL(str(ROOT / ".tools/native/contact_distance.dll"))
        cls.distance = cls.lib.membrane_contact_distance
        cls.distance.argtypes = [ct.POINTER(ct.c_double), ct.POINTER(ct.c_double),
                                 ct.c_double, ct.POINTER(ct.c_double)]
        cls.distance.restype = ct.c_int

    def query(self, a, b, face=FACE, radius=.1):
        segment = (ct.c_double * 6)(*(a + b))
        triangle = (ct.c_double * 9)(*(v for p in face for v in p))
        out = (ct.c_double * 22)(*([123.] * 22))
        status = self.distance(segment, triangle, radius, out)
        self.assertEqual(list(segment), a + b)
        self.assertEqual(list(triangle), [v for p in face for v in p])
        return status, list(out)

    def test_sphere_face_analytic_distance_and_derivative(self):
        status, out = self.query([.2, .3, .4], [.2, .3, .4])
        self.assertEqual(status, 0)
        self.assertAlmostEqual(out[0], .09, places=14)
        self.assertAlmostEqual(out[1], .2, places=14)
        for got, expected in zip(out[8:11], [.4, .2, .4]):
            self.assertAlmostEqual(got, expected, places=13)
        for got, expected in zip(out[11:20], [0, -.24, 0, 0, -.12, 0, 0, -.24, 0]):
            self.assertAlmostEqual(got, expected, places=13)

    def test_finite_endpoint_not_infinite_axis(self):
        status, out = self.query([.2, .3, .4], [.2, .6, .4])
        self.assertEqual(status, 0)
        self.assertAlmostEqual(out[0], .09, places=14)
        self.assertEqual(out[20], 0.)

    def test_vertex_feature(self):
        status, out = self.query([1.2, .3, -.2], [1.2, .3, -.2])
        self.assertEqual(status, 0)
        self.assertAlmostEqual(out[0], .17, places=14)
        self.assertEqual(out[8:11], [0., 1., 0.])

    def test_shared_finite_endpoint_is_one_witness(self):
        corner = .1*(1.-.2/math.sqrt(.02))
        for dz in (-1e-6, 1e-6):
            face = [[corner, 0., corner+dz], [-1., 0., 0.], [0., 0., -1.]]
            status, out = self.query([.1, 0., .1], [.1, 0., .1], face, .2)
            self.assertEqual(status, 0)
            self.assertEqual(out[5:8], face[0])
            self.assertEqual(out[8:11], [1., 0., 0.])

    def test_skew_edge_interior_feature(self):
        face = [[-1., 0., 0.], [1., 0., 0.], [0., 0., -1.]]
        status, out = self.query([0., -.2, .6], [0., .8, -.4], face)
        self.assertEqual(status, 0)
        self.assertAlmostEqual(out[0], .08, places=14)
        self.assertAlmostEqual(out[20], .4, places=13)
        for got, expected in zip(out[11:20], [0, -.2, -.2, 0, -.2, -.2, 0, 0, 0]):
            self.assertAlmostEqual(got, expected, places=13)

    def test_axis_triangle_crossing_is_not_edge_only_distance(self):
        status, out = self.query([.2, 1., .2], [.2, -1., .2])
        self.assertEqual(status, 1)
        self.assertEqual(out[0], 0.)
        self.assertAlmostEqual(out[1], -.1)
        self.assertEqual(out[11:20], [0.] * 9)

    def test_coplanar_axis_crosses_triangle(self):
        status, out = self.query([-1., 0., .2], [2., 0., .2])
        self.assertEqual(status, 1)
        self.assertLessEqual(out[0], 1e-28)

    def test_axis_reversal_and_triangle_permutations(self):
        a, b = [0., -.2, .6], [0., .8, -.4]
        face = [[-1., 0., 0.], [1., 0., 0.], [0., 0., -1.]]
        status, expected = self.query(a, b, face)
        for order in itertools.permutations(range(3)):
            status, out = self.query(b, a, [face[i] for i in order])
            self.assertEqual(status, 0)
            self.assertAlmostEqual(out[0], expected[0], places=14)
            self.assertAlmostEqual(out[20], 1. - expected[20], places=13)
            for local, original in enumerate(order):
                for axis in range(3):
                    self.assertAlmostEqual(out[11 + 3*local + axis], expected[11 + 3*original + axis], places=12)

    def test_gradient_matches_finite_differences(self):
        cases = [([.2, .3, .4], [.2, .6, .4], FACE),
                 ([0., -.2, .6], [0., .8, -.4], [[-1., 0., 0.], [1., 0., 0.], [0., 0., -1.]])]
        for a, b, face in cases:
            status, out = self.query(a, b, face)
            self.assertEqual(status, 0)
            for k in range(9):
                plus, minus = [p[:] for p in face], [p[:] for p in face]
                plus[k//3][k % 3] += 1e-6
                minus[k//3][k % 3] -= 1e-6
                numeric = (self.query(a, b, plus)[1][0] - self.query(a, b, minus)[1][0]) / 2e-6
                self.assertAlmostEqual(out[11+k], numeric, delta=1e-9)

    def test_unsigned_distance_does_not_hide_side_change(self):
        _, above = self.query([.2, .3, .4], [.2, .3, .4])
        _, below = self.query([.2, -.3, .4], [.2, -.3, .4])
        self.assertAlmostEqual(above[0], below[0])
        self.assertAlmostEqual(above[12], -below[12])

    def test_translated_small_geometry_retains_distance_and_gradient(self):
        point, shift = [.2, .3, .4], [5., -3., 2.]
        for scale in (1., 1e-6):
            transform = lambda p: [shift[i]+scale*p[i] for i in range(3)]
            status, out = self.query(transform(point), transform(point), [transform(p) for p in FACE], .1*scale)
            self.assertEqual(status, 0)
            self.assertAlmostEqual(out[0]/scale**2, .09, delta=1e-9)
            for got, expected in zip(out[11:20], [0, -.24, 0, 0, -.12, 0, 0, -.24, 0]):
                self.assertAlmostEqual(got/scale, expected, delta=1e-9)

    def test_parallel_minimizers_are_explicitly_ambiguous(self):
        status, out = self.query([.2, .1, .2], [.2, .1, .6])
        self.assertEqual(status, 3)
        self.assertAlmostEqual(out[0], .01, places=14)
        self.assertTrue(all(math.isfinite(x) for x in out))

    def test_ambiguity_does_not_disappear_at_small_gradient_scale(self):
        for a, b in [([.2, 1e-13, .2], [.2, 1e-13, .6]),
                     ([.2, .1, .2], [.2+1e-13, .1, .2])]:
            status, _ = self.query(a, b)
            self.assertEqual(status, 3)

    def test_skinny_nondegenerate_face(self):
        status, out = self.query([.2, .1, 3e-9], [.2, .1, 3e-9], [[0., 0., 0.], [1., 0., 0.], [0., 0., 1e-8]])
        self.assertIn(status, (0, 3))
        self.assertAlmostEqual(out[0], .01, places=14)

    def test_degenerate_face_is_not_regular_clearance(self):
        status, out = self.query([.2, .1, .2], [.2, .1, .2], [[0., 0., 0.], [1., 0., 0.], [2., 0., 0.]])
        self.assertEqual(status, 2)
        self.assertAlmostEqual(out[0], .05, places=14)

    def test_plane_cancellation_cannot_be_definite_intersection(self):
        # Exact plane is z-x-y=0; residual=-2^-67, squared distance=2^-134/3.
        # Reconstructed witnesses cannot resolve all components at x=z=.25.
        point = [.25, 2.**-67, .25]
        status, out = self.query(point, point, [[0., 0., 0.], [1., 0., 1.], [0., 1., 1.]])
        self.assertEqual(status, 2)
        self.assertTrue(all(math.isfinite(value) for value in out))

    def test_invalid_query_does_not_publish_output(self):
        for a, radius in [([math.nan, 0., 0.], .1), ([math.inf, 0., 0.], .1),
                          ([17., 0., 0.], .1), ([0., 0., 0.], 0.),
                          ([0., 0., 0.], math.nan), ([0., 0., 0.], .31)]:
            segment = (ct.c_double * 6)(*(a + [0., 0., 0.]))
            triangle = (ct.c_double * 9)(*(v for p in FACE for v in p))
            out = (ct.c_double * 22)(*([123.] * 22))
            self.assertEqual(self.distance(segment, triangle, radius, out), -1)
            self.assertEqual(list(out), [123.] * 22)
        self.assertEqual(self.distance(None, None, .1, None), -1)
        out = (ct.c_double * 22)(*([123.] * 22))
        triangle = (ct.c_double * 9)(*(v for p in FACE for v in p))
        self.assertEqual(self.distance(None, triangle, .1, out), -1)
        self.assertEqual(list(out), [123.] * 22)


if __name__ == "__main__":
    unittest.main()
