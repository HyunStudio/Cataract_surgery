"""Unit, integration, and dirty tests for 3D-to-surgery semantic adapter."""
from __future__ import annotations

import math
import random

import pytest

from ophthosim.engine import Phase
from ophthosim.input3d import (DEPTH_TOLERANCE, STAGE_DEPTH,
                               Surgery3DController, eye_to_pixel,
                               eye_to_world, pointer_to_eye)
from ophthosim.replay import ReplayGame

W, H = 1280, 720


def gesture(controller, x, y, *, fresh_press=False):
    controller.adjust_depth_to_target()
    point = eye_to_pixel(x, y, controller.tool_depth, W, H, controller.view)
    assert point is not None
    return controller.pointer(*point, W, H, fresh_press=fresh_press)


def enter_capsule(controller):
    assert controller.command("confirm")
    assert controller.command("prepare")
    assert controller.game.phase == Phase.ENTRY
    for x, y in controller.game._entry_target:
        assert gesture(controller, x, y)
    assert controller.game.phase == Phase.CAPSULE


def enter_phaco(controller):
    enter_capsule(controller)
    for i in range(24):
        theta = (i + .5) * math.tau / 24
        gesture(controller, .5 + .28 * math.cos(theta),
                .5 + .28 * math.sin(theta))
    assert controller.game.phase == Phase.PHACO


def test_full_synthetic_procedure_in_3d_input_mode_and_replay():
    c = Surgery3DController(seed=28)
    enter_phaco(c)
    while c.game.phase == Phase.PHACO:
        assert gesture(c, .5, .5)
    assert c.game.phase == Phase.CORTEX
    while c.game.phase == Phase.CORTEX:
        assert gesture(c, .5, .5)
    assert c.game.phase == Phase.IOL
    assert gesture(c, .5, .5, fresh_press=True)
    assert c.game.phase == Phase.CLOSE
    for item in ("alignment", "wound", "handoff"):
        assert c.command("verify", item)
    assert c.game.phase == Phase.RECOVERY
    assert c.game.ending == "SIMULATION COMPLETE"
    replayed = ReplayGame.replay_jsonl(c.game.export_replay_jsonl())
    assert replayed.snapshot() == c.game.snapshot()
    assert replayed.export_jsonl() == c.game.export_jsonl()


@pytest.mark.parametrize("case,trigger,alert", [
    ("motion", Phase.CAPSULE, "PATIENT MOTION"),
    ("vitals", Phase.PHACO, "PATIENT MONITOR"),
    ("capsule", Phase.PHACO, "CAPSULE INTEGRITY"),
])
def test_3d_scenario_safety_holds_prevent_click_bypass(case,trigger,alert):
    c = Surgery3DController(case=case)
    if trigger == Phase.CAPSULE:
        enter_capsule(c)
    else:
        enter_phaco(c)
    assert c.game.patient.alert == alert and c.game.paused
    before = c.game.snapshot()
    for _ in range(12):
        assert not c.pointer(640,360,W,H)
    assert c.game.snapshot() == before
    assert c.command("assess")
    if case == "capsule":
        assert c.game.phase == Phase.ABORTED
        assert c.game.ending == "SAFELY ABORTED"
    else:
        assert not c.game.patient.alert and not c.game.paused


def test_camera_rotation_zoom_roundtrip():
    c = Surgery3DController()
    c.command("confirm")
    c.command("prepare")
    p = (.69,.46)
    for yaw,pitch,zoom in [(0,0,3.6),(.5,.2,4.4),(-.65,-.45,2.8)]:
        c.view.yaw,c.view.pitch,c.view.zoom = yaw,pitch,zoom
        c.adjust_depth_to_target()
        px = eye_to_pixel(*p,c.tool_depth,W,H,c.view)
        hit = pointer_to_eye(*px,W,H,c.view,c.tool_depth)
        assert hit is not None
        assert (hit.eye_x,hit.eye_y) == pytest.approx(p,abs=1e-10)
    assert gesture(c,*p)


def test_wrong_depth_cannot_mutate_surgery_state():
    c = Surgery3DController()
    c.command("confirm")
    c.command("prepare")
    c.tool_depth = c.target_depth + DEPTH_TOLERANCE + .01
    before = c.game.snapshot()
    pt = eye_to_pixel(.69,.46,c.tool_depth,W,H,c.view)
    assert not c.pointer(*pt,W,H)
    assert c.game.snapshot() == before
    assert c.depth_rejections == 1
    c.tool_depth = c.target_depth
    assert gesture(c,.69,.46)


def test_manual_depth_changes_are_bounded_and_invalid_rejected():
    c = Surgery3DController()
    for _ in range(300):
        assert c.adjust_depth(-1) >= -.3
    assert c.tool_depth == -.3
    for _ in range(300):
        assert c.adjust_depth(1) <= .2
    assert c.tool_depth == .2
    for bad in (0, 2, False, None, "1", 1.2, 10**400):
        with pytest.raises(ValueError):
            c.adjust_depth(bad)


def test_abort_while_alerted_from_3d_and_restart():
    c = Surgery3DController("motion", 49)
    enter_capsule(c)
    assert c.command("abort")
    assert c.game.phase == Phase.ABORTED
    assert not c.command("prepare")
    replayed = ReplayGame.replay_jsonl(c.game.export_replay_jsonl())
    assert replayed.snapshot() == c.game.snapshot()
    c.restart()
    assert c.game.phase == Phase.PREOP and c.game.case == "motion"
    assert c.game.seed == 49 and c.last_pose is None


@pytest.mark.parametrize("bad", [None, True, False, "bad", float("nan"),
                                  float("inf"), 10**400, [], {}])
def test_bad_screen_coordinates_are_rejected(bad):
    c = Surgery3DController()
    c.command("confirm")
    c.command("prepare")
    c.adjust_depth_to_target()
    with pytest.raises(ValueError):
        c.pointer(bad,300,W,H)


@pytest.mark.parametrize("bad", [-.1, 1.1, float("inf"), float("nan"),
                                  10**400, None, True])
def test_invalid_eye_coordinates_rejected(bad):
    with pytest.raises(ValueError):
        eye_to_world(bad,.5,.04)


def test_screen_miss_and_rejected_commands_do_not_mutate_game():
    c = Surgery3DController()
    c.command("confirm")
    c.command("prepare")
    before = c.game.snapshot()
    assert c.pointer(-4,10,W,H) is False
    assert c.pointer(99999,10,W,H) is False
    assert c.command("delete_everything") is False
    assert c.game.snapshot() == before


def test_2000_randomized_3d_input_roundtrip_does_not_crash():
    rng = random.Random(404)
    c = Surgery3DController()
    c.command("confirm")
    c.command("prepare")
    for _ in range(2000):
        c.view.yaw = rng.uniform(-1.2,1.2)
        c.view.pitch = rng.uniform(-.8,.8)
        c.view.zoom = rng.uniform(2.6,5.0)
        c.pointer(rng.uniform(-100,1400),rng.uniform(-100,900),W,H)
    assert c.game.phase in {Phase.ENTRY, Phase.CAPSULE}
    assert len(c.game.journal) < 16000


def test_removal_hold_cannot_auto_place_iol():
    c = Surgery3DController()
    enter_phaco(c)
    # Even if a user keeps dragging well past the end of cleanup, the new
    # IOL phase cannot treat a continuous hold as a deliberate placement.
    for _ in range(500):
        gesture(c, .5, .5)
    assert c.game.phase == Phase.IOL
    assert c.game.eye.iol_alignment == 0.
    assert not gesture(c, .5, .5)
    assert gesture(c, .5, .5, fresh_press=True)
    assert c.game.phase == Phase.CLOSE
