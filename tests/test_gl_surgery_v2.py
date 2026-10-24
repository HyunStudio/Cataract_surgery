"""3D surgery parity with engine v2 (SDL dummy surface; no OpenGL needed)."""
import json
import math
import os

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from ophthosim.engine import (COMPLICATIONS, ENDINGS, FINAL_CHECKS, HAZARDS, PREOP_CHECKS,
                              TOOL_NAMES, Phase)
from ophthosim.gl_surgery import SurgeryHUD, advance_preop, main, save_session
from ophthosim.input3d import STAGE_DEPTH, Surgery3DController, eye_to_pixel
from ophthosim.surface_probe3d import probe_surface
from ophthosim.tool3d import visible_stylus

from surgeon_helpers import SITES, use3d

W, H = 1280, 720


def press(c, x, y, fresh=False):
    pixel = eye_to_pixel(x, y, c.tool_depth, W, H, c.view)
    assert pixel is not None
    return c.pointer(*pixel, W, H, fresh_press=fresh)


def to_close(c, stop_on_alert=False, manage=True):
    """Drive along the ideal path to CLOSE with 3D clicks: assess alerts
    (unless told to stop), manage complications with their instrument, and
    use viscoelastic and hydrodissection where a surgeon would."""
    g = c.game
    for _ in range(2000):
        if g.phase in (Phase.CLOSE,) or g.ending:
            return
        if g.patient.alert:
            if stop_on_alert:
                return
            c.command("assess")
            continue
        if g.pending and manage:
            comp = COMPLICATIONS[g.pending[0]]
            if comp.remedy == "escalate":
                c.command("escalate")
            else:
                use3d(c, comp.remedy, *SITES[comp.site])
            continue
        if g.phase == Phase.PREOP:
            assert advance_preop(c)
        elif g.phase == Phase.ANESTHESIA:
            c.command("prepare")
        elif g.phase == Phase.ENTRY:
            for i, (x, y) in enumerate(g._entry_target):
                if i in g._entered or g.patient.alert or g.phase != Phase.ENTRY:
                    continue
                press(c, x, y, True)
                if not g.ovd_chamber and g.phase == Phase.ENTRY and not g.patient.alert:
                    use3d(c, "ovd_cannula")
        elif g.phase == Phase.CAPSULE:
            if not g.ovd_chamber:
                use3d(c, "ovd_cannula")
            for i in range(24):
                if g.phase != Phase.CAPSULE or g.patient.alert:
                    break
                a = (i + .5) * math.tau / 24
                press(c, .5 + .28 * math.cos(a), .5 + .28 * math.sin(a))
        elif g.phase in (Phase.PHACO, Phase.CORTEX):
            if g.phase == Phase.PHACO and not g.hydro_done and g.eye.opacity == 1.0:
                use3d(c, "hydro_cannula")
            press(c, .5, .5)
            c.advance_clock(1 / 60)        # held at 60 Hz: tissue stress decays
        elif g.phase == Phase.IOL:
            if not g.ovd_bag:
                use3d(c, "ovd_cannula")
            press(c, .5, .5, True)


def test_space_advances_checklist_then_starts():
    c = Surgery3DController()
    for count in (1, 2, 3):
        assert advance_preop(c)
        assert len(c.game.eye.preop_checks) == count and c.game.phase == Phase.PREOP
    assert advance_preop(c)
    assert c.game.phase == Phase.ANESTHESIA


def test_decentered_iol_is_repositioned_with_a_fresh_3d_click():
    c = Surgery3DController("decenter", seed=3)
    to_close(c)
    assert c.game.phase == Phase.CLOSE and c.game.patient.alert == "IOL DECENTRATION"
    assert c.target_depth is None or c.game.patient.alert   # held: no tool
    assert c.command("assess")
    assert c.target_depth == STAGE_DEPTH[Phase.IOL]
    assert not c.command("verify", "alignment")
    pixel = eye_to_pixel(.5, .5, c.tool_depth, W, H, c.view)
    contact = c.inspect(*pixel, W, H)
    assert contact.status == "TARGET" and visible_stylus(c) is not None
    assert probe_surface(c) is not None
    assert not press(c, .5, .5)               # held drag cannot place
    assert c.game._decentered
    assert press(c, .5, .5, True)
    assert not c.game._decentered and c.target_depth is None
    for item in FINAL_CHECKS:
        assert c.command("verify", item)
    assert c.game.ending == "COMPLICATION MANAGED"


def test_close_without_decentration_has_no_tool():
    c = Surgery3DController(seed=3)
    to_close(c)
    assert c.game.phase == Phase.CLOSE and c.target_depth is None
    pixel = eye_to_pixel(.5, .5, STAGE_DEPTH[Phase.IOL], W, H, c.view)
    assert c.inspect(*pixel, W, H).status == "INACTIVE"
    assert not c.pointer(*pixel, W, H, fresh_press=True)


def _surface():
    pygame = pytest.importorskip("pygame")
    pygame.init()
    surf = pygame.Surface((W, H), pygame.SRCALPHA)
    font = pygame.font.SysFont("segoeui", 20)
    title = pygame.font.SysFont("segoeui", 28, bold=True)
    return pygame, surf, font, title


@pytest.mark.parametrize("lang", ["en", "ko"])
def test_hud_renders_every_alert_and_ending(lang):
    pygame, surf, font, title = _surface()
    card = SurgeryHUD.card_rect(W, H)
    try:
        frames = {}
        for case in HAZARDS:
            c = Surgery3DController(case, seed=5)
            hud = SurgeryHUD(c)
            hud.lang = lang
            to_close(c, stop_on_alert=True)
            if not c.game.patient.alert:          # leak fires on the final checks
                for item in FINAL_CHECKS:
                    c.command("verify", item)
            assert c.game.patient.alert == HAZARDS[case][1], case
            surf.fill((0, 0, 0, 0))
            hud.draw(pygame, surf, c.view, W, H, font, title)
            frames[case] = pygame.image.tobytes(surf.subsurface(card), "RGBA")
            c.command("assess")
            if c.game.pending:                    # management card replaces the hold card
                surf.fill((0, 0, 0, 0))
                hud.draw(pygame, surf, c.view, W, H, font, title)
                assert pygame.image.tobytes(surf.subsurface(card), "RGBA") != frames[case]
        assert len(set(frames.values())) == len(frames)
        endings = {}
        for case, action in (("normal", None), ("motion", "assess"), ("normal", "abort"),
                             ("vitals", "timeout"), ("hyphema", "ignore")):
            c = Surgery3DController(case, seed=5)
            hud = SurgeryHUD(c)
            hud.lang = lang
            if action == "abort":
                c.command("abort")
            else:
                to_close(c, stop_on_alert=action in ("timeout", "ignore"))
                if c.game.patient.alert and action == "timeout":
                    for _ in range(700):
                        c.advance_clock(.05)
                elif c.game.patient.alert:
                    c.command("assess")
                    to_close(c, manage=action != "ignore")
                for item in FINAL_CHECKS:
                    c.command("verify", item)
                if action == "timeout" and not c.game.ending:
                    pytest.fail("vitals case should have timed out")
            assert c.game.ending, case
            surf.fill((0, 0, 0, 0))
            hud.draw(pygame, surf, c.view, W, H, font, title)
            endings[c.game.ending] = pygame.image.tobytes(surf.subsurface((340, 145, 600, 410)), "RGBA")
        assert set(endings) == set(ENDINGS)
        assert len(set(endings.values())) == len(ENDINGS)
    finally:
        pygame.quit()


def test_preop_chart_card_and_instrument_row():
    pygame, surf, font, title = _surface()
    try:
        c = Surgery3DController("bleed")
        hud = SurgeryHUD(c)
        hud.draw(pygame, surf, c.view, W, H, font, title)
        card = pygame.image.tobytes(surf.subsurface(SurgeryHUD.card_rect(W, H)), "RGBA")
        assert len(set(card[i:i + 4] for i in range(0, len(card), 4))) > 20
        while c.game.phase in (Phase.PREOP, Phase.ANESTHESIA):
            advance_preop(c) if c.game.phase == Phase.PREOP else c.command("prepare")
        slots = dict(SurgeryHUD.tray_slots(W, H))
        assert set(slots) == set(TOOL_NAMES)
        from ophthosim.gl_surgery import tray_pick
        x, y, w, h = slots["cautery"]
        assert tray_pick(c, x + 3, y + 3, W, H) and c.game.tool == "cautery"
        assert not tray_pick(c, W // 2, H // 2, W, H)
    finally:
        pygame.quit()


def test_preop_hud_shows_checklist_not_tool():
    pygame, surf, font, title = _surface()
    try:
        c = Surgery3DController()
        hud = SurgeryHUD(c)
        hud.draw(pygame, surf, c.view, W, H, font, title)
        before = pygame.image.tobytes(surf.subsurface((20, 345, 230, 90)), "RGBA")
        advance_preop(c)
        surf.fill((0, 0, 0, 0))
        hud.draw(pygame, surf, c.view, W, H, font, title)
        assert pygame.image.tobytes(surf.subsurface((20, 345, 230, 90)), "RGBA") != before
    finally:
        pygame.quit()


def test_3d_export_writes_explained_report(tmp_path):
    c = Surgery3DController("haze", seed=8)
    to_close(c)
    for item in FINAL_CHECKS:
        c.command("verify", item)
    first, second = save_session(c, tmp_path, lang="ko")
    report = json.loads((tmp_path / "gl3d_haze_standard_seed_8.report.json").read_text("utf-8"))
    assert report["language"] == "ko" and report["score"] == c.game.score()
    assert (tmp_path / "gl3d_haze_standard_seed_8.metrics.csv").is_file()
    assert first.is_file() and second.is_file()


def test_cli_validation():
    for argv in (["--difficulty", "easy"], ["--lang", "de"], ["--case", "nope"],
                 ["--seed", str(2**64)]):
        with pytest.raises(SystemExit):
            main(argv)


def test_t_key_cycles_tools_and_hard_requires_choice():
    from ophthosim.gl_surgery import cycle_tool, quick_use
    c = Surgery3DController(difficulty="hard")
    while c.game.phase == Phase.PREOP:
        advance_preop(c)
    c.command("prepare")
    x, y = c.game._entry_target[0]
    assert not press(c, x, y, True) and c.game.wrong_tool == 1
    seen = []
    for _ in TOOL_NAMES:
        assert cycle_tool(c)
        seen.append(c.game.tool)
    assert seen == list(TOOL_NAMES)
    assert c.game.tool == TOOL_NAMES[-1]
    assert cycle_tool(c, -1) and c.game.tool == TOOL_NAMES[-2]
    while c.game.tool != "keratome":
        cycle_tool(c)
    assert press(c, x, y, True)
    assert quick_use(c, "ovd_cannula") and c.game.ovd_chamber


def test_resume_controller_restores_verified_autosave(tmp_path):
    from ophthosim.autosave import write_autosave
    from ophthosim.gl_surgery import resume_controller
    c = Surgery3DController("vitals", seed=4)
    to_close(c, stop_on_alert=True)
    for _ in range(30):
        c.advance_clock(.05)
    path = write_autosave(c.game, tmp_path / "a.replay.jsonl")
    other = Surgery3DController()
    assert resume_controller(other, path)
    assert other.game.snapshot() == c.game.snapshot()
    assert other.view.phase == c.view.phase
    path.write_text("broken", encoding="utf-8")
    with pytest.raises(ValueError):
        resume_controller(Surgery3DController(), path)
    c.command("abort")
    assert write_autosave(c.game, path) is None and not path.exists()
