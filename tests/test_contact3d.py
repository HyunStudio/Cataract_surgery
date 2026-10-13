"""Stage-specific contact guide: non-mutating safety and geometry tests."""
import math
import random

import pytest

from ophthosim.contact3d import ContactGuide, contact_guide, guide_ring_mesh
from ophthosim.engine import Phase
from ophthosim.gl_preview import GPUEyePreview, View, pack_mesh
from ophthosim.input3d import Surgery3DController, ToolPose, eye_to_pixel
from ophthosim.replay import ReplayGame

W,H = 1280,720


def advance_to_capsule(c):
    assert c.command("confirm")
    assert c.command("prepare")
    for x,y in c.game._entry_target:
        c.adjust_depth_to_target()
        pt = eye_to_pixel(x,y,c.tool_depth,W,H,c.view)
        assert c.pointer(*pt,W,H,fresh_press=True)
    assert c.game.phase == Phase.CAPSULE


def preview(c,x,y,*,align=True):
    if align:
        c.adjust_depth_to_target()
    p=eye_to_pixel(x,y,c.tool_depth,W,H,c.view)
    assert p is not None
    return c.inspect(*p,W,H)


def test_guide_cache_closed_ring_and_gpu_packing():
    m=guide_ring_mesh()
    assert m is guide_ring_mesh()
    m.validate()
    assert len(m.faces)==64
    vb,ib,n=pack_mesh(m)
    assert len(vb)==len(m.vertices)*24
    assert len(ib)==4*n
    assert all(-.06 < v < .06 for pt in m.vertices for v in pt)


def test_hover_is_read_only_and_replay_identical():
    c=Surgery3DController()
    c.command("confirm")
    c.command("prepare")
    snapshot=c.game.snapshot()
    journal=c.game.export_replay_jsonl()
    probe=preview(c,.69,.46)
    assert probe.status=="TARGET" and probe.location
    assert c.last_contact==probe and c.last_pose is not None
    assert c.game.snapshot()==snapshot
    assert c.game.export_replay_jsonl()==journal
    # Hover never advances a task; only actual pointer can advance it.
    assert c.game.eye.entry_hits==0
    c.adjust_depth_to_target()
    p=eye_to_pixel(.69,.46,c.tool_depth,W,H,c.view)
    assert c.pointer(*p,W,H, fresh_press=True)
    assert c.game.eye.entry_hits==1
    assert preview(c,.69,.46).status=="VISITED"


def test_capsule_and_lens_stage_targets_match_game_task_ranges():
    c=Surgery3DController()
    advance_to_capsule(c)
    assert preview(c,.5+.28,.5).status=="TARGET"
    assert preview(c,.5,.5).status=="NEAR"
    for i in range(24):
        if c.game.phase!=Phase.CAPSULE:
            break
        a=(i+.5)*math.tau/24
        c.adjust_depth_to_target()
        p=eye_to_pixel(.5+.28*math.cos(a),.5+.28*math.sin(a),
                       c.tool_depth,W,H,c.view)
        c.pointer(*p,W,H)
    assert c.game.phase == Phase.PHACO
    assert c.command("hydro")
    assert preview(c,.5,.5).status=="TARGET"
    assert preview(c,.95,.95).status=="OUTSIDE"
    while c.game.phase in (Phase.PHACO, Phase.CORTEX):
        c.adjust_depth_to_target()
        p=eye_to_pixel(.5,.5,c.tool_depth,W,H,c.view)
        assert c.pointer(*p,W,H)
    assert c.game.phase == Phase.IOL
    assert preview(c,.5,.5).status=="TARGET"
    assert preview(c,.7,.5).status=="NEAR"
    # Preview is NOT an action authority. Near-alignment placement remains
    # governed by the existing game state machine.
    c.adjust_depth_to_target()
    p=eye_to_pixel(.7,.5,c.tool_depth,W,H,c.view)
    assert c.pointer(*p,W,H,fresh_press=True)
    assert c.game.phase == Phase.IOL


def test_wrong_depth_hides_stale_guide_without_phase_change():
    c=Surgery3DController()
    c.command("confirm")
    c.command("prepare")
    assert preview(c,.69,.46).status=="TARGET"
    snapshot=c.game.snapshot()
    c.adjust_depth(1)
    c.adjust_depth(1)
    c.adjust_depth(1)
    assert preview(c,.69,.46,align=False).status=="DEPTH"
    assert c.last_pose is None
    assert c.last_contact.location is None
    assert c.game.snapshot()==snapshot
    p=eye_to_pixel(.69,.46,c.tool_depth,W,H,c.view)
    assert not c.pointer(*p,W,H)
    assert c.depth_rejections==1


def test_safety_alert_forces_hold_and_no_hover_action():
    c=Surgery3DController("motion")
    advance_to_capsule(c)
    assert c.game.patient.alert == "PATIENT MOTION"
    snapshot=c.game.snapshot()
    status=preview(c,.78,.5)
    assert status==ContactGuide("HOLD")
    assert c.last_pose is None
    assert c.game.snapshot()==snapshot
    assert c.command("abort")
    assert preview(c,.78,.5).status=="HOLD"
    assert ReplayGame.replay_jsonl(c.game.export_replay_jsonl()).ending=="SAFELY ABORTED"


def test_camera_rotated_hover_matches_same_world_position():
    c=Surgery3DController()
    c.command("confirm")
    c.command("prepare")
    for yaw,pitch,zoom in ((0,0,3.6),(.55,.22,4.),(-.8,-.45,2.8)):
        c.view.yaw,c.view.pitch,c.view.zoom=yaw,pitch,zoom
        v=preview(c,.69,.46)
        assert v.status=="TARGET"
        assert v.location==pytest.approx((.19,.04,.04),abs=1e-10)


@pytest.mark.parametrize("bad",[None,True,[],{},float("nan"),float("inf"),
                               10**400,-10**400,"0"])
def test_corrupt_depth_fails_without_overflow(bad):
    c=Surgery3DController()
    with pytest.raises(ValueError):
        contact_guide(c.game,None,bad,c.target_depth)


@pytest.mark.parametrize("bad",[None,True,[],{},float("nan"),float("inf"),
                               10**400,-10**400,"0"])
def test_corrupt_world_pose_fails_without_overflow(bad):
    c=Surgery3DController()
    c.command("confirm")
    c.command("prepare")
    c.adjust_depth_to_target()
    pose=ToolPose(.5,.5,bad,0.,c.tool_depth)
    with pytest.raises(ValueError):
        contact_guide(c.game,pose,c.tool_depth,c.target_depth)


def test_contact_guide_invalid_state_or_location_rejected():
    for invalid in (ContactGuide("UNSAFE"),ContactGuide("HOLD",(0.,0.,0.)),
                    ContactGuide("TARGET",(0.,0.)),
                    ContactGuide("TARGET",(0.,float("nan"),0.)),
                    ContactGuide("TARGET",(0.,10**400,0.))):
        with pytest.raises(ValueError):
            invalid.check()


def test_renderer_checks_bad_guide_before_gl_context():
    obj=object.__new__(GPUEyePreview)
    for bad in (ContactGuide("HOLD",(0.,0.,0.)),ContactGuide("BAD"),True,{}):
        with pytest.raises(ValueError):
            obj.render(View(),60.,contact=bad)


def test_seeded_1500_hover_points_cannot_change_game():
    rng=random.Random(261)
    c=Surgery3DController()
    c.command("confirm")
    c.command("prepare")
    prior=c.game.export_replay_jsonl()
    snapshot=c.game.snapshot()
    for _ in range(1500):
        c.view.yaw=rng.uniform(-1.2,1.2)
        c.view.pitch=rng.uniform(-.8,.8)
        c.view.zoom=rng.uniform(2.6,5.)
        c.inspect(rng.uniform(-100,1400),rng.uniform(-100,900),W,H)
        if c.last_contact is not None:
            c.last_contact.check()
    assert c.game.export_replay_jsonl()==prior
    assert c.game.snapshot()==snapshot
