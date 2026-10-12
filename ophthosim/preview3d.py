"""Software-projected interactive 3D *anatomy preview* for the Pygame UI.

This is a genuine 3D mesh with 3D rotation and perspective projection, drawn
as 2D triangles on Pygame's CPU surface. It is not a GPU surgical renderer,
optical model, surgical tissue physics, or validated medical geometry.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import math
from .geometry import ellipsoid, iris_annulus, cornea_dome, Mesh


@dataclass(frozen=True, slots=True)
class Face2D:
    points: tuple[tuple[int, int], tuple[int, int], tuple[int, int]]
    color: tuple[int, int, int]
    depth: float


@dataclass(frozen=True, slots=True)
class Line2D:
    a: tuple[int, int]
    b: tuple[int, int]


def _scalar(value: object, limit: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("Invalid preview value")
    try:
        result = float(value)
    except (OverflowError, ValueError) as exc:
        raise ValueError("Invalid preview value") from exc
    if not math.isfinite(result) or abs(result) > limit:
        raise ValueError("Invalid preview value")
    return result


@lru_cache(maxsize=1)
def preview_meshes() -> dict[str, Mesh]:
    """Cache low-poly presentation assets; never regenerate them per frame."""
    return {
        "iris": iris_annulus(inner=.31, outer=.69, slices=48),
        "lens": ellipsoid("lens", (.43, .43, .18),
                          center=(0., 0., -.19), slices=32, stacks=12),
        "iol": ellipsoid("iol", (.42, .42, .055),
                         center=(0., 0., -.19), slices=32, stacks=10),
        "cornea": cornea_dome(slices=32, stacks=8),
    }


def rotate(point: tuple[float, float, float], yaw: float, pitch: float
           ) -> tuple[float, float, float]:
    """Yaw about Y, then pitch about X; +Z points toward the observer."""
    x, y, z = point
    cy, sy = math.cos(yaw), math.sin(yaw)
    cp, sp = math.cos(pitch), math.sin(pitch)
    xx, zz = cy * x + sy * z, -sy * x + cy * z
    return (xx, cp * y - sp * zz, sp * y + cp * zz)


def project(point: tuple[float, float, float],
            yaw: float, pitch: float,
            center: tuple[int, int] = (640, 366),
            focal: float = 690.) -> tuple[int, int]:
    """Project normalized 3D eye coordinates onto the microscope panel."""
    yaw, pitch = _scalar(yaw, 1.2), _scalar(pitch, .9)
    focal = _scalar(focal, 3000.)
    if focal <= 0:
        raise ValueError("Invalid focal distance")
    if len(center) != 2 or any(type(q) is not int or abs(q) > 10000 for q in center):
        raise ValueError("Invalid viewport center")
    if len(point) != 3:
        raise ValueError("Invalid point")
    xyz = tuple(_scalar(v, 10.) for v in point)
    x, y, z = rotate(xyz, yaw, pitch)
    depth = 3.65 - z
    if depth <= .001:
        raise ValueError("Geometry is behind the camera")
    return (round(center[0] + focal * x / depth),
            round(center[1] - focal * y / depth))


def build_preview(phase: str, opacity: float, alignment: float,
                  yaw: float = 0., pitch: float = 0.,
                  center: tuple[int, int] = (640, 366)
                  ) -> tuple[list[Face2D], list[Line2D]]:
    """Build stable painter-sorted polygons and optional cornea contour lines.

    Does not affect clinical-state, tool hit testing, or the scoring engine.
    """
    yaw, pitch = _scalar(yaw, 1.2), _scalar(pitch, .9)
    opacity, alignment = _scalar(opacity, 1.), _scalar(alignment, 1.)
    if not 0 <= opacity <= 1 or not 0 <= alignment <= 1:
        raise ValueError("Normalized state required")
    if phase not in {"PREOP", "ANESTHESIA", "ENTRY", "CAPSULE",
                     "PHACO", "CORTEX", "IOL", "CLOSE", "RECOVERY", "ABORTED"}:
        raise ValueError("Unknown phase")
    meshes = preview_meshes()
    iol = phase in {"IOL", "CLOSE", "RECOVERY"}
    # Synthetic alignment feedback: lateral offset is purely visual.
    offset = (.18 * (1 - alignment), 0., 0.) if iol else (0., 0., 0.)
    tris: list[Face2D] = []
    for name in ("iris", "iol" if iol else "lens"):
        mesh = meshes[name]
        translated = [tuple(v[i] + (offset[i] if name == "iol" else 0.)
                            for i in range(3)) for v in mesh.vertices]
        xyz = [rotate(v, yaw, pitch) for v in translated]
        screen = [project(v, 0., 0., center) for v in xyz]
        for ia, ib, ic in mesh.faces:
            na, nb, nc = mesh.normals[ia], mesh.normals[ib], mesh.normals[ic]
            nx = (na[0] + nb[0] + nc[0]) / 3
            ny = (na[1] + nb[1] + nc[1]) / 3
            nz = (na[2] + nb[2] + nc[2]) / 3
            rn = rotate((nx, ny, nz), yaw, pitch)
            if rn[2] <= .025:
                continue
            diffuse = max(0., min(1., .32 + .52 * (rn[0]*-.36 + rn[1]*.38 + rn[2]*.86)))
            if name == "iris":
                base = (35, 121, 135)
            elif iol:
                base = (104, 204, 227)
            else:
                base = (int(94 + 118 * opacity),
                        int(92 + 102 * opacity), int(103 + 49 * opacity))
            color = tuple(min(255, max(0, round(c * diffuse))) for c in base)
            tris.append(Face2D((screen[ia], screen[ib], screen[ic]),
                               color, (xyz[ia][2] + xyz[ib][2] + xyz[ic][2]) / 3))
    tris.sort(key=lambda t: t.depth)
    # Sparse dome meridians and contour arcs show camera-angle depth without
    # opaque triangles covering the lens. This is NOT optical refraction.
    dome = meshes["cornea"]
    lines: list[Line2D] = []
    stride = 33  # 32 slices + repeated seam vertex
    rows = len(dome.vertices) // stride
    for i in range(1, rows):
        for j in range(0, 32, 4):
            a = project(dome.vertices[i*stride+j], yaw, pitch, center)
            b = project(dome.vertices[i*stride+j+4], yaw, pitch, center)
            lines.append(Line2D(a, b))
    return tris, lines


def draw_preview(pygame, surface, phase: str, opacity: float,
                 alignment: float, yaw: float, pitch: float) -> None:
    """Draw the anatomy preview inside the existing operating field."""
    cx, cy = 640, 366
    pygame.draw.circle(surface, (13, 36, 47), (cx, cy), 224)
    pygame.draw.circle(surface, (136, 164, 177), (cx, cy), 219)
    pygame.draw.circle(surface, (26, 51, 67), (cx, cy), 201)
    faces, lines = build_preview(phase, opacity, alignment, yaw, pitch)
    for face in faces:
        pygame.draw.polygon(surface, face.color, face.points)
    for line in lines:
        pygame.draw.line(surface, (93, 158, 173), line.a, line.b, 1)
    pygame.draw.circle(surface, (104, 194, 209), (cx, cy), 227, 2)
