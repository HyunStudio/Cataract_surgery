"""Conservative change bounds versus an independent Decimal active-set reference."""
import ctypes as ct
import hashlib
import json
import math
from decimal import Decimal as D,localcontext
from pathlib import Path
import random
import unittest
try:
    from .decimal_distance_reference import contact_merit,complete_merit,decimal
except ImportError:
    from decimal_distance_reference import contact_merit,complete_merit,decimal
ROOT=Path(__file__).resolve().parents[2]
array=lambda values:(ct.c_double*len(values))(*values)

class MeritDifferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib=ct.CDLL(str(ROOT/".tools/native/contact_merit_probe.dll"))
        cls.contact=cls.lib.merit_contact_change
        cls.contact.argtypes=[ct.POINTER(ct.c_double)]*3+[ct.c_double]*3+[ct.POINTER(ct.c_double)]
        cls.contact.restype=ct.c_int
        cls.edge=cls.lib.merit_edge_change
        cls.edge.argtypes=[ct.POINTER(ct.c_double)]*2+[ct.c_double]*2+[ct.POINTER(ct.c_double)]
        cls.edge.restype=ct.c_int
        cls.witness=cls.lib.merit_contact_witness_change
        cls.witness.argtypes=[ct.POINTER(ct.c_double)]*5+[ct.c_double]*3+[ct.POINTER(ct.c_double)]
        cls.witness.restype=ct.c_int
        cls.interpolate=cls.lib.merit_interpolate
        cls.interpolate.argtypes=[ct.POINTER(ct.c_double)]*2+[ct.c_double,ct.POINTER(ct.c_double)]
        cls.interpolate.restype=None

    def compare_contact(self,old,new,axis,radius=.1,multiplier=.002,penalty=100.):
        out=array([99.,99.]); code=self.contact(array(old),array(new),array(axis),radius,multiplier,penalty,out)
        self.assertEqual(code,0,(old,new,axis))
        with localcontext() as ctx:
            ctx.prec=80
            exact=contact_merit(axis,new,radius,multiplier,penalty)-contact_merit(axis,old,radius,multiplier,penalty)
            self.assertLessEqual(decimal(out[0]),exact+D('1e-60'))
            self.assertGreaterEqual(decimal(out[1]),exact-D('1e-60'))
        return out,exact

    def test_no_represented_motion_is_exactly_zero(self):
        old=[0.,0.,0.,1.,0.,0.,0.,0.,1.]
        out,_=self.compare_contact(old,old,[.2,.1,.2,.2,.1,.2])
        self.assertEqual(list(out),[0.,0.])

    def test_tiny_plane_change_and_translations(self):
        for offset in [0.,8.,-8.]:
            old=[offset,offset,offset,offset+1,offset,offset,offset,offset,offset+1]
            new=old[:]
            for vertex in range(3): new[3*vertex+1]+=1e-12
            axis=[offset+.2,offset+.1,offset+.2]*2
            out,exact=self.compare_contact(old,new,axis)
            self.assertGreater(exact,0)
            self.assertLess(out[1]-out[0],1e-23)

    def test_inactive_to_active_and_active_to_inactive(self):
        old=[0.,0.,0.,1.,0.,0.,0.,0.,1.]
        new=old[:]
        for vertex in range(3): new[3*vertex+1]+=.02
        axis=[.2,.11,.2]*2
        self.compare_contact(old,new,axis,multiplier=0.)
        self.compare_contact(new,old,axis,multiplier=0.)

    def test_vertices_edges_and_segment_interior(self):
        old=[0.,0.,0.,1.,0.,0.,0.,0.,1.]
        for axis in [[-.05,.04,-.05]*2,[.5,.04,-.05]*2,[.5,-.5,-.1,.5,.5,-.1],[.8,.2,.8,.8,.8,.8]]:
            new=old[:]; new[1]+=1e-11; new[7]-=2e-12
            self.compare_contact(old,new,axis,radius=.2)

    def test_independent_random_finite_feature_bounds(self):
        rng=random.Random(39871)
        for _ in range(48):
            old=[0.,0.,0.,1.,0.,0.,0.,0.,1.]
            axis=[rng.uniform(-.4,1.4),rng.uniform(.02,.3),rng.uniform(-.4,1.4)]
            axis+=axis if rng.random()<.5 else [axis[0]+rng.uniform(-.5,.5),axis[1]+rng.uniform(.1,.5),axis[2]+rng.uniform(-.5,.5)]
            new=[value+rng.uniform(-1e-10,1e-10) for value in old]
            self.compare_contact(old,new,axis,radius=.2,multiplier=rng.choice([0.,.001,.02]))

    def test_invalid_geometry_cannot_publish_a_bound(self):
        old=[0.,0.,0.]*3; out=array([99.,99.])
        self.assertEqual(self.contact(array(old),array(old),array([0.,.1,0.]*2),.1,.001,100.,out),1)
        self.assertEqual(list(out),[99.,99.])

    def test_spring_change_retains_tiny_cancellation(self):
        old=[8.,0.,0.,8.125,0.,0.]; new=old[:]; new[0]+=1e-12
        out=array([99.,99.]); self.assertEqual(self.edge(array(old),array(new),.12501,20.,out),0)
        with localcontext() as ctx:
            ctx.prec=80
            norm=lambda p:sum(((decimal(p[k])-decimal(p[k+3]))**2 for k in range(3)),D(0)).sqrt()
            exact=decimal(20.)*((norm(new)-decimal(.12501))**2-(norm(old)-decimal(.12501))**2)/2
            self.assertLessEqual(decimal(out[0]),exact)
            self.assertGreaterEqual(decimal(out[1]),exact)
            self.assertLess(out[1]-out[0],1e-28)

    def test_suboptimal_new_witness_cannot_invent_descent(self):
        old=[0.,0.,0.,1.,0.,0.,0.,0.,1.]; new=old[:]; new[7]=-1e-4
        axis=[.02,.09999,.02]*2; out=array([99.,99.])
        self.assertEqual(self.witness(array(old),array(new),array(axis),array([0.,.04,.5]),array([0.,1.,1.]),.1,.002,100.,out),0)
        with localcontext() as ctx:
            ctx.prec=80
            exact=contact_merit(axis,new,.1,.002,100.)-contact_merit(axis,old,.1,.002,100.)
            self.assertLessEqual(decimal(out[0]),exact)
            self.assertGreaterEqual(decimal(out[1]),exact)
            self.assertGreater(out[1],0.)

    def test_actual265_failed_full_step_has_certified_merit_descent(self):
        request_path=ROOT/"native/tests/fixtures/joint_static265.json"
        p=json.loads(request_path.read_text())
        snapshot=json.loads((ROOT/"native/tests/fixtures/merit_stagnation265.json").read_text())
        self.assertEqual(hashlib.sha256(request_path.read_bytes()).hexdigest(),snapshot["request_sha256"])
        old,new=snapshot["xyz"],snapshot["trial"]
        with localcontext() as ctx:
            ctx.prec=80
            inertia=D(0)
            for vertex,inverse in enumerate(p["inverse"]):
                if inverse==0: continue
                for axis in range(3):
                    i=3*vertex+axis
                    change=decimal(new[i])-decimal(old[i])
                    inertia+=decimal(1/inverse)*change*(decimal(new[i])+decimal(old[i])-2*decimal(p["predicted"][i]))/2
            low=high=inertia
            for a,b,rest in zip(p["a"],p["b"],p["rest"]):
                out=array([99.,99.])
                self.assertEqual(self.edge(array(old[3*a:3*a+3]+old[3*b:3*b+3]),array(new[3*a:3*a+3]+new[3*b:3*b+3]),rest,1/p["alpha"],out),0)
                low+=decimal(out[0]); high+=decimal(out[1])
            bodies=len(p["capsules"])//7
            for face in range(len(p["triangles"])//3):
                ids=p["triangles"][3*face:3*face+3]
                first=[old[3*vertex+k] for vertex in ids for k in range(3)]
                last=[new[3*vertex+k] for vertex in ids for k in range(3)]
                for body in range(bodies):
                    capsule=p["capsules"][7*body:7*body+7]; out=array([99.,99.])
                    multiplier=snapshot["dual"].get(str(face*bodies+body),0.)
                    self.assertEqual(self.contact(array(first),array(last),array(capsule[:6]),capsule[6],multiplier,snapshot["rho"],out),0)
                    low+=decimal(out[0]); high+=decimal(out[1])
            exact=complete_merit(p,new,snapshot["dual"],snapshot["rho"])-complete_merit(p,old,snapshot["dual"],snapshot["rho"])
            self.assertLess(abs(exact-D(snapshot["reference_merit_change"])),D('1e-60'))
            self.assertLessEqual(low,exact); self.assertGreaterEqual(high,exact)
            self.assertLess(high,decimal(snapshot["slope"])*decimal(1e-4))

    def test_selected_time_uses_represented_rounding_not_scaled_endpoint_delta(self):
        previous=[8.,8.,8.,9.,8.,8.,8.,8.,9.]
        first=previous[:]; last=previous[:]
        for vertex in range(3):
            first[3*vertex+1]+=math.ulp(8.)
            last[3*vertex+1]+=2*math.ulp(8.)
        for time in [.25,.75,1.]:
            old=array([99.]*9); new=array([99.]*9)
            self.interpolate(array(previous),array(first),time,old)
            self.interpolate(array(previous),array(last),time,new)
            with localcontext() as ctx:
                ctx.prec=80
                expected=[float((1-decimal(time))*decimal(a)+decimal(time)*decimal(b)) for a,b in zip(previous,last)]
            self.assertEqual(list(new),expected)
            bounds,_=self.compare_contact(list(old),list(new),[8.2,8.1,8.2]*2)
            if time==.25:
                self.assertEqual(list(old),list(new))
                self.assertEqual(list(bounds),[0.,0.])
