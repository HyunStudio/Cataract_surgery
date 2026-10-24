"""Step-by-step playback of a verified replay journal (results/replay screen).

The whole file is integrity-checked first (``ReplayGame.replay_jsonl``); only
then is a fresh game advanced record by record, so the viewer can play,
pause, single-step and change speed while always showing an engine state
that really occurred. Playback issues no new user commands.
"""
from __future__ import annotations

import json
from typing import Any

from .replay import ReplayGame

SPEEDS = (.5, 1., 2., 4., 8.)


class ReplayPlayer:
    def __init__(self, raw: str) -> None:
        self.final = ReplayGame.replay_jsonl(raw)          # raises ValueError
        lines = raw.splitlines()
        header = json.loads(lines[0])
        self.records: list[dict[str, Any]] = [json.loads(line) for line in lines[1:-1]]
        self.game = ReplayGame(header['case'], header['seed'], header['difficulty'])
        self.index = 0
        self._ticks_left = 0
        self._dt = 0.
        self.playing = True
        self.speed = 1.

    @property
    def done(self) -> bool:
        return self.index >= len(self.records) and self._ticks_left == 0

    @property
    def progress(self) -> float:
        return 1. if not self.records else min(1., self.index / len(self.records))

    def _unit(self) -> float:
        """Apply one tick or one action; return the simulated seconds used."""
        if self._ticks_left:
            self.game.tick(self._dt)
            self._ticks_left -= 1
            return self._dt
        if self.index >= len(self.records):
            return 0.
        record = self.records[self.index]
        self.index += 1
        if record['kind'] == 'tick':
            self._dt, self._ticks_left = record['dt'], record['count']
            return self._unit()
        self.game.action(record['name'], record.get('x'), record.get('y'))
        return 0.

    def advance(self, seconds: float) -> None:
        """Play ``seconds`` of wall time at the current speed (if playing)."""
        if not self.playing:
            return
        budget = max(0., float(seconds)) * self.speed
        units = 0
        while budget > 0 and not self.done and units < 100000:
            budget -= self._unit()
            units += 1

    def step(self) -> None:
        """Advance exactly one journal unit (a tick or an action)."""
        if not self.done:
            self._unit()

    def finish(self) -> None:
        while not self.done:
            self._unit()

    def toggle(self) -> None:
        self.playing = not self.playing

    def faster(self) -> None:
        self.speed = SPEEDS[min(len(SPEEDS) - 1, SPEEDS.index(self.speed) + 1)]

    def slower(self) -> None:
        self.speed = SPEEDS[max(0, SPEEDS.index(self.speed) - 1)]
