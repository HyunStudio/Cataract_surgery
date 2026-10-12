"""Replay integrity, safety-event, round-trip and adversarial tests."""
import json
import math
import random

import pytest

from ophthosim.engine import Phase
from ophthosim.replay import ReplayGame


def _reach_capsule(game):
    assert game.action("confirm")
    assert game.action("prepare")
    for xy in game._entry_target:
        assert game.action("touch", *xy)


def _reach_phaco(game):
    _reach_capsule(game)
    if game.patient.alert:
        assert game.action("assess")
    for i in range(24):
        angle = (i + .5) * math.tau / 24
        assert game.action("trace", .5 + .28 * math.cos(angle),
                           .5 + .28 * math.sin(angle))


def _finish(game):
    _reach_phaco(game)
    if game.patient.alert:
        assert game.action("assess")
    for _ in range(80):
        assert game.action("remove", .5, .5)
    assert game.action("place", .5, .5)
    for step in ("alignment", "wound", "handoff"):
        assert game.action("verify", step)
    assert game.phase == Phase.RECOVERY


def test_normal_complete_roundtrip():
    game = ReplayGame()
    game.tick(.016)
    _finish(game)
    raw = game.export_replay_jsonl()
    again = ReplayGame.replay_jsonl(raw)
    assert again.snapshot() == game.snapshot()
    assert again.export_jsonl() == game.export_jsonl()
    assert again.export_replay_jsonl() == raw
    assert '"kind":"integrity"' in raw


@pytest.mark.parametrize("case", ["motion", "vitals", "capsule"])
def test_alert_branches_replay(case):
    game = ReplayGame(case, seed=222)
    _reach_capsule(game)
    if case == "motion":
        assert game.paused
        assert game.action("assess")
        for i in range(24):
            a = (i + .5) * math.tau / 24
            game.action("trace", .5 + .28 * math.cos(a), .5 + .28 * math.sin(a))
    else:
        for i in range(24):
            a = (i + .5) * math.tau / 24
            game.action("trace", .5 + .28 * math.cos(a), .5 + .28 * math.sin(a))
        assert game.paused
        assert game.action("assess")
    again = ReplayGame.replay_jsonl(game.export_replay_jsonl())
    assert again.snapshot() == game.snapshot()
    assert again.export_jsonl() == game.export_jsonl()


def test_paused_ticks_not_saved_and_replay_exact():
    game = ReplayGame()
    game.tick(.016)
    game.action("pause")
    game.tick(20)
    game.action("pause")
    game.tick(1)
    game.tick(.01)
    raw = game.export_replay_jsonl()
    assert '"count":2' not in raw  # unequal dt
    assert game.time == pytest.approx(.076)
    again = ReplayGame.replay_jsonl(raw)
    assert again.time == game.time


def test_repeated_ticks_compact():
    game = ReplayGame()
    for _ in range(500):
        game.tick(1 / 60)
    assert len(game.journal) == 1
    assert game.journal[0]["count"] == 500
    assert ReplayGame.replay_jsonl(game.export_replay_jsonl()).step == 500


def test_rejected_commands_not_recorded():
    game = ReplayGame()
    assert not game.action("remove", .5, .5)
    assert game.action("confirm")
    assert game.phase == Phase.ANESTHESIA
    assert game.action("abort")
    assert ReplayGame.replay_jsonl(game.export_replay_jsonl()).ending == "SAFELY ABORTED"


def test_dirty_coordinates_after_entry_are_rejected_without_journal_corruption():
    game = ReplayGame()
    _reach_capsule(game)
    initial = len(game.journal)
    for bad in (10**400, -1, float("nan"), float("inf"), None, "bad", True):
        assert not game.action("trace", bad, .5)
    assert len(game.journal) == initial
    ReplayGame.replay_jsonl(game.export_replay_jsonl())


def test_replay_detects_tampered_action():
    game = ReplayGame()
    _reach_capsule(game)
    raw = game.export_replay_jsonl()
    records = [json.loads(line) for line in raw.splitlines()]
    records[2]["name"] = "abort"
    tampered = "\n".join(json.dumps(x) for x in records) + "\n"
    with pytest.raises(ValueError):
        ReplayGame.replay_jsonl(tampered)


@pytest.mark.parametrize("raw", [
    "", "{}", "[]\n[]", "abc",
    '{"kind":"session","kind":"session"}\n{}',
    '{"kind":"session","schema_version":1,"case":"normal","seed":true}\n{}',
    '{"kind":"session","schema_version":1,"case":"normal","seed":7}\n{"kind":"integrity","events_sha256":"x","snapshot_sha256":"x","records":0}',
])
def test_dirty_replay_inputs_rejected(raw):
    with pytest.raises(ValueError):
        ReplayGame.replay_jsonl(raw)


def test_dirty_timing_and_large_count_rejected():
    game = ReplayGame()
    raw = game.export_replay_jsonl()
    rec = [json.loads(line) for line in raw.splitlines()]
    for val in (False, -1, float("inf"), .9):
        manipulated = rec[:1] + [{"kind": "tick", "dt": val, "count": 1}] + [dict(rec[-1], records=1)]
        with pytest.raises(ValueError):
            ReplayGame.replay_jsonl("\n".join(json.dumps(x) for x in manipulated))
    bad_count = rec[:1] + [{"kind": "tick", "dt": .016, "count": 300001}] + [dict(rec[-1], records=1)]
    with pytest.raises(ValueError):
        ReplayGame.replay_jsonl("\n".join(json.dumps(x) for x in bad_count))


def test_journal_overflow_refuses_incomplete_export():
    game = ReplayGame()
    game.MAX_RECORDS = 2
    game.action("confirm")
    game.action("prepare")
    game.action("pause")
    assert game.journal_overflow
    with pytest.raises(RuntimeError, match="safety limits"):
        game.export_replay_jsonl()


def test_replay_fuzz_2000_malformed_user_inputs():
    game = ReplayGame(seed=98)
    rng = random.Random(98)
    vals = [-5, 0, .5, 1, float("nan"), float("inf"), None, True, "bad", 10**400]
    commands = ["touch", "trace", "place", "remove", "verify", "nonsense", None, 10]
    for _ in range(2000):
        assert isinstance(game.action(rng.choice(commands), rng.choice(vals), rng.choice(vals)), bool)
    assert ReplayGame.replay_jsonl(game.export_replay_jsonl()).snapshot() == game.snapshot()
