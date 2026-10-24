"""3D complication and bleeding signs: read-only mapping and cached meshes."""
import pytest

from ophthosim.complication3d import (LEVELS, MAX_LENS_SHIFT, PUPIL_RADIUS, STYLE,
                                      ComplicationVisuals, complication_meshes,
                                      complication_visuals, hyphema_mesh, miosis_ring)
from ophthosim.engine import HAZARDS
from ophthosim.replay import ReplayGame

import surgeon_helpers as H


def at_alert(case, assess=True):
    g = ReplayGame(case, 7, 'standard')
    H.run_to(g, stop_at_alert=True)
    assert g.patient.alert == HAZARDS[case][1]
    if assess:
        g.action('assess')
    return g


def test_quiet_case_shows_nothing():
    g = ReplayGame('normal', 7, 'standard')
    assert not complication_visuals(g).any
    H.run_to(g)
    assert g.ending and not complication_visuals(g).any


@pytest.mark.parametrize('case, check', [
    ('iris', lambda v: v.iris_prolapse == 1 and v.pupil_radius < PUPIL_RADIUS),
    ('pupil', lambda v: v.pupil_radius < PUPIL_RADIUS),
    ('leak', lambda v: v.wound_leak),
    ('capsule', lambda v: v.capsule_rupture),
    ('zonules', lambda v: v.lens_shift > 0),
    ('bleed', lambda v: v.blood_film > 0),
    ('hyphema', lambda v: v.hyphema > 0),
    ('sch', lambda v: v.reflex_loss > 0),
])
def test_each_complication_has_a_sign_while_pending(case, check):
    g = at_alert(case)
    visuals = complication_visuals(g)
    assert check(visuals), visuals


@pytest.mark.parametrize('case, flag', [('iris', 'iris_hooks'), ('zonules', 'ctr'),
                                        ('leak', 'sutures')])
def test_management_devices_appear_and_signs_settle(case, flag):
    g = at_alert(case)
    H.manage(g)
    visuals = complication_visuals(g)
    assert getattr(visuals, flag)
    if case == 'zonules':
        assert visuals.lens_shift == 0          # the CTR re-centres the bag
    if case == 'leak':
        assert not visuals.wound_leak


def test_ignored_iris_prolapse_becomes_trauma_and_hyphema():
    g = at_alert('iris')
    H.run_to(g, manage_pending=False)
    visuals = complication_visuals(g)
    assert visuals.iris_prolapse == 2 and visuals.hyphema > 0


def test_mapping_is_read_only_and_quantized():
    g = at_alert('hyphema')
    before = g.snapshot()
    visuals = complication_visuals(g)
    assert g.snapshot() == before
    assert visuals.hyphema * LEVELS == round(visuals.hyphema * LEVELS)


@pytest.mark.parametrize('bad', [
    dict(pupil_radius=.1), dict(pupil_radius=float('nan')), dict(lens_shift=MAX_LENS_SHIFT + .1),
    dict(hyphema=1.5), dict(blood_film=-.1), dict(iris_prolapse=3), dict(iris_prolapse=True),
    dict(wound_leak=1), dict(ctr='yes'),
])
def test_invalid_visuals_are_rejected(bad):
    with pytest.raises(ValueError):
        ComplicationVisuals(**bad).check()


def test_meshes_are_cached_valid_and_styled():
    meshes = complication_meshes()
    assert meshes is complication_meshes()
    for name, mesh in meshes.items():
        mesh.validate()
        assert name in STYLE or name == 'rhexis_tear_long'
    assert hyphema_mesh(.3) is hyphema_mesh(.3)
    assert miosis_ring(.2) is miosis_ring(.2)


def test_hyphema_level_rises_and_closes_at_the_fluid_line():
    low, high = hyphema_mesh(.2), hyphema_mesh(.7)
    top = lambda m: max(v[1] for v in m.vertices)
    assert top(high) > top(low)
    # Fan closed along the chord: one triangle per rim edge plus the chord.
    assert len(low.faces) == len(low.vertices) - 1
    with pytest.raises(ValueError):
        hyphema_mesh(0.)
