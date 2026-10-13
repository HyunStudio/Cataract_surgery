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
        if game.phase == Phase.CAPSULE:
            assert game.action("trace", .5 + .28 * math.cos(angle),
                               .5 + .28 * math.sin(angle))
    assert game.phase == Phase.PHACO


def _finish(game):
    _reach_phaco(game)
    if game.patient.alert:
        assert game.action("assess")
    while game.phase in (Phase.PHACO, Phase.CORTEX):
        assert game.action("remove", .5, .5)
        game.tick(1 / 60)
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


def test_no_op_commands_are_not_journaled_but_replay_exactly():
    game = ReplayGame()
    assert not game.action("remove", .5, .5)
    assert game.journal == []
    assert game.action("confirm")
    assert game.journal[-1]["accepted"] is True
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

def test_stress_from_rejected_actions_replays_exactly():
    game = ReplayGame("normal")
    _reach_phaco(game)
    for _ in range(110):
        game.action("remove", 0.0, 0.0)
        if game.patient.alert:
            break
    assert game.patient.alert == "CAPSULE INTEGRITY"
    assert game.paused
    assert any(item["kind"] == "action" and item.get("name") == "remove"
               and item["accepted"] is False for item in game.journal)
    assert game.action("assess")
    assert game.phase == Phase.ABORTED
    copy = ReplayGame.replay_jsonl(game.export_replay_jsonl())
    assert copy.snapshot() == game.snapshot()
    assert copy.export_jsonl() == game.export_jsonl()


def test_replay_rejects_changed_acceptance_bit():
    game = ReplayGame()
    game.action("confirm")
    rows = [json.loads(line) for line in game.export_replay_jsonl().splitlines()]
    rows[1]["accepted"] = False
    with pytest.raises(ValueError, match="modified"):
        ReplayGame.replay_jsonl("\n".join(json.dumps(row) for row in rows))

def test_standalone_verify_cli(tmp_path, capsys):
    from ophthosim.verify_replay import main

    game = ReplayGame()
    game.action("confirm")
    game.action("abort")
    target = tmp_path / "session.replay.jsonl"
    target.write_text(game.export_replay_jsonl(), encoding="utf-8")
    assert main([str(target)]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "verified"
    assert output["clinical_validation"] is False
    assert output["ending"] == "SAFELY ABORTED"
    target.write_text(target.read_text(encoding="utf-8").replace('"accepted":true', '"accepted":false'), encoding="utf-8")
    assert main([str(target)]) == 2
    assert "REPLAY INVALID" in capsys.readouterr().err


def test_verify_cli_refuses_missing_file(tmp_path, capsys):
    from ophthosim.verify_replay import main

    assert main([str(tmp_path / "not_found.jsonl")]) == 2
    assert "REPLAY INVALID" in capsys.readouterr().err
