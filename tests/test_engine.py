"""Headless, deterministic functional / adversarial tests."""
import json
import math
import random

import pytest

from ophthosim.engine import Game, Phase


def enter_capsule(game):
    assert game.action('confirm')
    assert game.action('prepare')
    assert game.phase == Phase.ENTRY
    for x, y in game._entry_target:
        assert game.action('touch',x,y)
    assert game.phase == Phase.CAPSULE


def trace_capsule(game):
    for i in range(24):
        a=(i+.5)*math.tau/24
        game.action('trace', .5 + .28*math.cos(a),.5 + .28*math.sin(a))
    assert game.phase == Phase.PHACO


def finish(game):
    enter_capsule(game)
    trace_capsule(game)
    for _ in range(40):
        game.action('remove', .5, .5)
    assert game.phase == Phase.CORTEX
    for _ in range(40):
        game.action('remove', .5, .5)
    assert game.phase == Phase.IOL
    assert game.action('place',.51,.51)
    assert game.phase == Phase.CLOSE
    for name in ('alignment','wound','handoff'):
        assert game.action('verify',name)
    assert game.phase == Phase.RECOVERY
    assert game.ending == 'SIMULATION COMPLETE'


def test_complete_session():
    game=Game()
    finish(game)
    assert game.eye.opacity == 0
    assert game.eye.cortex == 0
    assert game.eye.iol_alignment > .65
    assert game.score() >= 85


def test_no_stage_skip():
    game=Game()
    assert not game.action('remove',.5,.5)
    assert not game.action('place',.5,.5)
    assert not game.action('verify','alignment')
    assert game.phase == Phase.PREOP
    enter_capsule(game)
    assert not game.action('place',.5,.5)
    assert game.phase == Phase.CAPSULE


@pytest.mark.parametrize('case', ['normal','motion','vitals','capsule'])
def test_all_scenarios_construct(case):
    game=Game(case,42)
    assert game.snapshot()['case']==case


@pytest.mark.parametrize('seed', [True,'7',2.4,None])
def test_bad_seed_rejected(seed):
    with pytest.raises(ValueError):Game(seed=seed)


def test_unknown_case_rejected():
    with pytest.raises(ValueError):Game('clinical-real-case')


@pytest.mark.parametrize('value', [float('nan'),float('inf'),float('-inf'),-1.0,'abc',None,True,10**400])
def test_dirty_coordinates(value):
    game=Game();enter_capsule(game)
    assert not game.action('trace',value,.5)
    assert not game.action('trace',.5,value)
    assert game.phase == Phase.CAPSULE
    assert not game.eye.capsule_points


@pytest.mark.parametrize('value', [-1,float('nan'),float('inf'),'abc',None,True])
def test_dirty_dt(value):
    game=Game()
    with pytest.raises(ValueError):game.tick(value)
    assert game.time==0


def test_malformed_commands_are_ignored():
    game=Game()
    assert not game.action(None)
    assert not game.action(123)
    assert not game.action('x'*900)
    assert game.phase == Phase.PREOP


def test_safe_abort_is_available():
    game=Game();enter_capsule(game)
    assert game.action('abort')
    assert game.ending=='SAFELY ABORTED'
    assert game.phase==Phase.ABORTED
    assert not game.action('confirm')


def test_motion_alert_pause_and_assessment():
    game=Game('motion');enter_capsule(game)
    game.tick(1/60)
    assert game.paused
    assert game.patient.alert=='PATIENT MOTION'
    assert not game.action('trace',.78,.5)
    assert game.action('assess')
    assert not game.paused
    assert not game.patient.alert
    trace_capsule(game)
    assert game.phase==Phase.PHACO


def test_vital_alert_only_once_and_no_bypass():
    game=Game('vitals');enter_capsule(game);trace_capsule(game)
    game.tick(.016)
    assert game.paused
    assert game.patient.alert=='PATIENT MONITOR'
    assert not game.action('remove',.5,.5)
    assert game.action('assess')
    assert game.patient.spo2==99
    game.tick(.016)
    assert game.patient.alert==''


def test_capsule_event_recommends_abort():
    game=Game('capsule');enter_capsule(game);trace_capsule(game)
    game.tick(.016)
    assert game.patient.alert=='CAPSULE INTEGRITY'
    assert game.action('assess')
    assert game.phase==Phase.ABORTED
    assert game.ending=='SAFELY ABORTED'


def test_pause_freezes_time():
    game=Game();game.tick(.016)
    assert game.action('pause')
    previous=game.time
    game.tick(10)
    assert game.time==previous
    assert game.action('pause')
    game.tick(.016)
    assert game.time>previous


def test_dt_clamped():
    game=Game();game.tick(1000)
    assert game.time==pytest.approx(.05)


def test_export_json_lines_valid_and_consistent():
    game=Game();finish(game)
    events=[json.loads(line) for line in game.export_jsonl().splitlines()]
    assert len(events)==game.event_count()
    assert all(event['schema_version']==1 and event['seed']==7 for event in events)
    assert events[-1]['kind']=='ending'
    assert events[-1]['phase']=='RECOVERY'


def test_seeded_replay_equal():
    first,second=Game('vitals',1337),Game('vitals',1337)
    for game in (first,second):
        enter_capsule(game);trace_capsule(game);game.tick(.016)
        game.action('assess');game.tick(.016)
    assert first.export_jsonl()==second.export_jsonl()
    assert first.snapshot()==second.snapshot()


def test_dirty_input_fuzz_5000():
    game=Game(seed=99)
    rng=random.Random(99)
    choices=['remove','trace','place','touch','verify','?',1,None,'assess','pause']
    vals=[-99,-1,0,.5,1,99,float('nan'),float('inf'),None,'bad',True]
    for i in range(5000):
        try:
            game.action(rng.choice(choices),rng.choice(vals),rng.choice(vals))
            if i%11==0:game.tick(.016)
        except (TypeError,ValueError,OverflowError) as exc:
            pytest.fail(f'Unhandled input at iteration {i}: {exc}')
    assert game.phase in Phase
    assert 0<=game.score()<=100


def test_event_list_bounded():
    game=Game()
    for _ in range(Game.MAX_EVENTS+10):
        game.action('pause')
    assert game.event_count()==Game.MAX_EVENTS


def test_alert_cannot_be_skipped_by_burst_of_actions():
    motion=Game('motion')
    enter_capsule(motion)
    # The hazard must be active on phase entry, *before* any frame tick.
    assert motion.patient.alert=='PATIENT MOTION'
    assert motion.paused
    for _ in range(100):
        assert not motion.action('trace',.78,.5)
    assert motion.phase==Phase.CAPSULE

    vital=Game('vitals')
    enter_capsule(vital)
    trace_capsule(vital)
    assert vital.patient.alert=='PATIENT MONITOR'
    for _ in range(100):
        assert not vital.action('remove',.5,.5)
    assert vital.eye.opacity==1


def test_case_boundary_invariants_and_extreme_invalid_actions():
    game=Game('normal')
    enter_capsule(game)
    for _ in range(200):
        assert not game.action('trace', 10**400, 10**400)
    assert not game.action('trace', -math.inf, .5)
    assert game.phase==Phase.CAPSULE
    assert 0 <= game.patient.spo2 <= 100