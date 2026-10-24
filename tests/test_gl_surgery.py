"""GUI-independent and SDL dummy tests for 3D surgical game overlay."""
import math
import os
from pathlib import Path
import subprocess
import sys

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from ophthosim.engine import Phase
from ophthosim.gl_surgery import SurgeryHUD, save_session, PHASE_NAMES, CHECKS
from ophthosim.input3d import Surgery3DController, eye_to_pixel
from ophthosim.replay import ReplayGame


def test_full_3d_session_export_validates_replay(tmp_path):
    c=Surgery3DController(seed=12)
    for _check in ("identity", "site", "iol_plan"): c.command("verify", _check)
    c.command("confirm")
    c.command("prepare")
    for x,y in c.game._entry_target:
        pixel=eye_to_pixel(x,y,c.tool_depth,1280,720,c.view)
        assert c.pointer(*pixel,1280,720, fresh_press=True)
    for i in range(24):
        angle=(i+.5)*math.tau/24
        pixel=eye_to_pixel(.5+.28*math.cos(angle),.5+.28*math.sin(angle),
                           c.tool_depth,1280,720,c.view)
        c.pointer(*pixel,1280,720)
    for _ in range(82):
        pixel=eye_to_pixel(.5,.5,c.tool_depth,1280,720,c.view)
        c.pointer(*pixel,1280,720)
    assert c.game.phase==Phase.IOL
    pixel=eye_to_pixel(.5,.5,c.tool_depth,1280,720,c.view)
    assert c.pointer(*pixel,1280,720,fresh_press=True)
    for item in CHECKS:
        assert c.command("verify",item)
    assert c.game.phase == Phase.RECOVERY
    trace,replay = save_session(c,tmp_path)
    assert trace.is_file() and replay.is_file()
    again=ReplayGame.replay_jsonl(replay.read_text(encoding="utf-8"))
    assert again.snapshot()==c.game.snapshot()
    assert trace.read_text(encoding="utf-8")==again.export_jsonl()


def test_alert_branch_does_not_skip_safety_gate(tmp_path):
    c=Surgery3DController("motion")
    for _check in ("identity", "site", "iol_plan"): c.command("verify", _check)
    c.command("confirm")
    c.command("prepare")
    for x,y in c.game._entry_target:
        point=eye_to_pixel(x,y,c.tool_depth,1280,720,c.view)
        c.pointer(*point,1280,720,fresh_press=True)
    assert c.game.phase==Phase.CAPSULE and c.game.patient.alert
    assert not c.pointer(640,360,1280,720,fresh_press=True)
    c.command("abort")
    _,p=save_session(c,tmp_path)
    again=ReplayGame.replay_jsonl(p.read_text(encoding="utf-8"))
    assert again.ending=="SAFELY ABORTED"


def test_cli_help_does_not_require_opengl_context():
    proc=subprocess.run([sys.executable,"-m","ophthosim.gl_surgery","--help"],
                        capture_output=True,text=True)
    assert proc.returncode==0
    assert "--case" in proc.stdout and "--seed" in proc.stdout


def test_hud_render_all_surgical_phases_on_sdl_surface():
    pygame=pytest.importorskip("pygame")
    pygame.init()
    try:
        c=Surgery3DController()
        hud=SurgeryHUD(c)
        image=pygame.Surface((1280,720),pygame.SRCALPHA)
        font=pygame.font.SysFont("segoeui",20)
        big=pygame.font.SysFont("segoeui",28,bold=True)
        for phase in Phase:
            c.game.phase=phase
            c.game.ending=("SIMULATION COMPLETE" if phase==Phase.RECOVERY else
                            "SAFELY ABORTED" if phase==Phase.ABORTED else None)
            c._sync(Phase.ABORTED if phase!=Phase.ABORTED else Phase.RECOVERY)
            image.fill((0,0,0,0))
            hud.draw(pygame,image,c.view,1280,720,font,big)
            assert image.get_at((20,185)).a>0
        c.game.phase=Phase.CAPSULE
        c.game.patient.alert="PATIENT MOTION"
        c.game.paused=True
        image.fill((0,0,0,0))
        hud.draw(pygame,image,c.view,1280,720,font,big)
        assert image.get_at((450,335)).a>0
    finally:
        pygame.quit()


def test_controller_rejects_bad_case_before_gpu_window_creation():
    for case in ("unspecified", None, 1):
        with pytest.raises((ValueError, TypeError)):
            Surgery3DController(case)


def test_synthetic_ui_labels_cover_every_game_phase():
    assert set(PHASE_NAMES)==set(Phase)
    assert CHECKS==("alignment","wound","handoff")
