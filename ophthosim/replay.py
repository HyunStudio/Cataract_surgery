"""Deterministic accepted-command journal and guarded replay.

Records synthetic semantic commands, not mouse trajectories or medical actions.
It deliberately stores only accepted commands and effective simulation ticks.
"""
from __future__ import annotations

import hashlib
import json
import math
from typing import Any

from .engine import Game


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate replay field")
        result[key] = value
    return result


def _invalid_constant(value: str) -> None:
    raise ValueError(f"Invalid numeric constant in replay: {value}")


class ReplayGame(Game):
    """Game with bounded, deterministic command capture and integrity checks."""

    REPLAY_VERSION = 1
    MAX_RECORDS = 16000
    MAX_TICKS = 300000
    MAX_REPLAY_BYTES = 12_000_000

    def __init__(self, case: str = "normal", seed: int = 7) -> None:
        super().__init__(case, seed)
        self.journal: list[dict[str, Any]] = []
        self.journal_overflow = False
        self._dispatch_depth = 0
        self._recorded_ticks = 0

    def _append(self, record: dict[str, Any]) -> None:
        if len(self.journal) >= self.MAX_RECORDS:
            self.journal_overflow = True
            return
        self.journal.append(record)

    def action(self, name: str, x: Any = None, y: Any = None) -> bool:
        # Game.action('assess') can internally call self.action('abort').
        # Only the outer command belongs to the user's command stream.
        is_outer = self._dispatch_depth == 0
        self._dispatch_depth += 1
        try:
            accepted = super().action(name, x, y)
        finally:
            self._dispatch_depth -= 1
        if is_outer and isinstance(name, str):
            item: dict[str, Any] = {"kind": "action", "name": name,
                                    "accepted": accepted}
            if name == "verify" and isinstance(x, str) and len(x) <= 80:
                item["x"] = x
                self._append(item)
            elif name in {"touch", "trace", "remove", "place"}:
                point = self._xy(x, y)
                if point is not None:
                    # Failed in-range actions also matter. A missed 'remove'
                    # can increment the synthetic capsule-stress counter.
                    item["x"], item["y"] = point
                    self._append(item)
            elif name in {"abort", "assess", "pause", "confirm", "prepare"}:
                self._append(item)
        return accepted

    def tick(self, dt: float) -> None:
        was_running = not self.paused and not self.ending
        super().tick(dt)
        if not was_running or dt == 0:
            return
        effective = min(float(dt), self.MAX_DT)
        if self._recorded_ticks >= self.MAX_TICKS:
            self.journal_overflow = True
            return
        self._recorded_ticks += 1
        # Run-length compression keeps a 60 FPS session compact without
        # changing the exact order of commands and simulation steps.
        if (self.journal and self.journal[-1]["kind"] == "tick"
                and self.journal[-1]["dt"] == effective
                and self.journal[-1]["count"] < 100000):
            self.journal[-1]["count"] += 1
        else:
            self._append({"kind": "tick", "dt": effective, "count": 1})

    def export_replay_jsonl(self) -> str:
        if self.journal_overflow:
            raise RuntimeError("Replay capture exceeded safety limits")
        header = {"kind": "session", "schema_version": self.REPLAY_VERSION,
                  "case": self.case, "seed": self.seed}
        footer = {"kind": "integrity",
                  "journal_sha256": _digest("\n".join(_canonical(row) for row in [header, *self.journal])),
                  "events_sha256": _digest(self.export_jsonl()),
                  "snapshot_sha256": _digest(_canonical(self.snapshot())),
                  "records": len(self.journal)}
        return "\n".join(_canonical(row)
                         for row in [header, *self.journal, footer]) + "\n"

    @classmethod
    def replay_jsonl(cls, raw: str) -> "ReplayGame":
        if not isinstance(raw, str) or len(raw.encode("utf-8")) > cls.MAX_REPLAY_BYTES:
            raise ValueError("Replay is not text or exceeds size limit")
        lines = raw.splitlines()
        if len(lines) < 2 or len(lines) > cls.MAX_RECORDS + 2:
            raise ValueError("Invalid replay length")
        try:
            records = [json.loads(line, object_pairs_hook=_unique_object,
                                  parse_constant=_invalid_constant)
                       for line in lines]
        except (TypeError, json.JSONDecodeError, RecursionError) as exc:
            raise ValueError("Malformed replay JSON") from exc
        header, footer = records[0], records[-1]
        if not isinstance(header, dict) or set(header) != {"kind", "schema_version", "case", "seed"}:
            raise ValueError("Invalid replay header")
        if header["kind"] != "session" or header["schema_version"] != cls.REPLAY_VERSION:
            raise ValueError("Unsupported replay version")
        if not isinstance(footer, dict) or set(footer) != {"kind", "journal_sha256", "events_sha256", "snapshot_sha256", "records"}:
            raise ValueError("Invalid replay integrity footer")
        if footer["kind"] != "integrity" or footer["records"] != len(records) - 2:
            raise ValueError("Replay record count mismatch")
        if any(not isinstance(footer[key], str) or len(footer[key]) != 64
               for key in ("journal_sha256", "events_sha256", "snapshot_sha256")):
            raise ValueError("Malformed replay digest")
        if footer["journal_sha256"] != _digest("\n".join(_canonical(row) for row in records[:-1])):
            raise ValueError("Replay command journal was modified")
        try:
            game = cls(case=header["case"], seed=header["seed"])
        except (ValueError, TypeError, OverflowError) as exc:
            raise ValueError("Invalid case or seed") from exc
        count = 0
        for entry in records[1:-1]:
            if not isinstance(entry, dict):
                raise ValueError("Invalid replay event")
            if entry.get("kind") == "tick":
                if set(entry) != {"kind", "dt", "count"}:
                    raise ValueError("Unknown tick fields")
                dt, repetitions = entry["dt"], entry["count"]
                if (type(dt) not in (float, int) or not math.isfinite(dt)
                        or not 0 < dt <= cls.MAX_DT
                        or type(repetitions) is not int or not 1 <= repetitions <= 100000):
                    raise ValueError("Invalid replay time/count")
                count += repetitions
                if count > cls.MAX_TICKS:
                    raise ValueError("Replay step budget exceeded")
                for _ in range(repetitions):
                    game.tick(dt)
            elif entry.get("kind") == "action":
                if not set(entry).issubset({"kind", "name", "x", "y", "accepted"}) or "name" not in entry:
                    raise ValueError("Unknown action fields")
                if type(entry.get("accepted")) is not bool:
                    raise ValueError("Action acceptance marker missing")
                actual = game.action(entry["name"], entry.get("x"), entry.get("y"))
                if actual != entry["accepted"]:
                    raise ValueError("Replay command outcome mismatch")
            else:
                raise ValueError("Unknown replay event type")
        if (footer["events_sha256"] != _digest(game.export_jsonl())
                or footer["snapshot_sha256"] != _digest(_canonical(game.snapshot()))):
            raise ValueError("Replay integrity mismatch")
        return game
