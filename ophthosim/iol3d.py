"""Stylized foldable-IOL visual model and deterministic deployment timeline.

The shape, haptics and times are deliberately synthetic. This module is only
for non-clinical educational visualization; it does not specify a real implant,
clinical insertion technique or tissue contact forces. Only rendered imagery
changes: the authoritative Game state and scoring remain unmodified.
"""
from __future__ import annotations

from functools import lru_cache
import math

from .engine import Phase
from .geometry import Mesh, ellipsoid


@lru_cache(maxsize=1)
def foldable_iol_mesh() -> Mesh:
    """Combine a slim optical lens with two curved, tubular stylized haptics.

    Ring count and output size are fixed to bound allocations. Vertices lie
    in the visual eye's normalized model space. No clinical dimensions.
    """
    optic = ellipsoid("optic", (.36, .36, .045),
                      center=(0, 0, -.19), slices=32, stacks=12)
    vertices = list(optic.vertices)
    normals = list(optic.normals)
    faces = list(optic.faces)

    steps, sides = 22, 8
    for sign in (-1, 1):
        base = len(vertices)
        for k in range(steps + 1):
            t = k / steps
            # An intentionally schematic curved support. Both strands remain
            # within the unit sphere and are symmetric across the optical axis.
            x = sign * (.29 + .39*t - .07*t*t)
            y = sign * (.20 + .13*math.sin(math.pi*t) - .035*t)
            z = -.19 + .02*math.sin(math.pi*t)
            dx = sign * (.39 - .14*t)
            dy = sign * (.13*math.pi*math.cos(math.pi*t) - .035)
            length = math.hypot(dx, dy)
            nx, ny = -dy / length, dx / length
            for j in range(sides):
                a = 2*math.pi*j/sides
                radial = .013*math.cos(a)
                vz = .013*math.sin(a)
                vertices.append((x + radial*nx, y + radial*ny, z + vz))
                normals.append((math.cos(a)*nx, math.cos(a)*ny, math.sin(a)))
        for k in range(steps):
            for j in range(sides):
                a = base + k*sides+j
                b = base + k*sides+(j+1)%sides
                c = base + (k+1)*sides+j
                d = base + (k+1)*sides+(j+1)%sides
                faces.extend(((a,b,c),(b,d,c)))

    mesh = Mesh("iol", tuple(vertices), tuple(normals), tuple(faces))
    mesh.validate()
    return mesh


def iol_visual_deployment(game, duration_s: float = 1.5) -> float:
    """Visual state fraction 0→1 using simulation time, never wall-clock.

    In the IOL stage an undeployed object is shown. A successful placement
    moves the game to CLOSE; only then does the nonphysical unfolding animation
    begin. A paused simulation freezes this value with its time. All completed
    RECOVERY cases render the final fully unfolded appearance.
    """
    if not isinstance(duration_s, (int, float)) or isinstance(duration_s, bool):
        raise ValueError("Invalid synthetic deployment duration")
    try:
        d = float(duration_s)
    except (ValueError, OverflowError) as exc:
        raise ValueError("Invalid synthetic deployment duration") from exc
    if not math.isfinite(d) or not .1 <= d <= 30.:
        raise ValueError("Invalid synthetic deployment duration")
    if game.phase == Phase.IOL:
        return 0.
    if game.phase == Phase.RECOVERY:
        return 1.
    if game.phase != Phase.CLOSE:
        return 1.
    for event in reversed(game.events):
        if (event.get("kind") == "phase"
                and event.get("data", {}).get("to") == Phase.CLOSE.value):
            elapsed = max(0., min(d, game.time - event["sim_time_ms"] / 1000.))
            t = elapsed / d
            return round(t*t*(3.-2.*t), 6)
    # Defensive: tests may deliberately construct a phase without invoking
    # the engine transition. Avoid fabricating an insertion timeline.
    return 1.
