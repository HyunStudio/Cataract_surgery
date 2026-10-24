"""SDL dummy-display integration tests; executed by GitHub Actions with pygame installed."""
import os

os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')

import pytest

pygame = pytest.importorskip('pygame')
from ophthosim.app import App, to_eye, to_screen
from ophthosim.engine import Game, Phase


@pytest.fixture
def app(tmp_path):
    pygame.init()
    instance=App(pygame,scale=1)
    instance.autosave_path=tmp_path/'autosave.replay.jsonl'
    yield instance
    pygame.quit()


def test_first_frame_and_monitor(app):
    app.draw()
    assert app.canvas.get_size()==(1280,720)
    assert app.screen.get_size()==(1280,720)
    assert app.canvas.get_at((0,0))[:3] == (7,18,30)


def test_all_phase_screens_render(app):
    for phase in Phase:
        app.game.phase=phase
        app.game.paused=False
        app.game.ending='SIMULATION COMPLETE' if phase==Phase.RECOVERY else ('SAFELY ABORTED' if phase==Phase.ABORTED else None)
        app.draw()


def test_export_completed_game_visual(app):
    app.game=Game('normal')
    g=app.game
    for _check in ('identity', 'site', 'iol_plan'): g.action('verify', _check)
    g.action('confirm')
    g.action('prepare')
    for x,y in g._entry_target:
        g.action('touch',x,y)
    import math
    for i in range(24):
        theta=(i+.5)*math.tau/24
        g.action('trace',.5+.28*math.cos(theta),.5+.28*math.sin(theta))
    for _ in range(80):
        g.action('remove',.5,.5)
    assert g.action('place',.5,.5)
    for key in ('alignment','wound','handoff'):
        g.action('verify',key)
    assert g.phase==Phase.RECOVERY
    assert g.score()==100
    app.draw()
    os.makedirs('build/screenshots',exist_ok=True)
    pygame.image.save(app.canvas,'build/screenshots/recovery.png')


def test_alert_and_pause_layers_render(app):
    app.game._alert('PATIENT MOTION')
    app.draw()
    assert app.game.paused
    assert app.game.action('assess')
    app.draw()
    assert app.game.action('pause')
    app.draw()


def test_resize_and_coordinate_mapping(app):
    app.screen=pygame.display.set_mode((1920,1080),pygame.RESIZABLE)
    assert app.mapped((960,540))==(640,360)
    app.draw()
    pt=(.52,.45)
    sx,sy=to_screen(pt)
    x,y=to_eye((sx,sy))
    assert abs(x-pt[0]) < .003
    assert abs(y-pt[1]) < .003


def test_ui_keyboard_case_selection_and_start(app):
    app.dispatch(pygame.event.Event(pygame.KEYDOWN,{'key':pygame.K_2}))
    assert app.game.case == 'motion'
    # Space ticks the three pre-op checks one by one, then starts the case.
    for expected in (1,2,3):
        app.dispatch(pygame.event.Event(pygame.KEYDOWN,{'key':pygame.K_SPACE}))
        assert len(app.game.eye.preop_checks) == expected
        assert app.game.phase == Phase.PREOP
    app.dispatch(pygame.event.Event(pygame.KEYDOWN,{'key':pygame.K_SPACE}))
    assert app.game.phase == Phase.ANESTHESIA
    app.dispatch(pygame.event.Event(pygame.KEYDOWN,{'key':pygame.K_SPACE}))
    assert app.game.phase == Phase.ENTRY
    app.draw()


def test_ui_dirty_mouse_coordinates_do_not_crash(app):
    for _ in range(5):
        app.dispatch(pygame.event.Event(pygame.KEYDOWN,{'key':pygame.K_SPACE}))
    for pos in [(-200,-200),(99999,99999),(0,0),(1920,1080)]:
        app.dispatch(pygame.event.Event(pygame.MOUSEBUTTONDOWN,{'pos':pos,'button':1}))
        app.dispatch(pygame.event.Event(pygame.MOUSEBUTTONUP,{'pos':pos,'button':1}))
        app.draw()
    assert app.game.phase==Phase.ENTRY
def test_gui_exports_verifiable_replay(app, tmp_path, monkeypatch):
    """An end-user save must include a loader-verifiable command journal."""
    from ophthosim.replay import ReplayGame

    monkeypatch.chdir(tmp_path)
    for _check in ('identity', 'site', 'iol_plan'): app.game.action('verify', _check)
    assert app.game.action('confirm')
    assert app.game.action('prepare')
    assert app.game.action('abort')
    app.save()
    trace_path=tmp_path/'session_logs/case_normal_standard_seed_7.jsonl'
    replay_path=tmp_path/'session_logs/case_normal_standard_seed_7.replay.jsonl'
    assert trace_path.is_file() and replay_path.is_file()
    restored=ReplayGame.replay_jsonl(replay_path.read_text(encoding='utf-8'))
    assert restored.snapshot()==app.game.snapshot()
    assert restored.export_jsonl()==trace_path.read_text(encoding='utf-8')


def test_gui_replay_overflow_is_reported_not_crash(app, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    app.game.MAX_RECORDS=0
    for _check in ('identity', 'site', 'iol_plan'): app.game.action('verify', _check)
    app.game.action('confirm')
    app.game.action('abort')
    app.save()
    assert app.message == 'Export failed: RuntimeError'


def test_3d_mesh_preview_is_interactive_but_cannot_apply_surgical_actions(app):
    """CPU mesh rotates; surgical interactions remain disabled in preview mode."""
    for _check in ('identity', 'site', 'iol_plan'): app.game.action('verify', _check)
    app.game.action('confirm')
    app.game.action('prepare')
    assert app.game.phase == Phase.ENTRY
    app.dispatch(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_g}))
    assert app.view_3d
    initial = app.view_yaw
    app.dispatch(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_l}))
    assert app.view_yaw > initial
    for x,y in app.game._entry_target:
        px,py=(round(640+(x-.5)*444),round(366+(y-.5)*444))
        app.dispatch(pygame.event.Event(pygame.MOUSEBUTTONDOWN,
                                        {'button':1,'pos':(px,py)}))
        app.dispatch(pygame.event.Event(pygame.MOUSEBUTTONUP,
                                        {'button':1,'pos':(px,py)}))
    assert app.game.phase == Phase.ENTRY
    assert app.game.eye.entry_hits == 0
    app.draw()
    os.makedirs('build/screenshots',exist_ok=True)
    pygame.image.save(app.canvas, 'build/screenshots/mesh3d-preview.png')
    app.dispatch(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_g}))
    assert not app.view_3d
    app.dispatch(pygame.event.Event(pygame.MOUSEBUTTONDOWN,
                                    {'button':1,'pos':(round(640+(.69-.5)*444),
                                                        round(366+(.46-.5)*444))}))
    assert app.game.eye.entry_hits == 1


def test_3d_preview_orbit_clamps_and_phase_rendering(app):
    app.dispatch(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_g}))
    for _ in range(100):
        app.dispatch(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_l}))
        app.dispatch(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_i}))
    assert app.view_yaw == 1.2 and app.view_pitch == .9
    for phase in Phase:
        app.game.phase = phase
        app.game.ending = ('SIMULATION COMPLETE' if phase == Phase.RECOVERY else
                           'SAFELY ABORTED' if phase == Phase.ABORTED else None)
        app.draw()


def test_monitor_waveforms_change_with_synthetic_patient_heart_rate(app):
    """Both waveform panels are driven by the same shared patient state."""
    app.game.time = 2.0
    app.game.patient.heart_rate = 70
    app.draw()
    a_ecg = app.canvas.subsurface((995, 254, 246, 49)).copy()
    a_pleth = app.canvas.subsurface((1090, 484, 150, 30)).copy()
    app.game.patient.heart_rate = 120
    app.draw()
    b_ecg = app.canvas.subsurface((995, 254, 246, 49)).copy()
    b_pleth = app.canvas.subsurface((1090, 484, 150, 30)).copy()
    assert pygame.image.tobytes(a_ecg, 'RGB') != pygame.image.tobytes(b_ecg, 'RGB')
    assert pygame.image.tobytes(a_pleth, 'RGB') != pygame.image.tobytes(b_pleth, 'RGB')
