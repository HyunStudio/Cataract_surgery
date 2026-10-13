"""CPU mirror of the synthetic IOL vertex shader for read-only picking.

This reproduces the rendered GPU vertex positions (not normals or tissue
physics) for the *synthetic* IOL optic and two haptics. Deformed mesh indexes
are built on demand by the atlas; callers must not use this as an authority
for a surgical action, harm assessment or medical interpretation.
"""
from __future__ import annotations

from functools import lru_cache
import math

from .geometry import Mesh
from .iol3d import foldable_iol_mesh


def _fraction(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"Invalid {name}")
    # Reject arbitrary-width Python integers before converting to float.
    if not 0 <= value <= 1 or not math.isfinite(value):
        raise ValueError(f"Invalid {name}")
    return float(value)


def iol_vertex_position(vertex: tuple[float, float, float],
                        deployment: object, alignment: object = 1.0
                        ) -> tuple[float, float, float]:
    """Match GLSL u_iol_fold and x-only u_offset, before rotation.

    GLSL:
      local_pos.x = mix(0.24 * in_position.x, in_position.x, fold);
      local_pos.z += (1.0 - fold) * 0.30 * abs(in_position.x);
      p = rotation * (local_pos + offset);
    """
    d = _fraction(deployment, "IOL deployment")
    a = _fraction(alignment, "IOL alignment")
    if not isinstance(vertex, (tuple, list)) or len(vertex) != 3:
        raise ValueError("Invalid IOL vertex")
    for v in vertex:
        if (isinstance(v, bool) or not isinstance(v, (int, float))
                or not -2 <= v <= 2 or not math.isfinite(v)):
            raise ValueError("Invalid IOL vertex")
    x, y, z = vertex
    return (x * (.24 + .76 * d) + .18 * (1 - a),
            float(y), z + (1. - d) * .30 * abs(x))


@lru_cache(maxsize=16)
def deformed_iol_mesh(deployment: float = 1.0,
                      alignment: float = 1.0) -> Mesh:
    """Return one immutable, finite, budgeted mesh at a visual fold state.

    No per-frame index building or mutation of the GPU source mesh. Cache is
    bounded to 16 combinations, including intermediate deployment values.
    """
    d = _fraction(deployment, "IOL deployment")
    a = _fraction(alignment, "IOL alignment")
    original = foldable_iol_mesh()
    vertices = tuple(iol_vertex_position(p, d, a) for p in original.vertices)
    result = Mesh("iol", vertices, original.normals, original.faces)
    result.validate()
    return result
