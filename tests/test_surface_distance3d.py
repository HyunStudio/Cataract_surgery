"""Synthetic 3D closest-triangle search, safety and adversarial QA."""
import math
import random

import pytest

from ophthosim.geometry import Mesh
from ophthosim.mesh_raycast import build_index
from ophthosim.surface_distance3d import (SurfaceDistance, nearest_triangle)
from ophthosim.surface_probe3d import (SurfaceProbe, probe_surface, _static_indexes,
                                        _iol_index)
from ophthosim.vision3d import VisualFeedback
from ophthosim.input3d import Surgery3DController, eye_to_pixel, STAGE_DEPTH
from ophthosim.engine import Phase
from ophthosim.gl_preview import GPUEyePreview,View


def triangle():
    m=Mesh("triangle",((0.,0.,0.),(1.,0.,0.),(0.,1.,0.)),
           ((0.,0.,1.),)*3,((0,1,2),))
    return build_index(m)


def test_triangle_interior_face_and_barycentrics():
    hit=nearest_triangle(triangle(),(.25,.25,.40))
    assert hit is not None
    assert hit.distance==pytest.approx(.4)
    assert hit.point==pytest.approx((.25,.25,0.))
    assert hit.barycentric==pytest.approx((.5,.25,.25))
    assert hit.face_index==0


def test_triangle_edge_vertex_and_outside_plane():
    idx=triangle()
    cases=[
        ((.5,-.1,0.),(.5,0.,0.)),
        ((-1.,-1.,0.),(0.,0.,0.)),
        ((2.,2.,0.),(.5,.5,0.)),
    ]
    for point,expected in cases:
        hit=nearest_triangle(idx,point)
        assert hit and hit.point==pytest.approx(expected)
        assert sum(hit.barycentric)==pytest.approx(1.,abs=1e-10)
        hit.check()


def test_degenerate_face_fails_to_nearest_edge():
    mesh=Mesh("degenerate",((0.,0.,0.),(1.,0.,0.),(2.,0.,0.)),
              ((0.,0.,1.),)*3,((0,1,2),))
    hit=nearest_triangle(build_index(mesh),(.5,.4,0.))
    assert hit and hit.point==pytest.approx((.5,0.,0.))
    assert hit.distance==pytest.approx(.4)
    hit.check()


def test_bvh_nearest_does_not_pick_farther_triangle():
    mesh=Mesh("double",((0,0,0),(1,0,0),(0,1,0),
                         (0,0,2),(1,0,2),(0,1,2)),
              ((0,0,1),)*6,((0,1,2),(3,4,5)))
    idx=build_index(mesh)
    assert nearest_triangle(idx,(.2,.2,1.9)).face_index==1
    assert nearest_triangle(idx,(.2,.2,.1)).face_index==0
    assert nearest_triangle(idx,(.2,.2,1.),max_distance=.9) is None
    assert nearest_triangle(idx,(.2,.2,1.),max_distance=1.).face_index==0


def test_single_triangle_far_budget_and_center():
    idx=triangle()
    assert nearest_triangle(idx,(0,0,3),max_distance=.9) is None
    assert nearest_triangle(idx,(.2,.2,0),max_distance=0).distance==0


def test_mesh_probe_gated_before_case_and_during_abort():
    ctrl=Surgery3DController()
    assert probe_surface(ctrl) is None
    assert ctrl.command("confirm")
    assert ctrl.command("prepare")
    pt=eye_to_pixel(*ctrl.game._entry_target[0],ctrl.tool_depth,1280,720,ctrl.view)
    old=ctrl.game.snapshot()
    ctrl.inspect(*pt,1280,720)
    probe=probe_surface(ctrl)
    assert probe is not None and probe.name in ("iris","lens")
    assert probe.status in ("CLOSE","NEAR","FAR")
    assert ctrl.game.snapshot()==old
    assert ctrl.game.export_replay_jsonl()==ctrl.game.export_replay_jsonl()
    assert ctrl.command("pause")
    assert probe_surface(ctrl) is None
    assert ctrl.command("pause")
    assert probe_surface(ctrl) is None  # no stale tool after resume
    ctrl.inspect(*pt,1280,720)
    assert probe_surface(ctrl) is not None
    assert ctrl.command("abort")
    assert probe_surface(ctrl) is None


def test_motion_safety_hold_never_produces_mesh_probe():
    ctrl=Surgery3DController("motion")
    ctrl.command("confirm")
    ctrl.command("prepare")
    for x,y in ctrl.game._entry_target:
        pt=eye_to_pixel(x,y,ctrl.tool_depth,1280,720,ctrl.view)
        ctrl.pointer(*pt,1280,720,fresh_press=True)
    assert ctrl.game.patient.alert
    assert probe_surface(ctrl) is None
    assert ctrl.game.paused


def test_model_shift_adjusted_for_camera_orientation_without_changing_game():
    ctrl=Surgery3DController()
    ctrl.command("confirm")
    ctrl.command("prepare")
    pt=eye_to_pixel(.69,.46,ctrl.tool_depth,1280,720,ctrl.view)
    ctrl.inspect(*pt,1280,720)
    base=probe_surface(ctrl)
    assert base is not None
    ctrl.view.yaw=.4
    ctrl.view.pitch=.2
    shifted=probe_surface(ctrl,VisualFeedback(motion_x=.035,motion_y=-.02))
    assert shifted is not None
    assert math.isfinite(shifted.gap)
    assert ctrl.game.eye.entry_hits==0


def test_initial_phaco_or_iol_synthetic_mesh_cache_is_bounded():
    indexes=_static_indexes()
    assert set(indexes)=={"iris","lens"}
    assert _static_indexes() is indexes
    _iol_index.cache_clear()
    a=_iol_index(0.,1.)
    assert a is _iol_index(0.,1.)
    for i in range(25):
        _iol_index(i/25.,1.)
    assert _iol_index.cache_info().currsize<=8


@pytest.mark.parametrize("bad",[None,True,False,"x",float("nan"),
                                float("inf"),10**400,[],{}])
def test_bad_distance_input_rejected(bad):
    idx=triangle()
    with pytest.raises(ValueError):
        nearest_triangle(idx,(bad,0.,0.))
    with pytest.raises(ValueError):
        nearest_triangle(idx,(0,0,0),max_distance=bad)


def test_bad_point_shape_and_bvh_object_fail_closed():
    idx=triangle()
    for pt in (None,True,{},(1,),(1,2,3,4)):
        with pytest.raises(ValueError):
            nearest_triangle(idx,pt)
    with pytest.raises(ValueError):
        nearest_triangle(None,(0,0,0))


@pytest.mark.parametrize("bad",[None,True,"nan",float("nan"),
                                float("inf"),-1,10**400,[],{}])
def test_corrupt_surface_result_rejected(bad):
    with pytest.raises(ValueError):
        SurfaceDistance("x",bad,(0,0,0),0,(1,0,0)).check()
    with pytest.raises(ValueError):
        SurfaceProbe("NEAR","lens",bad,(0.,0.,0.),0).check()


def test_reject_invalid_gpu_surface_probe_before_gl_context():
    instance=object.__new__(GPUEyePreview)
    for bad in (True,object(),{},SurfaceProbe("NEAR","lens",float("nan"),
                                             (0.,0.,0.),0),
                SurfaceProbe("UNKNOWN","iris",.1,(0.,0.,0.),0)):
        with pytest.raises(ValueError):
            instance.render(View(),60.,surface_probe=bad)


def test_seeded_500_nearest_surface_queries_are_deterministic_and_finite():
    rng=random.Random(47)
    idx=_static_indexes()["lens"]
    for i in range(500):
        p=tuple(rng.uniform(-1.,1.) for _ in range(3))
        a=nearest_triangle(idx,p)
        b=nearest_triangle(idx,p)
        assert a==b
        if a:
            assert all(math.isfinite(v) for v in (*a.point,a.distance))
            assert sum(a.barycentric)==pytest.approx(1.,abs=1e-8)
