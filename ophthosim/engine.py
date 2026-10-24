"""Deterministic, non-clinical cataract surgery simulation (engine v3).

The player is the operating surgeon. The procedure follows the real order of
a phacoemulsification case; realistic instruments are chosen for each step
and for each complication (docs/V3_INSTRUMENTS_BLEEDING_MODEL_PLAN_KO.md).

Every numeric value is a synthetic game quantity. There are no device
settings, drug doses or clinical thresholds in this model; tolerances,
timings and score weights are game-design hypotheses, not validated skill
measures.
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
FINAL_CHECKS = ('alignment', 'wound', 'handoff')

# --- Instruments ----------------------------------------------------------
# Generic instrument types only: no sizes, energy, vacuum or flow settings.
STEP_TOOLS = ('keratome', 'sideport', 'ovd_cannula', 'cystotome', 'forceps',
              'hydro_cannula', 'phaco', 'ia', 'injector')
SITUATION_TOOLS = ('iol_hook', 'iris_hooks', 'ctr', 'cautery', 'irrigation', 'suture')
TOOL_NAMES = STEP_TOOLS + SITUATION_TOOLS
# Instruments applied with a pointer 'use' instead of the stage action.
USE_TOOLS = frozenset(('ovd_cannula', 'hydro_cannula', *SITUATION_TOOLS)) - {'iol_hook'}
ENTRY_BLADES = ('keratome', 'sideport', 'sideport')   # main incision, two side ports
# Instrument(s) each stage task accepts (the first is picked automatically).
TASK_TOOLS = {Phase.CAPSULE: ('cystotome', 'forceps'), Phase.PHACO: ('phaco',),
              Phase.CORTEX: ('ia',), Phase.IOL: ('injector',)}
STAGE_ACTIONS = {Phase.ENTRY: 'touch', Phase.CAPSULE: 'trace', Phase.PHACO: 'remove',
                 Phase.CORTEX: 'remove', Phase.IOL: 'place', Phase.CLOSE: 'place'}
TASK_ACTIONS = frozenset(STAGE_ACTIONS.values())

ENDING_COMPLETE = 'SIMULATION COMPLETE'
ENDING_MANAGED = 'COMPLICATION MANAGED'
ENDING_UNRESOLVED = 'COMPLICATION UNRESOLVED'
ENDING_ABORTED = 'SAFELY ABORTED'
ENDING_FAILED = 'CRITICAL FAILURE'
ENDINGS = (ENDING_COMPLETE, ENDING_MANAGED, ENDING_UNRESOLVED, ENDING_ABORTED, ENDING_FAILED)

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
    tool_hints: bool = False       # hints name the managing instrument


DIFFICULTIES: dict[str, Rules] = {
    'tutorial': Rules('tutorial', .12, (.17, .39), 18, .36, .005, .55, None, True, True, True),
    'standard': Rules('standard', .09, (.19, .37), 20, .33, .01, .65, 30., True, True, False),
    'hard': Rules('hard', .07, (.21, .35), 22, .30, .015, .75, 15., False, False, False),
}

# Scenario hazards: case key -> (phase in which it can occur, alert label).
HAZARDS: dict[str, tuple[Phase, str]] = {
    'motion': (Phase.CAPSULE, 'PATIENT MOTION'),
    'vitals': (Phase.PHACO, 'PATIENT MONITOR'),
    'capsule': (Phase.PHACO, 'CAPSULE INTEGRITY'),
    'pupil': (Phase.PHACO, 'PUPIL CONSTRICTION'),
    'haze': (Phase.CORTEX, 'CORNEAL HAZE'),
    'decenter': (Phase.CLOSE, 'IOL DECENTRATION'),
    # Fires when the final checklist would complete, holding the ending.
    'leak': (Phase.CLOSE, 'WOUND LEAK RISK'),
    'iris': (Phase.PHACO, 'IRIS PROLAPSE'),
    'zonules': (Phase.CAPSULE, 'ZONULAR WEAKNESS'),
    'bleed': (Phase.ENTRY, 'INCISION BLEEDING'),
    'hyphema': (Phase.PHACO, 'HYPHEMA'),
    'sch': (Phase.CORTEX, 'SUPRACHOROIDAL HEMORRHAGE'),
}
CASES = ('normal', *HAZARDS, 'random')
# Alerts that can also arise from the surgeon's own technique.
EMERGENT_ALERTS = ('RHEXIS TEAR',)
ALERT_KINDS = tuple(label for _, label in HAZARDS.values()) + EMERGENT_ALERTS


@dataclass(frozen=True, slots=True)
class Complication:
    """How a complication is managed after it has been assessed (A)."""
    remedy: str | None      # instrument id, 'escalate' (call senior), or None
    site: str | None = None  # where the instrument must be used
    major: bool = False      # continuing the stage task while pending fails


COMPLICATIONS: dict[str, Complication] = {
    'PATIENT MOTION': Complication(None),
    'PATIENT MONITOR': Complication(None),
    'CORNEAL HAZE': Complication(None),
    'PUPIL CONSTRICTION': Complication('iris_hooks', 'pupil'),
    'IRIS PROLAPSE': Complication('iris_hooks', 'pupil'),
    'ZONULAR WEAKNESS': Complication('ctr', 'centre'),
    'RHEXIS TEAR': Complication('ovd_cannula', 'centre'),
    'INCISION BLEEDING': Complication('cautery', 'incision'),
    'HYPHEMA': Complication('irrigation', 'centre'),
    'CAPSULE INTEGRITY': Complication('escalate', None, major=True),
    'SUPRACHOROIDAL HEMORRHAGE': Complication('suture', 'incision', major=True),
    'IOL DECENTRATION': Complication('iol_hook', 'centre'),
    'WOUND LEAK RISK': Complication('suture', 'incision'),
}
MAIN_INCISION = (.69, .46)


@dataclass(frozen=True, slots=True)
class Profile:
    """Synthetic patient profile (display + risk modifiers; no real person)."""
    age: int
    conditions: tuple[str, ...] = ()
    medications: tuple[str, ...] = ()   # drug classes only, never doses
    anxiety: float = .2
    heart_rate: int = 74
    sbp: int = 122
    dbp: int = 76


PROFILES: dict[str, Profile] = {
    'normal': Profile(68),
    'motion': Profile(59, ('claustrophobia',), anxiety=.9),
    'vitals': Profile(81, ('copd',)),
    'capsule': Profile(64, ('posterior_polar',)),
    'pupil': Profile(72, ('diabetes',)),
    'haze': Profile(77, ('fuchs_dystrophy',)),
    'decenter': Profile(70, ('high_myopia',)),
    'leak': Profile(70),
    'iris': Profile(74, ('bph',), ('alpha_blocker',)),
    'zonules': Profile(79, ('pseudoexfoliation',)),
    'bleed': Profile(76, ('atrial_fibrillation',), ('anticoagulant',), .3, 82, 138, 84),
    'hyphema': Profile(73, ('bph',), ('alpha_blocker', 'anticoagulant'), .3, 78, 134, 80),
    'sch': Profile(84, ('hypertension', 'high_myopia'), ('anticoagulant',), .4, 80, 158, 92),
    'random': Profile(66),
}


@dataclass(slots=True)
class Eye:
    opacity: float = 1.0
    cortex: float = 1.0
    capsule_integrity: float = 1.0
    iol_alignment: float = 0.0
    wound_integrity: float = 0.0
    pupil: float = 1.0            # visual pupil size; limits the work radius
    cornea_clarity: float = 1.0   # 1 = clear synthetic view
    blood_film: float = 0.0       # blood over the incision/cornea (0..1)
    hyphema: float = 0.0          # blood layered in the anterior chamber (0..1)
    red_reflex: float = 1.0       # 0 = lost (suprachoroidal haemorrhage)
    chamber: float = 1.0          # anterior chamber depth, 1 = normal
    entry_hits: int = 0
    capsule_points: set[int] = field(default_factory=set)
    final_checks: set[str] = field(default_factory=set)
    preop_checks: set[str] = field(default_factory=set)

    @property
    def visibility(self) -> float:
        """Synthetic view quality through cornea, blood and red reflex."""
        return round(self.cornea_clarity * (1 - .5 * self.blood_film)
                     * (1 - .6 * self.hyphema) * (.6 + .4 * self.red_reflex), 4)


@dataclass(slots=True)
class Patient:
    heart_rate: int = 74
    spo2: int = 99
    sbp: int = 122
    dbp: int = 76
    cooperation: float = 1.0
    motion: float = 0.0
    alert: str = ''
    # Physiology targets: vitals drift towards these (synthetic dynamics).
    hr_target: int = 74
    sbp_target: int = 122
    dbp_target: int = 76
    spo2_target: int = 99


class Game:
    """A strict phase machine; callers may never change `phase` via actions."""

    VERSION = 3
    MAX_EVENTS = 12000
    MAX_DT = 0.05
    RESPONSE_GRACE = 3.0          # seconds of full response credit
    # One held-instrument command per fixed 1/60 s tick: removal takes about
    # 4 s and cortex cleanup about 3 s of steady work at any frame rate.
    PHACO_STEP = .004
    CORTEX_STEP = .006
    STRESS_DECAY_PER_S = .12
    STRESS_WARNING = .5
    NO_HYDRO_STRESS = .004
    RUNOUT_EDGE = .46
    RUNOUT_LIMIT = 20
    RUNOUT_LIMIT_SHALLOW = 6
    VITAL_STEP_S = .25            # seconds per 1-unit vital drift
    TECHNIQUE_DEDUCTIONS = {'rhexis_without_ovd': 3, 'phaco_without_hydro': 3,
                            'iol_without_ovd': 3}

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
        self.profile = PROFILES[case]
        self.eye = Eye()
        p = self.profile
        hr = p.heart_rate + round(10 * max(0., p.anxiety - .2))   # = baseline_hr
        self.patient = Patient(heart_rate=hr, sbp=p.sbp, dbp=p.dbp, hr_target=hr,
                               sbp_target=p.sbp, dbp_target=p.dbp)
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
        self.stress_warnings = 0
        self.stress_scale = 1.0
        self._furthest = 0
        self._alert_elapsed = 0.0
        self._decentered = False
        self._vital_clock = 0.0
        self.alerts: list[dict[str, Any]] = []
        self.pending: list[str] = []          # assessed, awaiting management
        self.flags: set[str] = set()          # permanent events, never reset
        self.ovd_chamber = False
        self.ovd_bag = False
        self.hydro_done = False
        self.runout = 0
        self._iris_strain = 0
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

    def _flag(self, name: str) -> None:
        if name not in self.flags:
            self.flags.add(name)
            self._record('flag', {'name': name})

    @property
    def work_radius(self) -> float:
        """Usable lens-field radius; a constricted pupil shrinks it."""
        return round(self.rules.work_radius * min(1.0, .25 + .75 * self.eye.pupil), 4)

    @property
    def tissue_stress(self) -> float:
        return min(1.0, max(0.0, self._stress))

    @property
    def stress_warning(self) -> bool:
        return self._stress >= self.STRESS_WARNING

    @property
    def bleeding_factor(self) -> float:
        """Anticoagulation makes synthetic bleeding heavier (display/risk only)."""
        return 1.5 if 'anticoagulant' in self.profile.medications else 1.0

    @property
    def required_tools(self) -> tuple[str, ...]:
        """Instruments the current situation accepts (first = preferred)."""
        if self.pending:
            remedy = COMPLICATIONS[self.pending[0]].remedy
            if remedy not in (None, 'escalate'):
                return (remedy,)
        if self.phase == Phase.CLOSE and self._decentered:
            return ('iol_hook',)
        if self.phase == Phase.ENTRY:
            for index in range(3):
                if index not in self._entered:
                    return (ENTRY_BLADES[index],)
            return ()
        return TASK_TOOLS.get(self.phase, ())

    @property
    def required_tool(self) -> str | None:
        """Preferred instrument for the current situation (None if none)."""
        tools = self.required_tools
        return tools[0] if tools else None

    @property
    def stage_tool(self) -> str | None:
        """Instrument for the current stage task, ignoring complications."""
        return self._auto_tool()

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
                'tool': self.tool, 'pending': list(self.pending),
                'flags': sorted(self.flags), 'tissue_stress': round(self._stress, 6),
                'ovd_chamber': self.ovd_chamber, 'ovd_bag': self.ovd_bag,
                'hydro_done': self.hydro_done,
                'score': self.score()}

    def state_key(self) -> tuple[Any, ...]:
        """Every mutable field an action may change, for no-op detection."""
        e, p = self.eye, self.patient
        return (self.phase, self.paused, self.ending, self._stress, self._stress_warned,
                self.stress_warnings, self.stress_scale, len(self.events),
                frozenset(self._entered), self._scenario_fired, self._decentered,
                tuple(self.pending), frozenset(self.flags), self.ovd_chamber,
                self.ovd_bag, self.hydro_done, self.runout, self._iris_strain,
                self.near_misses, self.rejected_inputs, self.iol_attempts, self.pauses,
                self.tool, self.wrong_tool, self._last_point, len(self.alerts),
                tuple((a.get('response'), a.get('managed')) for a in self.alerts),
                e.opacity, e.cortex, e.capsule_integrity, e.iol_alignment,
                e.wound_integrity, e.pupil, e.cornea_clarity, e.blood_film, e.hyphema,
                e.red_reflex, e.chamber, e.entry_hits, frozenset(e.capsule_points),
                frozenset(e.final_checks), frozenset(e.preop_checks),
                p.heart_rate, p.spo2, p.sbp, p.dbp, p.cooperation, p.motion, p.alert,
                p.hr_target, p.sbp_target, p.dbp_target, p.spo2_target)

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
            if alert.get('managed') is False:
                fraction *= .5   # recognised but never managed
            items.append({'kind': alert['kind'], 'latency': latency,
                          'response': alert.get('response'),
                          'managed': alert.get('managed'), 'fraction': round(fraction, 4)})
        if not items:
            return float(weight), items
        return weight * sum(i['fraction'] for i in items) / len(items), items

    def _safety_points(self) -> tuple[float, dict[str, Any]]:
        weight = dict(SCORE_WEIGHTS)['safety']
        ended = self.ending is not None
        if not ended or self.ending == ENDING_FAILED:
            return 0.0, {'ending': self.ending, 'veto': self.ending == ENDING_FAILED}
        if self.ending == ENDING_UNRESOLVED:
            return 0.0, {'ending': self.ending, 'veto': False, 'unresolved': True}
        deductions = {k: v for k, v in self.TECHNIQUE_DEDUCTIONS.items() if k in self.flags}
        lost = (sum(deductions.values()) + 2 * self.wrong_tool + 4 * self.stress_warnings)
        return max(0.0, weight - lost), {'ending': self.ending, 'veto': False,
                                         'technique': sorted(deductions),
                                         'wrong_tool': self.wrong_tool,
                                         'stress_warnings': self.stress_warnings}

    def score_breakdown(self) -> list[dict[str, Any]]:
        """Explainable per-category points; each earned only once evaluated."""
        weights = dict(SCORE_WEIGHTS)
        furthest = self._furthest
        cortex_index = PHASES.index(Phase.CORTEX)
        close_index = PHASES.index(Phase.CLOSE)
        ended = self.ending is not None
        stages = weights['stages'] * max(0, min(7, furthest - 1)) / 7
        tissue = 0.0
        if furthest >= cortex_index:
            tissue = max(0.0, weights['tissue'] * self.eye.capsule_integrity
                         - min(8.0, .2 * self.near_misses))
        iol = weights['iol'] * self.eye.iol_alignment if furthest >= close_index else 0.0
        response, alert_items = self._response_points()
        if not ended:
            response = 0.0
        safety, safety_detail = self._safety_points()
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
             'detail': safety_detail},
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
            'wrong_tool': self.wrong_tool, 'stress_warnings': self.stress_warnings,
            'unmanaged': list(self.pending), 'flags': sorted(self.flags),
            'action_path': {k: round(v, 4) for k, v in self.action_path.items()},
            'alerts': [dict(a) for a in self.alerts],
        }

    # ------------------------------------------------------------------
    def _set_vitals(self, *, hr: int | None = None, spo2: int | None = None,
                    sbp: int | None = None, dbp: int | None = None,
                    instant: bool = True) -> None:
        """Set physiology targets; `instant` also jumps the displayed value."""
        p = self.patient
        for name, value in (('heart_rate', hr), ('spo2', spo2), ('sbp', sbp), ('dbp', dbp)):
            if value is None:
                continue
            target = {'heart_rate': 'hr_target', 'spo2': 'spo2_target',
                      'sbp': 'sbp_target', 'dbp': 'dbp_target'}[name]
            setattr(p, target, int(value))
            if instant:
                setattr(p, name, int(value))

    @property
    def baseline_hr(self) -> int:
        p = self.profile
        return p.heart_rate + round(10 * max(0., p.anxiety - .2))

    def _drift_vitals(self, dt: float) -> None:
        self._vital_clock += dt
        p = self.patient
        while self._vital_clock >= self.VITAL_STEP_S:
            self._vital_clock -= self.VITAL_STEP_S
            for name, target in (('heart_rate', 'hr_target'), ('spo2', 'spo2_target'),
                                 ('sbp', 'sbp_target'), ('dbp', 'dbp_target')):
                value, goal = getattr(p, name), getattr(p, target)
                if value != goal:
                    setattr(p, name, value + (1 if goal > value else -1))

    # ------------------------------------------------------------------
    def _advance(self, to: Phase) -> None:
        previous = self.phase
        self.phase_times[previous.value] = round(
            self.phase_times.get(previous.value, 0.0) + self.time - self._phase_started, 3)
        self._phase_started = self.time
        self.phase = to
        self._last_point = None
        self.tool = self._auto_tool() if self.rules.auto_tool else None
        if to in PHASES:
            self._furthest = max(self._furthest, PHASES.index(to))
        self._record('phase', {'from': previous.value, 'to': to.value})
        # Trigger case hazards on *state entry* or condition: a burst of
        # input events must not be able to skip a hazard before the next tick.
        self._check_hazards()
        if to == Phase.RECOVERY:
            if self.pending:
                self._finish(ENDING_UNRESOLVED)
            else:
                self._finish(ENDING_MANAGED if self.alerts else ENDING_COMPLETE)

    def _auto_tool(self) -> str | None:
        """Stage instrument handed over in assisted difficulties (never a
        situation instrument: those the surgeon always chooses)."""
        if self.phase == Phase.CLOSE and self._decentered:
            return 'iol_hook'
        if self.phase == Phase.ENTRY:
            for index in range(3):
                if index not in self._entered:
                    return ENTRY_BLADES[index]
            return None
        tools = TASK_TOOLS.get(self.phase, ())
        return tools[0] if tools else None

    def _hazard_due(self, key: str) -> bool:
        phase, _ = HAZARDS[key]
        if self.phase != phase or key == 'leak':
            return False
        e = self.eye
        if key == 'iris':
            return e.opacity <= .7
        if key == 'zonules':
            return len(e.capsule_points) >= 10
        if key == 'bleed':
            return 0 in self._entered
        if key == 'hyphema':
            return e.opacity <= .5
        if key == 'sch':
            return e.cortex <= .6
        return True

    def _check_hazards(self) -> None:
        if self.patient.alert or self.ending:
            return
        # Technique-driven escalations come first.
        if ('tear_extending' in self.flags and 'tear_rupture' not in self.flags
                and self.phase == Phase.PHACO and self.eye.opacity <= .6):
            self._flag('tear_rupture')
            self.eye.capsule_integrity = min(self.eye.capsule_integrity, .55)
            self._alert('CAPSULE INTEGRITY')
            return
        if ('iris_trauma' in self.flags and 'trauma_hyphema' not in self.flags
                and self.phase in (Phase.PHACO, Phase.CORTEX)):
            self._flag('trauma_hyphema')
            self.eye.hyphema = round(min(.8, .3 * self.bleeding_factor), 4)
            self._alert('HYPHEMA')
            return
        if not self._scenario_fired and self.hazard in HAZARDS and self._hazard_due(self.hazard):
            self._fire(self.hazard)

    def _fire(self, hazard: str) -> None:
        self._scenario_fired = True
        label = HAZARDS[hazard][1]
        bf = self.bleeding_factor
        if hazard == 'motion':
            self.patient.motion = 0.9
            self.patient.cooperation = 0.25
            self._set_vitals(hr=104)
        elif hazard == 'vitals':
            self._set_vitals(spo2=91, hr=99)
        elif hazard == 'capsule':
            self.eye.capsule_integrity = .55
        elif hazard == 'pupil':
            self.eye.pupil = .62
        elif hazard == 'haze':
            self.eye.cornea_clarity = .4
        elif hazard == 'decenter':
            self.eye.iol_alignment = round(min(self.eye.iol_alignment, .42), 4)
            self._decentered = True
        elif hazard == 'leak':
            self.eye.final_checks.discard('wound')
            self.eye.wound_integrity = round(len(self.eye.final_checks) / 3, 4)
            self.eye.chamber = .8
        elif hazard == 'iris':
            self.eye.pupil = min(self.eye.pupil, .8)
        elif hazard == 'bleed':
            self.eye.blood_film = round(min(.9, .45 * bf), 4)
        elif hazard == 'hyphema':
            self.eye.hyphema = round(min(.8, .3 * bf), 4)
        elif hazard == 'sch':
            # Sudden firm eye: chamber shallows, red reflex is lost, pain.
            self.eye.red_reflex = 0.0
            self.eye.chamber = .3
            self.patient.motion = .3
            self._set_vitals(hr=self.patient.heart_rate + 22,
                             sbp=self.patient.sbp + 34, dbp=self.patient.dbp + 14,
                             instant=False)
        self._alert(label)
        if self.rules.auto_tool and self._decentered:
            self.tool = 'iol_hook'

    def _finish(self, ending: str) -> None:
        self.ending = ending
        self.paused = False
        for label in self.pending:
            for alert in reversed(self.alerts):
                if alert['kind'] == label and alert.get('managed') is None:
                    alert['managed'] = False
                    break
        self._record('ending', {'outcome': ending, 'score': self.score(),
                                'unmanaged': list(self.pending)})

    def _alert(self, kind: str) -> None:
        if self.patient.alert or self.ending:
            return
        self.patient.alert = kind
        self.paused = True
        self._warning_seen = False
        self._alert_elapsed = 0.0
        needs = COMPLICATIONS[kind].remedy is not None
        self.alerts.append({'kind': kind, 'phase': self.phase.value,
                            'step': self.step, 'latency': None, 'response': None,
                            'managed': None if needs else True})
        self._record('alert', {'kind': kind})

    def _respond(self, response: str) -> None:
        if self.alerts and self.alerts[-1]['response'] is None:
            self.alerts[-1]['response'] = response
            self.alerts[-1]['latency'] = round(self._alert_elapsed, 3)

    def _manage(self, label: str, how: str) -> None:
        """Resolve an assessed complication and apply its effect."""
        self.pending.remove(label)
        for alert in reversed(self.alerts):
            if alert['kind'] == label and alert.get('managed') is None:
                alert['managed'] = True
                break
        e = self.eye
        if label in ('PUPIL CONSTRICTION', 'IRIS PROLAPSE'):
            e.pupil = max(e.pupil, .9)
            self._flag('iris_hooks_placed')
        elif label == 'ZONULAR WEAKNESS':
            self._flag('ctr_inserted')
            self.stress_scale = min(3.0, self.stress_scale * 1.2)
        elif label == 'RHEXIS TEAR':
            self.ovd_chamber = True
            e.capsule_integrity = min(e.capsule_integrity, .8)
            self.stress_scale = min(3.0, self.stress_scale * 1.5)
            self._flag('tear_managed')
        elif label == 'INCISION BLEEDING':
            e.blood_film = 0.0
        elif label == 'HYPHEMA':
            e.hyphema = .05
        elif label == 'CAPSULE INTEGRITY':
            self._flag('senior_called')
            self.stress_scale = min(3.0, self.stress_scale * 2)
        elif label == 'IOL DECENTRATION':
            self._decentered = False
        elif label == 'WOUND LEAK RISK':
            self._flag('wound_sutured')
            e.chamber = 1.0
        self._record('managed', {'alert': label, 'by': how})
        if label == 'SUPRACHOROIDAL HEMORRHAGE':
            # Wound closed at once; the case then stops safely (referral).
            self._flag('wound_closed_emergently')
            e.chamber = .6
            self.phase_times[self.phase.value] = round(
                self.phase_times.get(self.phase.value, 0.0) + self.time - self._phase_started, 3)
            self.phase = Phase.ABORTED
            self._finish(ENDING_ABORTED)

    def _fail(self, reason: str) -> None:
        self._record('veto', {'reason': reason, 'alert': self.pending[0] if self.pending else ''})
        self._advance(Phase.FAILED)
        self._finish(ENDING_FAILED)

    def _add_stress(self, amount: float) -> None:
        self._stress += amount
        if self._stress >= self.STRESS_WARNING and not self._stress_warned:
            self._stress_warned = True
            self.stress_warnings += 1
            self._record('stress_warning', {'stress': round(self._stress, 4)})
        if self._stress >= 1.0:
            self.eye.capsule_integrity = max(0.0, round(self.eye.capsule_integrity - .2, 4))
            self._stress = 0.0
            self._stress_warned = False
            self._alert('CAPSULE INTEGRITY')

    # ------------------------------------------------------------------
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
        self._drift_vitals(dt)
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
        if self._stress > 0:
            self._stress = max(0.0, self._stress - self.STRESS_DECAY_PER_S * dt)
            if self._stress_warned and self._stress < self.STRESS_WARNING / 2:
                self._stress_warned = False
        if 'HYPHEMA' in self.pending:
            # Unmanaged bleeding keeps layering in the chamber.
            self.eye.hyphema = round(min(.8, self.eye.hyphema + .02 * dt * self.bleeding_factor), 4)

    def _track(self, point: tuple[float, float]) -> None:
        key = self.phase.value
        if self._last_point is not None:
            self.action_path[key] = self.action_path.get(key, 0.0) + math.dist(self._last_point, point)
        self._last_point = point

    def _at_site(self, site: str | None, point: tuple[float, float]) -> bool:
        r = math.dist(point, (.5, .5))
        if site == 'incision':
            return math.dist(point, MAIN_INCISION) < .1
        if site == 'pupil':
            return .12 <= r <= .38
        if site == 'centre':
            return r <= .3
        return True

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
            self.patient.alert = ''
            self.paused = False
            self._alert_elapsed = 0.0
            if alert in ('PATIENT MOTION', 'PATIENT MONITOR'):
                # The team settles the patient: vitals return towards baseline.
                self.patient.motion = 0.0
                self.patient.cooperation = 1.0
                self._set_vitals(hr=self.baseline_hr + 2, spo2=99)
                self._set_vitals(hr=self.baseline_hr, instant=False)
            if alert == 'CORNEAL HAZE':
                self.eye.cornea_clarity = .7   # re-evaluated, partially clear
            if COMPLICATIONS[alert].remedy is not None:
                # Recognised: the surgeon must now manage it.
                self.pending.append(alert)
            self._check_hazards()
            return True
        if self.paused or self.patient.alert:
            return False
        if name == 'tool':
            if not isinstance(x, str) or x not in TOOL_NAMES or x == self.tool:
                return False
            self.tool = x
            self._record('tool', {'tool': x})
            return True
        if name == 'escalate':
            # Call the senior surgeon / vitreoretinal team (abstract).
            for label in self.pending:
                if COMPLICATIONS[label].remedy == 'escalate':
                    self._manage(label, 'escalate')
                    return True
            return False
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
        if name == 'use':
            accepted = self._use(point)
            if accepted:
                self._track(point)
                self._check_hazards()
                still_needed = self.pending and COMPLICATIONS[self.pending[0]].remedy == self.tool
                if self.rules.auto_tool and not still_needed and not self.ending:
                    # Assisted levels: the scrub nurse hands the stage
                    # instrument back after a cannula or situation tool.
                    self.tool = self._auto_tool()
            return accepted
        if name in TASK_ACTIONS and point is not None:
            # A major complication is pending: carrying on is the failure.
            for label in self.pending:
                if COMPLICATIONS[label].major and STAGE_ACTIONS.get(self.phase) == name:
                    self._fail('continued_through_' + label.lower().replace(' ', '_'))
                    return False
            if STAGE_ACTIONS.get(self.phase) == name and not self._task_tool_ok(point):
                self.wrong_tool += 1
                self.rejected_inputs += 1
                self._record('rejected', {'action': name, 'reason': 'wrong_tool',
                                          'tool': self.tool,
                                          'required': list(self._task_required(point))})
                self._wrong_tool_strain()
                return False
        accepted = self._procedure(name, point, x)
        if point is not None:
            if accepted:
                self._track(point)
                self._check_hazards()
            elif name in TASK_ACTIONS:
                self.rejected_inputs += 1
        return accepted

    def _task_required(self, point) -> tuple[str, ...]:
        if self.phase == Phase.ENTRY:
            for index, target in enumerate(self._entry_target):
                if index not in self._entered and math.dist(point, target) < self.rules.entry_radius:
                    return (ENTRY_BLADES[index],)
            return ('keratome', 'sideport')
        if self.phase == Phase.CLOSE:
            return ('iol_hook',)
        return TASK_TOOLS.get(self.phase, ())

    def _task_tool_ok(self, point) -> bool:
        if self.rules.auto_tool:
            # Assisted difficulties hand over the stage instrument.
            if self.tool not in self._task_required(point):
                self.tool = self._task_required(point)[0]
            return True
        return self.tool in self._task_required(point)

    def _wrong_tool_strain(self) -> None:
        if self.phase in (Phase.CAPSULE, Phase.PHACO, Phase.CORTEX, Phase.IOL):
            self._add_stress(.02 * self.stress_scale)

    def _use(self, point: tuple[float, float]) -> bool:
        """Use the held instrument at `point` (cannulas and situation tools)."""
        tool = self.tool
        if tool is None:
            return False
        for label in list(self.pending):
            comp = COMPLICATIONS[label]
            if comp.remedy == tool:
                if not self._at_site(comp.site, point):
                    self.rejected_inputs += 1
                    self._record('rejected', {'action': 'use', 'reason': 'wrong_site',
                                              'tool': tool, 'alert': label})
                    return False
                if label == 'IOL DECENTRATION':
                    self._place(point)
                    if not self._decentered:
                        self._manage(label, tool)
                    return True
                self._manage(label, tool)
                return True
        if tool == 'ovd_cannula':
            if ((self.phase == Phase.ENTRY and self._entered) or self.phase == Phase.CAPSULE) \
                    and not self.ovd_chamber and math.dist(point, (.5, .5)) <= .38:
                self.ovd_chamber = True
                self._record('ovd', {'space': 'chamber'})
                return True
            if self.phase == Phase.IOL and not self.ovd_bag and math.dist(point, (.5, .5)) <= .3:
                self.ovd_bag = True
                self._record('ovd', {'space': 'bag'})
                return True
            return False
        if tool == 'hydro_cannula':
            if (self.phase == Phase.PHACO and self.eye.opacity == 1.0 and not self.hydro_done
                    and math.dist(point, (.5, .5)) <= .3):
                self.hydro_done = True
                self._record('hydrodissection')
                return True
            return False
        if tool == 'iol_hook' and self.phase == Phase.CLOSE and self._decentered:
            self._place(point)
            return True
        if tool in SITUATION_TOOLS:
            # A situation instrument with nothing to manage is a wrong choice.
            self.wrong_tool += 1
            self.rejected_inputs += 1
            self._record('rejected', {'action': 'use', 'reason': 'wrong_tool', 'tool': tool,
                                      'required': list(self.required_tools)})
            self._wrong_tool_strain()
        return False

    def _place(self, point: tuple[float, float]) -> None:
        distance = math.dist(point, (.5, .5))
        self.iol_attempts += 1
        alignment = max(0.0, 1 - distance * 3)
        if 'zonular_dialysis' in self.flags:
            alignment = max(0.0, alignment - .25)   # unstable bag decentres the lens
        self.eye.iol_alignment = round(alignment, 4)
        reposition = self.phase == Phase.CLOSE
        self._record('placed', {'alignment': self.eye.iol_alignment, 'reposition': reposition})
        if not reposition:
            if not self.ovd_bag:
                self._flag('iol_without_ovd')
            if 'senior_called' in self.flags:
                self._flag('sulcus_iol')
        if self.eye.iol_alignment >= self.rules.iol_threshold:
            if self.phase == Phase.IOL:
                self._advance(Phase.CLOSE)
            else:
                self._decentered = False
        elif not reposition:
            self._record('iol_decentred', {'alignment': self.eye.iol_alignment})

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
                    elif rules.auto_tool:
                        self.tool = self._auto_tool()
                    return True
            return False
        if self.phase == Phase.CAPSULE and name == 'trace':
            angle = (math.atan2(point[1] - .5, point[0] - .5) + 2 * math.pi) % (2 * math.pi)
            radius = math.dist(point, (.5, .5))
            low, high = rules.capsule_band
            if not self.ovd_chamber:
                # Shallow chamber without viscoelastic: the safe annulus narrows.
                low, high = low + .03, high - .03
            if low < radius < high:
                if not self.ovd_chamber:
                    self._flag('rhexis_without_ovd')
                self.eye.capsule_points.add(int(angle / (2 * math.pi) * 24) % 24)
                if len(self.eye.capsule_points) >= rules.capsule_bins:
                    self._record('capsule_completed', {'bins': len(self.eye.capsule_points)})
                    self._advance(Phase.PHACO)
                return True
            if high <= radius < self.RUNOUT_EDGE and 'RHEXIS TEAR' not in [a['kind'] for a in self.alerts]:
                # Pulling outwards makes the capsulorhexis run out radially.
                self.runout += 1
                limit = self.RUNOUT_LIMIT if self.ovd_chamber else self.RUNOUT_LIMIT_SHALLOW
                if self.runout >= limit:
                    self._alert('RHEXIS TEAR')
            return False
        if self.phase in (Phase.PHACO, Phase.CORTEX) and name == 'remove':
            if math.dist(point, (.5, .5)) >= self.work_radius:
                self.near_misses += 1
                self._add_stress(rules.stress_step * self.stress_scale
                                 * (1.3 if self.eye.visibility < .6 else 1.0))
                return False
            if 'IRIS PROLAPSE' in self.pending:
                # Operating on through a prolapsing iris damages it.
                self._iris_strain += 1
                if self._iris_strain >= 30:
                    self._flag('iris_trauma')
                    self.eye.pupil = min(self.eye.pupil, .5)
            if 'ZONULAR WEAKNESS' in self.pending:
                self._flag('zonular_dialysis')
                self._add_stress(.003)
            if 'RHEXIS TEAR' in self.pending:
                self._flag('tear_extending')
            if self.phase == Phase.PHACO:
                if not self.hydro_done:
                    self._flag('phaco_without_hydro')
                    self._add_stress(self.NO_HYDRO_STRESS)
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
        if name == 'place' and (self.phase == Phase.IOL or
                                (self.phase == Phase.CLOSE and self._decentered)):
            was_decentered = self._decentered
            self._place(point)
            if was_decentered and not self._decentered and 'IOL DECENTRATION' in self.pending:
                self._manage('IOL DECENTRATION', 'iol_hook')
            return True
        if self.phase == Phase.CLOSE and name == 'verify':
            if not isinstance(x, str) or x not in FINAL_CHECKS:
                return False
            if x == 'alignment' and (self._decentered or
                                     self.eye.iol_alignment < rules.iol_threshold):
                self._record('rejected', {'action': 'verify', 'item': x,
                                          'reason': 'iol_not_centered'})
                return False
            if x == 'wound' and 'WOUND LEAK RISK' in self.pending:
                self._record('rejected', {'action': 'verify', 'item': x,
                                          'reason': 'wound_not_sealed'})
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
