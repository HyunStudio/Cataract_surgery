"""Deterministic, non-clinical cataract interaction simulation.

Every numeric value is a synthetic game score, not clinical guidance.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
import json
import math
import random
from typing import Any


class Phase(str, Enum):
    PREOP = 'PREOP'
    ANESTHESIA = 'ANESTHESIA'
    ENTRY = 'ENTRY'
    CAPSULE = 'CAPSULE'
    PHACO = 'PHACO'
    CORTEX = 'CORTEX'
    IOL = 'IOL'
    CLOSE = 'CLOSE'
    RECOVERY = 'RECOVERY'
    ABORTED = 'ABORTED'


PHASES = (Phase.PREOP, Phase.ANESTHESIA, Phase.ENTRY, Phase.CAPSULE,
          Phase.PHACO, Phase.CORTEX, Phase.IOL, Phase.CLOSE, Phase.RECOVERY)


@dataclass(slots=True)
class Eye:
    opacity: float = 1.0
    cortex: float = 1.0
    capsule_integrity: float = 1.0
    iol_alignment: float = 0.0
    wound_integrity: float = 0.0
    entry_hits: int = 0
    capsule_points: set[int] = field(default_factory=set)
    final_checks: set[str] = field(default_factory=set)


@dataclass(slots=True)
class Patient:
    heart_rate: int = 74
    spo2: int = 99
    sbp: int = 122
    dbp: int = 76
    cooperation: float = 1.0
    motion: float = 0.0
    alert: str = ''


class Game:
    """A strict phase machine; callers may never change `phase` via actions."""

    VERSION = 1
    MAX_EVENTS = 12000
    MAX_DT = 0.05

    def __init__(self, case: str = 'normal', seed: int = 7):
        if case not in {'normal', 'motion', 'vitals', 'capsule'}:
            raise ValueError('Unknown scenario')
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise ValueError('seed must be integer')
        self.case = case
        self.seed = seed
        self.rng = random.Random(seed)
        self.eye = Eye()
        self.patient = Patient()
        self.phase = Phase.PREOP
        self.time = 0.0
        self.step = 0
        self.paused = False
        self.ending: str | None = None
        self.events: list[dict[str, Any]] = []
        self._entry_target = [(0.69, .46), (.70, .55), (.69, .64)]
        self._entered: set[int] = set()
        self._warning_seen = False
        self._scenario_fired = False
        self._stress = 0.0
        self._record('start', {'case': case, 'seed': seed})

    @staticmethod
    def _xy(x: Any, y: Any) -> tuple[float, float] | None:
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) for v in (x, y)):
            return None
        # Range-check *before* isfinite: huge Python ints can overflow float conversion.
        if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0):
            return None
        if not math.isfinite(x) or not math.isfinite(y):
            return None
        if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0):
            return None
        return float(x), float(y)

    def _record(self, kind: str, data: dict[str, Any] | None = None) -> None:
        if len(self.events) >= self.MAX_EVENTS:
            return
        self.events.append({'schema_version': self.VERSION, 'seed': self.seed,
                            'case': self.case, 'step': self.step,
                            'sim_time_ms': round(self.time * 1000), 'phase': self.phase.value,
                            'kind': kind, 'data': data or {}})

    def snapshot(self) -> dict[str, Any]:
        return {'phase': self.phase.value, 'time': round(self.time, 3),
                'patient': asdict(self.patient),
                'eye': {**asdict(self.eye), 'capsule_points': sorted(self.eye.capsule_points),
                        'final_checks': sorted(self.eye.final_checks)},
                'paused': self.paused, 'ending': self.ending,
                'case': self.case, 'seed': self.seed, 'step': self.step,
                'score': self.score()}

    def score(self) -> int:
        completed = PHASES.index(self.phase) if self.phase in PHASES else 0
        phases = min(8, completed) * 3
        tissue = round(26 * self.eye.capsule_integrity)
        placement = round(20 * self.eye.iol_alignment)
        progress = round(16 * (1 - self.eye.opacity) * (1 - self.eye.cortex))
        safety = 14 if self.patient.alert == '' else (8 if self._warning_seen else 0)
        result = max(0, min(100, phases + tissue + placement + progress + safety))
        return result

    def _advance(self, to: Phase) -> None:
        previous = self.phase
        self.phase = to
        self._record('phase', {'from': previous.value, 'to': to.value})
        # Trigger case hazards on *state entry*: a burst of input events must
        # not be able to skip a hazard before the next frame's tick.
        if not self._scenario_fired:
            hazard = {
                ('motion', Phase.CAPSULE): 'PATIENT MOTION',
                ('vitals', Phase.PHACO): 'PATIENT MONITOR',
                ('capsule', Phase.PHACO): 'CAPSULE INTEGRITY',
            }.get((self.case, to))
            if hazard:
                self._scenario_fired = True
                if hazard == 'PATIENT MOTION':
                    self.patient.motion = 0.9
                    self.patient.cooperation = 0.25
                    self.patient.heart_rate = 104
                elif hazard == 'PATIENT MONITOR':
                    self.patient.spo2 = 91
                    self.patient.heart_rate = 99
                else:
                    self.eye.capsule_integrity = .55
                self._alert(hazard)
        if to == Phase.RECOVERY:
            self.ending = 'SIMULATION COMPLETE'
            self._record('ending', {'outcome': self.ending, 'score': self.score()})

    def _alert(self, kind: str) -> None:
        if self.patient.alert or self.ending:
            return
        self.patient.alert = kind
        self.paused = True
        self._warning_seen = False
        self._record('alert', {'kind': kind})

    def tick(self, dt: float) -> None:
        if isinstance(dt, bool) or not isinstance(dt, (int, float)) or not math.isfinite(dt) or dt < 0:
            raise ValueError('dt must be finite and nonnegative')
        if self.paused or self.ending:
            return
        dt = min(float(dt), self.MAX_DT)
        self.time += dt
        self.step += 1

    def action(self, name: str, x: Any = None, y: Any = None) -> bool:
        """Return whether the game accepted the semantic user command."""
        if not isinstance(name, str) or len(name) > 80:
            return False
        if name == 'abort' and self.phase not in (Phase.RECOVERY, Phase.ABORTED):
            self.phase = Phase.ABORTED
            self.ending = 'SAFELY ABORTED'
            self.paused = False
            self._record('ending', {'outcome': self.ending})
            return True
        if self.ending:
            return False
        if name == 'pause':
            self.paused = not self.paused if not self.patient.alert else True
            self._record('pause', {'paused': self.paused})
            return True
        if name == 'assess' and self.patient.alert:
            self._warning_seen = True
            self._record('assessed', {'alert': self.patient.alert})
            if self.patient.alert == 'CAPSULE INTEGRITY':
                # Unsafe procedural continuation is intentionally not taught.
                return self.action('abort')
            self.patient.alert = ''
            self.patient.motion = 0.0
            self.patient.cooperation = 1.0
            self.patient.heart_rate = 76
            self.patient.spo2 = 99
            self.paused = False
            return True
        if self.paused or self.patient.alert:
            return False
        point = self._xy(x, y)
        if self.phase == Phase.PREOP and name == 'confirm':
            self._advance(Phase.ANESTHESIA)
            return True
        if self.phase == Phase.ANESTHESIA and name == 'prepare':
            self._advance(Phase.ENTRY)
            return True
        if point is None and name not in {'verify'}:
            return False
        if self.phase == Phase.ENTRY and name == 'touch':
            for index, target in enumerate(self._entry_target):
                if index not in self._entered and math.dist(point, target) < .09:
                    self._entered.add(index)
                    self.eye.entry_hits = len(self._entered)
                    self._record('entry_point', {'index': index})
                    if len(self._entered) == 3:
                        self._advance(Phase.CAPSULE)
                    return True
            return False
        if self.phase == Phase.CAPSULE and name == 'trace':
            angle = (math.atan2(point[1] - .5, point[0] - .5) + 2 * math.pi) % (2 * math.pi)
            radius = math.dist(point, (.5, .5))
            if .19 < radius < .37:
                self.eye.capsule_points.add(int(angle / (2 * math.pi) * 24) % 24)
                if len(self.eye.capsule_points) >= 20:
                    self._record('capsule_completed', {'bins': len(self.eye.capsule_points)})
                    self._advance(Phase.PHACO)
                return True
            return False
        if self.phase in (Phase.PHACO, Phase.CORTEX) and name == 'remove':
            if math.dist(point, (.5, .5)) >= .33:
                self._stress += .01
                if self._stress >= 1.0:
                    self.eye.capsule_integrity = max(0.0, self.eye.capsule_integrity - .2)
                    self._stress = 0.0
                    self._alert('CAPSULE INTEGRITY')
                return False
            if self.phase == Phase.PHACO:
                self.eye.opacity = max(0, round(self.eye.opacity - .025, 4))
                if self.eye.opacity <= .001:
                    self.eye.opacity = 0.0
                    self._advance(Phase.CORTEX)
            else:
                self.eye.cortex = max(0, round(self.eye.cortex - .025, 4))
                if self.eye.cortex <= .001:
                    self.eye.cortex = 0.0
                    self._advance(Phase.IOL)
            self._record('removed', {'x': round(point[0], 4), 'y': round(point[1], 4)})
            return True
        if self.phase == Phase.IOL and name == 'place':
            distance = math.dist(point, (.5, .5))
            self.eye.iol_alignment = round(max(0.0, 1 - distance * 3), 4)
            self._record('placed', {'alignment': self.eye.iol_alignment})
            if self.eye.iol_alignment >= .65:
                self._advance(Phase.CLOSE)
            return True
        if self.phase == Phase.CLOSE and name == 'verify':
            if not isinstance(x, str) or x not in {'alignment', 'wound', 'handoff'}:
                return False
            self.eye.final_checks.add(x)
            self._record('check', {'item': x})
            self.eye.wound_integrity = len(self.eye.final_checks) / 3
            if len(self.eye.final_checks) == 3:
                self._advance(Phase.RECOVERY)
            return True
        return False

    def export_jsonl(self) -> str:
        return '\n'.join(json.dumps(event, sort_keys=True, ensure_ascii=False)
                         for event in self.events) + '\n'

    def event_count(self) -> int:
        return len(self.events)