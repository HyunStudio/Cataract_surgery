"""Deterministic, non-clinical cataract interaction simulation.

Every numeric value is a synthetic game score, not clinical guidance. The
tolerances, alert timings and score weights are game-design hypotheses; none
is a clinical threshold or a validated skill measure.
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
    FAILED = 'FAILED'


PHASES = (Phase.PREOP, Phase.ANESTHESIA, Phase.ENTRY, Phase.CAPSULE,
          Phase.PHACO, Phase.CORTEX, Phase.IOL, Phase.CLOSE, Phase.RECOVERY)
TERMINAL = frozenset((Phase.RECOVERY, Phase.ABORTED, Phase.FAILED))

PREOP_CHECKS = ('identity', 'site', 'iol_plan')
# Stage-bound synthetic instruments (names only; no device behaviour/settings).
TOOL_NAMES = ('blade', 'forceps', 'phaco', 'aspirator', 'injector')
STAGE_TOOLS = {Phase.ENTRY: 'blade', Phase.CAPSULE: 'forceps', Phase.PHACO: 'phaco',
               Phase.CORTEX: 'aspirator', Phase.IOL: 'injector'}
FINAL_CHECKS = ('alignment', 'wound', 'handoff')

ENDING_COMPLETE = 'SIMULATION COMPLETE'
ENDING_MANAGED = 'COMPLICATION MANAGED'
ENDING_ABORTED = 'SAFELY ABORTED'
ENDING_FAILED = 'CRITICAL FAILURE'
ENDINGS = (ENDING_COMPLETE, ENDING_MANAGED, ENDING_ABORTED, ENDING_FAILED)

# Score weights from the product specification (game hypotheses only).
SCORE_WEIGHTS = (('stages', 20), ('tissue', 25), ('iol', 20),
                 ('response', 20), ('safety', 15))


@dataclass(frozen=True, slots=True)
class Rules:
    """Difficulty-dependent tolerances in normalized eye coordinates."""
    name: str
    entry_radius: float
    capsule_band: tuple[float, float]
    capsule_bins: int
    work_radius: float
    stress_step: float
    iol_threshold: float
    alert_timeout: float | None   # seconds of unattended alert before veto
    guides: bool                   # ghost guides are a tutorial/standard aid
    auto_tool: bool = True         # stage instrument picked automatically


DIFFICULTIES: dict[str, Rules] = {
    'tutorial': Rules('tutorial', .12, (.17, .39), 18, .36, .005, .55, None, True, True),
    'standard': Rules('standard', .09, (.19, .37), 20, .33, .01, .65, 30., True, True),
    'hard': Rules('hard', .07, (.21, .35), 22, .30, .015, .75, 15., False, False),
}

# Scenario hazards: (phase that triggers it on entry, alert label).
HAZARDS: dict[str, tuple[Phase, str]] = {
    'motion': (Phase.CAPSULE, 'PATIENT MOTION'),
    'vitals': (Phase.PHACO, 'PATIENT MONITOR'),
    'capsule': (Phase.PHACO, 'CAPSULE INTEGRITY'),
    'pupil': (Phase.PHACO, 'PUPIL CONSTRICTION'),
    'haze': (Phase.CORTEX, 'CORNEAL HAZE'),
    'decenter': (Phase.CLOSE, 'IOL DECENTRATION'),
    # Fires when the final checklist would complete, holding the ending.
    'leak': (Phase.CLOSE, 'WOUND LEAK RISK'),
}
CASES = ('normal', *HAZARDS, 'random')
ALERT_KINDS = tuple(label for _, label in HAZARDS.values())


@dataclass(slots=True)
class Eye:
    opacity: float = 1.0
    cortex: float = 1.0
    capsule_integrity: float = 1.0
    iol_alignment: float = 0.0
    wound_integrity: float = 0.0
    pupil: float = 1.0            # visual pupil size; limits the work radius
    cornea_clarity: float = 1.0   # 1 = clear synthetic view
    entry_hits: int = 0
    capsule_points: set[int] = field(default_factory=set)
    final_checks: set[str] = field(default_factory=set)
    preop_checks: set[str] = field(default_factory=set)


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
    RESPONSE_GRACE = 3.0          # seconds of full response credit

    def __init__(self, case: str = 'normal', seed: int = 7,
                 difficulty: str = 'standard'):
        if case not in CASES:
            raise ValueError('Unknown scenario')
        if (isinstance(seed, bool) or not isinstance(seed, int)
                or abs(seed) > 2**63 - 1):
            raise ValueError('seed must be a bounded 64-bit integer')
        if difficulty not in DIFFICULTIES:
            raise ValueError('Unknown difficulty')
        self.case = case
        self.seed = seed
        self.difficulty = difficulty
        self.rules = DIFFICULTIES[difficulty]
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
        self._furthest = 0
        self._alert_elapsed = 0.0
        self._decentered = False
        self.alerts: list[dict[str, Any]] = []
        self.phase_times: dict[str, float] = {}
        self._phase_started = 0.0
        self.near_misses = 0
        self.rejected_inputs = 0
        self.iol_attempts = 0
        self.pauses = 0
        self.action_path: dict[str, float] = {}
        self.tool: str | None = None
        self.wrong_tool = 0
        self._last_point: tuple[float, float] | None = None
        self.hazard = case
        self._record('start', {'case': case, 'seed': seed,
                               'difficulty': difficulty})
        if case == 'random':
            # Seeded draw; the trigger source is logged for reproducibility.
            self.hazard = self.rng.choice(sorted(HAZARDS))
            self._record('scenario_draw', {'hazard': self.hazard,
                                           'source': 'seeded_rng'})

    # ------------------------------------------------------------------
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

    @property
    def work_radius(self) -> float:
        """Usable lens-field radius; a constricted pupil shrinks it."""
        return round(self.rules.work_radius * min(1.0, .25 + .75 * self.eye.pupil), 4)

    @property
    def required_tool(self) -> str | None:
        """Instrument the current task expects (None outside instrument tasks)."""
        if self.phase == Phase.CLOSE and self._decentered:
            return 'injector'
        return STAGE_TOOLS.get(self.phase)

    @property
    def alert_elapsed(self) -> float:
        return self._alert_elapsed

    def snapshot(self) -> dict[str, Any]:
        return {'phase': self.phase.value, 'time': round(self.time, 3),
                'patient': asdict(self.patient),
                'eye': {**asdict(self.eye), 'capsule_points': sorted(self.eye.capsule_points),
                        'final_checks': sorted(self.eye.final_checks),
                        'preop_checks': sorted(self.eye.preop_checks)},
                'paused': self.paused, 'ending': self.ending,
                'case': self.case, 'hazard': self.hazard,
                'difficulty': self.difficulty, 'seed': self.seed,
                'step': self.step, 'alert_elapsed': round(self._alert_elapsed, 3),
                'tool': self.tool,
                'score': self.score()}

    # ------------------------------------------------------------------
    def _response_points(self) -> tuple[float, list[dict[str, Any]]]:
        weight = dict(SCORE_WEIGHTS)['response']
        window = (self.rules.alert_timeout or 30.) - self.RESPONSE_GRACE
        items = []
        for alert in self.alerts:
            latency = alert.get('latency')
            if alert.get('response') in (None, 'timeout') or latency is None:
                fraction = 0.0
            else:
                fraction = max(0.0, min(1.0, 1 - max(0.0, latency - self.RESPONSE_GRACE) / window))
            items.append({'kind': alert['kind'], 'latency': latency,
                          'response': alert.get('response'), 'fraction': round(fraction, 4)})
        if not items:
            return float(weight), items
        return weight * sum(i['fraction'] for i in items) / len(items), items

    def score_breakdown(self) -> list[dict[str, Any]]:
        """Explainable per-category points; each earned only once evaluated."""
        weights = dict(SCORE_WEIGHTS)
        furthest = self._furthest
        cortex_index = PHASES.index(Phase.CORTEX)
        close_index = PHASES.index(Phase.CLOSE)
        ended = self.ending is not None
        failed = self.ending == ENDING_FAILED
        stages = weights['stages'] * max(0, min(7, furthest - 1)) / 7
        tissue = 0.0
        if furthest >= cortex_index:
            tissue = max(0.0, weights['tissue'] * self.eye.capsule_integrity
                         - min(8.0, .2 * self.near_misses))
        iol = weights['iol'] * self.eye.iol_alignment if furthest >= close_index else 0.0
        response, alert_items = self._response_points()
        if not ended:
            response = 0.0
        safety = float(weights['safety']) if ended and not failed else 0.0
        return [
            {'key': 'stages', 'points': round(stages, 2), 'max': weights['stages'],
             'detail': {'furthest_phase': PHASES[furthest].value, 'completed': max(0, min(7, furthest - 1)), 'of': 7}},
            {'key': 'tissue', 'points': round(tissue, 2), 'max': weights['tissue'],
             'detail': {'capsule_integrity': round(self.eye.capsule_integrity, 4),
                        'near_misses': self.near_misses, 'evaluated': furthest >= cortex_index}},
            {'key': 'iol', 'points': round(iol, 2), 'max': weights['iol'],
             'detail': {'alignment': round(self.eye.iol_alignment, 4),
                        'attempts': self.iol_attempts, 'evaluated': furthest >= close_index}},
            {'key': 'response', 'points': round(response, 2), 'max': weights['response'],
             'detail': {'alerts': alert_items, 'evaluated': ended}},
            {'key': 'safety', 'points': round(safety, 2), 'max': weights['safety'],
             'detail': {'ending': self.ending, 'veto': failed}},
        ]

    def score(self) -> int:
        total = sum(item['points'] for item in self.score_breakdown())
        return max(0, min(100, round(total)))

    def metrics(self) -> dict[str, Any]:
        """Research-oriented synthetic interaction metrics (no clinical meaning)."""
        times = dict(self.phase_times)
        if self.phase.value not in times and self.ending is None:
            times[self.phase.value] = round(self.time - self._phase_started, 3)
        return {
            'case': self.case, 'hazard': self.hazard, 'difficulty': self.difficulty,
            'seed': self.seed, 'ending': self.ending, 'score': self.score(),
            'sim_time_s': round(self.time, 3), 'phase_time_s': times,
            'near_misses': self.near_misses, 'rejected_inputs': self.rejected_inputs,
            'iol_attempts': self.iol_attempts, 'pauses': self.pauses,
            'wrong_tool': self.wrong_tool,
            'action_path': {k: round(v, 4) for k, v in self.action_path.items()},
            'alerts': [dict(a) for a in self.alerts],
        }

    # ------------------------------------------------------------------
    def _advance(self, to: Phase) -> None:
        previous = self.phase
        self.phase_times[previous.value] = round(
            self.phase_times.get(previous.value, 0.0) + self.time - self._phase_started, 3)
        self._phase_started = self.time
        self.phase = to
        self._last_point = None
        self.tool = STAGE_TOOLS.get(to) if self.rules.auto_tool else None
        if to in PHASES:
            self._furthest = max(self._furthest, PHASES.index(to))
        self._record('phase', {'from': previous.value, 'to': to.value})
        # Trigger case hazards on *state entry*: a burst of input events must
        # not be able to skip a hazard before the next frame's tick.
        hazard = HAZARDS.get(self.hazard)
        if (hazard and not self._scenario_fired and hazard[0] == to
                and self.hazard != 'leak'):
            self._fire(self.hazard)
        if to == Phase.RECOVERY:
            self._finish(ENDING_MANAGED if self.alerts else ENDING_COMPLETE)

    def _fire(self, hazard: str) -> None:
        self._scenario_fired = True
        label = HAZARDS[hazard][1]
        if hazard == 'motion':
            self.patient.motion = 0.9
            self.patient.cooperation = 0.25
            self.patient.heart_rate = 104
        elif hazard == 'vitals':
            self.patient.spo2 = 91
            self.patient.heart_rate = 99
        elif hazard == 'capsule':
            self.eye.capsule_integrity = .55
        elif hazard == 'pupil':
            self.eye.pupil = .62
        elif hazard == 'haze':
            self.eye.cornea_clarity = .4
        elif hazard == 'decenter':
            self.eye.iol_alignment = round(min(self.eye.iol_alignment, .42), 4)
            self._decentered = True
            self.tool = 'injector' if self.rules.auto_tool else None
        elif hazard == 'leak':
            self.eye.final_checks.discard('wound')
            self.eye.wound_integrity = round(len(self.eye.final_checks) / 3, 4)
        self._alert(label)

    def _finish(self, ending: str) -> None:
        self.ending = ending
        self.paused = False
        self._record('ending', {'outcome': ending, 'score': self.score()})

    def _alert(self, kind: str) -> None:
        if self.patient.alert or self.ending:
            return
        self.patient.alert = kind
        self.paused = True
        self._warning_seen = False
        self._alert_elapsed = 0.0
        self.alerts.append({'kind': kind, 'phase': self.phase.value,
                            'step': self.step, 'latency': None, 'response': None})
        self._record('alert', {'kind': kind})

    def _respond(self, response: str) -> None:
        if self.alerts and self.alerts[-1]['response'] is None:
            self.alerts[-1]['response'] = response
            self.alerts[-1]['latency'] = round(self._alert_elapsed, 3)

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
        if self.ending:
            return
        dt = min(value, self.MAX_DT)
        if self.patient.alert:
            # The procedure clock stays frozen during a safety hold, but the
            # hold itself is timed: an unattended alert ends in a veto.
            self._alert_elapsed += dt
            self.step += 1
            timeout = self.rules.alert_timeout
            if timeout is not None and self._alert_elapsed >= timeout:
                self._respond('timeout')
                self.alerts[-1]['latency'] = None
                kind = self.patient.alert
                self._record('veto', {'reason': 'alert_unaddressed', 'alert': kind})
                self._advance(Phase.FAILED)
                self._finish(ENDING_FAILED)
            return
        if self.paused:
            return
        self.time += dt
        self.step += 1

    def _track(self, point: tuple[float, float]) -> None:
        key = self.phase.value
        if self._last_point is not None:
            self.action_path[key] = self.action_path.get(key, 0.0) + math.dist(self._last_point, point)
        self._last_point = point

    def action(self, name: str, x: Any = None, y: Any = None) -> bool:
        """Return whether the game accepted the semantic user command."""
        if not isinstance(name, str) or len(name) > 80:
            return False
        if name == 'abort' and self.phase not in TERMINAL:
            self._respond('abort')
            self.phase_times[self.phase.value] = round(
                self.phase_times.get(self.phase.value, 0.0) + self.time - self._phase_started, 3)
            self.phase = Phase.ABORTED
            self._finish(ENDING_ABORTED)
            return True
        if self.ending:
            return False
        if name == 'pause':
            self.paused = not self.paused if not self.patient.alert else True
            self.pauses += 1
            self._record('pause', {'paused': self.paused})
            return True
        if name == 'assess' and self.patient.alert:
            self._warning_seen = True
            alert = self.patient.alert
            self._respond('assess')
            self._record('assessed', {'alert': alert,
                                      'latency_s': round(self._alert_elapsed, 3)})
            if alert == 'CAPSULE INTEGRITY':
                # Unsafe procedural continuation is intentionally not taught.
                return self.action('abort')
            self.patient.alert = ''
            self.patient.motion = 0.0
            self.patient.cooperation = 1.0
            self.patient.heart_rate = 76
            self.patient.spo2 = 99
            if alert == 'CORNEAL HAZE':
                self.eye.cornea_clarity = .7   # re-evaluated, partially clear
            self.paused = False
            self._alert_elapsed = 0.0
            return True
        if self.paused or self.patient.alert:
            return False
        if name == 'tool':
            if not isinstance(x, str) or x not in TOOL_NAMES:
                return False
            self.tool = x
            self._record('tool', {'tool': x})
            return True
        if self.phase == Phase.PREOP and name == 'verify':
            if not isinstance(x, str) or x not in PREOP_CHECKS:
                return False
            self.eye.preop_checks.add(x)
            self._record('preop_check', {'item': x})
            return True
        if self.phase == Phase.PREOP and name == 'confirm':
            # Mandatory verification cannot be skipped.
            if len(self.eye.preop_checks) < len(PREOP_CHECKS):
                self._record('rejected', {'action': 'confirm', 'reason': 'preop_checks_incomplete'})
                return False
            self._advance(Phase.ANESTHESIA)
            return True
        if self.phase == Phase.ANESTHESIA and name == 'prepare':
            self._advance(Phase.ENTRY)
            return True
        point = self._xy(x, y)
        if point is None and name not in {'verify'}:
            return False
        required = self.required_tool
        stage_action = {Phase.ENTRY: 'touch', Phase.CAPSULE: 'trace', Phase.PHACO: 'remove',
                        Phase.CORTEX: 'remove', Phase.IOL: 'place',
                        Phase.CLOSE: 'place'}.get(self.phase)
        # Only the stage's own action is an instrument use; any other command
        # is simply not applicable here and is handled (rejected) below.
        if (point is not None and required is not None and self.tool != required
                and name == stage_action):
            self.wrong_tool += 1
            self.rejected_inputs += 1
            self._record('rejected', {'action': name, 'reason': 'wrong_tool',
                                      'tool': self.tool, 'required': required})
            return False
        accepted = self._procedure(name, point, x)
        if point is not None:
            if accepted:
                self._track(point)
            elif name in {'touch', 'trace', 'remove', 'place'}:
                self.rejected_inputs += 1
        return accepted

    def _procedure(self, name: str, point, x: Any) -> bool:
        rules = self.rules
        if self.phase == Phase.ENTRY and name == 'touch':
            for index, target in enumerate(self._entry_target):
                if index not in self._entered and math.dist(point, target) < rules.entry_radius:
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
            low, high = rules.capsule_band
            if low < radius < high:
                self.eye.capsule_points.add(int(angle / (2 * math.pi) * 24) % 24)
                if len(self.eye.capsule_points) >= rules.capsule_bins:
                    self._record('capsule_completed', {'bins': len(self.eye.capsule_points)})
                    self._advance(Phase.PHACO)
                return True
            return False
        if self.phase in (Phase.PHACO, Phase.CORTEX) and name == 'remove':
            if math.dist(point, (.5, .5)) >= self.work_radius:
                self.near_misses += 1
                self._stress += rules.stress_step
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
        if name == 'place' and (self.phase == Phase.IOL or
                                (self.phase == Phase.CLOSE and self._decentered)):
            distance = math.dist(point, (.5, .5))
            self.iol_attempts += 1
            self.eye.iol_alignment = round(max(0.0, 1 - distance * 3), 4)
            self._record('placed', {'alignment': self.eye.iol_alignment,
                                    'reposition': self.phase == Phase.CLOSE})
            if self.eye.iol_alignment >= rules.iol_threshold:
                if self.phase == Phase.IOL:
                    self._advance(Phase.CLOSE)
                else:
                    self._decentered = False
            return True
        if self.phase == Phase.CLOSE and name == 'verify':
            if not isinstance(x, str) or x not in FINAL_CHECKS:
                return False
            if x == 'alignment' and (self._decentered or
                                     self.eye.iol_alignment < rules.iol_threshold):
                self._record('rejected', {'action': 'verify', 'item': x,
                                          'reason': 'iol_not_centered'})
                return False
            self.eye.final_checks.add(x)
            self._record('check', {'item': x})
            self.eye.wound_integrity = round(len(self.eye.final_checks) / 3, 4)
            if len(self.eye.final_checks) == 3:
                if self.hazard == 'leak' and not self._scenario_fired:
                    # Insufficient closure check: ending is held, not granted.
                    self._fire('leak')
                    return True
                self._advance(Phase.RECOVERY)
            return True
        return False

    def export_jsonl(self) -> str:
        return '\n'.join(json.dumps(event, sort_keys=True, ensure_ascii=False)
                         for event in self.events) + '\n'

    def event_count(self) -> int:
        return len(self.events)
