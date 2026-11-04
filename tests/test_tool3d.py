"""Synthetic 3D instrument visibility and geometry dirty tests.

These tests never claim physical microneedle shape/force or clinical validity.
"""
import math

import pytest

from ophthosim.geometry import Mesh
from ophthosim.gl_preview import GPUEyePreview, View, pack_mesh
from ophthosim.input3d import Surgery3DController, ToolPose, eye_to_pixel
from ophthosim.tool3d import stylus_mesh, visible_stylus


def _entry():
    c = Surgery3DController()
    for _check in ("identity", "site", "iol_plan"): c.command("verify", _check)
    assert c.command("confirm")
    assert c.command("prepare")
    return c


def _touch(c):
    x, y = c.game._entry_target[0]
    pixel = eye_to_pixel(x, y, c.tool_depth, 1280, 720, c.view)
    assert pixel
    assert c.pointer(*pixel, 1280, 720, fresh_press=True)
    return c


def test_cached_tool_is_bounded_and_closed():
    mesh = stylus_mesh()
    assert isinstance(mesh, Mesh)
    assert mesh is stylus_mesh()
    mesh.validate()
    assert len(mesh.vertices) <= 128 and len(mesh.faces) <= 256
    assert min(z for x, y, z in mesh.vertices) < 0.
    assert max(z for x, y, z in mesh.vertices) > .3
    assert all(math.hypot(x, y) < .03 for x, y, z in mesh.vertices)
    vb, ib, count = pack_mesh(mesh)
    assert len(vb) == 24 * len(mesh.vertices)
    assert len(ib) == 4 * count
    assert count == len(mesh.faces) * 3


def test_default_and_preoperative_tool_is_hidden():
    c = Surgery3DController()
    assert visible_stylus(c) is None
    for _check in ("identity", "site", "iol_plan"): c.command("verify", _check)
    c.command("confirm")
    assert visible_stylus(c) is None


def test_tool_pose_follows_valid_guarded_3d_click():
    c = _touch(_entry())
    point = visible_stylus(c)
    assert point is not None
    assert point == pytest.approx((.19, .04, .04), abs=.005)
    assert c.last_pose is not None
    # Viewer never changes the underlying game state.
    before = c.game.snapshot()
    assert visible_stylus(c) == point
    assert c.game.snapshot() == before


def test_pause_abort_and_stage_transitions_hide_previous_pose():
    c = _touch(_entry())
    assert visible_stylus(c) is not None
    assert c.command("pause")
    assert visible_stylus(c) is None
    assert c.command("pause")
    # Clearing a paused pose is deliberate: avoid automatically reusing an
    # earlier potentially unsafe instrument position after unpausing.
    assert visible_stylus(c) is None
    x,y=c.game._entry_target[0]
    px=eye_to_pixel(x,y,c.tool_depth,1280,720,c.view)
    before=c.game.snapshot()
    c.inspect(*px,1280,720)
    assert c.game.snapshot()==before
    assert visible_stylus(c) is not None
    assert c.command("abort")
    assert visible_stylus(c) is None
    c.restart()
    assert visible_stylus(c) is None


def test_patient_safety_hold_hides_instrument():
    c = Surgery3DController("motion")
    for _check in ("identity", "site", "iol_plan"): c.command("verify", _check)
    c.command("confirm")
    c.command("prepare")
    for x, y in c.game._entry_target:
        pt = eye_to_pixel(x, y, c.tool_depth, 1280, 720, c.view)
        c.pointer(*pt, 1280, 720, fresh_press=True)
    assert c.game.patient.alert == "PATIENT MOTION"
    assert visible_stylus(c) is None


def test_incorrect_depth_pose_is_hidden_not_used_for_collision():
    c = _touch(_entry())
    c.last_pose = ToolPose(.5, .5, 0., 0., .2)
    assert visible_stylus(c) is None


@pytest.mark.parametrize("bad", [None, True, "x", float("nan"),
                                  float("inf"), 10**400, -10**400])
def test_dirty_visual_pose_does_not_crash(bad):
    c = _entry()
    c.last_pose = ToolPose(.4, .6, bad, 0., c.tool_depth)
    assert visible_stylus(c) is None
    c.last_pose = ToolPose(bad, .6, 0., 0., c.tool_depth)
    assert visible_stylus(c) is None


@pytest.mark.parametrize("bad", [None, True, "x", [], {}, float("nan"),
                                  float("inf"), 10**400])
def test_render_rejects_invalid_gpu_pose_before_using_context(bad):
    # GPU context is intentionally not constructed. Inputs fail closed before
    # window/driver interaction and can be tested on headless CI.
    obj = object.__new__(GPUEyePreview)
    with pytest.raises(ValueError):
        obj.render(View(), 60., tool_pose=(bad, 0., 0.))


@pytest.mark.parametrize("bad", [None, True, "x", 0, (1,2), (), [0,0,0,0], {}])
def test_invalid_gpu_vector_shape_fails_before_gl_context(bad):
    obj = object.__new__(GPUEyePreview)
    with pytest.raises(ValueError):
        obj.render(View(), 60., tool_pose=bad if bad is not None else (0, 0))
