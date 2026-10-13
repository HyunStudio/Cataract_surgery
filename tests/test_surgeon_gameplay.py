"""Regression tests for the surgeon-game review fixes.

Covers fixed-step held instruments, bounded replay journals, decaying tissue
stress with an early warning, manual 3D depth control, non-overwriting
session saves, honest renderer/FPS labels and the surgeon debrief.
"""
import math
import os

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import pytest

from ophthosim.engine import Game, Phase
from ophthosim.gl_preview import fps_label, renderer_kind
from ophthosim.input3d import (APPROACH_DEPTH, DEPTH_TOLERANCE, STAGE_DEPTH,
                               Surgery3DController)
from ophthosim.replay import ReplayGame, session_paths


def to_capsule(game):
    assert game.action('confirm') and game.action('prepare')
    for x, y in game._entry_target:
        assert game.action('touch', x, y)
    assert game.phase == Phase.CAPSULE


def to_phaco(game):
    to_capsule(game)
    for i in range(24):
        a = (i + .5) * math.tau / 24
        game.action('trace', .5 + .28 * math.cos(a), .5 + .28 * math.sin(a))
    assert game.phase == Phase.PHACO


# --- Held instrument work is per simulated tick ------------------------------

def test_removal_takes_seconds_of_simulated_work_not_one_click():
    game = Game()
    to_phaco(game)
    ticks = 0
    while game.phase == Phase.PHACO:
        assert game.action('remove', .5, .5)
        game.tick(1 / 60)
        ticks += 1
    assert 3. <= ticks / 60 <= 6.  # roughly four seconds of steady work
    while game.phase == Phase.CORTEX:
        assert game.action('remove', .5, .5)
        game.tick(1 / 60)
        ticks += 1
    assert game.phase == Phase.IOL
    assert 6. <= ticks / 60 <= 9.


def test_2d_app_progress_ignores_mouse_event_rate():
    pygame = pytest.importorskip('pygame')
    from ophthosim.app import App, to_screen
    pygame.init()
    try:
        app = App(pygame, scale=1)
        to_phaco(app.game)
        centre = to_screen((.5, .5))
        app.dispatch(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'button': 1, 'pos': centre}))
        # A 1000 Hz mouse produces many motion events; none may act directly.
        for i in range(2000):
            app.dispatch(pygame.event.Event(pygame.MOUSEMOTION,
                                            {'pos': (centre[0] + i % 3, centre[1]),
                                             'rel': (1, 0), 'buttons': (1, 0, 0)}))
        assert app.game.eye.opacity == 1.
        for _ in range(60):
            app.tick_once()
        assert app.game.eye.opacity == pytest.approx(1 - 60 * Game.PHACO_STEP)
    finally:
        pygame.quit()


def test_2d_app_releases_held_instrument_on_safety_hold():
    pygame = pytest.importorskip('pygame')
    from ophthosim.app import App
    pygame.init()
    try:
        app = App(pygame, scale=1)
        to_phaco(app.game)
        app.drag = True
        app.game._alert('PATIENT MONITOR')
        app.tick_once()
        assert app.drag is False
    finally:
        pygame.quit()


# --- Replay journal stays bounded ---------------------------------------------

def test_capsule_mouse_spam_no_longer_overflows_replay():
    game = ReplayGame()
    to_capsule(game)
    before = len(game.journal)
    for _ in range(ReplayGame.MAX_RECORDS // 10):
        game.action('trace', .5, .5)          # outside the ring: no-op
        game.action('trace', .78, .5)         # same visited segment: no-op after 1st
    assert len(game.journal) == before + 1
    assert not game.journal_overflow
    again = ReplayGame.replay_jsonl(game.export_replay_jsonl())
    assert again.snapshot() == game.snapshot()


def test_state_changing_rejections_are_still_journaled():
    game = ReplayGame()
    to_phaco(game)
    assert not game.action('remove', .95, .5)
    assert game.journal[-1] == {'kind': 'action', 'name': 'remove', 'accepted': False,
                                'x': .95, 'y': .5}


# --- Tissue stress: decays, warns early, then alerts ---------------------------

def test_stress_warning_comes_before_alert_and_costs_points():
    game = ReplayGame()
    to_phaco(game)
    while not game.stress_warning:
        assert not game.action('remove', .95, .5)
    assert not game.patient.alert
    assert game.stress_warnings == 1
    assert any(e['kind'] == 'stress_warning' for e in game.events)
    # Back to the centre: strain decays with simulated time, no alert.
    for _ in range(600):
        game.action('remove', .5, .5)
        game.tick(1 / 60)
        if game.phase not in (Phase.PHACO, Phase.CORTEX):
            break
    assert game.tissue_stress < Game.STRESS_WARNING_RESET
    assert not game.patient.alert
    again = ReplayGame.replay_jsonl(game.export_replay_jsonl())
    assert again.snapshot() == game.snapshot()


def test_brief_slips_spread_over_time_do_not_force_an_abort():
    game = Game()
    to_phaco(game)
    for _ in range(8):                     # eight 0.5 s slips, 3 s apart
        for _ in range(30):
            game.action('remove', .95, .5)
            game.tick(1 / 60)
        for _ in range(180):
            game.tick(1 / 60)
    assert not game.patient.alert
    assert game.stress_warnings == 0
    assert game.off_target == 240


def test_sustained_off_target_work_still_raises_capsule_alert():
    game = Game()
    to_phaco(game)
    for _ in range(600):
        game.action('remove', .95, .5)
        game.tick(1 / 60)
        if game.patient.alert:
            break
    assert game.patient.alert == 'CAPSULE INTEGRITY'
    assert game.stress_warnings == 1


def test_clean_run_keeps_full_safety_score():
    game = Game()
    to_phaco(game)
    while game.phase in (Phase.PHACO, Phase.CORTEX):
        game.action('remove', .5, .5)
        game.tick(1 / 60)
    assert game.action('place', .5, .5)
    for item in ('alignment', 'wound', 'handoff'):
        assert game.action('verify', item)
    assert game.score() == 100


def test_event_trace_marks_truncation():
    game = Game()
    for _ in range(Game.MAX_EVENTS + 5):
        game.action('pause')
    assert game.event_count() == Game.MAX_EVENTS
    assert game.events[-1]['kind'] == 'events_truncated'


# --- Manual 3D depth control ----------------------------------------------------

def test_3d_tip_starts_above_the_eye_and_needs_q_presses():
    c = Surgery3DController()
    assert c.tool_depth == APPROACH_DEPTH
    c.command('confirm')
    c.command('prepare')
    assert c.depth_hint() == 'DEEPER'
    assert c.adjust_depth_to_target() == 4
    assert c.tool_depth == pytest.approx(STAGE_DEPTH[Phase.ENTRY])
    assert c.depth_hint() == 'OK'


def test_3d_depth_is_not_snapped_when_the_phase_advances():
    c = Surgery3DController()
    c.command('confirm')
    c.command('prepare')
    c.adjust_depth_to_target()
    from ophthosim.input3d import eye_to_pixel
    for x, y in c.game._entry_target:
        assert c.pointer(*eye_to_pixel(x, y, c.tool_depth, 1280, 720, c.view),
                         1280, 720, fresh_press=True)
    assert c.game.phase == Phase.CAPSULE
    assert c.tool_depth == pytest.approx(STAGE_DEPTH[Phase.ENTRY])
    assert abs(c.tool_depth - c.target_depth) > DEPTH_TOLERANCE
    assert c.depth_hint() == 'DEEPER'
    c.adjust_depth(1)
    c.adjust_depth(1)
    assert c.depth_hint() == 'DEEPER'


def test_depth_hint_idle_outside_instrument_phases():
    c = Surgery3DController()
    assert c.depth_hint() is None
    assert c.adjust_depth_to_target() == 0


# --- Saves, renderer labels, debrief ---------------------------------------------

def test_session_paths_never_overwrite(tmp_path):
    first = session_paths(tmp_path, 'case_normal_seed_7')
    assert first[0].name == 'case_normal_seed_7.jsonl'
    first[0].write_text('x', encoding='utf-8')
    second = session_paths(tmp_path, 'case_normal_seed_7')
    assert second[0].name == 'case_normal_seed_7_2.jsonl'
    assert second[1].name == 'case_normal_seed_7_2.replay.jsonl'


def test_2d_save_keeps_earlier_sessions(tmp_path, monkeypatch):
    pygame = pytest.importorskip('pygame')
    from ophthosim.app import App
    monkeypatch.chdir(tmp_path)
    pygame.init()
    try:
        app = App(pygame, scale=1)
        app.game.action('confirm')
        app.game.action('abort')
        app.save()
        app.save()
        names = sorted(p.name for p in (tmp_path / 'session_logs').iterdir())
        assert names == ['case_normal_seed_7.jsonl', 'case_normal_seed_7.replay.jsonl',
                         'case_normal_seed_7_2.jsonl', 'case_normal_seed_7_2.replay.jsonl']
    finally:
        pygame.quit()


def test_failed_replay_export_writes_no_lone_trace(tmp_path, monkeypatch):
    pygame = pytest.importorskip('pygame')
    from ophthosim.app import App
    monkeypatch.chdir(tmp_path)
    pygame.init()
    try:
        app = App(pygame, scale=1)
        app.game.MAX_RECORDS = 0
        app.game.action('confirm')
        app.save()
        assert app.message == 'Export failed: RuntimeError'
        assert not (tmp_path / 'session_logs').exists()
    finally:
        pygame.quit()


@pytest.mark.parametrize('name,kind', [
    ('llvmpipe (LLVM 17.0.6, 256 bits)', 'software'),
    ('Mesa softpipe', 'software'),
    ('Google SwiftShader', 'software'),
    ('NVIDIA GeForce RTX 3070 Laptop GPU/PCIe/SSE2', 'hardware'),
    ('AMD Radeon(TM) Graphics', 'hardware'),
    ('Mesa Intel(R) UHD Graphics 620 (KBL GT2)', 'hardware'),
])
def test_renderer_kind(name, kind):
    assert renderer_kind(name) == kind


@pytest.mark.parametrize('value,text', [(None, 'FPS: --'), (0., 'FPS: --'),
                                        (float('nan'), 'FPS: --'), (True, 'FPS: --'),
                                        (59.6, 'FPS: 60')])
def test_fps_label_only_shows_measured_values(value, text):
    assert fps_label(value) == text


def test_debrief_credits_a_safe_stop_after_complication():
    game = Game('capsule')
    to_phaco(game)
    assert game.patient.alert == 'CAPSULE INTEGRITY'
    assert game.action('assess')
    assert game.phase == Phase.ABORTED
    lines = dict(game.debrief())
    assert lines['Decision'] == 'Recognised and stopped safely'
    assert lines['Safety holds'] == '1 raised, 1 assessed'


def test_phase_durations_follow_simulated_time():
    game = Game()
    game.tick(1 / 60)
    game.action('confirm')
    for _ in range(30):
        game.tick(1 / 60)
    game.action('prepare')
    durations = game.phase_durations()
    assert durations['PREOP'] == pytest.approx(1 / 60, abs=.006)
    assert durations['ANESTHESIA'] == pytest.approx(.5, abs=.006)


def test_2d_result_screen_does_not_offer_dead_abort_key():
    pygame = pytest.importorskip('pygame')
    from ophthosim.app import App
    pygame.init()
    try:
        app = App(pygame, scale=1)
        app.game.action('confirm')
        app.game.action('abort')
        assert not app.game.action('abort')
        app.draw()
        # Footer message renders fully inside the 720 px canvas.
        footer = app.fonts['tiny'].size(app.message)
        assert 699 + footer[1] <= 720
    finally:
        pygame.quit()
