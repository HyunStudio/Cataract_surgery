"""Engine v2: pre-op gate, difficulty rules, four endings, explainable score,
extra synthetic complications, research metrics and replay schema v2.

All values are game-design hypotheses; nothing here is clinical guidance.
"""
import json
import math

import pytest

from ophthosim.engine import (CASES, DIFFICULTIES, ENDING_ABORTED, ENDING_COMPLETE,
                              ENDING_FAILED, ENDING_MANAGED, FINAL_CHECKS, HAZARDS,
                              PREOP_CHECKS, SCORE_WEIGHTS, Game, Phase)
from ophthosim.replay import ReplayGame


def preop(game):
    for item in PREOP_CHECKS:
        assert game.action('verify', item)
    assert game.action('confirm')
    assert game.action('prepare')


def arm(game):
    """Pick the stage instrument (hard mode does not auto-select it)."""
    if game.required_tool and game.tool != game.required_tool:
        assert game.action('tool', game.required_tool)


def entry(game):
    arm(game)
    for x, y in game._entry_target:
        assert game.action('touch', x, y)


def capsule(game):
    arm(game)
    for i in range(24):
        a = (i + .5) * math.tau / 24
        game.action('trace', .5 + .28 * math.cos(a), .5 + .28 * math.sin(a))


def clear(game, phase):
    arm(game)
    for _ in range(60):
        if game.phase != phase:
            break
        game.action('remove', .5, .5)


def run_to(game, target):
    """Drive a game along the ideal path, assessing alerts immediately."""
    steps = {Phase.PREOP: lambda: preop(game), Phase.ENTRY: lambda: entry(game),
             Phase.CAPSULE: lambda: capsule(game),
             Phase.PHACO: lambda: clear(game, Phase.PHACO),
             Phase.CORTEX: lambda: clear(game, Phase.CORTEX),
             Phase.IOL: lambda: (arm(game), game.action('place', .5, .5))}
    for _ in range(40):
        if game.phase == target or game.ending:
            return
        if game.patient.alert:
            game.action('assess')
            continue
        if game.phase == Phase.CLOSE:
            if game._decentered:
                arm(game)
                game.action('place', .5, .5)
                continue
            for item in FINAL_CHECKS:
                if game.patient.alert:
                    break
                game.action('verify', item)
            continue
        steps[game.phase]()


# --- pre-op gate -------------------------------------------------------
def test_confirm_requires_every_preop_check():
    game = Game()
    assert not game.action('confirm')
    assert game.action('verify', 'identity')
    assert game.action('verify', 'site')
    assert not game.action('confirm')
    assert game.phase == Phase.PREOP
    assert game.action('verify', 'iol_plan')
    assert game.action('confirm')
    assert game.phase == Phase.ANESTHESIA
    rejected = [e for e in game.events if e['kind'] == 'rejected']
    assert len(rejected) == 2 and rejected[0]['data']['reason'] == 'preop_checks_incomplete'


@pytest.mark.parametrize('item', ['wound', 'IDENTITY', '', None, 5, 'x' * 90])
def test_invalid_preop_items_rejected(item):
    game = Game()
    assert not game.action('verify', item)
    assert not game.eye.preop_checks


def test_preop_checks_are_not_final_checks():
    game = Game()
    preop(game)
    assert not game.action('verify', 'identity')   # wrong phase now
    assert game.eye.preop_checks == set(PREOP_CHECKS)
    assert not game.eye.final_checks


# --- difficulty ----------------------------------------------------------
def test_unknown_difficulty_rejected():
    for bad in ('expert', '', None, 1):
        with pytest.raises(ValueError):
            Game(difficulty=bad)


def test_entry_tolerance_depends_on_difficulty():
    near = (.69 + .105, .46)   # 0.105 from the first target
    results = {}
    for level in DIFFICULTIES:
        game = Game(difficulty=level)
        preop(game)
        results[level] = game.action('touch', *near)
    assert results == {'tutorial': True, 'standard': False, 'hard': False}


def test_capsule_bins_required_by_difficulty():
    for level, rules in DIFFICULTIES.items():
        game = Game(difficulty=level)
        preop(game)
        entry(game)
        arm(game)
        for i in range(rules.capsule_bins - 1):
            a = (i + .5) * math.tau / 24
            game.action('trace', .5 + .28 * math.cos(a), .5 + .28 * math.sin(a))
        assert game.phase == Phase.CAPSULE
        a = (rules.capsule_bins - .5) * math.tau / 24
        game.action('trace', .5 + .28 * math.cos(a), .5 + .28 * math.sin(a))
        assert game.phase == Phase.PHACO


def test_iol_threshold_depends_on_difficulty():
    point = (.5 + .1, .5)   # alignment 0.7
    outcomes = {}
    for level in DIFFICULTIES:
        game = Game(difficulty=level)
        run_to(game, Phase.IOL)
        arm(game)
        game.action('place', *point)
        outcomes[level] = game.phase
    assert outcomes == {'tutorial': Phase.CLOSE, 'standard': Phase.CLOSE,
                        'hard': Phase.IOL}


# --- endings and veto -----------------------------------------------------
def test_ideal_normal_case_is_complete_with_full_breakdown():
    game = Game()
    run_to(game, Phase.RECOVERY)
    assert game.ending == ENDING_COMPLETE
    assert game.score() == 100
    breakdown = game.score_breakdown()
    assert [b['key'] for b in breakdown] == [k for k, _ in SCORE_WEIGHTS]
    assert all(b['points'] == b['max'] for b in breakdown)
    assert sum(b['max'] for b in breakdown) == 100


@pytest.mark.parametrize('case', ['motion', 'vitals', 'pupil', 'haze', 'decenter', 'leak'])
def test_assessed_complication_ends_as_managed(case):
    game = Game(case)
    run_to(game, Phase.RECOVERY)
    assert game.phase == Phase.RECOVERY
    assert game.ending == ENDING_MANAGED
    assert len(game.alerts) == 1 and game.alerts[0]['response'] == 'assess'
    assert game.alerts[0]['kind'] == HAZARDS[case][1]


def test_capsule_complication_still_ends_in_safe_abort():
    game = Game('capsule')
    run_to(game, Phase.RECOVERY)
    assert game.phase == Phase.ABORTED and game.ending == ENDING_ABORTED


def test_unattended_alert_is_a_critical_failure_veto():
    game = Game('motion')
    run_to(game, Phase.CAPSULE)
    assert game.patient.alert == 'PATIENT MOTION'
    game.action('pause')                     # pausing cannot freeze the hold
    for _ in range(int(29.9 / .05)):
        game.tick(.05)
    assert game.ending is None
    for _ in range(4):
        game.tick(.05)
    assert game.phase == Phase.FAILED
    assert game.ending == ENDING_FAILED
    assert game.alerts[0]['response'] == 'timeout'
    breakdown = {b['key']: b for b in game.score_breakdown()}
    assert breakdown['safety']['points'] == 0 and breakdown['safety']['detail']['veto']
    assert breakdown['response']['points'] == 0
    assert any(e['kind'] == 'veto' for e in game.events)
    assert not game.action('assess') and not game.action('abort')


def test_hard_times_out_sooner_and_tutorial_never():
    hard = Game('motion', difficulty='hard')
    run_to(hard, Phase.CAPSULE)
    for _ in range(int(15.05 / .05)):
        hard.tick(.05)
    assert hard.ending == ENDING_FAILED
    tutorial = Game('motion', difficulty='tutorial')
    run_to(tutorial, Phase.CAPSULE)
    for _ in range(4000):
        tutorial.tick(.05)
    assert tutorial.ending is None and tutorial.patient.alert
    assert tutorial.action('assess')


def test_response_points_fall_with_latency():
    scores = []
    for wait in (0, 6., 18.):
        game = Game('vitals')
        run_to(game, Phase.PHACO)
        for _ in range(round(wait / .05)):
            game.tick(.05)
        assert game.action('assess')
        run_to(game, Phase.RECOVERY)
        response = game.score_breakdown()[3]
        scores.append(response['points'])
        assert response['detail']['alerts'][0]['latency'] == pytest.approx(wait, abs=1e-6)
    assert scores[0] == 20 and scores[0] > scores[1] > scores[2] > 0


def test_safe_abort_without_alert_keeps_safety_points():
    game = Game()
    run_to(game, Phase.CAPSULE)
    assert game.action('abort')
    breakdown = {b['key']: b['points'] for b in game.score_breakdown()}
    assert game.ending == ENDING_ABORTED
    assert breakdown['safety'] == 15 and breakdown['response'] == 20
    assert breakdown['tissue'] == 0 and breakdown['iol'] == 0


def test_points_are_only_earned_once_evaluated():
    game = Game()
    assert game.score() == 0
    run_to(game, Phase.PHACO)
    breakdown = {b['key']: b for b in game.score_breakdown()}
    assert breakdown['tissue']['points'] == 0 and not breakdown['tissue']['detail']['evaluated']
    assert breakdown['response']['points'] == 0 and breakdown['safety']['points'] == 0
    assert game.score() < 20


# --- complications --------------------------------------------------------
def test_pupil_constriction_shrinks_the_work_radius():
    game = Game('pupil')
    run_to(game, Phase.PHACO)
    assert game.patient.alert == 'PUPIL CONSTRICTION'
    assert game.action('assess')
    assert game.eye.pupil < 1 and game.work_radius < game.rules.work_radius
    edge = .5 + (game.work_radius + game.rules.work_radius) / 2
    assert not game.action('remove', edge, .5)
    assert game.near_misses == 1
    assert game.action('remove', .5, .5)


def test_corneal_haze_partially_clears_after_assessment():
    game = Game('haze')
    run_to(game, Phase.CORTEX)
    assert game.patient.alert == 'CORNEAL HAZE' and game.eye.cornea_clarity == .4
    assert game.action('assess')
    assert game.eye.cornea_clarity == .7


def test_iol_decentration_blocks_alignment_check_until_repositioned():
    game = Game('decenter')
    run_to(game, Phase.CLOSE)
    assert game.patient.alert == 'IOL DECENTRATION'
    assert game.eye.iol_alignment <= .42
    assert game.action('assess')
    assert not game.action('verify', 'alignment')
    assert not game.action('place', .9, .9) or game._decentered   # poor reposition
    assert game.action('place', .5, .5)
    assert not game._decentered
    assert game.action('verify', 'alignment')
    assert game.iol_attempts >= 2


def test_wound_leak_holds_the_ending_until_rechecked():
    game = Game('leak')
    run_to(game, Phase.CLOSE)
    for item in FINAL_CHECKS:
        assert game.action('verify', item)
    assert game.phase == Phase.CLOSE and game.ending is None
    assert game.patient.alert == 'WOUND LEAK RISK'
    assert 'wound' not in game.eye.final_checks
    assert game.action('assess')
    assert game.phase == Phase.CLOSE
    assert game.action('verify', 'wound')
    assert game.phase == Phase.RECOVERY and game.ending == ENDING_MANAGED


def test_random_case_draw_is_seeded_and_logged():
    draws = {seed: Game('random', seed).hazard for seed in range(40)}
    assert set(draws.values()) <= set(HAZARDS)
    assert len(set(draws.values())) >= 4
    for seed, hazard in draws.items():
        game = Game('random', seed)
        assert game.hazard == hazard
        assert game.events[1]['kind'] == 'scenario_draw'
        assert game.events[1]['data'] == {'hazard': hazard, 'source': 'seeded_rng',
                                          'probability': round(1 / len(HAZARDS), 4)}


def test_every_case_reaches_an_ending():
    for case in CASES:
        for level in DIFFICULTIES:
            game = Game(case, 3, level)
            run_to(game, Phase.RECOVERY)
            assert game.ending in (ENDING_COMPLETE, ENDING_MANAGED, ENDING_ABORTED)


# --- metrics ---------------------------------------------------------------
def test_metrics_track_time_paths_and_near_misses():
    game = Game()
    run_to(game, Phase.PHACO)
    for _ in range(30):
        game.tick(.05)
    game.action('remove', .95, .5)
    run_to(game, Phase.RECOVERY)
    m = game.metrics()
    assert m['near_misses'] == 1 and m['rejected_inputs'] >= 1
    assert m['phase_time_s']['PHACO'] == pytest.approx(1.5)
    assert sum(m['phase_time_s'].values()) == pytest.approx(m['sim_time_s'])
    assert m['action_path']['CAPSULE'] > 1.0
    assert m['iol_attempts'] == 1 and m['ending'] == ENDING_COMPLETE
    json.dumps(m)   # serializable


# --- replay v2 --------------------------------------------------------------
@pytest.mark.parametrize('case,level', [('normal', 'hard'), ('decenter', 'tutorial'),
                                        ('leak', 'standard'), ('random', 'hard')])
def test_replay_round_trip_includes_difficulty(case, level):
    game = ReplayGame(case, 11, level)
    run_to(game, Phase.RECOVERY)
    raw = game.export_replay_jsonl()
    header = json.loads(raw.splitlines()[0])
    assert header['schema_version'] == 3 and header['difficulty'] == level
    again = ReplayGame.replay_jsonl(raw)
    assert again.snapshot() == game.snapshot()
    assert again.score_breakdown() == game.score_breakdown()


def test_replay_reproduces_timed_out_failure():
    game = ReplayGame('vitals', 5)
    run_to(game, Phase.PHACO)
    for _ in range(700):
        game.tick(.05)
    assert game.ending == ENDING_FAILED
    again = ReplayGame.replay_jsonl(game.export_replay_jsonl())
    assert again.ending == ENDING_FAILED and again.snapshot() == game.snapshot()


def test_replay_rejects_v1_header_and_edited_difficulty():
    game = ReplayGame()
    run_to(game, Phase.CAPSULE)
    lines = game.export_replay_jsonl().splitlines()
    header = json.loads(lines[0])
    legacy = dict(header)
    legacy.pop('difficulty')
    legacy['schema_version'] = 1
    with pytest.raises(ValueError):
        ReplayGame.replay_jsonl('\n'.join([json.dumps(legacy), *lines[1:]]))
    header['difficulty'] = 'tutorial'
    with pytest.raises(ValueError):
        ReplayGame.replay_jsonl('\n'.join([json.dumps(header, separators=(',', ':'),
                                                      sort_keys=True), *lines[1:]]))


# --- instruments --------------------------------------------------------------
def test_standard_auto_selects_and_hard_requires_the_stage_tool():
    standard = Game()
    preop(standard)
    assert standard.tool == 'blade' and standard.required_tool == 'blade'
    hard = Game(difficulty='hard')
    preop(hard)
    assert hard.tool is None and hard.required_tool == 'blade'
    x, y = hard._entry_target[0]
    assert not hard.action('touch', x, y)
    assert hard.wrong_tool == 1 and hard.rejected_inputs == 1
    assert hard.action('tool', 'phaco')
    assert not hard.action('touch', x, y) and hard.wrong_tool == 2
    assert hard.action('tool', 'blade') and hard.action('touch', x, y)
    reasons = [e['data'] for e in hard.events if e['kind'] == 'rejected']
    assert reasons[-1] == {'action': 'touch', 'reason': 'wrong_tool',
                           'tool': 'phaco', 'required': 'blade'}


@pytest.mark.parametrize('bad', ['scalpel', '', None, 3, 'BLADE'])
def test_unknown_tools_rejected(bad):
    game = Game()
    assert not game.action('tool', bad)


def test_tool_choice_blocked_during_alert_and_journaled_in_replay():
    game = ReplayGame('motion', 2, 'hard')
    run_to(game, Phase.CAPSULE)
    assert game.patient.alert
    assert not game.action('tool', 'forceps')
    run_to(game, Phase.RECOVERY)
    raw = game.export_replay_jsonl()
    assert '"name":"tool"' in raw
    assert ReplayGame.replay_jsonl(raw).snapshot() == game.snapshot()
    assert game.metrics()['wrong_tool'] == 0
