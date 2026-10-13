"""Synthetic case briefs and complication catalogue for the mock surgery game.

Data only: nothing here changes game state. Each complication describes what
the operating surgeon *sees* and the three decisions offered after assessing
it. Management options are deliberately abstract ("stop, stabilise, call for
senior help"); no device settings, drug doses or rescue technique are given.
"""
from __future__ import annotations

from dataclasses import dataclass

# Decision identifiers accepted by Game.action('decide', <option>).
CONTINUE, MANAGE, REFER = 'continue', 'manage', 'refer'
DECISIONS = (CONTINUE, MANAGE, REFER)


@dataclass(frozen=True, slots=True)
class Complication:
    key: str            # value stored in Patient.alert (stable, also in logs)
    title: str          # display title
    stage: str          # where it typically occurs
    signs: str          # what the surgeon sees under the microscope/monitor
    major: bool         # ignoring a major complication is a critical failure
    decision: bool      # requires a continue/manage/refer decision
    manage: str = ''    # label of the management option
    continue_result: str = ''   # what happens if the surgeon carries on
    refer_result: str = 'Stop safely and refer'


CATALOG: dict[str, Complication] = {c.key: c for c in (
    Complication(
        'SITE MISMATCH', 'WRONG-SITE ALERT', 'Time-out',
        'Consent and list say LEFT eye; the surgical mark is on the RIGHT eye.',
        major=True, decision=True,
        manage='Stop, re-verify with team, correct the mark',
        continue_result='Wrong-site surgery (never event)',
        refer_result='Postpone the case until resolved'),
    Complication(
        'PATIENT MOTION', 'PATIENT MOVEMENT', 'Capsulorhexis',
        'Microscope view jerks; the patient is anxious and moving; heart rate up.',
        major=False, decision=False),
    Complication(
        'PATIENT MONITOR', 'VITAL SIGN ALERT', 'Lens removal',
        'SpO2 falling and heart rate rising on the monitor.',
        major=False, decision=False),
    Complication(
        'RHEXIS TEAR', 'ANTERIOR CAPSULE TEAR', 'Capsulorhexis',
        'The rhexis edge is running out radially towards the periphery.',
        major=False, decision=True,
        manage='Stop, re-stabilise chamber, capsule-sparing',
        continue_result='Tear extends; posterior capsule at risk later'),
    Complication(
        'ZONULAR WEAKNESS', 'ZONULAR WEAKNESS', 'Capsulorhexis',
        'The capsular bag moves with the instrument; the lens wobbles.',
        major=False, decision=True,
        manage='Stop, support the capsular bag, go gently',
        continue_result='Zonular dialysis: unstable bag, IOL decentration'),
    Complication(
        'IRIS PROLAPSE', 'IRIS PROLAPSE', 'Lens removal',
        'Floppy iris billowing out of the main incision; the pupil is constricting.',
        major=False, decision=True,
        manage='Stop, reposit iris, stabilise the pupil',
        continue_result='Iris trauma and a small working pupil'),
    Complication(
        'CAPSULE INTEGRITY', 'POSTERIOR CAPSULE RUPTURE', 'Lens removal / cortex',
        'Chamber suddenly deepens; lens fragments sink backwards; vitreous may present.',
        major=True, decision=True,
        manage='Stop, stabilise, call senior / VR support',
        continue_result='Nucleus fragments dropped into the vitreous',
        refer_result='Stop, close and refer to the VR team'),
    Complication(
        'WOUND LEAK', 'WOUND LEAK', 'Closure',
        'Aqueous is leaking from the main incision and the chamber is shallowing.',
        major=True, decision=True,
        manage='Seal the wound and re-check',
        continue_result='Leaking wound left at the end of surgery (infection risk)'),
)}


@dataclass(frozen=True, slots=True)
class CaseBrief:
    key: str
    title: str
    patient: str        # synthetic, never a real person
    risks: str          # what a surgeon would note pre-operatively
    hazards: tuple[str, ...]


CASES: dict[str, CaseBrief] = {c.key: c for c in (
    CaseBrief('normal', 'Routine cataract', 'Mock patient A-01, 68 y, LEFT eye',
              'No additional risk factors noted', ()),
    CaseBrief('motion', 'Anxious patient', 'Mock patient B-02, 59 y, LEFT eye',
              'Very anxious, claustrophobic under drapes', ('PATIENT MOTION',)),
    CaseBrief('vitals', 'Respiratory history', 'Mock patient C-03, 81 y, LEFT eye',
              'Chronic lung disease; watch the monitor', ('PATIENT MONITOR',)),
    CaseBrief('capsule', 'Posterior polar cataract', 'Mock patient D-04, 64 y, LEFT eye',
              'Posterior polar opacity: fragile posterior capsule', ('CAPSULE INTEGRITY',)),
    CaseBrief('timeout', 'Time-out check', 'Mock patient E-05, 73 y, LEFT eye',
              'Consent form to be checked at time-out', ('SITE MISMATCH',)),
    CaseBrief('iris', 'Floppy iris risk', 'Mock patient F-06, 77 y, LEFT eye',
              'Takes an alpha-1 blocker: floppy-iris risk', ('IRIS PROLAPSE',)),
    CaseBrief('zonules', 'Pseudoexfoliation', 'Mock patient G-07, 79 y, LEFT eye',
              'Pseudoexfoliation material: weak zonules likely', ('ZONULAR WEAKNESS',)),
    CaseBrief('leak', 'Routine with closure check', 'Mock patient H-08, 70 y, LEFT eye',
              'No additional risk factors noted', ('WOUND LEAK',)),
    CaseBrief('random', 'Unknown case', 'Mock patient X-09, age unknown, LEFT eye',
              'Incomplete notes: expect the unexpected', ()),
)}
CASE_KEYS = tuple(CASES)
# Seeded pool for the 'random' case (two are drawn per seed).
RANDOM_POOL = ('PATIENT MOTION', 'PATIENT MONITOR', 'ZONULAR WEAKNESS',
               'IRIS PROLAPSE', 'WOUND LEAK')

# outcome -> (headline, explanation)
OUTCOMES = {
    'SUCCESS': ('SUCCESS', 'Uncomplicated mock surgery'),
    'MANAGED': ('COMPLICATION MANAGED', 'Completed after managing complications'),
    'COMPLICATED': ('COMPLICATED', 'Completed, but a complication was ignored'),
    'SAFE_ABORT': ('SAFE ABORT', 'Stopped safely by the surgeon'),
    'CRITICAL_FAILURE': ('CRITICAL FAILURE', 'A major complication was ignored'),
}

_FLAG_NOTES = {
    'rhexis_without_ovd': 'Shallow chamber: rhexis started without viscoelastic.',
    'phaco_without_hydro': 'Nucleus not free: hydrodissection was skipped.',
    'iol_without_ovd': 'IOL injected without viscoelastic in the bag.',
    'tear_extending': 'The capsule tear is extending.',
    'zonular_dialysis': 'Zonular dialysis: the bag is unstable.',
    'iris_trauma': 'Iris trauma: the pupil is small now.',
    'sulcus_iol': 'IOL placed in the sulcus (posterior capsule open).',
    'wound_sealed': 'Wound sealed: re-check it.',
    'site_corrected': 'Site verified and corrected: repeat the time-out.',
}


def step_marker(done: bool, key_hint: str) -> str:
    """Checklist prefix: [x] done, [V]/[D]/[1] key to press, [ ] mouse task."""
    if done:
        return '[x]'
    return f'[{key_hint}]' if key_hint in ('V', 'D', '1', '2', '3', 'SPACE') else '[ ]'


def narrate(event: dict) -> str | None:
    """Short status-line text for a game event (display only)."""
    kind, data = event.get('kind'), event.get('data', {})
    if kind == 'timeout':
        return ('Time-out: discrepancy found!' if data.get('discrepancy')
                else 'Time-out complete: patient, eye and implant confirmed.')
    if kind == 'ovd':
        return f"Viscoelastic injected into the {data.get('space', 'eye')}."
    if kind == 'hydrodissection':
        return 'Hydrodissection done: the nucleus rotates freely.'
    if kind == 'flag':
        return _FLAG_NOTES.get(data.get('name'))
    if kind == 'iol_decentred':
        return 'IOL decentred: click again at the optical centre.'
    if kind == 'stress_warning':
        return 'Tissue stress! Bring the tip back to the centre.'
    if kind == 'alert':
        entry = CATALOG.get(data.get('kind'))
        return f'SAFETY HOLD: {entry.title}. Press A to assess.' if entry else None
    if kind == 'check' and data.get('leak'):
        return 'Leak found at the main incision!'
    if kind == 'phase':
        step = _STEP_NAMES.get(data.get('to'))
        return f'Next step: {step}.' if step else None
    if kind == 'ending':
        outcome = data.get('outcome')
        if outcome == 'SIMULATION COMPLETE':
            return 'Procedure complete: read your debrief.'
        if outcome == 'CRITICAL FAILURE':
            return f"Critical failure: {data.get('reason', 'major complication ignored')}."
        return 'Procedure stopped safely.'
    return None


_STEP_NAMES = {'ANESTHESIA': 'anaesthesia and prep', 'ENTRY': 'incisions',
               'CAPSULE': 'capsulorhexis', 'PHACO': 'phacoemulsification',
               'CORTEX': 'cortex aspiration', 'IOL': 'IOL implantation',
               'CLOSE': 'closure checks'}
