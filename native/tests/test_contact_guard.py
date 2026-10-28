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

    def test_actual_second_substep_budget_exhaustion_cannot_accept(self):
        data=json.loads((ROOT/'native/tests/fixtures/joint_motion261_second.json').read_text())
        d=lambda values:(ct.c_double*len(values))(*values)
        ints=lambda values:(ct.c_int*len(values))(*values)
        old=d(data['previous']); current=d(data['current']); packets=d(data['packets'])
        faces=ints(data['triangles']); kinds=ints(data['kinds']); stats=d([99.]*8)
        code=self.guard(len(old)//3,old,current,len(faces)//3,faces,len(kinds),kinds,packets,128,1e-9,stats)
        self.assertEqual(code,2,list(stats))
        self.assertEqual(list(stats)[2:4],[40.,1.]); self.assertEqual(stats[7],1)
        self.assertEqual(list(old),data['previous']); self.assertEqual(list(current),data['current'])

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

if __name__=="__main__": unittest.main()
