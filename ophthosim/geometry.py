"""Small, dependency-free normalized 3D anatomy mesh prototypes.

Meshes are graphical placeholders for a future GPU renderer, never clinical
anatomy. +Z faces the microscope. Meshes do not control game-state physics.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import TypeAlias

Vec3: TypeAlias = tuple[float, float, float]
Face: TypeAlias = tuple[int, int, int]


@dataclass(frozen=True, slots=True)
class Mesh:
    name: str
    vertices: tuple[Vec3, ...]
    normals: tuple[Vec3, ...]
    faces: tuple[Face, ...]

    def validate(self) -> None:
        if not self.vertices or len(self.vertices) != len(self.normals) or not self.faces:
            raise ValueError("Empty or inconsistent mesh")
        n = len(self.vertices)
        for vec in (*self.vertices, *self.normals):
            if len(vec) != 3 or not all(math.isfinite(v) for v in vec):
                raise ValueError("Mesh contains invalid vectors")
        for a, b, c in self.faces:
            if not (0 <= a < n and 0 <= b < n and 0 <= c < n):
                raise ValueError("Mesh has invalid face indices")
            if len({a, b, c}) != 3:
                raise ValueError("Mesh has duplicate vertex indices")


def _positive(value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("Expected positive finite scalar")
    try:
        f = float(value)
    except (OverflowError, ValueError) as exc:
        raise ValueError("Expected positive finite scalar") from exc
    if not math.isfinite(f) or not 0 < f <= 10:
        raise ValueError("Expected positive finite scalar <= 10")
    return f


def _coordinate(value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("Expected finite normalized coordinate")
    try:
        f = float(value)
    except (OverflowError, ValueError) as exc:
        raise ValueError("Expected finite normalized coordinate") from exc
    if not math.isfinite(f) or abs(f) > 10:
        raise ValueError("Expected finite normalized coordinate")
    return f


def _quality(slices: int, stacks: int) -> None:
    if (type(slices) is not int or not 8 <= slices <= 128
            or type(stacks) is not int or not 4 <= stacks <= 64):
        raise ValueError("Mesh resolution must be bounded")


def ellipsoid(name: str, radii: Vec3, center: Vec3 = (0, 0, 0),
              slices: int = 32, stacks: int = 16) -> Mesh:
    """Create a triangulated closed elliptical globe/lens surface."""
    _quality(slices, stacks)
    if len(radii) != 3 or len(center) != 3:
        raise ValueError("Expected three dimensional vectors")
    rx, ry, rz = map(_positive, radii)
    ox, oy, oz = map(_coordinate, center)
    vertices: list[Vec3] = []
    normals: list[Vec3] = []
    faces: list[Face] = []
    for i in range(stacks + 1):
        theta = math.pi * i / stacks
        st, ct = math.sin(theta), math.cos(theta)
        for j in range(slices + 1):
            phi = math.tau * j / slices
            ux, uy, uz = st * math.cos(phi), st * math.sin(phi), ct
            vertices.append((ox + rx * ux, oy + ry * uy, oz + rz * uz))
            nx, ny, nz = ux / rx, uy / ry, uz / rz
            norm = math.sqrt(nx * nx + ny * ny + nz * nz)
            normals.append((nx / norm, ny / norm, nz / norm))
    stride = slices + 1
    for i in range(stacks):
        for j in range(slices):
            a = i * stride + j
            b = a + 1
            c = a + stride
            d = c + 1
            if i:
                faces.append((a, c, b))
            if i < stacks - 1:
                faces.append((b, c, d))
    mesh = Mesh(name, tuple(vertices), tuple(normals), tuple(faces))
    mesh.validate()
    return mesh


def iris_annulus(inner: float = .29, outer: float = .66,
                 depth: float = .03, slices: int = 64) -> Mesh:
    """Flat eye-facing ring with an unobstructed pupil opening."""
    if type(slices) is not int or not 8 <= slices <= 128:
        raise ValueError("Invalid iris resolution")
    ri, ro = _positive(inner), _positive(outer)
    z = _coordinate(depth)
    if ri >= ro:
        raise ValueError("Iris inner radius must be smaller than outer")
    vertices: list[Vec3] = []
    faces: list[Face] = []
    for j in range(slices + 1):
        phi = math.tau * j / slices
        cp, sp = math.cos(phi), math.sin(phi)
        vertices.extend(((ro * cp, ro * sp, z), (ri * cp, ri * sp, z)))
    for j in range(slices):
        a, b = j * 2, (j + 1) * 2
        faces.extend(((a, b, a + 1), (b, b + 1, a + 1)))
    mesh = Mesh("iris", tuple(vertices), ((0., 0., 1.),) * len(vertices), tuple(faces))
    mesh.validate()
    return mesh


def cornea_dome(radius: float = .74, cap_angle: float = .95,
                center_z: float = -.15, slices: int = 48, stacks: int = 12) -> Mesh:
    """An optically simple front dome; no physical refraction model."""
    _quality(slices, stacks)
    r, angle, cz = _positive(radius), _positive(cap_angle), _coordinate(center_z)
    if angle >= math.pi / 2:
        raise ValueError("Corneal cap must face forward")
    vertices: list[Vec3] = []
    normals: list[Vec3] = []
    faces: list[Face] = []
    for i in range(stacks + 1):
        theta = angle * i / stacks
        for j in range(slices + 1):
            phi = math.tau * j / slices
            nx, ny, nz = (math.sin(theta) * math.cos(phi),
                          math.sin(theta) * math.sin(phi), math.cos(theta))
            vertices.append((r * nx, r * ny, cz + r * nz))
            normals.append((nx, ny, nz))
    stride = slices + 1
    for i in range(stacks):
        for j in range(slices):
            a = i * stride + j
            if i:
                faces.append((a, a + stride, a + 1))
            faces.append((a + 1, a + stride, a + stride + 1))
    mesh = Mesh("cornea", tuple(vertices), tuple(normals), tuple(faces))
    mesh.validate()
    return mesh


def anterior_eye_meshes() -> dict[str, Mesh]:
    """Deterministic normalized visual-geometry bundle for a future renderer."""
    return {
        "sclera": ellipsoid("sclera", (1, 1, .88), center=(0, 0, -.25)),
        "iris": iris_annulus(),
        "lens": ellipsoid("lens", (.43, .43, .18), center=(0, 0, -.19)),
        "iol": ellipsoid("iol", (.41, .41, .06), center=(0, 0, -.19)),
        "cornea": cornea_dome()
    }


def ray_sphere_distance(origin: Vec3, direction: Vec3,
                        center: Vec3, radius: float) -> float | None:
    """Return first non-negative ray hit distance, or None on no intersection."""
    r = _positive(radius)
    if any(len(v) != 3 for v in (origin, direction, center)):
        raise ValueError("Ray coordinates must be 3D")
    o = tuple(_coordinate(v) for v in origin)
    d = tuple(_coordinate(v) for v in direction)
    c = tuple(_coordinate(v) for v in center)
    a = sum(v*v for v in d)
    if a <= 1e-15:
        raise ValueError("Ray direction must be nonzero")
    q = tuple(o[i] - c[i] for i in range(3))
    b = 2 * sum(q[i] * d[i] for i in range(3))
    cc = sum(v*v for v in q) - r*r
    discriminant = b*b - 4*a*cc
    if discriminant < 0:
        return None
    root = math.sqrt(discriminant)
    distances = ((-b-root)/(2*a), (-b+root)/(2*a))
    return next((t for t in distances if t >= 0), None)
