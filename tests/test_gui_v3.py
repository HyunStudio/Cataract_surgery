"""2.5D design completion: keyboard operation, tool depth, pan, UI scale,
help, patient card, drape, progress, particles, near-miss, stress warning,
results heatmap/before-after, confirm-abort, damping, research condition,
break reminder, and the replay viewer (SDL dummy display)."""
import os

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import json
import math

import pytest

pygame = pytest.importorskip('pygame')
from ophthosim.app import (BREAK_AFTER_S, DEPTH_TOLERANCE, FIELD, MAX_PARTICLES, TASK_DEPTH,
                           App, main, to_screen)
from ophthosim.engine import FINAL_CHECKS, Phase
from ophthosim.playback import SPEEDS, ReplayPlayer
from ophthosim.replay import ReplayGame

SHOTS = os.path.abspath('build/screenshots')


@pytest.fixture
def app(tmp_path):
    pygame.init()
    instance = App(pygame, scale=1)
    instance.autosave_path = tmp_path / 'autosave.replay.jsonl'
    yield instance
    pygame.quit()


def key(app, k, up=False):
    app.dispatch(pygame.event.Event(pygame.KEYUP if up else pygame.KEYDOWN, {'key': k}))


def click(app, pos, button=1):
    app.dispatch(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'button': button, 'pos': pos}))
    app.dispatch(pygame.event.Event(pygame.MOUSEBUTTONUP, {'button': button, 'pos': pos}))


def start(app):
    for _ in range(5):
        key(app, pygame.K_SPACE)
    app.draw()
    assert app.game.phase == Phase.ENTRY


def shot(app, name):
    app.draw()
    os.makedirs(SHOTS, exist_ok=True)
    pygame.image.save(app.canvas, f'{SHOTS}/{name}.png')


def pixels(app, rect):
    return pygame.image.tobytes(app.canvas.subsurface(rect), 'RGB')


def test_whole_entry_task_by_keyboard_only(app):
    start(app)
    for target in app.game._entry_target:
        tx, ty = to_screen(target)
        while abs(app.cursor[0] - tx) > 3 or abs(app.cursor[1] - ty) > 3:
            dx, dy = tx - app.cursor[0], ty - app.cursor[1]
            if abs(dx) > 3:
                key(app, pygame.K_RIGHT if dx > 0 else pygame.K_LEFT)
            if abs(dy) > 3:
                key(app, pygame.K_DOWN if dy > 0 else pygame.K_UP)
        key(app, pygame.K_RETURN)
        key(app, pygame.K_RETURN, up=True)
    assert app.game.phase == Phase.CAPSULE and not app.drag


def test_tool_depth_gates_actions_and_resets_per_stage(app):
    start(app)
    assert app.tool_depth == TASK_DEPTH[Phase.ENTRY]
    for _ in range(4):
        key(app, pygame.K_e)
    assert not app.depth_ok()
    click(app, to_screen(app.game._entry_target[0]))
    assert app.game.eye.entry_hits == 0 and app.depth_rejections == 1
    assert 'depth' in app.message.lower()
    shot(app, 'v3-depth-wrong')
    for _ in range(4):
        key(app, pygame.K_q)
    assert app.depth_ok()
    for target in app.game._entry_target:
        click(app, to_screen(target))
    app.draw()
    assert app.game.phase == Phase.CAPSULE
    assert app.tool_depth == TASK_DEPTH[Phase.CAPSULE]
    assert abs(app.tool_depth - TASK_DEPTH[Phase.CAPSULE]) <= DEPTH_TOLERANCE


def test_shift_wheel_changes_depth_and_wheel_zooms(app, monkeypatch):
    start(app)
    monkeypatch.setattr(pygame.key, 'get_mods', lambda: pygame.KMOD_SHIFT)
    app.dispatch(pygame.event.Event(pygame.MOUSEWHEEL, {'x': 0, 'y': 2}))
    assert app.tool_depth == pytest.approx(TASK_DEPTH[Phase.ENTRY] + .08) and app.zoom == 1.0
    monkeypatch.setattr(pygame.key, 'get_mods', lambda: 0)
    app.dispatch(pygame.event.Event(pygame.MOUSEWHEEL, {'x': 0, 'y': 2}))
    assert app.zoom == 1.2


def test_middle_drag_pans_and_input_stays_mapped(app):
    start(app)
    app.set_zoom(1.6)
    app.dispatch(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'button': 2, 'pos': (600, 400)}))
    app.dispatch(pygame.event.Event(pygame.MOUSEMOTION, {'pos': (560, 380), 'rel': (-40, -20),
                                                         'buttons': (0, 1, 0)}))
    app.dispatch(pygame.event.Event(pygame.MOUSEBUTTONUP, {'button': 2, 'pos': (560, 380)}))
    assert app.pan != (0., 0.)
    fx, fy, _, _ = FIELD
    x0, y0, _, _ = app._crop()
    for target in app.game._entry_target:
        sx, sy = to_screen(target)
        click(app, (round(fx + (sx - x0) * app.zoom), round(fy + (sy - y0) * app.zoom)))
    assert app.game.phase == Phase.CAPSULE


def test_f2_cycles_ui_scale_and_mapping_stays_consistent(app):
    key(app, pygame.K_F2)
    assert app.scale == 1.25 and app.screen.get_size() == (1600, 900)
    assert app.mapped((800, 450)) == (640, 360)
    for _ in range(3):
        key(app, pygame.K_F2)
    assert app.scale == 1.0


def test_help_request_by_key_click_and_f1(app):
    start(app)
    key(app, pygame.K_SLASH)
    assert app.game.help_requests == 1 and app.show_help
    key(app, pygame.K_F1)      # closes
    key(app, pygame.K_F1)      # opens again -> request
    assert app.game.help_requests == 2
    click(app, (100, 660))
    assert app.game.help_requests == 3
    shot(app, 'v3-help-request')


def test_patient_card_drape_and_progress_render(app):
    app.draw()
    card = pixels(app, (27, 292, 225, 40))
    app.new_game(case='motion')
    app.draw()
    assert pixels(app, (27, 292, 225, 40)) == card or app.game.patient_card['eye']
    shot(app, 'v3-preop-card')
    key(app, pygame.K_SPACE); key(app, pygame.K_SPACE); key(app, pygame.K_SPACE)
    key(app, pygame.K_SPACE)
    assert app.game.phase == Phase.ANESTHESIA
    app.draw(); anesthesia = pixels(app, (300, 120, 120, 120))
    shot(app, 'v3-drape')
    key(app, pygame.K_SPACE); app.draw()
    assert pixels(app, (300, 120, 120, 120)) != anesthesia      # drape opens up
    progress = pixels(app, (291, 676, 658, 8))
    for target in app.game._entry_target:
        click(app, to_screen(target))
    app.draw()
    assert pixels(app, (291, 676, 658, 8)) != progress


def test_particles_are_bounded_and_disabled_with_reduced_motion(app):
    start(app)
    g = app.game
    for target in g._entry_target:
        g.action('touch', *target)
    for i in range(24):
        a = (i + .5) * math.tau / 24
        g.action('trace', .5 + .28 * math.cos(a), .5 + .28 * math.sin(a))
    for _ in range(30):
        g.action('remove', .5, .5)
        app.draw()
    assert 0 < len(app.particles) <= MAX_PARTICLES
    shot(app, 'v3-phaco-particles')
    app.tick_ui(1.0)
    assert not app.particles
    key(app, pygame.K_m)
    g.action('remove', .5, .5)
    app.draw()
    assert not app.particles


def test_near_miss_mark_and_stress_warning(app):
    start(app)
    g = app.game
    for target in g._entry_target:
        g.action('touch', *target)
    for i in range(24):
        a = (i + .5) * math.tau / 24
        g.action('trace', .5 + .28 * math.cos(a), .5 + .28 * math.sin(a))
    g.action('remove', .9, .5)
    app.draw()
    assert app._near_mark is not None
    for _ in range(60):
        g.action('remove', .9, .5)
    app.draw()
    assert g.stress >= .6 and not g.patient.alert
    shot(app, 'v3-stress-warning')


def test_guides_are_tutorial_only(app):
    assert not app.game.rules.guides
    app.new_game(difficulty='tutorial')
    assert app.game.rules.guides


def test_results_show_heatmap_and_before_after(app):
    start(app)
    g = app.game
    for target in g._entry_target:
        g.action('touch', *target)
    for i in range(24):
        a = (i + .5) * math.tau / 24
        g.action('trace', .5 + .28 * math.cos(a), .5 + .28 * math.sin(a))
    g.action('remove', .9, .5)
    while g.phase in (Phase.PHACO, Phase.CORTEX):
        g.action('remove', .5, .5)
    g.action('place', .5, .5)
    for item in FINAL_CHECKS:
        g.action('verify', item)
    assert g.ending
    shot(app, 'v3-results-heatmap')
    heat = pixels(app, (27, 262, 225, 225))
    app.new_game()
    app.draw()
    assert pixels(app, (27, 262, 225, 225)) != heat


def test_confirm_abort_needs_two_presses_within_window(app):
    app.confirm_abort = True
    start(app)
    key(app, pygame.K_x)
    assert not app.game.ending and 'again' in app.message
    app.tick_ui(3.5)
    key(app, pygame.K_x)
    assert not app.game.ending
    key(app, pygame.K_x)
    assert app.game.ending == 'SAFELY ABORTED'


def test_cursor_damping_smooths_drag_motion(app):
    start(app)
    key(app, pygame.K_k)
    assert app.damping
    app.cursor = (500., 400.)
    app.drag = True
    app.dispatch(pygame.event.Event(pygame.MOUSEMOTION, {'pos': (600, 400), 'rel': (100, 0),
                                                         'buttons': (1, 0, 0)}))
    assert app.cursor[0] == pytest.approx(535.)


def test_enlarged_cross_section_overlay(app):
    start(app)
    app.draw(); before = pixels(app, FIELD)
    key(app, pygame.K_v)
    shot(app, 'v3-big-section')
    assert pixels(app, FIELD) != before


def test_low_visibility_condition_is_logged_research_condition(app, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    start(app)
    app.draw(); base = pixels(app, FIELD)
    app.condition = 'low_visibility'
    shot(app, 'v3-low-visibility')
    assert pixels(app, FIELD) != base
    key(app, pygame.K_x)
    key(app, pygame.K_e)
    report = json.loads(next(tmp_path.glob('session_logs/*.report.json')).read_text('utf-8'))
    ui = report['ui_conditions']
    assert ui['research_condition'] == 'low_visibility' and ui['window'] == [1280, 720]
    assert report['session_id'] == app.game.session_id and report['patient_card']


def test_break_reminder_after_twenty_minutes_of_play(app):
    start(app)
    app.tick_ui(BREAK_AFTER_S - 1)
    assert 'break' not in app.message
    app.tick_ui(2)
    assert 'break' in app.message


def test_replay_viewer_plays_steps_and_matches_final_state(app, tmp_path):
    game = ReplayGame('motion', 5)
    from test_engine_v2 import run_to
    for _ in range(30):
        game.tick(1 / 60)
    run_to(game, Phase.CAPSULE)
    for _ in range(90):
        game.tick(1 / 60)
    run_to(game, Phase.RECOVERY)
    raw = game.export_replay_jsonl()
    assert app.start_replay(raw)
    assert app.game.phase == Phase.PREOP
    key(app, pygame.K_SPACE)                      # pause
    assert not app.player.playing
    key(app, pygame.K_RIGHT)
    key(app, pygame.K_EQUALS)
    assert app.player.speed == 2.
    for _ in range(400):
        app.player.playing = True
        app.player.advance(.1)
        app.game = app.player.game
    shot(app, 'v3-replay-viewer')
    assert app.player.done and app.game.snapshot() == game.snapshot()
    snapshot = app.game.snapshot()
    click(app, to_screen((.5, .5)))               # viewer never issues commands
    assert app.game.snapshot() == snapshot
    assert not app.start_replay('{"broken": 1}\n')


def test_playback_player_units_and_speeds():
    game = ReplayGame('vitals', 2)
    from test_engine_v2 import run_to
    run_to(game, Phase.RECOVERY)
    player = ReplayPlayer(game.export_replay_jsonl())
    for _ in range(3):
        player.step()
    assert player.index >= 1 and not player.done
    for _ in range(10):
        player.faster()
    assert player.speed == SPEEDS[-1]
    for _ in range(10):
        player.slower()
    assert player.speed == SPEEDS[0]
    player.toggle(); player.advance(100)
    assert not player.done                         # paused: nothing happens
    player.finish()
    assert player.done and player.progress == 1.
    assert player.game.snapshot() == player.final.snapshot() == game.snapshot()


def test_cli_replay_and_condition_arguments(tmp_path):
    with pytest.raises(SystemExit):
        main(['--condition', 'blind'])
    bad = tmp_path / 'bad.replay.jsonl'
    bad.write_text('nope', encoding='utf-8')
    with pytest.raises(SystemExit):
        main(['--replay', str(bad)])
    with pytest.raises(SystemExit):
        main(['--replay', str(tmp_path / 'missing.jsonl')])
