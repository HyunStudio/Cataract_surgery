"""Deterministic, non-clinical cataract interaction simulation.

The player is the operating surgeon of a *mock* cataract procedure. Every
numeric value is a synthetic game score, not clinical guidance.
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

    VERSION = 2
    MAX_EVENTS = 12000
    MAX_DT = 0.05
    # Front-ends issue at most one held-instrument command per fixed 1/60 s
    # simulation tick, so these are per-tick amounts: removal takes ~4 s and
    # cleanup ~3 s of steady work regardless of the rendering frame rate.
    PHACO_STEP = .004
    CORTEX_STEP = .006
    # Off-target instrument work strains the synthetic capsule. Strain decays
    # while the surgeon works safely; a warning is shown before the alert.
    STRESS_PER_MISS = .01
    STRESS_DECAY_PER_S = .12
    STRESS_WARNING = .5
    STRESS_WARNING_RESET = .25

    def __init__(self, case: str = 'normal', seed: int = 7):
        if case not in {'normal', 'motion', 'vitals', 'capsule'}:
            raise ValueError('Unknown scenario')
        if (isinstance(seed, bool) or not isinstance(seed, int)
                or abs(seed) > 2**63 - 1):
            raise ValueError('seed must be a bounded 64-bit integer')
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
        self._stress_warned = False
        self.off_target = 0
        self.stress_warnings = 0
        self._record('start', {'case': case, 'seed': seed})

    @staticmethod
    def _xy(x: Any, y: Any) -> tuple[float, float] | None:
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) for v in (x, y)):
            return None
        # Range-check *before* float(): huge Python ints can overflow float
        # conversion. NaN fails every comparison, so it is rejected here too.
        if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0):
            return None
        return float(x), float(y)

    def _record(self, kind: str, data: dict[str, Any] | None = None) -> None:
        if len(self.events) >= self.MAX_EVENTS:
            return
        if len(self.events) == self.MAX_EVENTS - 1:
            # Never truncate silently: the last slot marks the cut-off.
            kind, data = 'events_truncated', {'limit': self.MAX_EVENTS}
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
                'tissue_stress': round(self._stress, 6),
                'off_target': self.off_target,
                'stress_warnings': self.stress_warnings,
                'score': self.score()}

    @property
    def tissue_stress(self) -> float:
        """Synthetic 0..1 strain from off-target work; 1.0 triggers an alert."""
        return min(1.0, max(0.0, self._stress))

    @property
    def stress_warning(self) -> bool:
        return self._stress >= self.STRESS_WARNING

    def state_key(self) -> tuple[Any, ...]:
        """Every mutable field that an action may change, for no-op detection."""
        e, p = self.eye, self.patient
        return (self.phase, self.paused, self.ending, self._stress,
                self._stress_warned, self.off_target, self.stress_warnings,
                self._warning_seen, self._scenario_fired, len(self.events),
                frozenset(self._entered), e.opacity, e.cortex,
                e.capsule_integrity, e.iol_alignment, e.wound_integrity,
                e.entry_hits, frozenset(e.capsule_points),
                frozenset(e.final_checks), p.heart_rate, p.spo2, p.sbp, p.dbp,
                p.cooperation, p.motion, p.alert)

    def phase_durations(self) -> dict[str, float]:
        """Simulated seconds spent in each phase, from the event trace."""
        durations: dict[str, float] = {}
        start, current = 0, Phase.PREOP.value
        for event in self.events:
            if event['kind'] == 'phase':
                target = event['data']['to']
            elif event['kind'] == 'ending' and event['data'].get('outcome') == 'SAFELY ABORTED':
                target = Phase.ABORTED.value
            else:
                continue
            durations[current] = durations.get(current, 0.) + (event['sim_time_ms'] - start) / 1000
            start, current = event['sim_time_ms'], target
        if not self.ending:
            durations[current] = durations.get(current, 0.) + (round(self.time * 1000) - start) / 1000
        return {k: round(v, 2) for k, v in durations.items()}

    def debrief(self) -> list[tuple[str, str]]:
        """Surgeon-facing (label, verdict) feedback lines; synthetic only."""
        lines: list[tuple[str, str]] = []
        alerts = [e['data'].get('kind') for e in self.events if e['kind'] == 'alert']
        assessed = sum(1 for e in self.events if e['kind'] == 'assessed')
        if self.phase == Phase.ABORTED:
            if 'CAPSULE INTEGRITY' in alerts:
                lines.append(('Decision', 'Recognised and stopped safely'))
            else:
                lines.append(('Decision', 'Procedure stopped by the surgeon'))
        elif self.phase == Phase.RECOVERY:
            lines.append(('Outcome', 'Mock procedure completed'))
        if alerts:
            lines.append(('Safety holds', f'{len(alerts)} raised, {assessed} assessed'))
        lines.append(('Off-target work', f'{self.off_target / 60:.1f} s'))
        lines.append(('Stress warnings', str(self.stress_warnings)))
        if self.eye.iol_alignment > 0:
            lines.append(('IOL centration', f'{self.eye.iol_alignment:.0%}'))
        durations = self.phase_durations()
        work = sum(durations.get(p.value, 0.) for p in (Phase.ENTRY, Phase.CAPSULE, Phase.PHACO,
                                                        Phase.CORTEX, Phase.IOL))
        if work:
            lines.append(('Instrument time', f'{work:.1f} s simulated'))
        return lines

    def score(self) -> int:
        completed = PHASES.index(self.phase) if self.phase in PHASES else 0
        phases = min(8, completed) * 3
        # Earn quality/safety points only once the relevant task is evaluated.
        # An untouched pre-operative case must not start at 40/100.
        tissue = round(26 * self.eye.capsule_integrity) if completed >= 4 else 0
        placement = round(20 * self.eye.iol_alignment) if completed >= 7 else 0
        progress = round(16 * (1 - self.eye.opacity) * (1 - self.eye.cortex)) if completed >= 6 else 0
        safety = 14 if self.phase == Phase.RECOVERY and not self.patient.alert else 0
        # Each stress warning costs technique points; it never goes negative.
        safety = max(0, safety - 4 * self.stress_warnings)
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
        # float() is guarded: converting a gigantic int can overflow before
        # math.isfinite has a chance to validate it.
        if isinstance(dt, bool) or not isinstance(dt, (int, float)):
            raise ValueError('dt must be finite and nonnegative')
        try:
            value = float(dt)
        except (OverflowError, ValueError) as exc:
            raise ValueError('dt must be finite and nonnegative') from exc
        if not math.isfinite(value) or value < 0:
            raise ValueError('dt must be finite and nonnegative')
        if self.paused or self.ending:
            return
        dt = min(value, self.MAX_DT)
        self.time += dt
        self.step += 1
        if self._stress > 0:
            self._stress = max(0.0, self._stress - self.STRESS_DECAY_PER_S * dt)
            if self._stress_warned and self._stress < self.STRESS_WARNING_RESET:
                self._stress_warned = False

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
                self._stress += self.STRESS_PER_MISS
                self.off_target += 1
                if self._stress >= self.STRESS_WARNING and not self._stress_warned:
                    self._stress_warned = True
                    self.stress_warnings += 1
                    self._record('stress_warning', {'stress': round(self._stress, 4)})
                if self._stress >= 1.0:
                    self.eye.capsule_integrity = max(0.0, self.eye.capsule_integrity - .2)
                    self._stress = 0.0
                    self._stress_warned = False
                    self._alert('CAPSULE INTEGRITY')
                return False
            if self.phase == Phase.PHACO:
                self.eye.opacity = max(0, round(self.eye.opacity - self.PHACO_STEP, 4))
                if self.eye.opacity <= .001:
                    self.eye.opacity = 0.0
                    self._advance(Phase.CORTEX)
            else:
                self.eye.cortex = max(0, round(self.eye.cortex - self.CORTEX_STEP, 4))
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