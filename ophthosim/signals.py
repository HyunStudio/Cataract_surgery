"""Synthetic waveform generator for the educational patient monitor.

Shapes and values are deliberately *not* clinical ECG or pulse oximetry
signals. They are deterministic UI feedback driven by the same synthetic
patient state that drives displayed vital numbers.
"""
from __future__ import annotations

import math


def _number(value: object, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise ValueError("Expected a bounded finite simulation number")
    try:
        value = float(value)
    except (OverflowError, ValueError) as exc:
        raise ValueError("Expected a bounded finite simulation number") from exc
    if not math.isfinite(value) or not minimum <= value <= maximum:
        raise ValueError("Expected a bounded finite simulation number")
    return value


def _periodic_distance(phase: float, center: float) -> float:
    return (phase - center + .5) % 1.0 - .5


def ecg_shape(phase: float) -> float:
    """Schematic P-QRS-T silhouette in normalized educational coordinates."""
    phase = _number(phase, 0.0, 1.0)
    gaussian = lambda loc, sigma: math.exp(-.5 * (_periodic_distance(phase, loc) / sigma)**2)
    return (.11 * gaussian(.17, .045)
            - .15 * gaussian(.34, .012)
            + .98 * gaussian(.37, .009)
            - .31 * gaussian(.40, .014)
            + .22 * gaussian(.64, .075))


def pleth_shape(phase: float) -> float:
    """Schematic peripheral pulse curve, not measured SpO2 physiology."""
    phase = _number(phase, 0.0, 1.0)
    if phase < .19:
        return max(0.0, phase / .19)
    tail = math.exp(-(phase - .19) * 4.7)
    notch = .13 * math.exp(-.5 * ((phase - .45) / .035)**2)
    return max(0.0, tail - notch)


def sample_trace(kind: str, heart_rate: object, elapsed: object,
                 count: int = 238, window_s: float = 3.0) -> tuple[float, ...]:
    """Return a bounded, deterministic array of synthetic samples.

    Renderers should map [-1,1] amplitude to pixel height. A stopped
    synthetic heart rate returns a flatline. Time is simulation time, not
    wall-clock time; paused games deliberately freeze the whole scene.
    """
    hr = _number(heart_rate, 0., 250.)
    t = _number(elapsed, 0., 10_000_000.)
    duration = _number(window_s, .1, 30.)
    if type(count) is not int or not 2 <= count <= 2048:
        raise ValueError("Bad waveform resolution")
    if kind not in {"ecg", "pleth"}:
        raise ValueError("Unknown waveform")
    if hr == 0:
        return (0.0,) * count
    signal = ecg_shape if kind == "ecg" else pleth_shape
    frequency = hr / 60.
    # A fixed time window gives visibly different beats at different HR.
    return tuple(signal(((t - duration + duration * i / (count - 1))
                         * frequency) % 1.) for i in range(count))
