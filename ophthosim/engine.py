"""Deterministic, non-clinical cataract interaction simulation.

The player is the operating surgeon of a *mock* cataract procedure that
follows the real sequence of a phacoemulsification case and its realistic
intra-operative complications (see docs/SURGERY_REALISM_PLAN_KO.md). Every
numeric value is a synthetic game score, not clinical guidance: there are no
device settings, drug doses or rescue techniques in this model.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
import json
import math
import random
from typing import Any

from .complications import (CASES, CATALOG, CONTINUE, DECISIONS, MANAGE,
                            OUTCOMES, RANDOM_POOL, REFER)


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
ENDED = (Phase.RECOVERY, Phase.ABORTED, Phase.FAILED)


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

    VERSION = 3
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
    # A nucleus that was not hydrodissected does not rotate freely, so even
    # central work strains the zonules/capsule (net of decay ~.002 per tick).
    NO_HYDRO_STRESS = .004
    WORK_RADIUS = .33
    # Capsulorhexis: the safe annulus narrows in a shallow (no viscoelastic)
    # chamber; outward pulls into the run-out zone tear the capsule.
    RHEXIS_BAND = (.19, .37)
    RHEXIS_BAND_SHALLOW = (.22, .34)
    RHEXIS_RUNOUT_EDGE = .46
    RUNOUT_LIMIT = 20
    RUNOUT_LIMIT_SHALLOW = 6
    TECHNIQUE_DEDUCTIONS = {'rhexis_without_ovd': 3, 'phaco_without_hydro': 3,
                            'iol_without_ovd': 3}

    def __init__(self, case: str = 'normal', seed: int = 7):
        if not isinstance(case, str) or case not in CASES:
            raise ValueError('Unknown scenario')
        if (isinstance(seed, bool) or not isinstance(seed, int)
                or abs(seed) > 2**63 - 1):
            raise ValueError('seed must be a bounded 64-bit integer')
        self.case = case
        self.seed = seed
        self.rng = random.Random(seed)
        if case == 'random':
            drawn = self.rng.sample(RANDOM_POOL, 2)
            self.hazards = tuple(sorted(drawn, key=RANDOM_POOL.index))
        else:
            self.hazards = CASES[case].hazards
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
        self._stress = 0.0
        self._stress_warned = False
        self.off_target = 0
        self.stress_warnings = 0
        # Realistic procedure state.
        self.fired: list[str] = []            # scheduled hazards already raised
        self.alert_history: list[str] = []    # every safety hold, in order
        self.awaiting_decision: str | None = None
        self.decisions: list[tuple[str, str]] = []
        self.flags: set[str] = set()          # permanent events, never reset
        self.ovd_chamber = False
        self.ovd_bag = False
        self.hydro_done = False
        self.runout = 0
        self.work_radius = self.WORK_RADIUS
        self.stress_scale = 1.0
        self.on_target_stress = 0.0
        self.failure_reason = ''
        self._record('start', {'case': case, 'seed': seed, 'hazards': list(self.hazards)})

    # ------------------------------------------------------------------ util
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
                'hazards': list(self.hazards), 'fired': list(self.fired),
                'alert_history': list(self.alert_history),
                'awaiting_decision': self.awaiting_decision,
                'decisions': [list(d) for d in self.decisions],
                'flags': sorted(self.flags),
                'ovd_chamber': self.ovd_chamber, 'ovd_bag': self.ovd_bag,
                'hydro_done': self.hydro_done, 'outcome': self.outcome(),
                'score': self.score()}

    @property
    def tissue_stress(self) -> float:
        """Synthetic 0..1 strain from off-target work; 1.0 triggers an alert."""
        return min(1.0, max(0.0, self._stress))

    @property
    def stress_warning(self) -> bool:
        return self._stress >= self.STRESS_WARNING

    @property
    def complication(self):
        """Catalogue entry of the active safety hold, if any."""
        return CATALOG.get(self.patient.alert)

    def state_key(self) -> tuple[Any, ...]:
        """Every mutable field that an action may change, for no-op detection."""
        e, p = self.eye, self.patient
        return (self.phase, self.paused, self.ending, self._stress,
                self._stress_warned, self.off_target, self.stress_warnings,
                self._warning_seen, len(self.events),
                frozenset(self._entered), e.opacity, e.cortex,
                e.capsule_integrity, e.iol_alignment, e.wound_integrity,
                e.entry_hits, frozenset(e.capsule_points),
                frozenset(e.final_checks), p.heart_rate, p.spo2, p.sbp, p.dbp,
                p.cooperation, p.motion, p.alert, tuple(self.fired),
                tuple(self.alert_history), self.awaiting_decision,
                tuple(self.decisions), frozenset(self.flags), self.ovd_chamber,
                self.ovd_bag, self.hydro_done, self.runout, self.work_radius,
                self.stress_scale, self.on_target_stress)

    # -------------------------------------------------------------- results
    def outcome(self) -> str | None:
        """SUCCESS / MANAGED / COMPLICATED / SAFE_ABORT / CRITICAL_FAILURE."""
        if self.phase == Phase.FAILED:
            return 'CRITICAL_FAILURE'
        if self.phase == Phase.ABORTED:
            return 'SAFE_ABORT'
        if self.phase == Phase.RECOVERY:
            if any(choice == CONTINUE for _, choice in self.decisions):
                return 'COMPLICATED'
            return 'MANAGED' if self.alert_history else 'SUCCESS'
        return None

    def outcome_title(self) -> tuple[str, str]:
        """(headline, explanation) of the outcome, or empty strings."""
        outcome = self.outcome()
        return OUTCOMES[outcome] if outcome else ('', '')

    def phase_durations(self) -> dict[str, float]:
        """Simulated seconds spent in each phase, from the event trace."""
        durations: dict[str, float] = {}
        start, current = 0, Phase.PREOP.value
        for event in self.events:
            if event['kind'] == 'phase':
                target = event['data']['to']
            elif event['kind'] == 'ending' and event['data'].get('outcome') != 'SIMULATION COMPLETE':
                target = Phase.FAILED.value if event['data'].get('outcome') == 'CRITICAL FAILURE' \
                    else Phase.ABORTED.value
            else:
                continue
            durations[current] = durations.get(current, 0.) + (event['sim_time_ms'] - start) / 1000
            start, current = event['sim_time_ms'], target
        if not self.ending:
            durations[current] = durations.get(current, 0.) + (round(self.time * 1000) - start) / 1000
        return {k: round(v, 2) for k, v in durations.items()}

    def checklist(self) -> list[tuple[str, bool, str]]:
        """Real procedure sub-steps of the current phase: (label, done, input)."""
        ph, e = self.phase, self.eye
        if ph == Phase.PREOP:
            return [('Case brief reviewed', True, ''),
                    ('Time-out', False, 'SPACE')]
        if ph == Phase.ANESTHESIA:
            return [('Anaesthesia & drape', False, 'SPACE')]
        if ph == Phase.ENTRY:
            return [('Main incision', 0 in self._entered, 'click'),
                    ('Side port 1', 1 in self._entered, 'click'),
                    ('Side port 2', 2 in self._entered, 'click'),
                    ('Viscoelastic (OVD)', self.ovd_chamber, 'V')]
        if ph == Phase.CAPSULE:
            return [('Viscoelastic (OVD)', self.ovd_chamber, 'V'),
                    (f'Capsulorhexis {len(e.capsule_points)}/20', False, 'drag')]
        if ph == Phase.PHACO:
            return [('Hydrodissection', self.hydro_done, 'D'),
                    (f'Nucleus removal {1 - e.opacity:.0%}', False, 'hold')]
        if ph == Phase.CORTEX:
            return [(f'Cortex I/A {1 - e.cortex:.0%}', False, 'hold')]
        if ph == Phase.IOL:
            return [('OVD in capsular bag', self.ovd_bag, 'V'),
                    ('Inject & centre IOL', False, 'click')]
        if ph == Phase.CLOSE:
            return [('IOL centred', 'alignment' in e.final_checks, '1'),
                    ('Wounds watertight', 'wound' in e.final_checks, '2'),
                    ('Team handoff', 'handoff' in e.final_checks, '3')]
        return []

    def debrief(self) -> list[tuple[str, str]]:
        """Surgeon-facing (label, verdict) feedback lines; synthetic only."""
        lines: list[tuple[str, str]] = []
        outcome = self.outcome()
        if outcome:
            lines.append(('Result', OUTCOMES[outcome][1]))
        if self.failure_reason:
            lines.append(('Cause', self.failure_reason))
        verdict = {CONTINUE: 'ignored', MANAGE: 'managed', REFER: 'stopped and referred'}
        decided = {key for key, _ in self.decisions}
        for key, choice in self.decisions:
            lines.append((CATALOG[key].title.title(), verdict[choice]))
        for key in self.alert_history:
            if key not in decided and key in CATALOG and not CATALOG[key].decision:
                lines.append((CATALOG[key].title.title(), 'assessed'))
                decided.add(key)
        if self.phase == Phase.ABORTED and not self.decisions and self.alert_history:
            lines.append(('Decision', 'Recognised and stopped safely'))
        elif self.phase == Phase.ABORTED and not self.alert_history:
            lines.append(('Decision', 'Procedure stopped by the surgeon'))
        skipped = [name for flag, name in (('rhexis_without_ovd', 'chamber OVD'),
                                           ('phaco_without_hydro', 'hydrodissection'),
                                           ('iol_without_ovd', 'bag OVD'))
                   if flag in self.flags]
        if skipped:
            lines.append(('Skipped steps', ', '.join(skipped)))
        lines.append(('Off-target work', f'{self.off_target / 60:.1f} s'))
        lines.append(('Stress warnings', str(self.stress_warnings)))
        if self.eye.iol_alignment > 0:
            lines.append(('IOL centration', f'{self.eye.iol_alignment:.0%}'))
        if 'sulcus_iol' in self.flags:
            lines.append(('IOL position', 'Sulcus (posterior capsule open)'))
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
        # Technique and safety deductions; the bucket never goes negative.
        safety -= 4 * self.stress_warnings
        safety -= sum(v for k, v in self.TECHNIQUE_DEDUCTIONS.items() if k in self.flags)
        safety -= 5 * sum(1 for _, choice in self.decisions if choice == CONTINUE)
        result = max(0, min(100, phases + tissue + placement + progress + max(0, safety)))
        return result

    # ---------------------------------------------------------- transitions
    def _advance(self, to: Phase) -> None:
        previous = self.phase
        self.phase = to
        self._record('phase', {'from': previous.value, 'to': to.value})
        # Trigger case hazards on *state entry*: a burst of input events must
        # not be able to skip a hazard before the next frame's tick.
        self._check_hazards()
        if to == Phase.RECOVERY:
            self.ending = 'SIMULATION COMPLETE'
            self._record('ending', {'outcome': self.ending, 'result': self.outcome(),
                                    'score': self.score()})

    def _hazard_due(self, key: str) -> bool:
        ph, e = self.phase, self.eye
        if key == 'PATIENT MOTION':
            return ph == Phase.CAPSULE
        if key in ('PATIENT MONITOR', 'CAPSULE INTEGRITY'):
            return ph == Phase.PHACO
        if key == 'IRIS PROLAPSE':
            return ph == Phase.PHACO and e.opacity <= .7
        if key == 'ZONULAR WEAKNESS':
            return (ph == Phase.CAPSULE and len(e.capsule_points) >= 10) or ph == Phase.PHACO
        return False  # SITE MISMATCH / WOUND LEAK are found by explicit checks

    def _check_hazards(self) -> None:
        if self.patient.alert or self.ending:
            return
        # An ignored anterior capsule tear extends into the posterior capsule.
        if ('tear_extending' in self.flags and 'tear_rupture' not in self.flags
                and self.phase == Phase.PHACO and self.eye.opacity <= .6):
            self._flag('tear_rupture')
            self.eye.capsule_integrity = min(self.eye.capsule_integrity, .55)
            self._alert('CAPSULE INTEGRITY')
            return
        for key in self.hazards:
            if key not in self.fired and self._hazard_due(key):
                self._raise_hazard(key)
                return

    def _raise_hazard(self, key: str) -> None:
        self.fired.append(key)
        if key == 'PATIENT MOTION':
            self.patient.motion = 0.9
            self.patient.cooperation = 0.25
            self.patient.heart_rate = 104
        elif key == 'PATIENT MONITOR':
            self.patient.spo2 = 91
            self.patient.heart_rate = 99
        elif key == 'CAPSULE INTEGRITY':
            self.eye.capsule_integrity = .55
        self._alert(key)

    def _alert(self, kind: str) -> None:
        if self.patient.alert or self.ending:
            return
        self.patient.alert = kind
        self.alert_history.append(kind)
        self.paused = True
        self._warning_seen = False
        self._record('alert', {'kind': kind})

    @staticmethod
    def _needs_decision(alert: str) -> bool:
        entry = CATALOG.get(alert)
        return bool(entry and entry.decision)

    def _clear_alert(self) -> None:
        self.patient.alert = ''
        self.patient.motion = 0.0
        self.patient.cooperation = 1.0
        self.patient.heart_rate = 76
        self.patient.spo2 = 99
        self.paused = False

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

    def _fail(self, reason: str) -> None:
        self.phase = Phase.FAILED
        self.ending = 'CRITICAL FAILURE'
        self.failure_reason = reason
        self.paused = False
        self._record('ending', {'outcome': self.ending, 'reason': reason})

    def _apply_decision(self, key: str, choice: str) -> None:
        if choice == MANAGE:
            if key == 'CAPSULE INTEGRITY':
                self._flag('pcr_managed')
                self.stress_scale = min(3.0, self.stress_scale * 2)
            elif key == 'RHEXIS TEAR':
                self._flag('rhexis_tear_managed')
                self.eye.capsule_integrity = min(self.eye.capsule_integrity, .8)
                self.stress_scale = min(3.0, self.stress_scale * 1.5)
            elif key == 'ZONULAR WEAKNESS':
                self._flag('bag_supported')
                self.stress_scale = min(3.0, self.stress_scale * 1.2)
            elif key == 'IRIS PROLAPSE':
                self._flag('iris_reposited')
                self.work_radius = min(self.work_radius, .30)
            elif key == 'SITE MISMATCH':
                self._flag('site_corrected')
            elif key == 'WOUND LEAK':
                self._flag('wound_sealed')
        else:  # CONTINUE on a non-major complication: it escalates.
            if key == 'RHEXIS TEAR':
                self._flag('tear_extending')
                self.eye.capsule_integrity = min(self.eye.capsule_integrity, .8)
            elif key == 'ZONULAR WEAKNESS':
                self._flag('zonular_dialysis')
                self.stress_scale = min(3.0, self.stress_scale * 2)
                self.on_target_stress += .003
            elif key == 'IRIS PROLAPSE':
                self._flag('iris_trauma')
                self.work_radius = min(self.work_radius, .25)
                self.stress_scale = min(3.0, self.stress_scale * 1.3)

    # ---------------------------------------------------------------- clock
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

    # -------------------------------------------------------------- actions
    def action(self, name: str, x: Any = None, y: Any = None) -> bool:
        """Return whether the game accepted the semantic user command."""
        if not isinstance(name, str) or len(name) > 80:
            return False
        if name == 'abort' and self.phase not in ENDED:
            self.phase = Phase.ABORTED
            self.ending = 'SAFELY ABORTED'
            self.paused = False
            if self.patient.alert:
                self._record('decision', {'alert': self.patient.alert, 'choice': REFER})
                if self.awaiting_decision or self._needs_decision(self.patient.alert):
                    self.decisions.append((self.patient.alert, REFER))
            self.awaiting_decision = None
            self._record('ending', {'outcome': self.ending})
            return True
        if self.ending:
            return False
        if name == 'pause':
            self.paused = not self.paused if not self.patient.alert else True
            self._record('pause', {'paused': self.paused})
            return True
        if name == 'assess' and self.patient.alert and not self.awaiting_decision:
            self._warning_seen = True
            self._record('assessed', {'alert': self.patient.alert})
            if self._needs_decision(self.patient.alert):
                # Recognised: the surgeon must now decide how to proceed.
                self.awaiting_decision = self.patient.alert
                return True
            self._clear_alert()
            self._check_hazards()
            return True
        if name == 'decide':
            if not self.awaiting_decision or not isinstance(x, str) or x not in DECISIONS:
                return False
            key = self.awaiting_decision
            if x == REFER:
                return self.action('abort')
            self.awaiting_decision = None
            self.decisions.append((key, x))
            self._record('decision', {'alert': key, 'choice': x})
            if x == CONTINUE and CATALOG[key].major:
                self.patient.alert = ''
                self._fail(CATALOG[key].continue_result)
                return True
            self._apply_decision(key, x)
            self._clear_alert()
            self._check_hazards()
            return True
        if self.paused or self.patient.alert:
            return False
        if self.phase == Phase.PREOP and name == 'confirm':
            if 'SITE MISMATCH' in self.hazards and 'SITE MISMATCH' not in self.fired:
                # The time-out itself is what catches the discrepancy.
                self._record('timeout', {'discrepancy': True})
                self._raise_hazard('SITE MISMATCH')
                return True
            self._record('timeout', {'discrepancy': False})
            self._advance(Phase.ANESTHESIA)
            return True
        if self.phase == Phase.ANESTHESIA and name == 'prepare':
            self._advance(Phase.ENTRY)
            return True
        if name == 'ovd':
            if ((self.phase == Phase.ENTRY and self.eye.entry_hits >= 1)
                    or self.phase == Phase.CAPSULE) and not self.ovd_chamber:
                self.ovd_chamber = True
                self._record('ovd', {'space': 'chamber'})
                return True
            if self.phase == Phase.IOL and not self.ovd_bag:
                self.ovd_bag = True
                self._record('ovd', {'space': 'bag'})
                return True
            return False
        if name == 'hydro':
            if self.phase == Phase.PHACO and self.eye.opacity == 1.0 and not self.hydro_done:
                self.hydro_done = True
                self._record('hydrodissection')
                return True
            return False
        point = self._xy(x, y)
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
            low, high = self.RHEXIS_BAND if self.ovd_chamber else self.RHEXIS_BAND_SHALLOW
            if low < radius < high:
                if not self.ovd_chamber:
                    self._flag('rhexis_without_ovd')
                self.eye.capsule_points.add(int(angle / (2 * math.pi) * 24) % 24)
                if len(self.eye.capsule_points) >= 20:
                    self._record('capsule_completed', {'bins': len(self.eye.capsule_points)})
                    self._advance(Phase.PHACO)
                else:
                    self._check_hazards()
                return True
            if high <= radius < self.RHEXIS_RUNOUT_EDGE and 'RHEXIS TEAR' not in self.alert_history:
                # Pulling outwards makes the capsulorhexis run out radially.
                self.runout += 1
                limit = self.RUNOUT_LIMIT if self.ovd_chamber else self.RUNOUT_LIMIT_SHALLOW
                if self.runout >= limit:
                    self._alert('RHEXIS TEAR')
            return False
        if self.phase in (Phase.PHACO, Phase.CORTEX) and name == 'remove':
            if math.dist(point, (.5, .5)) >= self.work_radius:
                self.off_target += 1
                self._add_stress(self.STRESS_PER_MISS * self.stress_scale)
                return False
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
            if self.on_target_stress:
                self._add_stress(self.on_target_stress)
            self._record('removed', {'x': round(point[0], 4), 'y': round(point[1], 4)})
            self._check_hazards()
            return True
        if self.phase == Phase.IOL and name == 'place':
            distance = math.dist(point, (.5, .5))
            alignment = max(0.0, 1 - distance * 3)
            if 'zonular_dialysis' in self.flags:
                alignment = max(0.0, alignment - .25)  # unstable bag decentres the lens
            self.eye.iol_alignment = round(alignment, 4)
            if not self.ovd_bag:
                self._flag('iol_without_ovd')
            if 'pcr_managed' in self.flags:
                self._flag('sulcus_iol')
            self._record('placed', {'alignment': self.eye.iol_alignment})
            if self.eye.iol_alignment >= .65:
                self._advance(Phase.CLOSE)
            else:
                self._record('iol_decentred', {'alignment': self.eye.iol_alignment})
            return True
        if self.phase == Phase.CLOSE and name == 'verify':
            if not isinstance(x, str) or x not in {'alignment', 'wound', 'handoff'}:
                return False
            if (x == 'wound' and 'WOUND LEAK' in self.hazards
                    and 'wound_sealed' not in self.flags):
                if 'WOUND LEAK' in self.fired:
                    return False
                self._record('check', {'item': x, 'leak': True})
                self._raise_hazard('WOUND LEAK')
                return True
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
