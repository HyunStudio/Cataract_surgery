"""Engine v3: instruments chosen for the situation, bleeding, patient
profiles and vital signs, technique-driven complications and their chains."""
import math

import pytest

from ophthosim.engine import (COMPLICATIONS, ENDING_ABORTED, ENDING_COMPLETE, ENDING_FAILED,
                              ENDING_MANAGED, ENDING_UNRESOLVED, HAZARDS, PROFILES,
                              SITUATION_TOOLS, STEP_TOOLS, TOOL_NAMES, USE_TOOLS, Phase)
from ophthosim.i18n import EN, KO, t
from ophthosim.replay import ReplayGame

import surgeon_helpers as H


def game(case='normal', difficulty='standard', seed=7):
    return ReplayGame(case, seed, difficulty)


def at_alert(case, difficulty='standard'):
    g = game(case, difficulty)
    H.run_to(g, stop_at_alert=True)
    assert g.patient.alert == HAZARDS[case][1]
    return g


# --- instruments ------------------------------------------------------------------
def test_instrument_sets():
    assert len(TOOL_NAMES) == 15 and set(STEP_TOOLS).isdisjoint(SITUATION_TOOLS)
    assert 'iol_hook' not in USE_TOOLS and {'ovd_cannula', 'hydro_cannula'} <= USE_TOOLS
    for comp in COMPLICATIONS.values():
        assert comp.remedy in (None, 'escalate', *TOOL_NAMES)


def test_ideal_surgeon_completes_every_case():
    for case in ('normal', *HAZARDS):
        g = game(case)
        H.run_to(g)
        if not g.ending:
            for item in ('alignment', 'wound', 'handoff'):
                g.action('verify', item)
        expected = {'normal': ENDING_COMPLETE, 'sch': ENDING_ABORTED}.get(case, ENDING_MANAGED)
        assert g.ending == expected, case
        assert not g.pending


def test_situation_tool_used_without_need_counts_as_wrong_tool():
    g = game()
    H.run_to(g, Phase.ENTRY)
    before = g.wrong_tool
    assert not H.use(g, 'cautery', *H.SITES['incision'])
    assert g.wrong_tool == before + 1


def test_right_tool_at_the_wrong_site_does_not_manage():
    g = at_alert('bleed')
    g.action('assess')
    assert not H.use(g, 'cautery', .5, .5)            # centre, not the incision
    assert g.pending == ['INCISION BLEEDING']
    assert H.use(g, 'cautery', *H.SITES['incision']) and not g.pending


def test_tool_change_blocked_during_a_safety_hold():
    g = at_alert('bleed')
    assert not g.action('tool', 'cautery')
    g.action('assess')
    assert g.action('tool', 'cautery')


def test_tool_hints_only_in_tutorial():
    assert game(difficulty='tutorial').rules.tool_hints
    assert not game().rules.tool_hints and not game(difficulty='hard').rules.tool_hints


# --- bleeding ---------------------------------------------------------------------
def test_anticoagulant_makes_bleeding_heavier():
    assert game('bleed').bleeding_factor == 1.5 and game('normal').bleeding_factor == 1.0
    g = at_alert('bleed')
    assert g.eye.blood_film == pytest.approx(min(.9, .45 * 1.5))
    assert g.eye.visibility < 1


def test_unmanaged_hyphema_keeps_layering_and_irrigation_clears_it():
    g = at_alert('hyphema')
    g.action('assess')
    start = g.eye.hyphema
    for _ in range(120):
        g.tick(1 / 10)
    assert g.eye.hyphema > start
    assert H.use(g, 'irrigation', *H.SITES['centre'])
    assert g.eye.hyphema == .05 and not g.pending


def test_suprachoroidal_haemorrhage_is_closed_and_the_case_stopped():
    g = at_alert('sch')
    assert g.eye.red_reflex == 0 and g.eye.chamber < .5
    g.action('assess')
    hr = g.patient.heart_rate
    for _ in range(40):
        g.tick(.25)
    assert g.patient.heart_rate > hr                  # vitals climb towards the target
    assert H.use(g, 'suture', *H.SITES['incision'])
    assert g.ending == ENDING_ABORTED and 'wound_closed_emergently' in g.flags


def test_continuing_through_a_major_complication_fails():
    g = at_alert('sch')
    g.action('assess')
    H.arm(g)
    g.action('remove', .5, .5)
    assert g.ending == ENDING_FAILED


# --- patient profile and vitals -----------------------------------------------------------
def test_profiles_set_baseline_vitals():
    for case, profile in PROFILES.items():
        g = game(case)
        # An anxious patient starts with a faster pulse.
        assert g.baseline_hr == profile.heart_rate + round(10 * max(0, profile.anxiety - .2))
        assert (g.patient.heart_rate, g.patient.sbp, g.patient.dbp) == (
            g.baseline_hr, profile.sbp, profile.dbp)
        for key in profile.conditions:
            assert t('ko', 'cond.' + key) != 'cond.' + key
        for key in profile.medications:
            assert t('ko', 'med.' + key) != 'med.' + key


def test_vitals_drift_back_to_baseline_after_motion():
    g = at_alert('motion')
    assert g.patient.heart_rate >= 100
    g.action('assess')
    for _ in range(400):
        g.tick(.25)
    assert abs(g.patient.heart_rate - g.baseline_hr) <= 2


# --- technique-driven complications --------------------------------------------------
def test_tissue_stress_warns_and_decays():
    g = game()
    H.run_to(g, Phase.PHACO)
    H.use(g, 'hydro_cannula')
    H.arm(g)
    for _ in range(80):                               # outside the safe working radius
        g.action('remove', .5 + g.work_radius + .05, .5)
        if g.stress_warning:
            break
    assert g.stress_warning and g.stress_warnings == 1
    level = g.tissue_stress
    for _ in range(60):
        g.tick(.1)
    assert g.tissue_stress < level


def test_phaco_without_hydrodissection_is_a_technique_deduction():
    g = game()
    H.run_to(g, Phase.CLOSE, hydro=False)
    assert 'phaco_without_hydro' in g.flags


def test_capsulorhexis_runout_tears_sooner_without_viscoelastic():
    counts = {}
    for ovd in (True, False):
        g = game()
        H.run_to(g, Phase.ENTRY)
        H.entry(g, ovd=ovd)
        assert g.phase == Phase.CAPSULE
        if ovd and not g.ovd_chamber:
            H.use(g, 'ovd_cannula')
        H.arm(g)
        for n in range(1, 40):
            a = n * .3
            g.action('trace', .5 + .45 * math.cos(a), .5 + .45 * math.sin(a))
            if g.patient.alert:
                counts[ovd] = n
                break
        assert g.patient.alert == 'RHEXIS TEAR'
    assert counts[False] < counts[True]


def test_ignored_rhexis_tear_extends_into_posterior_capsule_rupture():
    g = game()
    H.run_to(g, Phase.CAPSULE)
    H.arm(g)
    for n in range(40):
        g.action('trace', .5 + .45 * math.cos(n), .5 + .45 * math.sin(n))
        if g.patient.alert:
            break
    g.action('assess')
    assert g.pending == ['RHEXIS TEAR']
    H.capsule(g)
    H.clear(g, Phase.PHACO, stop_pending=False)
    assert 'tear_extending' in g.flags
    assert g.patient.alert == 'CAPSULE INTEGRITY'


def test_ignored_zonular_weakness_leads_to_failure():
    g = at_alert('zonules')
    g.action('assess')
    H.run_to(g, manage_pending=False)
    assert 'zonular_dialysis' in g.flags and g.ending == ENDING_FAILED


def test_ignored_iris_prolapse_traumatises_the_iris_and_bleeds():
    g = at_alert('iris')
    g.action('assess')
    H.run_to(g, manage_pending=False)
    assert 'iris_trauma' in g.flags and 'trauma_hyphema' in g.flags
    assert g.ending == ENDING_UNRESOLVED


def test_unresolved_complication_scores_no_safety():
    g = at_alert('pupil')
    g.action('assess')
    H.run_to(g, manage_pending=False)
    assert g.ending == ENDING_UNRESOLVED
    assert g._safety_points()[0] == 0


# --- language coverage ---------------------------------------------------------------
def test_every_key_is_translated_in_both_languages():
    assert set(EN) == set(KO)
    for alert in COMPLICATIONS:
        for prefix in ('alert.', 'hint.'):
            assert prefix + alert in EN
    for tool in TOOL_NAMES:
        assert 'tool.' + tool in EN and 'short.' + tool in EN
    for site in ('incision', 'pupil', 'centre'):
        assert 'site.' + site in EN
