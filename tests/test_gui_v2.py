"""2.5D app v2: menus, checklists, every hazard/ending screen, KO/EN, palettes,
zoom/focus mapping, depth cross-section, results report and sounds.

Runs on the SDL dummy display. Screenshots go to build/screenshots/ for review.
"""
import os

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import json
import math

import pytest

pygame = pytest.importorskip('pygame')
from ophthosim.app import FIELD, FOCUS_TARGET, App, to_screen
from ophthosim.engine import CASES, DIFFICULTIES, ENDINGS, FINAL_CHECKS, PREOP_CHECKS, Phase

SHOTS = os.path.abspath('build/screenshots')   # tests may chdir


@pytest.fixture
def app():
    pygame.init()
    instance = App(pygame, scale=1)
    yield instance
    pygame.quit()


def key(app, k):
    app.dispatch(pygame.event.Event(pygame.KEYDOWN, {'key': k}))


def click(app, pos):
    app.dispatch(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'button': 1, 'pos': pos}))
    app.dispatch(pygame.event.Event(pygame.MOUSEBUTTONUP, {'button': 1, 'pos': pos}))


def start(app):
    for _ in range(5):
        key(app, pygame.K_SPACE)
    assert app.game.phase == Phase.ENTRY


def zoomed_screen(app, point):
    """Canvas position of an eye point under the current microscope zoom."""
    x, y = to_screen(point)
    fx, fy, _, _ = FIELD
    x0, y0, _, _ = app._crop()
    return (round(fx + (x - x0) * app.zoom), round(fy + (y - y0) * app.zoom))


def shot(app, name):
    app.draw()
    os.makedirs(SHOTS, exist_ok=True)
    pygame.image.save(app.canvas, f'{SHOTS}/{name}.png')


def pixels(app, rect):
    return pygame.image.tobytes(app.canvas.subsurface(rect), 'RGB')


# --- menus & checklists ---------------------------------------------------------
def test_number_keys_select_all_nine_cases_and_d_cycles_difficulty(app):
    for index, case in enumerate(CASES):
        key(app, pygame.K_1 + index)
        assert app.game.case == case
    seen = []
    for _ in DIFFICULTIES:
        key(app, pygame.K_d)
        seen.append(app.game.difficulty)
    assert sorted(seen) == sorted(DIFFICULTIES)
    key(app, pygame.K_SPACE)            # first check locks the case selection
    key(app, pygame.K_1)
    key(app, pygame.K_d)
    assert app.game.case == CASES[-1] and app.game.eye.preop_checks


def test_preop_checklist_items_are_clickable(app):
    for i, item in enumerate(PREOP_CHECKS):
        click(app, (100, 343 + i * 62 + 25))
        assert item in app.game.eye.preop_checks
    shot(app, 'v2-preop-checklist')
    click(app, (100, 600))               # start button
    assert app.game.phase == Phase.ANESTHESIA


def test_close_checklist_number_keys(app):
    g = app.game
    for item in PREOP_CHECKS:
        g.action('verify', item)
    g.action('confirm'); g.action('prepare')
    for x, y in g._entry_target:
        g.action('touch', x, y)
    for i in range(24):
        a = (i + .5) * math.tau / 24
        g.action('trace', .5 + .28 * math.cos(a), .5 + .28 * math.sin(a))
    for _ in range(80):
        g.action('remove', .5, .5)
    g.action('place', .5, .5)
    assert g.phase == Phase.CLOSE
    for index in range(3):
        key(app, pygame.K_1 + index)
    assert g.phase == Phase.RECOVERY and g.eye.final_checks == set(FINAL_CHECKS)


# --- zoom & focus ------------------------------------------------------------------
def test_zoomed_clicks_map_back_to_eye_coordinates(app):
    start(app)
    for _ in range(5):
        app.dispatch(pygame.event.Event(pygame.MOUSEWHEEL, {'x': 0, 'y': 1}))
    assert app.zoom == 1.5
    for target in app.game._entry_target:
        click(app, zoomed_screen(app, target))
    assert app.game.phase == Phase.CAPSULE
    shot(app, 'v2-zoomed-capsule')
    for _ in range(20):
        key(app, pygame.K_MINUS)
    assert app.zoom == 1.0


def test_zoom_is_locked_during_a_drag(app):
    start(app)
    app.drag = True
    app.set_zoom(1.6)
    assert app.zoom == 1.0


def test_focus_blur_is_visual_only_and_tutorial_autofocuses(app):
    start(app)
    sharp_focus = FOCUS_TARGET[Phase.ENTRY]
    app.focus = sharp_focus
    app.draw()
    sharp = pixels(app, FIELD)
    for _ in range(12):
        key(app, pygame.K_RIGHTBRACKET)
    assert app.focus_error() > .12
    app.draw()
    assert pixels(app, FIELD) != sharp
    snapshot = app.game.snapshot()
    click(app, to_screen(app.game._entry_target[0]))   # still accepted when blurred
    assert app.game.eye.entry_hits == 1 and app.game.snapshot() != snapshot
    app.game.difficulty = 'tutorial'
    assert app.focus_error() == 0.0


# --- hazards, alerts, endings ----------------------------------------------------------
def drive(app, target=None):
    g = app.game
    for _ in range(60):
        if g.ending or g.phase == target:
            return
        if g.patient.alert:
            return
        if g.phase in (Phase.PREOP, Phase.ANESTHESIA):
            key(app, pygame.K_SPACE)
        elif g.phase == Phase.ENTRY:
            for p in g._entry_target:
                g.action('touch', *p)
        elif g.phase == Phase.CAPSULE:
            for i in range(24):
                a = (i + .5) * math.tau / 24
                g.action('trace', .5 + .28 * math.cos(a), .5 + .28 * math.sin(a))
        elif g.phase in (Phase.PHACO, Phase.CORTEX):
            phase = g.phase
            while g.phase == phase and not g.patient.alert:
                g.action('remove', .5, .5)
        elif g.phase == Phase.IOL or (g.phase == Phase.CLOSE and g._decentered):
            g.action('place', .5, .5)
        elif g.phase == Phase.CLOSE:
            for item in FINAL_CHECKS:
                if not g.patient.alert:
                    g.action('verify', item)


@pytest.mark.parametrize('case', ['motion', 'vitals', 'capsule', 'pupil', 'haze', 'decenter', 'leak'])
@pytest.mark.parametrize('lang', ['en', 'ko'])
def test_every_hazard_screen_renders_with_timer(app, case, lang):
    app.lang = lang
    app.new_game(case=case)
    drive(app)
    assert app.game.patient.alert
    app.game.tick(.5)
    shot(app, f'v2-alert-{case}-{lang}')
    assert len(app.game.alerts) == app._alerts_heard == 1
    key(app, pygame.K_a)
    drive(app)
    app.draw()
    assert app.game.ending is not None or app.game.patient.alert == ''


def test_decentration_requires_repositioning_click(app):
    app.new_game(case='decenter')
    drive(app)
    assert app.game.patient.alert == 'IOL DECENTRATION'
    key(app, pygame.K_a)
    shot(app, 'v2-decentered')
    click(app, (100, 343 + 25))          # alignment check blocked while decentered
    assert 'alignment' not in app.game.eye.final_checks
    click(app, to_screen((.5, .5)))
    assert not app.game._decentered
    click(app, (100, 343 + 25))
    assert 'alignment' in app.game.eye.final_checks


@pytest.mark.parametrize('lang', ['en', 'ko'])
def test_all_four_ending_screens(app, lang, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    app.lang = lang
    seen = set()
    for case, finish in (('normal', None), ('motion', 'assess'), ('normal', 'abort'),
                         ('vitals', 'timeout')):
        app.new_game(case=case)
        drive(app, Phase.CAPSULE if finish == 'abort' else None)
        if finish == 'assess':
            key(app, pygame.K_a); drive(app)
        elif finish == 'abort':
            key(app, pygame.K_x)
        elif finish == 'timeout':
            for _ in range(700):
                app.game.tick(.05)
        assert app.game.ending
        seen.add(app.game.ending)
        shot(app, f"v2-ending-{app.game.ending.split()[0].lower()}-{lang}")
        key(app, pygame.K_e)
        report = next(tmp_path.glob(f'session_logs/case_{case}_standard_seed_7.report.json'))
        assert json.loads(report.read_text('utf-8'))['language'] == lang
    assert seen == set(ENDINGS)


# --- accessibility, language, sound -------------------------------------------------------
def test_language_toggle_changes_rendered_text(app):
    app.draw()
    english = pixels(app, (15, 75, 250, 200))
    key(app, pygame.K_l)
    assert app.lang == 'ko'
    app.draw()
    assert pixels(app, (15, 75, 250, 200)) != english
    key(app, pygame.K_l)
    assert app.lang == 'en'


def test_palettes_change_output_and_keep_text(app):
    start(app)
    app.draw()
    base = pixels(app, (0, 0, 1280, 720))
    key(app, pygame.K_h)
    shot(app, 'v2-high-contrast')
    contrast = pixels(app, (0, 0, 1280, 720))
    key(app, pygame.K_h); key(app, pygame.K_c)
    shot(app, 'v2-colour-safe')
    assert len({base, contrast, pixels(app, (0, 0, 1280, 720))}) == 3
    assert app.canvas.get_at((0, 0))[:3] == (7, 18, 30)


def test_reduced_motion_freezes_cataract_animation(app):
    start(app)
    key(app, pygame.K_m)
    app.game.time = 1.0; app.draw(); first = pixels(app, FIELD)
    app.game.time = 9.0; app.draw()
    assert pixels(app, FIELD) == first
    key(app, pygame.K_m)
    app.draw()
    assert pixels(app, FIELD) != first


def test_cross_section_follows_the_shared_snapshot(app):
    start(app)
    rect = (27, 492, 225, 148)
    app.draw(); before = pixels(app, rect)
    app.game.eye.opacity = .1
    app.draw()
    assert pixels(app, rect) != before


def test_help_overlay_and_sound_toggle(app):
    key(app, pygame.K_F1)
    shot(app, 'v2-help')
    assert app.show_help
    key(app, pygame.K_s)
    assert not app.sounds.enabled
    app.sounds.play('alert')             # muted: must not raise
    key(app, pygame.K_s)
    assert app.sounds.enabled
    app.sounds.play('nonexistent')


def test_cli_rejects_bad_arguments():
    from ophthosim.app import main
    for argv in (['--difficulty', 'easy'], ['--case', 'real'], ['--lang', 'fr'],
                 ['--scale', '9'], ['--seed', str(2**70)]):
        with pytest.raises(SystemExit):
            main(argv)
