"""Whole-interval clearance of double tissue and capsule trajectories."""
import ctypes as ct
import itertools
import json
import math
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]

def linear(a,b,radius):
    return list(a)+list(a)+list(b)+list(b)+[radius]+[0.]*28

def arc():
    # A point at local(+1,0,0) rotates -90..+90 degrees around Z.
    h=math.sqrt(.5)
    return [0.,-1.,0.]*2+[0.,1.,0.]*2+[.05]+[0.]*6+[0.,0.,-h,h,0.,0.,h,h]+[1.,0.,0.]*4+[0.,1.]

class ContactGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib=ct.CDLL(str(ROOT/".tools/native/contact_guard.dll"))
        cls.guard=cls.lib.membrane_guard_motion
        cls.guard.argtypes=[ct.c_int,ct.POINTER(ct.c_double),ct.POINTER(ct.c_double),ct.c_int,ct.POINTER(ct.c_int),
                           ct.c_int,ct.POINTER(ct.c_int),ct.POINTER(ct.c_double),ct.c_int,ct.c_double,ct.POINTER(ct.c_double)]
        cls.guard.restype=ct.c_int

    def query(self,old,current,body,kind=0,indices=(0,1,2),budget=128,gap=1e-9):
        d=lambda v:(ct.c_double*len(v))(*v)
        ints=lambda v:(ct.c_int*len(v))(*v)
        previous=d(old); xyz=d(current); motion=d(body); mesh=ints(indices); kinds=ints([kind])
        stats=d([99.]*8)
        code=self.guard(len(old)//3,previous,xyz,len(indices)//3,mesh,1,kinds,motion,budget,gap,stats)
        self.assertEqual(list(previous),old)
        self.assertEqual(list(xyz),current)
        self.assertEqual(list(motion),body)
        return code,list(stats)

    def face(self,y=0.):
        return [-1.,y,-1.,1.,y,-1.,0.,y,1.]

    def test_static_clear_is_certified_without_queries(self):
        face=self.face(); code,s=self.query(face,face,linear([0.,2.,0.],[0.,2.,0.],.1))
        self.assertEqual(code,0); self.assertEqual(s[0],0)

    def test_translation_crossing_with_clear_endpoints_is_rejected(self):
        face=self.face(); code,s=self.query(face,face,linear([0.,1.,0.],[0.,-1.,0.],.1))
        self.assertEqual(code,1); self.assertLess(s[4],-.09)
        self.assertLessEqual(s[0],128)

    def test_moving_tissue_crossing_is_rejected(self):
        code,_=self.query(self.face(-1.),self.face(1.),linear([0.,0.,0.],[0.,0.,0.],.1))
        self.assertEqual(code,1)

    def test_rigid_comotion_at_contact_retains_complete_clearance(self):
        old=self.face(); delta=[.5,.3,.2]
        current=[value+delta[i%3] for i,value in enumerate(old)]
        code,s=self.query(old,current,linear([0.,.1,0.],[.5,.4,.2],.1))
        self.assertEqual(code,0,s); self.assertLessEqual(s[0],128)

    def test_accepted_endpoint_gap_tolerance_is_not_replaced_by_proxy_skin(self):
        face=self.face(); center=[0.,.1-5e-10,0.]
        code,s=self.query(face,face,linear(center,center,.1))
        self.assertEqual(code,0,s)
        self.assertGreaterEqual(s[4],-1e-9)

    def test_penetration_beyond_original_gap_tolerance_rejects(self):
        face=self.face(); center=[0.,.1-2e-8,0.]
        self.assertEqual(self.query(face,face,linear(center,center,.1))[0],1)

    def test_arc_crossing_is_not_replaced_by_its_clear_chord(self):
        face=[1.,-.1,-.1,1.,.1,-.1,1.,0.,.1]
        code,s=self.query(face,face,arc(),kind=1)
        self.assertEqual(code,1,s)

    def test_clear_arc_is_refined_instead_of_using_a_solid_enclosure(self):
        face=[0.,-.1,-.1,0.,.1,-.1,0.,0.,.1]
        code,s=self.query(face,face,arc(),kind=1)
        self.assertEqual(code,0,s)
        self.assertGreater(s[5],0)

    def test_recorded_endpoints_are_retained_with_affine_pose_correction(self):
        packet=arc()
        for off in [0,3,6,9]: packet[off]+=.02
        face=[1.02,-.1,-.1,1.02,.1,-.1,1.02,0.,.1]
        self.assertEqual(self.query(face,face,packet,kind=1)[0],1)

    def test_no_query_budget_is_uncertain_never_clear(self):
        face=self.face(); code,s=self.query(face,face,linear([0.,.1,0.],[0.,.1,0.],.1),budget=0)
        self.assertEqual(code,2); self.assertEqual(s[0],0)

    def test_degenerate_nearby_geometry_is_uncertain(self):
        face=[-1.,0.,0.,0.,0.,0.,1.,0.,0.]
        self.assertEqual(self.query(face,face,linear([0.,.1,0.],[0.,.1,0.],.1))[0],2)

    def test_invalid_motion_rejects_without_overwriting_diagnostics(self):
        face=self.face()
        bad=[]
        p=linear([0.,2.,0.],[0.,2.,0.],.1); p[12]=-1.; bad.append((p,0))
        p=arc(); p[19:23]=[0.]*4; bad.append((p,1))
        p=arc(); p[39:41]=[.7,.2]; bad.append((p,1))
        p=linear([0.,2.,0.],[0.,2.,0.],.1); bad.append((p,3))
        for packet,kind in bad:
            code,s=self.query(face,face,packet,kind=kind)
            self.assertEqual(code,-1); self.assertEqual(s,[99.]*8)

    def test_winding_and_axis_endpoint_order_do_not_hide_crossing(self):
        face=self.face()
        for indices in itertools.permutations(range(3)):
            packet=linear([0.,1.,0.],[0.,-1.,0.],.1)
            # A nonzero segment, reversed at both recorded times.
            packet[0]=packet[6]=-.2; packet[3]=packet[9]=.2
            for reverse in [False,True]:
                if reverse:
                    packet[:6]=packet[3:6]+packet[:3]
                    packet[6:12]=packet[9:12]+packet[6:9]
                self.assertEqual(self.query(face,face,packet,indices=indices)[0],1)

    def test_actual_saved_joint_motion261_clears_without_proxy_projection(self):
        data=json.loads((ROOT/'native/tests/fixtures/joint_motion261.json').read_text())
        d=lambda values:(ct.c_double*len(values))(*values)
        ints=lambda values:(ct.c_int*len(values))(*values)
        old=d(data['previous']); current=d(data['current']); packets=d(data['packets'])
        faces=ints(data['triangles']); kinds=ints(data['kinds']); stats=d([99.]*8)
        code=self.guard(len(old)//3,old,current,len(faces)//3,faces,len(kinds),kinds,packets,128,1e-9,stats)
        self.assertEqual(code,0,list(stats))
        self.assertEqual(list(old),data['previous']); self.assertEqual(list(current),data['current'])
        self.assertEqual(list(packets),data['packets'])
        self.assertEqual(stats[1],2772); self.assertGreater(stats[5],0)

    def test_actual_second_substep_is_certified_with_original_query_limit(self):
        data=json.loads((ROOT/'native/tests/fixtures/joint_motion261_second.json').read_text())
        d=lambda values:(ct.c_double*len(values))(*values)
        ints=lambda values:(ct.c_int*len(values))(*values)
        old=d(data['previous']); current=d(data['current']); packets=d(data['packets'])
        faces=ints(data['triangles']); kinds=ints(data['kinds']); stats=d([99.]*8)
        code=self.guard(len(old)//3,old,current,len(faces)//3,faces,len(kinds),kinds,packets,128,1e-9,stats)
        self.assertEqual(code,0,list(stats))
        self.assertEqual(list(stats)[2:4],[-1.,-1.]); self.assertEqual(stats[7],0)
        self.assertEqual(list(old),data['previous']); self.assertEqual(list(current),data['current'])

    def test_actual_tick262_intermediate_penetration_must_reject(self):
        data=json.loads((ROOT/'native/tests/fixtures/joint_motion262.json').read_text())
        d=lambda values:(ct.c_double*len(values))(*values)
        ints=lambda values:(ct.c_int*len(values))(*values)
        old=d(data['previous']); current=d(data['current']); packets=d(data['packets'])
        faces=ints(data['triangles']); kinds=ints(data['kinds']); stats=d([99.]*8)
        code=self.guard(len(old)//3,old,current,len(faces)//3,faces,len(kinds),kinds,packets,128,1e-9,stats)
        self.assertEqual(code,1,list(stats)); self.assertEqual(list(stats)[2:4],[40.,1.])
        self.assertLess(stats[4],-8e-8)
        self.assertEqual(list(old),data['previous']); self.assertEqual(list(current),data['current'])

    def test_actual263_search_reaches_late_penetration_without_left_branch_starvation(self):
        data=json.loads((ROOT/'native/tests/fixtures/joint_motion263.json').read_text())
        d=lambda values:(ct.c_double*len(values))(*values)
        ints=lambda values:(ct.c_int*len(values))(*values)
        stats=d([99.]*8)
        code=self.guard(len(data['previous'])//3,d(data['previous']),d(data['current']),len(data['triangles'])//3,
                        ints(data['triangles']),len(data['kinds']),ints(data['kinds']),d(data['packets']),128,1e-9,stats)
        self.assertEqual(code,1,list(stats)); self.assertLess(stats[4],-1e-9)

    def test_refined263_finite_edge_uncertainty_cannot_accept(self):
        data=json.loads((ROOT/'native/tests/fixtures/joint_motion263_refined.json').read_text())
        d=lambda values:(ct.c_double*len(values))(*values)
        ints=lambda values:(ct.c_int*len(values))(*values)
        stats=d([99.]*8)
        code=self.guard(len(data['previous'])//3,d(data['previous']),d(data['current']),len(data['triangles'])//3,
                        ints(data['triangles']),len(data['kinds']),ints(data['kinds']),d(data['packets']),128,1e-9,stats)
        self.assertEqual(code,2,list(stats)); self.assertEqual(list(stats)[2:4],[40.,1.]); self.assertEqual(stats[7],1)

    def test_moving_plane_retains_time_correlation_at_contact(self):
        old=self.face(); current=self.face()
        slope=.01
        for j in range(3):
            old[3*j+1]=-slope*old[3*j]
            current[3*j+1]=slope*current[3*j]
        height=.1*math.sqrt(1+slope*slope)
        packet=linear([0.,height,0.],[0.,height,0.],.1)
        for order in itertools.permutations(range(3)):
            code,stats=self.query(old,current,packet,indices=order,budget=2)
            self.assertEqual(code,0,stats)
            self.assertEqual(stats[0],2)

    def test_independent_interior_plane_witnesses_cannot_be_certified_clear(self):
        cases=json.loads((ROOT/'native/tests/fixtures/moving_plane_crossings.json').read_text())['cases']
        dot=lambda a,b:sum(x*y for x,y in zip(a,b))
        sub=lambda a,b:[x-y for x,y in zip(a,b)]
        cross=lambda a,b:[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
        for case in cases:
            t=case['witness_t']
            face=[x*(1-t)+y*t for x,y in zip(case['old'],case['current'])]
            point=[x*(1-t)+y*t for x,y in zip(case['a'],case['b'])]
            e=sub(face[3:6],face[:3]); f=sub(face[6:9],face[:3]); n=cross(e,f)
            relative=sub(point,face[:3]); n2=dot(n,n); numerator=dot(relative,n)
            distance=abs(numerator)/math.sqrt(n2)
            projected=[x-y*numerator/n2 for x,y in zip(relative,n)]
            ee,ff,ef=dot(e,e),dot(f,f),dot(e,f)
            er,fr=dot(e,projected),dot(f,projected)
            u=(ff*er-ef*fr)/(ee*ff-ef*ef); v=(ee*fr-ef*er)/(ee*ff-ef*ef)
            self.assertGreaterEqual(min(u,v,1-u-v),0.)
            self.assertLess(distance,.06); self.assertAlmostEqual(distance,case['witness_distance'],places=12)
            packet=linear(case['a'],case['b'],.1)
            # Endpoints and midpoint are clear; a true interior witness is
            # closer than radius. Neither a cheap plane test nor exhaustion
            # may return a clear interval.
            self.assertNotEqual(self.query(case['old'],case['current'],packet,budget=3)[0],0)
            self.assertEqual(self.query(case['old'],case['current'],packet)[0],1)

    def test_capsule_endpoints_on_opposite_plane_sides_reject(self):
        face=self.face(); packet=linear([0.,.3,0.],[0.,.3,0.],.1)
        packet[3:6]=packet[9:12]=[0.,-.3,0.]
        self.assertEqual(self.query(face,face,packet)[0],1)

    def test_off_midpoint_triangle_collapse_cannot_hide_later_crossing(self):
        # e(t)=(1-4t,0,0) vanishes at .25; f(t)=(0,1-t,t).
        # At .75 the sphere center is .05*e(t)+.125*f(t), strictly
        # inside the restored triangle. At0,.5,1 its distance exceeds .1.
        old=[0.,0.,0.,1.,0.,0.,0.,1.,0.]
        current=[0.,0.,0.,-3.,0.,0.,0.,0.,1.]
        packet=linear([.05,1.25,.375],[-.15,-.375,0.],.1)
        self.assertEqual(self.query(old,current,packet,budget=3)[0],2)
        self.assertNotEqual(self.query(old,current,packet)[0],0)

    def test_collision_away_from_midpoint_requires_interval_search(self):
        angle=-math.pi/4
        x,y=math.cos(angle),math.sin(angle)
        face=[x,y-.01,-.01,x,y+.01,-.01,x,y,.01]
        code,stats=self.query(face,face,arc(),kind=1)
        self.assertEqual(code,1,stats); self.assertGreater(stats[5],0)

    def test_original_pose_subinterval_cannot_replay_entire_arc(self):
        packet=arc(); packet[39:41]=[.75,1.]
        for off in [0,3]: packet[off:off+3]=[math.sqrt(.5),math.sqrt(.5),0.]
        face=[1.,-.01,-.01,1.,.01,-.01,1.,0.,.01]
        self.assertEqual(self.query(face,face,packet,kind=1)[0],0)

    def test_witness_abi_reports_sample_time_without_changing_legacy_stats(self):
        witness_guard=self.lib.membrane_guard_motion_witness
        witness_guard.argtypes=self.guard.argtypes+[ct.POINTER(ct.c_double)]
        witness_guard.restype=ct.c_int
        face=(ct.c_double*9)(*self.face())
        packet=(ct.c_double*41)(*linear([0.,1.,0.],[0.,-1.,0.],.1))
        ids=(ct.c_int*3)(0,1,2); kinds=(ct.c_int*1)(0)
        stats=(ct.c_double*8)(*([99.]*8)); time=ct.c_double(99.)
        code=witness_guard(3,face,face,1,ids,1,kinds,packet,128,1e-9,stats,ct.byref(time))
        self.assertEqual(code,1); self.assertEqual(time.value,.5)
        code=witness_guard(3,face,face,1,ids,1,kinds,packet,0,1e-9,stats,ct.byref(time))
        self.assertEqual(code,2); self.assertEqual(time.value,-1.)
        time.value=99.; packet[12]=-1.
        code=witness_guard(3,face,face,1,ids,1,kinds,packet,128,1e-9,stats,ct.byref(time))
        self.assertEqual(code,-1); self.assertEqual(time.value,99.)

if __name__=="__main__": unittest.main()
