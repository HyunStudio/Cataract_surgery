"""Simplified capsule integrity visualization for a synthetic eye model.

This renders a schematic *indicator ring* inside the visible pupil. It is NOT
a clinical capsulorhexis, anatomy reconstruction, tearing model, or tissue
deformation simulation. Damage state is read from the authoritative Game.
No renderer can change safety decisions, points, or a procedural phase.
"""
from __future__ import annotations

from functools import lru_cache
import math

from .engine import Phase
from .geometry import Mesh


def _ring(name: str, *, gap: float = 0., segments: int = 72) -> Mesh:
    if name not in ("intact_capsule", "damaged_capsule"):
        raise ValueError("Invalid educational ring")
    if type(segments) is not int or not 12 <= segments <= 256:
        raise ValueError("Out-of-range synthetic segment count")
    if isinstance(gap, bool) or not isinstance(gap, (int, float)):
        raise ValueError("Invalid synthetic gap")
    try:
        gap = float(gap)
    except (OverflowError, ValueError) as exc:
        raise ValueError("Invalid synthetic gap") from exc
    if not math.isfinite(gap) or not 0. <= gap <= .8:
        raise ValueError("Invalid synthetic gap")
    # This synthetic ring intentionally sits IN FRONT of the iris/lens for
    # readable feedback, not at a medically accurate capsular depth.
    z, r_in, r_out = .067, .213, .238
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, int, int]] = []
    arc = math.tau - gap
    for i in range(segments + 1):
        # A gap opens around +X, with no triangle bridging the split.
        angle = gap / 2 + arc * i / segments
        ca, sa = math.cos(angle), math.sin(angle)
        vertices.extend(((r_out * ca, r_out * sa, z),
                         (r_in * ca, r_in * sa, z)))
        if i:
            a = (i - 1)*2
            b = i*2
            faces.extend(((a,b,a+1),(b,b+1,a+1)))
    mesh=Mesh(name,tuple(vertices),((0.,0.,1.),)*len(vertices),tuple(faces))
    mesh.validate()
    return mesh


@lru_cache(maxsize=1)
def capsule_indicator_meshes() -> dict[str, Mesh]:
    return {
        "intact": _ring("intact_capsule"),
        "damaged": _ring("damaged_capsule",gap=.58),
    }


def capsule_visible(game) -> bool:
    """A cosmetic presence gate; state and scoring are never changed."""
    if game.phase in (Phase.CAPSULE,Phase.PHACO,Phase.CORTEX,Phase.IOL,
                      Phase.CLOSE,Phase.RECOVERY):
        return True
    if game.phase in (Phase.ABORTED, Phase.FAILED) and game.eye.capsule_integrity < 1.:
        return True
    return False


def capsule_display_state(game) -> tuple[bool, float]:
    """Return visible flag and bounded damage scalar (0 healthy, 1 damaged).

    Malformed synthetic data fail closed rather than influencing GL uniforms.
    """
    raw = game.eye.capsule_integrity
    if isinstance(raw, bool) or not isinstance(raw, (int,float)):
        raise ValueError("Invalid simulated capsule integrity")
    if not 0. <= raw <= 1. or not math.isfinite(raw):
        raise ValueError("Invalid simulated capsule integrity")
    return capsule_visible(game), round(1. - float(raw), 6)
