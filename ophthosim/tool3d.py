"""Stylized 3D cursor stylus for the *synthetic* microsurgery viewport.

The shaft/tip is visual geometry only: it does not emulate a real surgical
instrument, deliver force, calculate tissue contact, or decide progression.
The replayable Game state machine remains the only action authority.
"""
from __future__ import annotations

from functools import lru_cache
import math

from .geometry import Mesh
from .input3d import Surgery3DController


@lru_cache(maxsize=1)
def stylus_mesh() -> Mesh:
    """Create a tiny bounded, closed tapered stylus with a visible narrow tip.

    Coordinates are relative to the action point at (0,0,0). Its handle
    extends toward +Z (the synthetic microscope) while the nib points -Z.
    Reusing one mesh on the GPU avoids allocations during a mouse drag.
    """
    segments = 12
    rings = (
        (0.000, .009),
        (0.095, .011),
        (0.340, .020),
    )
    vertices = []
    normals = []
    faces = []
    for z, radius in rings:
        for i in range(segments):
            angle = i * math.tau / segments
            nx, ny = math.cos(angle), math.sin(angle)
            vertices.append((radius * nx, radius * ny, z))
            normals.append((nx, ny, 0.))
    tip = len(vertices)
    vertices.append((0., 0., -.026))
    normals.append((0., 0., -1.))
    end_center = len(vertices)
    vertices.append((0., 0., rings[-1][0]))
    normals.append((0., 0., 1.))
    for ring in range(len(rings)-1):
        for i in range(segments):
            following = (i + 1) % segments
            a, b = ring * segments + i, ring * segments + following
            c, d = (ring+1) * segments + i, (ring+1) * segments + following
            faces.extend(((a, b, c), (b, d, c)))
    for i in range(segments):
        next_i = (i + 1) % segments
        faces.append((tip, next_i, i))
        faces.append((end_center, (len(rings)-1)*segments+i,
                      (len(rings)-1)*segments+next_i))
    result = Mesh("synthetic_stylus", tuple(vertices), tuple(normals),
                  tuple(faces))
    result.validate()
    return result


def visible_stylus(controller: Surgery3DController) -> tuple[float, float, float] | None:
    """Return a safe render-only tip pose, or nothing for unsafe/inactive state.

    Never expose a previous phase's or paused case's tool pose. Validation
    prevents corrupt or nonfinite game values from reaching OpenGL uniforms.
    """
    game = controller.game
    if game.ending or game.paused or game.patient.alert:
        return None
    if controller.target_depth is None or controller.last_pose is None:
        return None
    p = controller.last_pose
    coords = (p.world_x, p.world_y, p.world_z)
    if not all(isinstance(x, (int, float)) and not isinstance(x, bool)
               and math.isfinite(x) and -1. <= x <= 1. for x in coords):
        return None
    if abs(p.world_z - controller.target_depth) > .055:
        return None
    if not (0. <= p.eye_x <= 1. and 0. <= p.eye_y <= 1.):
        return None
    return coords
