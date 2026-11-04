"""Deterministic, non-clinical visual feedback for the 3D educational view.

This observes the existing synthetic patient/eye model only. It NEVER
changes a procedure, medical alert, score, replay or tool position. Movement
and haze are display metaphors; neither is a clinical optics simulation.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

from .engine import Phase


def _bounded(v: object, low: float, high: float, field: str) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise ValueError(f"Invalid {field}")
    # Compare bounds before converting huge Python integers to floats.
    if not low <= v <= high:
        raise ValueError(f"Invalid {field}")
    try:
        n = float(v)
    except (ValueError, OverflowError) as exc:
        raise ValueError(f"Invalid {field}") from exc
    if not math.isfinite(n):
        raise ValueError(f"Invalid {field}")
    return n


@dataclass(frozen=True, slots=True)
class VisualFeedback:
    """Bounded visual offsets in camera-plane normalized units, and veil."""

    motion_x: float = 0.0
    motion_y: float = 0.0
    haze: float = 0.0
    reduced_motion: bool = False
    high_contrast: bool = False

    def check(self) -> None:
        _bounded(self.motion_x, -.08, .08, "visual motion x")
        _bounded(self.motion_y, -.08, .08, "visual motion y")
        _bounded(self.haze, 0.0, .65, "synthetic visual haze")
        if type(self.reduced_motion) is not bool:
            raise ValueError("reduced_motion must be boolean")
        if type(self.high_contrast) is not bool:
            raise ValueError("high_contrast must be boolean")


def visual_feedback(game, *, reduced_motion: bool = False,
                    high_contrast: bool = False) -> VisualFeedback:
    """Read-only mapping: synthetic alert/motion and opacity -> display.

    Time-based movement is low frequency and bounded, with no flash/strobe.
    Safety-hold freezes the pose at a static offset (game time is paused).
    The reduced-motion option suppresses geometric motion, not alerts or
    safety interlocks. Static synthetic haze remains visible by design.
    """
    if type(reduced_motion) is not bool or type(high_contrast) is not bool:
        raise ValueError("Accessibility options must be booleans")
    motion = _bounded(game.patient.motion, 0., 1., "patient movement")
    opacity = _bounded(game.eye.opacity, 0., 1., "synthetic opacity")
    cortex = _bounded(game.eye.cortex, 0., 1., "synthetic cortex")
    moment = _bounded(game.time, 0., 1e7, "simulation clock")
    if not isinstance(game.phase, Phase):
        raise ValueError("Invalid educational phase")
    if not isinstance(game.patient.alert, str) or len(game.patient.alert) > 80:
        raise ValueError("Invalid patient alert")
    visible = game.phase in (Phase.ENTRY, Phase.CAPSULE, Phase.PHACO,
                             Phase.CORTEX)
    # Veil scales down as the simulated lens is cleared. It has no diagnostic
    # meaning, and no invasive/real-world values are represented.
    clarity = _bounded(getattr(game.eye, "cornea_clarity", 1.), 0., 1.,
                       "synthetic corneal clarity")
    haze = (.08 + .26 * opacity + .08 * cortex) if visible else 0.
    # Corneal-haze event: an extra veil until the view is re-evaluated.
    if game.phase not in (Phase.RECOVERY, Phase.ABORTED, Phase.FAILED):
        haze = min(.48, haze + .5 * (1. - clarity))
    if reduced_motion or motion == 0.:
        dx = dy = 0.
    elif game.paused or game.patient.alert:
        # Frozen, stable offset, not continuously shaking on an unsafe hold.
        dx = round(.040 * motion, 6)
        dy = round(-.026 * motion, 6)
    else:
        dx = round(.035 * motion * math.sin(moment * 2. * math.pi * .7), 6)
        dy = round(.023 * motion * math.sin(moment * 2. * math.pi * .53 + .9), 6)
    result = VisualFeedback(dx, dy, round(haze, 6),
                            reduced_motion, high_contrast)
    result.check()
    return result
