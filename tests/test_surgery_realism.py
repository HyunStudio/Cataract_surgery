"""Realistic procedure flow, complications, decisions and outcomes.

Implements the test plan in docs/SURGERY_REALISM_PLAN_KO.md section 7. All
cases are synthetic; the assertions check game rules, not clinical truth.
"""
import math
import os
import random

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import pytest

from ophthosim.complications import (CASE_KEYS, CASES, CATALOG, DECISIONS,
                                     OUTCOMES, RANDOM_POOL, narrate)
from ophthosim.engine import Game, Phase
from ophthosim.replay import ReplayGame

DECISION_CASES = {'capsule': 'CAPSULE INTEGRITY', 'timeout': 'SITE MISMATCH',
                  'iris': 'IRIS PROLAPSE', 'zonules': 'ZONULAR WEAKNESS',
                  'leak': 'WOUND LEAK'}
MAJOR = {'capsule', 'timeout', 'leak'}


def handle(game, choices):
    """Respond to any active safety hold like a surgeon would."""
    for _ in range(4):
        if not game.patient.alert or game.ending:
            return
        if not game.awaiting_decision:
            assert game.action('assess')
        if game.awaiting_decision:
            assert game.action('decide', choices.get(game.awaiting_decision, 'manage'))


def play(game, choices=None, *, ovd=True, hydro=True, ovd_bag=True, centre=(.5, .5)):
    """Drive a case from time-out to an ending with the given decisions."""
    choices = choices or {}
    for _ in range(3):
        if game.phase != Phase.PREOP or game.ending:
            break
        game.action('confirm')
        handle(game, choices)
    if game.ending:
        return game
    assert game.action('prepare')
    for x, y in game._entry_target:
        game.action('touch', x, y)
        handle(game, choices)
    if ovd and not game.ending:
        game.action('ovd')
    for i in range(24):
        if game.phase != Phase.CAPSULE or game.ending:
            break
        a = (i + .5) * math.tau / 24
        game.action('trace', .5 + .28 * math.cos(a), .5 + .28 * math.sin(a))
        handle(game, choices)
    handle(game, choices)
    if game.ending:
        return game
    if hydro:
        game.action('hydro')
    for _ in range(4000):
        if game.phase not in (Phase.PHACO, Phase.CORTEX) or game.ending:
            break
        game.action('remove', .5, .5)
        game.tick(1 / 60)
        handle(game, choices)
    if game.ending:
        return game
    assert game.phase == Phase.IOL
    if ovd_bag:
        assert game.action('ovd')
    for _ in range(5):
        if game.phase != Phase.IOL:
            break
        assert game.action('place', *centre)
    for _ in range(3):
        for item in ('alignment', 'wound', 'handoff'):
            if game.ending:
                break
            game.action('verify', item)
            handle(game, choices)
    return game


# --- Outcomes -------------------------------------------------------------------

def test_uncomplicated_case_with_correct_technique_is_success():
    game = play(Game('normal'))
    assert game.phase == Phase.RECOVERY
    assert game.outcome() == 'SUCCESS'
    assert game.outcome_title() == OUTCOMES['SUCCESS']
    assert game.score() == 100
    assert not game.alert_history


@pytest.mark.parametrize('case', ['motion', 'vitals', 'capsule', 'timeout',
                                  'iris', 'zonules', 'leak'])
def test_every_complication_managed_completes_as_managed(case):
    game = play(Game(case))
    assert game.phase == Phase.RECOVERY, game.debrief()
    assert game.outcome() == 'MANAGED'
    assert game.alert_history
    assert all(choice == 'manage' for _, choice in game.decisions)


@pytest.mark.parametrize('case', sorted(DECISION_CASES))
def test_stop_and_refer_is_a_safe_abort(case):
    game = play(Game(case), {DECISION_CASES[case]: 'refer'})
    assert game.phase == Phase.ABORTED
    assert game.outcome() == 'SAFE_ABORT'
    assert (DECISION_CASES[case], 'refer') in game.decisions
    assert dict(game.debrief())['Result'] == OUTCOMES['SAFE_ABORT'][1]


@pytest.mark.parametrize('case', sorted(MAJOR))
def test_ignoring_a_major_complication_is_critical_failure(case):
    key = DECISION_CASES[case]
    game = play(Game(case), {key: 'continue'})
    assert game.phase == Phase.FAILED
    assert game.ending == 'CRITICAL FAILURE'
    assert game.outcome() == 'CRITICAL_FAILURE'
    assert game.score() == 0
    assert game.failure_reason == CATALOG[key].continue_result
    assert not game.action('confirm') and not game.action('abort')


def test_ignoring_iris_prolapse_completes_with_complications():
    game = play(Game('iris'), {'IRIS PROLAPSE': 'continue'})
    assert game.phase == Phase.RECOVERY
    assert game.outcome() == 'COMPLICATED'
    assert 'iris_trauma' in game.flags
    assert game.work_radius == pytest.approx(.25)
    assert game.score() < play(Game('iris')).score()


def test_ignoring_zonular_weakness_decentres_the_iol():
    game = play(Game('zonules'), {'ZONULAR WEAKNESS': 'continue'})
    assert 'zonular_dialysis' in game.flags
    assert game.eye.iol_alignment <= .75
    assert game.outcome() == 'COMPLICATED'


# --- Stage-specific rules -----------------------------------------------------------

def test_site_mismatch_is_caught_by_the_time_out():
    game = Game('timeout')
    assert game.action('confirm')
    assert game.phase == Phase.PREOP
    assert game.patient.alert == 'SITE MISMATCH'
    assert not game.action('prepare')
    assert game.action('assess') and game.action('decide', 'manage')
    assert 'site_corrected' in game.flags
    assert game.action('confirm')
    assert game.phase == Phase.ANESTHESIA


def test_ovd_rules_follow_the_real_sequence():
    game = Game()
    assert not game.action('ovd')               # no incision yet
    game.action('confirm'); game.action('prepare')
    assert not game.action('ovd')               # still no access
    x, y = game._entry_target[0]
    assert game.action('touch', x, y)
    assert game.action('ovd')
    assert not game.action('ovd')               # chamber already filled
    assert game.ovd_chamber and not game.ovd_bag


def test_shallow_chamber_narrows_the_rhexis_and_tears_sooner():
    deep, shallow = Game(), Game()
    for game in (deep, shallow):
        game.action('confirm'); game.action('prepare')
        for x, y in game._entry_target:
            game.action('touch', x, y)
    assert deep.action('ovd')
    edge = (.5 + .355, .5)                       # inside deep band, outside shallow band
    assert deep.action('trace', *edge)
    assert not shallow.action('trace', *edge)
    for _ in range(Game.RUNOUT_LIMIT_SHALLOW - 1):
        shallow.action('trace', *edge)
    assert shallow.patient.alert == 'RHEXIS TEAR'
    out = (.5 + .40, .5)
    for _ in range(Game.RUNOUT_LIMIT - 1):
        deep.action('trace', *out)
    assert not deep.patient.alert
    deep.action('trace', *out)
    assert deep.patient.alert == 'RHEXIS TEAR'
    assert 'rhexis_without_ovd' not in deep.flags


def test_ignored_rhexis_tear_extends_into_posterior_capsule_rupture():
    game = Game()
    game.action('confirm'); game.action('prepare')
    for x, y in game._entry_target:
        game.action('touch', x, y)
    for _ in range(Game.RUNOUT_LIMIT_SHALLOW):
        game.action('trace', .9, .5)
    assert game.patient.alert == 'RHEXIS TEAR'
    assert game.action('assess') and game.action('decide', 'continue')
    assert 'tear_extending' in game.flags
    for i in range(24):
        a = (i + .5) * math.tau / 24
        game.action('trace', .5 + .28 * math.cos(a), .5 + .28 * math.sin(a))
    assert game.action('hydro')
    for _ in range(200):
        if game.patient.alert:
            break
        game.action('remove', .5, .5)
        game.tick(1 / 60)
    assert game.patient.alert == 'CAPSULE INTEGRITY'
    assert game.eye.opacity <= .6
    assert game.eye.capsule_integrity == pytest.approx(.55)


def test_hydrodissection_window_and_skipping_it_costs_technique():
    assert not Game().action('hydro')            # nothing to hydrodissect yet
    skipped = play(Game(), hydro=False)
    assert 'phaco_without_hydro' in skipped.flags
    assert skipped.score() <= 97
    assert dict(skipped.debrief())['Skipped steps'] == 'hydrodissection'
    proper = Game()
    proper.action('confirm'); proper.action('prepare')
    for x, y in proper._entry_target:
        proper.action('touch', x, y)
    proper.action('ovd')
    for i in range(24):
        a = (i + .5) * math.tau / 24
        proper.action('trace', .5 + .28 * math.cos(a), .5 + .28 * math.sin(a))
    assert proper.action('remove', .5, .5)
    assert not proper.action('hydro')            # too late once phaco has started


def test_iol_without_bag_viscoelastic_is_recorded():
    game = play(Game(), ovd_bag=False)
    assert 'iol_without_ovd' in game.flags
    assert game.score() == 97


def test_decentred_iol_must_be_repositioned():
    other = Game()
    other.action('confirm'); other.action('prepare')
    for x, y in other._entry_target:
        other.action('touch', x, y)
    for i in range(24):
        a = (i + .5) * math.tau / 24
        other.action('trace', .5 + .28 * math.cos(a), .5 + .28 * math.sin(a))
    other.action('hydro')
    while other.phase in (Phase.PHACO, Phase.CORTEX):
        other.action('remove', .5, .5)
        other.tick(1 / 60)
    assert other.action('place', .7, .5)
    assert other.phase == Phase.IOL
    assert any(e['kind'] == 'iol_decentred' for e in other.events)
    assert other.action('place', .5, .5)
    assert other.phase == Phase.CLOSE


def test_wound_leak_blocks_closure_until_sealed():
    game = Game('leak')
    play(game, {'WOUND LEAK': 'manage'})
    assert game.phase == Phase.RECOVERY
    assert 'wound_sealed' in game.flags
    assert [e['data'].get('leak') for e in game.events if e['kind'] == 'check'
            and e['data']['item'] == 'wound'] == [True, None]


def test_posterior_capsule_rupture_can_recur_after_management():
    game = Game('capsule')
    game.action('confirm'); game.action('prepare')
    for x, y in game._entry_target:
        game.action('touch', x, y)
    for i in range(24):
        a = (i + .5) * math.tau / 24
        game.action('trace', .5 + .28 * math.cos(a), .5 + .28 * math.sin(a))
    handle(game, {'CAPSULE INTEGRITY': 'manage'})
    assert 'pcr_managed' in game.flags and game.stress_scale == 2
    for _ in range(60):
        game.action('remove', .95, .5)
    assert game.patient.alert == 'CAPSULE INTEGRITY'
    assert game.alert_history.count('CAPSULE INTEGRITY') == 2


def test_managed_pcr_places_iol_in_the_sulcus():
    game = play(Game('capsule'))
    assert 'sulcus_iol' in game.flags


# --- Decision rules -------------------------------------------------------------

def test_decision_requires_assessment_and_blocks_instruments():
    fresh = Game('capsule')
    fresh.action('confirm'); fresh.action('prepare')
    for x, y in fresh._entry_target:
        fresh.action('touch', x, y)
    for i in range(24):
        a = (i + .5) * math.tau / 24
        fresh.action('trace', .5 + .28 * math.cos(a), .5 + .28 * math.sin(a))
    assert fresh.patient.alert == 'CAPSULE INTEGRITY'
    assert not fresh.action('decide', 'manage')          # not assessed yet
    assert fresh.action('assess')
    assert not fresh.action('assess')                     # already assessed
    assert not fresh.action('remove', .5, .5)
    assert not fresh.action('hydro')
    for bad in (None, 'bad', 1, True, 'x' * 90, ['manage']):
        assert not fresh.action('decide', bad)
    assert fresh.awaiting_decision == 'CAPSULE INTEGRITY'


def test_decide_without_a_complication_is_rejected():
    game = Game()
    for choice in DECISIONS:
        assert not game.action('decide', choice)


# --- Cases, randomness, replay ------------------------------------------------------

def test_case_catalogue_is_complete_and_consistent():
    assert len(CASE_KEYS) == 9
    for key, brief in CASES.items():
        assert brief.risks and brief.patient.startswith('Mock patient')
        assert all(h in CATALOG for h in brief.hazards)
    for entry in CATALOG.values():
        assert entry.signs and entry.title
        if entry.decision:
            assert entry.manage and entry.continue_result and entry.refer_result
            assert len(entry.manage) <= 46


def test_random_case_is_seeded_and_varied():
    combos = {Game('random', seed).hazards for seed in range(40)}
    assert len(combos) >= 5
    assert all(len(c) == 2 and set(c) <= set(RANDOM_POOL) for c in combos)
    assert Game('random', 12).hazards == Game('random', 12).hazards
    game = play(Game('random', 12))
    assert game.phase == Phase.RECOVERY
    assert game.outcome() == 'MANAGED'
    assert set(game.fired) == set(game.hazards)


@pytest.mark.parametrize('case,choice', [(c, d) for c in sorted(DECISION_CASES)
                                         for d in DECISIONS] + [('normal', 'manage'),
                                                                ('random', 'manage')])
def test_every_branch_replays_exactly(case, choice):
    game = play(ReplayGame(case, 5), {DECISION_CASES.get(case, ''): choice})
    assert game.ending
    again = ReplayGame.replay_jsonl(game.export_replay_jsonl())
    assert again.snapshot() == game.snapshot()
    assert again.export_jsonl() == game.export_jsonl()


def test_fuzz_new_commands_never_crash_and_replay():
    rng = random.Random(1313)
    names = ['decide', 'ovd', 'hydro', 'assess', 'confirm', 'prepare', 'touch',
             'trace', 'remove', 'place', 'verify', 'abort', None, 3]
    values = [None, 'manage', 'continue', 'refer', 'wound', 'bad', .5, .3, .9,
              float('nan'), 10**400, True]
    for case in ('timeout', 'capsule', 'random'):
        game = ReplayGame(case, rng.randrange(1000))
        for i in range(3000):
            name = rng.choice(names)
            if name == 'abort' and rng.random() < .97:
                continue
            assert isinstance(game.action(name, rng.choice(values), rng.choice(values)), bool)
            if i % 3 == 0:
                game.tick(1 / 60)
        assert 0 <= game.score() <= 100
        again = ReplayGame.replay_jsonl(game.export_replay_jsonl())
        assert again.snapshot() == game.snapshot()


def test_checklists_and_narration_cover_the_procedure():
    game = Game('leak')
    seen = set()
    for phase in Phase:
        game.phase = phase
        items = game.checklist()
        if phase in (Phase.RECOVERY, Phase.ABORTED, Phase.FAILED):
            assert items == []
        else:
            assert items and all(len(label) <= 24 for label, _, _ in items)
            seen.update(label for label, _, _ in items)
    assert {'Main incision', 'Hydrodissection', 'Wounds watertight'} <= seen
    played = play(Game('leak'))
    texts = [narrate(e) for e in played.events]
    assert 'Leak found at the main incision!' in texts
    assert 'Hydrodissection done: the nucleus rotates freely.' in texts


# --- Front-ends -------------------------------------------------------------------

class _AtDecision(Exception):
    pass


def _decision_states():
    """One game per decision case, paused with the decision menu open."""
    for case, key in DECISION_CASES.items():
        game = ReplayGame(case, 3)
        real_action = game.action

        def stop_before_deciding(name, x=None, y=None):
            if name == 'decide':
                raise _AtDecision
            return real_action(name, x, y)
        game.action = stop_before_deciding
        try:
            play(game)
        except _AtDecision:
            pass
        del game.action
        assert game.awaiting_decision == key
        yield game


def test_2d_screens_for_brief_complications_and_every_outcome():
    pygame = pytest.importorskip('pygame')
    from ophthosim.app import App
    pygame.init()
    try:
        app = App(pygame, scale=1)
        for key in CASE_KEYS:
            app.game = ReplayGame(key, 7)
            app.draw()
        for game in _decision_states():
            app.game = game
            app.draw()
            assert len(app._option_rects) == 3
            # Clicking option 2 manages the complication.
            x, y, w, h = app._option_rects[1]
            app.cursor = (x + 5, y + 5)
            app.pointer_action()
            assert (game.decisions[-1][1] if game.decisions else None) == 'manage'
        for case, choices in (('normal', {}), ('capsule', {'CAPSULE INTEGRITY': 'continue'}),
                              ('iris', {'IRIS PROLAPSE': 'continue'}),
                              ('leak', {'WOUND LEAK': 'refer'}), ('vitals', {})):
            app.game = play(ReplayGame(case, 7), choices)
            app.draw()
    finally:
        pygame.quit()


def test_2d_keyboard_decisions_and_procedure_keys():
    pygame = pytest.importorskip('pygame')
    from ophthosim.app import App
    pygame.init()
    try:
        app = App(pygame, scale=1)
        key = lambda k: app.dispatch(pygame.event.Event(pygame.KEYDOWN, {'key': k}))
        key(pygame.K_5)
        assert app.game.case == 'timeout'
        key(pygame.K_SPACE)
        assert app.game.patient.alert == 'SITE MISMATCH'
        key(pygame.K_a)
        key(pygame.K_2)
        assert app.game.decisions == [('SITE MISMATCH', 'manage')]
        assert app.message.startswith('Site verified')
        key(pygame.K_SPACE); key(pygame.K_SPACE)
        x, y = app.game._entry_target[0]
        assert app.game.action('touch', x, y)
        key(pygame.K_v)
        assert app.game.ovd_chamber
        assert app.message == 'Viscoelastic injected into the chamber.'
    finally:
        pygame.quit()


def test_2d_phase_change_releases_the_held_instrument():
    pygame = pytest.importorskip('pygame')
    from ophthosim.app import App, to_screen
    pygame.init()
    try:
        app = App(pygame, scale=1)
        g = app.game
        g.action('confirm'); g.action('prepare')
        for x, y in g._entry_target:
            g.action('touch', x, y)
        g.action('ovd')
        for i in range(19):
            a = (i + .5) * math.tau / 24
            g.action('trace', .5 + .28 * math.cos(a), .5 + .28 * math.sin(a))
        a = 19.5 * math.tau / 24
        pos = to_screen((.5 + .28 * math.cos(a), .5 + .28 * math.sin(a)))
        app.dispatch(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'button': 1, 'pos': pos}))
        app.tick_once()
        assert g.phase == Phase.PHACO
        for _ in range(30):
            app.tick_once()
        assert g.eye.opacity == 1.0 and not app.drag
        assert g.action('hydro')
    finally:
        pygame.quit()


def test_3d_hud_cards_and_outcomes_render():
    pygame = pytest.importorskip('pygame')
    from ophthosim.gl_surgery import OUTCOME_COLORS, PHASE_NAMES, SurgeryHUD
    from ophthosim.input3d import Surgery3DController
    assert set(PHASE_NAMES) == set(Phase)
    assert set(OUTCOME_COLORS) == set(OUTCOMES)
    pygame.init()
    try:
        surf = pygame.Surface((1280, 720), pygame.SRCALPHA)
        font = pygame.font.SysFont('segoeui', 20)
        big = pygame.font.SysFont('segoeui', 28, bold=True)
        c = Surgery3DController()
        hud = SurgeryHUD(c)
        games = [ReplayGame(k, 7) for k in CASE_KEYS] + list(_decision_states())
        games += [play(ReplayGame('capsule', 7), {'CAPSULE INTEGRITY': 'continue'}),
                  play(ReplayGame('zonules', 7)), play(ReplayGame('normal', 7))]
        for game in games:
            c.game = game
            surf.fill((0, 0, 0, 0))
            hud.narrate()
            hud.draw(pygame, surf, c.view, 1280, 720, font, big)
            assert surf.get_at((640, 360)).a > 0      # centre card drawn
    finally:
        pygame.quit()
