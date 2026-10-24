"""Read-only synthetic 3D motion/haze feedback and accessibility dirty tests."""
import math
import random

import pytest

from ophthosim.engine import Game, Phase
from ophthosim.gl_preview import GPUEyePreview, View
from ophthosim.vision3d import VisualFeedback, visual_feedback


def _capsule_case(case="normal"):
    g=Game(case,seed=31)
    for _check in ("identity", "site", "iol_plan"): g.action("verify", _check)
    assert g.action("confirm")
    assert g.action("prepare")
    for x,y in g._entry_target:
        assert g.action("touch",x,y)
    assert g.phase==Phase.CAPSULE
    return g


def test_hazard_motion_is_deterministic_static_during_safety_hold():
    g=_capsule_case("motion")
    assert g.patient.alert=="PATIENT MOTION" and g.paused
    first=visual_feedback(g)
    assert first.motion_x > 0 and first.motion_y < 0
    assert first.haze > 0
    before=g.snapshot()
    for _ in range(100):
        g.tick(.05)
        assert visual_feedback(g)==first
    # The hold is timed (an unattended alert ends in a veto), but procedure
    # time, anatomy, patient values and phase stay frozen.
    after=g.snapshot()
    assert after["alert_elapsed"]==pytest.approx(5.0)
    for key in ("phase","time","eye","patient","paused","ending","score"):
        assert after[key]==before[key]
    assert g.action("assess")
    assert g.patient.motion==0.0
    assert visual_feedback(g).motion_x==0.0


def test_reduced_motion_suppresses_displacement_but_not_warning():
    g=_capsule_case("motion")
    before=g.snapshot()
    reduced=visual_feedback(g,reduced_motion=True)
    default=visual_feedback(g)
    assert default.motion_x!=0
    assert reduced.motion_x==0 and reduced.motion_y==0
    assert reduced.haze==default.haze
    assert reduced.reduced_motion
    assert g.patient.alert=="PATIENT MOTION" and g.paused
    assert g.snapshot()==before


def test_high_contrast_and_reduced_motion_do_not_affect_surgery():
    g=_capsule_case("capsule")
    before=g.snapshot()
    a=visual_feedback(g,high_contrast=True,reduced_motion=True)
    assert a.high_contrast and a.reduced_motion
    assert visual_feedback(g)==visual_feedback(g)
    assert g.snapshot()==before
    assert g.action("abort")
    assert g.phase==Phase.ABORTED


def test_synthetic_haze_follows_opacity_not_random_wall_clock():
    g=_capsule_case()
    g.phase=Phase.PHACO
    a=visual_feedback(g).haze
    g.eye.opacity=.45
    b=visual_feedback(g).haze
    g.eye.opacity=0.
    g.eye.cortex=0.
    c=visual_feedback(g).haze
    assert a>b>c
    g.phase=Phase.IOL
    assert visual_feedback(g).haze==0.


def test_motion_is_bounded_and_tracks_simulation_clock():
    g=_capsule_case()
    g.patient.motion=.88
    points=[]
    for i in range(1000):
        g.time=i*.01
        v=visual_feedback(g)
        v.check()
        assert abs(v.motion_x)<=.08 and abs(v.motion_y)<=.08
        points.append((v.motion_x,v.motion_y))
    assert len(set(points))>100
    g.paused=True
    assert visual_feedback(g)==visual_feedback(g)


@pytest.mark.parametrize("bad",[None,True,False,"oops",float("nan"),
                                float("inf"),-1.,1.01,10**400,[],{}])
@pytest.mark.parametrize("field",["motion","opacity","cortex"])
def test_bad_simulated_numeric_state_is_rejected(bad,field):
    g=_capsule_case()
    obj=g.patient if field=="motion" else g.eye
    setattr(obj,field,bad)
    with pytest.raises(ValueError):
        visual_feedback(g)


@pytest.mark.parametrize("bad",[None,True,"x",float("nan"),
                                float("inf"),-1,10**400])
def test_invalid_time_rejected(bad):
    g=_capsule_case()
    g.time=bad
    with pytest.raises(ValueError):
        visual_feedback(g)


@pytest.mark.parametrize("bad",[None,1,0,"false",[],{}])
def test_bad_accessibility_options_rejected(bad):
    g=_capsule_case()
    with pytest.raises(ValueError):
        visual_feedback(g,reduced_motion=bad)
    with pytest.raises(ValueError):
        visual_feedback(g,high_contrast=bad)


@pytest.mark.parametrize("bad",[None,True,"hi",float("nan"),
                                float("inf"),10**400,-100])
def test_invalid_shader_visual_feedback_fails_before_gl_context(bad):
    obj=object.__new__(GPUEyePreview)
    for field in ("motion_x","motion_y","haze"):
        kwargs={field:bad}
        with pytest.raises(ValueError):
            obj.render(View(),60.,vision=VisualFeedback(**kwargs))


def test_invalid_visual_object_fails_before_gl_context():
    obj=object.__new__(GPUEyePreview)
    for bad in (True,[],{},0,object()):
        with pytest.raises(ValueError):
            obj.render(View(),60.,vision=bad)


def test_high_count_seeded_visual_feedback_fuzz_is_safe():
    rng=random.Random(651)
    g=_capsule_case()
    for _ in range(2000):
        g.patient.motion=rng.random()
        g.eye.opacity=rng.random()
        g.eye.cortex=rng.random()
        g.time=rng.uniform(0,10_000)
        g.paused=rng.choice((True,False))
        a=visual_feedback(g,reduced_motion=rng.choice((True,False)),
                          high_contrast=rng.choice((True,False)))
        a.check()
        assert 0.<=a.haze<=.65
        assert all(math.isfinite(v) for v in (a.motion_x,a.motion_y,a.haze))
