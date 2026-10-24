"""Engine v3: spec state contract, vitreous and capsule-rim events, help
requests, synthetic patient card and normalized endpoint-error metrics."""
import json
import math

import pytest

from ophthosim.engine import (CASES, ENDING_ABORTED, ENDING_MANAGED, HAZARDS,
                              RIM_ALERT, RIM_MISS_LIMIT, Game, Phase)
from ophthosim.replay import ReplayGame
from test_engine_v2 import arm, run_to


def test_cases_include_vitreous_and_ten_total():
    assert len(CASES) == 10 and 'vitreous' in CASES
    assert HAZARDS['vitreous'] == (Phase.CORTEX, 'VITREOUS EVENT')


def test_vitreous_event_escalates_to_safe_stop_and_is_irreversible():
    game = Game('vitreous')
    run_to(game, Phase.CORTEX)
    assert game.patient.alert == 'VITREOUS EVENT'
    snap = game.snapshot()
    assert snap['safety_hold'] and set(snap['irreversible']) == {'capsule_damage', 'vitreous'}
    assert game.action('assess')
    assert game.phase == Phase.ABORTED and game.ending == ENDING_ABORTED
    assert {'capsule_damage', 'vitreous'} <= set(game.snapshot()['irreversible'])


def _to_capsule(difficulty='standard'):
    game = Game(difficulty=difficulty)
    run_to(game, Phase.CAPSULE)
    arm(game)
    return game


@pytest.mark.parametrize('difficulty', ['tutorial', 'standard', 'hard'])
def test_repeated_off_path_tracing_raises_rim_alert_once(difficulty):
    game = _to_capsule(difficulty)
    limit = RIM_MISS_LIMIT[difficulty]
    for _ in range(limit - 1):
        assert not game.action('trace', .5, .5)          # centre: off the ring
    assert not game.patient.alert
    game.action('trace', .5, .5)
    assert game.patient.alert == RIM_ALERT and 'capsule_rim' in game.irreversible
    assert game.action('assess')
    for _ in range(limit * 2):
        game.action('trace', .5, .5)
    assert not game.patient.alert                            # fires only once
    assert sum(a['kind'] == RIM_ALERT for a in game.alerts) == 1


def test_rim_alert_increases_later_stress():
    plain = Game()
    run_to(plain, Phase.PHACO)
    rim = _to_capsule()
    for _ in range(RIM_MISS_LIMIT['standard']):
        rim.action('trace', .5, .5)
    rim.action('assess')
    run_to(rim, Phase.PHACO)
    for g in (plain, rim):
        arm(g)
        for _ in range(10):
            g.action('remove', .95, .5)
    assert rim.stress == pytest.approx(plain.stress * 1.5)
    run_to(rim, None)
    assert rim.ending == ENDING_MANAGED


def test_help_is_always_available_and_free():
    game = Game('motion')
    assert game.action('help')
    run_to(game, Phase.CAPSULE)
    assert game.patient.alert
    assert game.action('help')            # allowed during a safety hold
    before = game.score_breakdown()
    assert game.help_requests == 2
    assert game.score_breakdown() == before
    kinds = [e for e in game.events if e['kind'] == 'help_requested']
    assert kinds[-1]['data'] == {'alert': 'PATIENT MOTION'}
    game.action('abort')
    assert not game.action('help')


def test_snapshot_contract_fields():
    game = Game()
    run_to(game, Phase.PHACO)
    for _ in range(10):
        game.tick(.05)
    snap = game.snapshot()
    for key in ('schema_version', 'session_id', 'patient_card', 'phase_time',
                'safety_hold', 'irreversible', 'stress', 'fragments', 'help_requests'):
        assert key in snap
    assert snap['schema_version'] == 3 and snap['phase_time'] == pytest.approx(.5)
    assert snap['fragments'] == 12 and snap['safety_hold'] is False
    arm(game)
    for _ in range(20):
        game.action('remove', .5, .5)
    assert game.snapshot()['fragments'] == 6
    json.dumps(snap)


def test_events_carry_session_and_scenario_ids():
    a, b = Game('haze', 5, 'hard'), Game('haze', 5, 'hard')
    assert a.session_id == b.session_id and a.session_id.startswith('SIM-')
    assert Game('haze', 6, 'hard').session_id != a.session_id
    assert all(e['session_id'] == a.session_id and e['scenario_id'] == 'haze/hard'
               for e in a.events)


def test_patient_card_is_seeded_synthetic_and_logged():
    cards = {seed: Game(seed=seed).patient_card for seed in range(30)}
    assert {c['eye'] for c in cards.values()} == {'OD', 'OS'}
    assert all(2 <= c['opacity_grade'] <= 4 and c['patient_id'].startswith('SYN-')
               for c in cards.values())
    assert Game(seed=3).patient_card == cards[3]
    assert Game('pupil').patient_card['pupil'] == 'small'
    assert Game().events[0]['data']['card'] == Game().patient_card
    # The card draw must not change the seeded random-hazard draw.
    assert Game('random', 11).hazard == Game('random', 11).hazard


def test_endpoint_error_is_normalized_to_target_radius():
    game = Game()
    run_to(game, Phase.ENTRY)
    x, y = game._entry_target[0]
    assert game.action('touch', x + game.rules.entry_radius / 2, y)   # half a radius off
    for target in game._entry_target[1:]:
        assert game.action('touch', *target)                           # exact hits
    assert game.phase == Phase.CAPSULE
    arm(game)
    game.action('trace', .5 + .28, .5)                          # exactly on the ring
    run_to(game, Phase.RECOVERY)
    errors = game.metrics()['endpoint_error']
    assert errors['ENTRY'] == pytest.approx((.5 + 0 + 0) / 3, abs=1e-3)
    assert errors['IOL'] == 0.0
    assert 0 <= errors['CAPSULE'] < .1


def test_near_misses_are_logged_with_coordinates():
    game = Game()
    run_to(game, Phase.PHACO)
    arm(game)
    game.action('remove', .9, .5)
    miss = [e for e in game.events if e['kind'] == 'near_miss']
    assert miss and miss[0]['data'] == {'x': .9, 'y': .5}


def test_replay_v3_journals_help_and_rejects_v2_headers():
    game = ReplayGame('vitreous', 4, 'tutorial')
    game.action('help')
    run_to(game, Phase.CORTEX)
    game.action('help')
    game.action('assess')
    raw = game.export_replay_jsonl()
    assert raw.count('"name":"help"') == 2
    again = ReplayGame.replay_jsonl(raw)
    assert again.snapshot() == game.snapshot()
    header = json.loads(raw.splitlines()[0])
    header['schema_version'] = 2
    with pytest.raises(ValueError):
        ReplayGame.replay_jsonl('\n'.join([json.dumps(header), *raw.splitlines()[1:]]))
