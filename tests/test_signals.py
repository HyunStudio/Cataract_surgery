"""Unit and adversarial tests for synthetic display signals."""
import math
import random
import pytest
from ophthosim.signals import sample_trace, ecg_shape, pleth_shape


def test_ecg_and_pleth_are_deterministic_bounded():
    for kind in ("ecg", "pleth"):
        a = sample_trace(kind, 74, 23.1)
        assert a == sample_trace(kind, 74, 23.1)
        assert len(a) == 238
        assert all(math.isfinite(n) and -1 <= n <= 1 for n in a)


def test_monitor_signal_changes_when_hr_changes():
    assert sample_trace("ecg", 74, 1.2) != sample_trace("ecg", 104, 1.2)
    assert sample_trace("pleth", 74, 1.2) != sample_trace("pleth", 104, 1.2)


def test_zero_hr_returns_flat_schematic_trace():
    assert set(sample_trace("ecg", 0, 100)) == {0.0}
    assert set(sample_trace("pleth", 0, 100)) == {0.0}


def test_shape_stays_bounded_for_all_1000_phases():
    for i in range(1001):
        p = i / 1000.
        assert -.5 <= ecg_shape(p) <= 1.0
        assert 0 <= pleth_shape(p) <= 1.0


@pytest.mark.parametrize("bad", [None, True, float("nan"), float("inf"),
                                  -1, 251, 10**400, "92"])
def test_bad_heart_rate_is_rejected(bad):
    with pytest.raises(ValueError):
        sample_trace("ecg", bad, .1)


@pytest.mark.parametrize("bad", [None, True, float("nan"), float("inf"),
                                 -1, 10**400, "10"])
def test_bad_elapsed_rejected(bad):
    with pytest.raises(ValueError):
        sample_trace("pleth", 74, bad)


@pytest.mark.parametrize("count", [-1, 0, 1, 2049, True, 1.2, 10**400])
def test_bad_sample_count_rejected(count):
    with pytest.raises(ValueError):
        sample_trace("ecg", 74, 1, count=count)


def test_waveform_does_not_depend_on_global_random_state():
    random.seed(1000)
    a = sample_trace("ecg", 104, 2.)
    random.seed(3)
    b = sample_trace("ecg", 104, 2.)
    assert a == b


def test_alert_synthetic_patient_state_maps_to_display():
    from ophthosim.engine import Game, Phase
    g = Game("motion")
    for _check in ("identity", "site", "iol_plan"): g.action("verify", _check)
    g.action("confirm")
    g.action("prepare")
    for x,y in g._entry_target:
        g.action("touch",x,y)
    assert g.phase == Phase.CAPSULE
    assert g.patient.heart_rate == 104 and g.patient.alert
    assert sample_trace("ecg",g.patient.heart_rate,g.time) != sample_trace("ecg",74,g.time)
