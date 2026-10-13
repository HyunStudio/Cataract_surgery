"""Share one read-only 3D surface observation across GPU and HUD frames.

No clinical interaction or Game mutation: these are synthetic display tests.
"""
import math

import pytest

import ophthosim.gl_surgery as gl_surgery
import ophthosim.surface_probe3d as probes
from ophthosim.engine import Phase
from ophthosim.gl_surgery import SurgeryHUD
from ophthosim.input3d import Surgery3DController, eye_to_pixel
from ophthosim.surface_probe3d import SurfaceProbe
from ophthosim.vision3d import visual_feedback


def initial_hover():
    c=Surgery3DController(seed=19)
    assert c.command("confirm")
    assert c.command("prepare")
    p=eye_to_pixel(.69,.46,c.tool_depth,1280,720,c.view)
    assert p is not None
    c.inspect(*p,1280,720)
    assert c.last_pose is not None
    return c


def _ui():
    pygame=pytest.importorskip("pygame")
    pygame.init()
    surf=pygame.Surface((1280,720),pygame.SRCALPHA)
    font=pygame.font.SysFont("segoeui",20)
    large=pygame.font.SysFont("segoeui",28,bold=True)
    return pygame,surf,font,large


def _label_pixels(hud,pg,surf,font,large):
    surf.fill((0,0,0,0))
    hud.draw(pg,surf,hud.controller.view,1280,720,font,large)
    # The "MESH GAP" annotation is in this HUD-only region, outside side
    # panels and away from the eye graphics.
    return pg.image.tobytes(surf.subsurface((480,124,440,27)),"RGBA")


def test_hud_draw_reuses_prepared_surface_probe_and_never_reruns_bvh(monkeypatch):
    c=initial_hover()
    hud=SurgeryHUD(c)
    calls=[]
    actual=probes.nearest_triangle
    def counted(*args,**kwargs):
        calls.append(1)
        return actual(*args,**kwargs)
    monkeypatch.setattr(probes,"nearest_triangle",counted)
    status=probes.probe_surface(c,visual_feedback(c.game))
    assert status is not None
    assert len(calls)==2  # original static iris + lens geometries
    snapshot=c.game.snapshot()
    replay=c.game.export_replay_jsonl()
    hud.set_frame_proximity(status)

    def forbidden(*_args,**_kwargs):
        raise AssertionError("HUD re-executed expensive mesh proximity")
    monkeypatch.setattr(gl_surgery,"probe_surface",forbidden)
    pg,surf,font,large=_ui()
    try:
        active=_label_pixels(hud,pg,surf,font,large)
        # Multiple UI paint calls within one same visual frame MUST not query.
        for _ in range(5):
            assert _label_pixels(hud,pg,surf,font,large)==active
        assert len(calls)==2
        hud.set_frame_proximity(None)
        hidden=_label_pixels(hud,pg,surf,font,large)
        assert active!=hidden
        assert c.game.snapshot()==snapshot
        assert c.game.export_replay_jsonl()==replay
    finally:
        pg.quit()


def test_explicit_same_phase_cursor_change_invalidates_prepared_hud():
    c=initial_hover()
    hud=SurgeryHUD(c)
    status=probes.probe_surface(c)
    assert status is not None
    hud.set_frame_proximity(status)
    pg,surf,font,large=_ui()
    try:
        reference=_label_pixels(hud,pg,surf,font,large)
        p=eye_to_pixel(.80,.43,c.tool_depth,1280,720,c.view)
        c.inspect(*p,1280,720)
        assert c.last_pose is not None
        assert _label_pixels(hud,pg,surf,font,large)!=reference
    finally:
        pg.quit()


def test_camera_orbit_phase_change_and_safety_hold_hide_stale_probe():
    c=initial_hover()
    hud=SurgeryHUD(c)
    status=probes.probe_surface(c)
    assert status is not None
    hud.set_frame_proximity(status)
    pg,surf,font,large=_ui()
    try:
        ready=_label_pixels(hud,pg,surf,font,large)
        c.view.key("left")
        assert _label_pixels(hud,pg,surf,font,large)!=ready
        c.view.key("right")
        assert _label_pixels(hud,pg,surf,font,large)==ready
        c.game.phase=Phase.CAPSULE
        assert _label_pixels(hud,pg,surf,font,large)!=ready
        c.game.phase=Phase.ENTRY
        assert c.command("pause")
        assert _label_pixels(hud,pg,surf,font,large)!=ready
        with pytest.raises(ValueError):
            hud.set_frame_proximity(status)  # no paused tool pose
        assert c.command("pause")
        assert _label_pixels(hud,pg,surf,font,large)!=ready  # no stale tool
    finally:
        pg.quit()


@pytest.mark.parametrize("bad",[
    1,True,"probe",[],{},object(),
    SurfaceProbe("CLOSE","iris",float("nan"),(0.,0.,0.),1),
    SurfaceProbe("WRONG","iris",.04,(0.,0.,0.),1),
])
def test_hud_rejects_dirty_precomputed_values_without_game_mutation(bad):
    c=initial_hover()
    hud=SurgeryHUD(c)
    old=c.game.snapshot()
    with pytest.raises(ValueError):
        hud.set_frame_proximity(bad)
    assert c.game.snapshot()==old


def test_proximity_can_be_cleared_after_restart_and_has_no_stale_display():
    c=initial_hover()
    hud=SurgeryHUD(c)
    hud.set_frame_proximity(probes.probe_surface(c))
    assert hud.frame_proximity is not None
    c.restart()
    pg,surf,font,large=_ui()
    try:
        changed=_label_pixels(hud,pg,surf,font,large)
        hud.set_frame_proximity(None)
        assert _label_pixels(hud,pg,surf,font,large)==changed
    finally:
        pg.quit()
