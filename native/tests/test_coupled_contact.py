"""Joint energy/contact acceptance, including the captured local jaw problem."""
import ctypes as ct
import json
import math
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]


class CoupledContactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib = ct.CDLL(str(ROOT/".tools/native/membrane_contact.dll"))
        cls.solve = cls.lib.membrane_solve_contact
        cls.solve.argtypes = [ct.c_int, ct.POINTER(ct.c_double), ct.POINTER(ct.c_double),
                             ct.POINTER(ct.c_double), ct.c_int, ct.POINTER(ct.c_int),
                             ct.POINTER(ct.c_int), ct.POINTER(ct.c_double), ct.c_double,
                             ct.c_int, ct.POINTER(ct.c_int), ct.c_int, ct.POINTER(ct.c_double),
                             ct.c_int, ct.c_double, ct.c_double, ct.c_double,
                             ct.POINTER(ct.c_double), ct.POINTER(ct.c_double)]
        cls.solve.restype = ct.c_int
        geometry = ct.CDLL(str(ROOT/".tools/native/contact_distance.dll"))
        cls.distance = geometry.membrane_contact_distance
        cls.distance.argtypes = [ct.POINTER(ct.c_double), ct.POINTER(ct.c_double), ct.c_double, ct.POINTER(ct.c_double)]
        cls.distance.restype = ct.c_int

    def run_problem(self, p, budget=100):
        doubles = lambda x: (ct.c_double*len(x))(*x)
        integers = lambda x: (ct.c_int*len(x))(*x)
        x = doubles(p["initial"])
        faces = [v for face in p["triangles"] for v in face]
        bodies = [v for body in p["capsules"] for v in body["a"]+body["b"]+[body["radius"]]]
        count = len(p["triangles"])*len(p["capsules"])
        dual = doubles([99.]*count)
        stats = doubles([99.]*12)
        code = self.solve(len(p["inverse"]), doubles(p["predicted"]), x, doubles(p["inverse"]),
                          len(p["a"]), integers(p["a"]), integers(p["b"]), doubles(p["rest"]), p["alpha"],
                          len(p["triangles"]), integers(faces), len(p["capsules"]), doubles(bodies),
                          budget, 1e-8, 1e-9, 1e-11, dual, stats)
        return code, list(x), list(dual), list(stats)

    def corner(self, radius=.2, duplicate=False):
        x = [0., 0., 0., -1., 0., 0., 0., 0., -1.]
        return {"initial": x[:], "predicted": x[:], "inverse": [1., 0., 0.],
                "a": [], "b": [], "rest": [], "alpha": .1,
                "triangles": [[0, 1, 2]]*(2 if duplicate else 1),
                "capsules": [{"a": [.1, 0., .1], "b": [.1, 0., .1], "radius": radius}]}

    def test_analytic_contact_reaction_balances_inertia(self):
        p = self.corner()
        status, x, dual, stats = self.run_problem(p)
        self.assertEqual(status, 0, stats)
        expected = .1*(1.-.2/math.sqrt(.02))
        self.assertAlmostEqual(x[0], expected, delta=2e-7)
        self.assertAlmostEqual(x[2], expected, delta=2e-7)
        self.assertAlmostEqual(x[1], 0., delta=1e-10)
        self.assertEqual(x[3:], p["initial"][3:])
        self.assertAlmostEqual(dual[0], (.2-math.sqrt(.02))*.2/2., delta=1e-7)
        self.assertLessEqual(stats[1], 1e-8)
        self.assertLessEqual(stats[2], 1e-9)
        self.assertLessEqual(stats[3], 1e-11)

    def test_inactive_contact_has_zero_reaction(self):
        p = self.corner(.1)
        status, x, dual, _ = self.run_problem(p)
        self.assertEqual(status, 0)
        self.assertEqual(x, p["predicted"])
        self.assertEqual(dual, [0.])

    def test_duplicate_constraints_preserve_the_same_solution(self):
        p = self.corner(duplicate=True)
        status, x, dual, stats = self.run_problem(p)
        self.assertEqual(status, 0, stats)
        self.assertAlmostEqual(x[0], .1*(1.-.2/math.sqrt(.02)), delta=2e-7)
        self.assertAlmostEqual(sum(dual), (.2-math.sqrt(.02))*.1, delta=1e-7)
        self.assertTrue(all(v >= 0. for v in dual))

    def test_prescribed_penetration_rejects_atomically(self):
        p = self.corner(); p["inverse"] = [0., 0., 0.]
        status, x, dual, _ = self.run_problem(p)
        self.assertEqual(status, 3)
        self.assertEqual(x, p["initial"])
        self.assertEqual(dual, [99.])

    def test_opposing_contact_forces_cannot_hide_penetration(self):
        p = self.corner()
        p["initial"] = p["predicted"] = [0., 0., 0., 1., 0., 0., 0., 0., 1.]
        p["inverse"] = [1., 1., 1.]
        p["capsules"] = [{"a": [.2, y, .2], "b": [.2, y, .2], "radius": .2} for y in (-.1, .1)]
        status, x, dual, stats = self.run_problem(p, budget=5)
        self.assertNotEqual(status, 0, stats)
        self.assertEqual(x, p["initial"])
        self.assertEqual(dual, [99., 99.])

    def test_invalid_arguments_leave_positions_and_duals_unchanged(self):
        mutations = [lambda p: p["inverse"].__setitem__(0, -1.),
                     lambda p: p["predicted"].__setitem__(3, -.9),
                     lambda p: p["predicted"].__setitem__(0, math.nan),
                     lambda p: p["triangles"][0].__setitem__(0, 99),
                     lambda p: p.__setitem__("alpha", 0.),
                     lambda p: p["capsules"][0].__setitem__("radius", math.nan)]
        for mutate in mutations:
            p = self.corner(); mutate(p)
            status, x, dual, _ = self.run_problem(p)
            self.assertEqual(status, -1)
            self.assertEqual(x, p["initial"])
            self.assertEqual(dual, [99.])

    def test_exhaustion_does_not_publish_partial_motion(self):
        p = self.corner()
        status, x, dual, _ = self.run_problem(p, budget=0)
        self.assertEqual(status, 1)
        self.assertEqual(x, p["initial"])
        self.assertEqual(dual, [99.])

    def test_ambiguous_active_geometry_is_not_an_accepted_reaction(self):
        p = self.corner()
        p["initial"] = p["predicted"] = [0., 0., 0., 1., 0., 0., 0., 0., 1.]
        p["inverse"] = [1., 1., 1.]
        p["capsules"] = [{"a": [.2, .1, .2], "b": [.2, .1, .6], "radius": .2}]
        status, x, _, _ = self.run_problem(p)
        self.assertEqual(status, 4)
        self.assertEqual(x, p["initial"])

    def test_collapsed_material_edge_is_explicit_numerical_failure(self):
        p = {"initial": [0.]*6, "predicted": [0.]*6, "inverse": [1., 1.],
             "a": [0], "b": [1], "rest": [1.], "alpha": .1, "triangles": [], "capsules": []}
        status, x, _, _ = self.run_problem(p)
        self.assertEqual(status, 2)
        self.assertEqual(x, p["initial"])

    def test_overflowed_linear_norm_never_reports_zero_residual(self):
        p = {"initial": [.8, .8, .8], "predicted": [0., 0., 0.], "inverse": [6e-309],
             "a": [], "b": [], "rest": [], "alpha": .1, "triangles": [], "capsules": []}
        status, x, _, stats = self.run_problem(p)
        self.assertEqual(status, 2)
        self.assertEqual(x, p["initial"])
        self.assertTrue(math.isinf(stats[9]))

    def test_stationary_compressed_saddle_is_not_a_minimum(self):
        p = {"initial": [-.25, 0., 0., .25, 0., 0.], "predicted": [4.75, 0., 0., -4.75, 0., 0.],
             "inverse": [1., 1.], "a": [0], "b": [1], "rest": [1.], "alpha": .1,
             "triangles": [], "capsules": []}
        status, x, _, _ = self.run_problem(p)
        self.assertEqual(status, 5)
        self.assertEqual(x, p["initial"])

    def test_local_jaw_fixture_matches_independent_constrained_reference(self):
        p = json.loads((ROOT/"native/tests/fixtures/local_jaw_contact.json").read_text())
        status, x, dual, stats = self.run_problem(p)
        self.assertEqual(status, 0, stats)
        self.assertLessEqual(stats[1], 1e-8)
        self.assertLessEqual(stats[2], 1e-9)
        self.assertLessEqual(stats[3], 1e-11)
        for i, inverse in enumerate(p["inverse"]):
            if inverse == 0.:
                self.assertEqual(x[3*i:3*i+3], p["initial"][3*i:3*i+3])
        energy = sum(.5*sum((x[3*i+k]-p["predicted"][3*i+k])**2 for k in range(3))/w
                     for i, w in enumerate(p["inverse"]) if w > 0.)
        force = [0.]*len(x)
        for i, w in enumerate(p["inverse"]):
            if w > 0.:
                for k in range(3): force[3*i+k] = (x[3*i+k]-p["predicted"][3*i+k])/w
        for a, b, rest in zip(p["a"], p["b"], p["rest"]):
            delta = [x[3*a+k]-x[3*b+k] for k in range(3)]
            length = math.sqrt(sum(v*v for v in delta))
            energy += .5*(length-rest)**2/p["alpha"]
            for k in range(3):
                f = (length-rest)*delta[k]/(length*p["alpha"])
                force[3*a+k] += f; force[3*b+k] -= f
        self.assertAlmostEqual(energy, 1.2512200570759009e-8, delta=2e-10)
        for f, triangle in enumerate(p["triangles"]):
            for b, body in enumerate(p["capsules"]):
                segment = (ct.c_double*6)(*(body["a"]+body["b"]))
                face = (ct.c_double*9)(*(x[3*v+k] for v in triangle for k in range(3)))
                out = (ct.c_double*22)()
                self.assertGreaterEqual(self.distance(segment, face, body["radius"], out), 0)
                self.assertGreaterEqual(math.sqrt(out[0])-body["radius"], -1e-9)
                multiplier = dual[f*len(p["capsules"])+b]
                self.assertGreaterEqual(multiplier, 0.)
                for j, v in enumerate(triangle):
                    for k in range(3): force[3*v+k] -= multiplier*out[11+3*j+k]/body["radius"]**2
        self.assertLessEqual(max(abs(force[3*i+k]) for i, w in enumerate(p["inverse"]) if w > 0. for k in range(3)), 1e-8)

    def test_actual_packed64_tick264_converges_without_changing_predictor(self):
        self.assert_packed_request("joint_tick264.json")

    def test_actual_physical_jaws_second_substep_reaches_requested_kkt_gates(self):
        self.assert_packed_request("joint_physical264_second.json")

    def test_actual265_unresolved_static_substep_rejects_atomically(self):
        p=json.loads((ROOT/"native/tests/fixtures/joint_static265.json").read_text())
        p["triangles"]=[p["triangles"][i:i+3] for i in range(0,len(p["triangles"]),3)]
        flat=p["capsules"]
        p["capsules"]=[{"a":flat[i:i+3],"b":flat[i+3:i+6],"radius":flat[i+6]} for i in range(0,len(flat),7)]
        status,x,dual,stats=self.run_problem(p)
        self.assertEqual(status,2,stats)
        self.assertEqual(x,p["initial"])
        self.assertEqual(dual,[99.]*(len(p["triangles"])*len(p["capsules"])))
        self.assertGreater(stats[1],1e-8)

    def test_all_invalid_line_trials_without_contact_progress_fail_atomically(self):
        p={"initial":[16.,0.,0.,15.,0.,0.],"predicted":[16.,0.,0.,15.,0.,0.],
           "inverse":[1.,0.],"a":[0],"b":[1],"rest":[2.],"alpha":.1,"triangles":[],"capsules":[]}
        status,x,dual,stats=self.run_problem(p)
        self.assertEqual(status,2,stats)
        self.assertEqual(x,p["initial"]); self.assertEqual(dual,[])
        self.assertLess(stats[4],100)

    def assert_packed_request(self, name):
        p = json.loads((ROOT/"native/tests/fixtures"/name).read_text())
        p["triangles"] = [p["triangles"][i:i+3] for i in range(0,len(p["triangles"]),3)]
        p["capsules"] = [{"a":p["capsules"][i:i+3],"b":p["capsules"][i+3:i+6],"radius":p["capsules"][i+6]}
                         for i in range(0,len(p["capsules"]),7)]
        status, x, dual, stats = self.run_problem(p)
        self.assertEqual(status, 0, stats)
        force = [(x[3*v+k]-p["predicted"][3*v+k])/w if w>0 else 0.
                 for v,w in enumerate(p["inverse"]) for k in range(3)]
        for v,w in enumerate(p["inverse"]):
            if w==0: self.assertEqual(x[3*v:3*v+3],p["initial"][3*v:3*v+3])
        for a,b,rest in zip(p["a"],p["b"],p["rest"]):
            delta=[x[3*a+k]-x[3*b+k] for k in range(3)]
            length=math.sqrt(sum(v*v for v in delta))
            for k in range(3):
                value=(length-rest)*delta[k]/(length*p["alpha"])
                force[3*a+k]+=value; force[3*b+k]-=value
        for f,triangle in enumerate(p["triangles"]):
            for b,body in enumerate(p["capsules"]):
                segment=(ct.c_double*6)(*(body["a"]+body["b"]))
                face=(ct.c_double*9)(*(x[3*v+k] for v in triangle for k in range(3)))
                out=(ct.c_double*22)()
                self.assertIn(self.distance(segment,face,body["radius"],out),(0,3))
                self.assertGreaterEqual(math.sqrt(out[0])-body["radius"],-1e-9)
                multiplier=dual[f*len(p["capsules"])+b]
                self.assertGreaterEqual(multiplier,0.)
                self.assertLessEqual(abs(multiplier*(out[0]/body["radius"]**2-1)),1e-11)
                for j,v in enumerate(triangle):
                    for k in range(3): force[3*v+k]-=multiplier*out[11+3*j+k]/body["radius"]**2
        self.assertLessEqual(max(abs(force[3*v+k]) for v,w in enumerate(p["inverse"]) if w>0 for k in range(3)),1e-8)


if __name__ == "__main__":
    unittest.main()
