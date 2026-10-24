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
from ophthosim.engine import (CASES, DIFFICULTIES, ENDINGS, FINAL_CHECKS, HAZARDS, PREOP_CHECKS,
                              TOOL_NAMES, Phase)

import surgeon_helpers as H

SHOTS = os.path.abspath('build/screenshots')   # tests may chdir


@pytest.fixture
def app(tmp_path):
    pygame.init()
    instance = App(pygame, scale=1)
    instance.autosave_path = tmp_path / 'autosave.replay.jsonl'
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
def test_number_keys_n_and_d_select_cases_and_difficulty(app):
    for index, case in enumerate(CASES[:9]):
        key(app, pygame.K_1 + index)
        assert app.game.case == case
    for case in CASES[9:] + CASES[:1]:       # N walks the rest and wraps
        key(app, pygame.K_n)
        assert app.game.case == case
    seen = []
    for _ in DIFFICULTIES:
        key(app, pygame.K_d)
        seen.append(app.game.difficulty)
    assert sorted(seen) == sorted(DIFFICULTIES)
    key(app, pygame.K_SPACE)            # first check locks the case selection
    key(app, pygame.K_2)
    key(app, pygame.K_n)
    key(app, pygame.K_d)
    assert app.game.case == CASES[0] and app.game.eye.preop_checks


def test_preop_chart_shows_the_synthetic_patient(app):
    app.draw()
    plain = pixels(app, (292, 108, 300, 170))
    app.new_game(case='bleed')          # anticoagulated, atrial fibrillation
    app.draw()
    assert pixels(app, (292, 108, 300, 170)) != plain
    shot(app, 'v3-preop-chart-en')
    app.lang = 'ko'
    shot(app, 'v3-preop-chart-ko')


def test_preop_checklist_items_are_clickable(app):
    for i, item in enumerate(PREOP_CHECKS):
        click(app, (100, 343 + i * 62 + 25))
        assert item in app.game.eye.preop_checks
    shot(app, 'v2-preop-checklist')
    click(app, (100, 600))               # start button
    assert app.game.phase == Phase.ANESTHESIA


def test_close_checklist_number_keys(app):
    g = app.game
    H.run_to(g, Phase.CLOSE)
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
def drive(app, target=None, **kw):
    """Ideal surgeon up to `target`, the ending, or the next alert."""
    g = app.game
    while g.phase in (Phase.PREOP, Phase.ANESTHESIA) and not g.ending:
        key(app, pygame.K_SPACE)
    H.run_to(g, target, stop_at_alert=True, **kw)


@pytest.mark.parametrize('case', list(HAZARDS))
@pytest.mark.parametrize('lang', ['en', 'ko'])
def test_every_hazard_screen_renders_with_timer(app, case, lang):
    app.lang = lang
    app.new_game(case=case)
    drive(app)
    assert app.game.patient.alert == HAZARDS[case][1]
    app.game.tick(.5)
    shot(app, f'v2-alert-{case}-{lang}')
    assert len(app.game.alerts) == app._alerts_heard == 1
    key(app, pygame.K_a)
    if app.game.pending:
        shot(app, f'v3-manage-{case}-{lang}')
    for _ in range(4):
        drive(app)
        if app.game.ending or not app.game.patient.alert:
            break
        key(app, pygame.K_a)
    app.draw()
    assert app.game.ending is not None or app.game.patient.alert == ''


def test_pending_banner_hints_the_instrument_only_in_tutorial(app):
    for difficulty, hinted in (('tutorial', True), ('standard', False)):
        app.new_game(case='bleed', difficulty=difficulty)
        drive(app)
        key(app, pygame.K_a)
        assert app.game.pending == ['INCISION BLEEDING']
        app.draw()
        assert len(set(pixels(app, (352, 516, 570, 76)))) > 10
        slot = dict(app.tray_slots())['cautery']
        border = pixels(app, (slot[0] + 8, slot[1], slot[2] - 16, 1))
        assert (bytes(app.palette['warn']) in border) == hinted
        shot(app, f'v3-pending-bleed-{difficulty}')


def test_situation_instrument_from_the_tray_manages_bleeding(app):
    app.new_game(case='bleed')
    drive(app)
    key(app, pygame.K_a)
    g = app.game
    assert g.eye.blood_film > 0
    shot(app, 'v3-bleeding')
    slot = dict(app.tray_slots())['cautery']
    click(app, (slot[0] + 5, slot[1] + 5))
    assert g.tool == 'cautery'
    click(app, to_screen(H.SITES['incision']))
    assert not g.pending
    shot(app, 'v3-bleeding-managed')


def test_v_d_and_b_shortcuts(app):
    g = app.game
    drive(app, Phase.ENTRY)
    H.arm(g)
    g.action('touch', *g._entry_target[0])
    key(app, pygame.K_v)
    assert g.ovd_chamber and g.tool == 'sideport'   # standard mode hands the blade back
    H.run_to(g, Phase.PHACO)
    key(app, pygame.K_d)
    assert g.hydro_done
    app.new_game(case='capsule')
    drive(app)
    key(app, pygame.K_a)
    assert app.game.pending == ['CAPSULE INTEGRITY']
    key(app, pygame.K_b)
    assert not app.game.pending


def test_held_drag_stops_at_phase_change(app):
    g = app.game
    drive(app, Phase.PHACO)
    H.use(g, 'hydro_cannula')
    H.arm(g)
    app.dispatch(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'button': 1, 'pos': to_screen((.5, .5))}))
    before = g.eye.opacity
    for _ in range(30):
        app.held_input()
        g.tick(1 / 60)
    assert g.eye.opacity < before and app.drag
    app._drag_phase = Phase.CAPSULE      # as if the phase had changed under the drag
    app.held_input()
    assert not app.drag


def test_bleeding_and_complication_signs_render(app):
    seen = {}
    for case in ('hyphema', 'sch', 'iris', 'zonules'):
        app.new_game(case=case)
        drive(app)
        key(app, pygame.K_a)
        shot(app, f'v3-sign-{case}')
        seen[case] = app.game
    assert seen['hyphema'].eye.hyphema > 0
    assert seen['sch'].ending or seen['sch'].eye.red_reflex < 1
    assert seen['iris'].pending == ['IRIS PROLAPSE']
    assert seen['zonules'].pending == ['ZONULAR WEAKNESS']


def test_decentration_requires_repositioning_click(app):
    app.new_game(case='decenter')
    drive(app)
    assert app.game.patient.alert == 'IOL DECENTRATION'
    key(app, pygame.K_a)
    shot(app, 'v2-decentered')
    click(app, (100, 343 + 25))          # alignment check blocked while decentered
    assert 'alignment' not in app.game.eye.final_checks
    slot = dict(app.tray_slots())['iol_hook']
    click(app, (slot[0] + 5, slot[1] + 5))
    click(app, to_screen((.5, .5)))
    assert not app.game._decentered
    click(app, (100, 343 + 25))
    assert 'alignment' in app.game.eye.final_checks


@pytest.mark.parametrize('lang', ['en', 'ko'])
def test_all_five_ending_screens(app, lang, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    app.lang = lang
    seen = set()
    for case, finish in (('normal', None), ('motion', 'assess'), ('normal', 'abort'),
                         ('vitals', 'timeout'), ('hyphema', 'ignore')):
        app.new_game(case=case)
        drive(app, Phase.CAPSULE if finish == 'abort' else None)
        if finish == 'assess':
            key(app, pygame.K_a)
            drive(app)
        elif finish == 'abort':
            key(app, pygame.K_x)
        elif finish == 'timeout':
            for _ in range(700):
                app.game.tick(.05)
        elif finish == 'ignore':
            key(app, pygame.K_a)
            drive(app, manage_pending=False)
        assert app.game.ending
        seen.add(app.game.ending)
        shot(app, f"v2-ending-{app.game.ending.split()[-1].lower()}-{lang}")
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


# --- instruments, illumination, autosave ----------------------------------------
def test_tray_click_and_t_key_select_instruments(app):
    app.new_game(difficulty='hard')
    start(app)
    assert app.game.tool is None and app.game.required_tool == 'keratome'
    click(app, to_screen(app.game._entry_target[0]))
    app.draw()
    assert app.game.wrong_tool == 1 and 'keratome' in app.message.lower()
    slots = dict(app.tray_slots())
    assert set(slots) == set(TOOL_NAMES) and len({r[1] for r in slots.values()}) == 2
    click(app, (slots['phaco'][0] + 5, slots['phaco'][1] + 5))
    assert app.game.tool == 'phaco'
    key(app, pygame.K_t)                                    # -> I/A
    assert app.game.tool == 'ia'
    app.dispatch(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_t, 'mod': pygame.KMOD_LSHIFT}))
    assert app.game.tool == 'phaco'
    app.game.action('tool', 'suture')
    key(app, pygame.K_t)                                    # wraps to the first blade
    assert app.game.tool == 'keratome'
    shot(app, 'v2-tool-tray-hard')
    click(app, to_screen(app.game._entry_target[0]))
    assert app.game.eye.entry_hits == 1


def test_illumination_is_visual_only(app):
    start(app)
    app.draw(); normal = pixels(app, FIELD)
    snapshot = app.game.snapshot()
    for _ in range(3):
        key(app, pygame.K_COMMA)
    app.draw()
    assert app.light == .7 and pixels(app, FIELD) != normal
    for _ in range(10):
        key(app, pygame.K_PERIOD)
    assert app.light == 1.3
    app.draw()
    assert app.game.snapshot() == snapshot


def test_autosave_on_phase_change_and_quit_then_resume(app):
    app.new_game(case='motion')
    start(app)
    app.draw()                                              # phase changed -> saved
    assert app.autosave_path.is_file()
    for p in app.game._entry_target:
        app.game.action('touch', *p)
    for _ in range(40):
        app.game.tick(.05)                                  # timed hold in progress
    app.dispatch(pygame.event.Event(pygame.QUIT, {}))
    saved = app.game.snapshot()
    other = App(pygame, scale=1)
    assert other.resume(app.autosave_path)
    assert other.game.snapshot() == saved
    assert other.game.patient.alert == 'PATIENT MOTION'
    assert other.game.alert_elapsed == pytest.approx(2.0)
    assert other._alerts_heard == 1                       # no repeated alert tone
    app.autosave_path.write_text('{"tampered": true}\n', encoding='utf-8')
    third = App(pygame, scale=1)
    assert not third.resume(app.autosave_path)
    assert 'Autosave not resumed' in third.message and third.game.phase == Phase.PREOP


def test_finished_case_clears_its_autosave(app):
    start(app)
    app.draw()
    assert app.autosave_path.is_file()
    key(app, pygame.K_x)
    app.draw()
    assert not app.autosave_path.exists()
