"""Depth-aware picking for the experimental 3D anatomy atlas.

Matches the perspective and rotations in gl_preview.VERTEX_SHADER.
This is read-only selection of synthetic shapes, NOT surgical collision
response or clinical instrument guidance. Transparent cornea and the closed
sclera backdrop are intentionally excluded from selection.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

from .geometry import Vec3

NEAR = 0.5
FAR = 16.0
PERSPECTIVE_SCALE = 2.3


@dataclass(frozen=True, slots=True)
class Ray:
    origin: Vec3
    direction: Vec3


@dataclass(frozen=True, slots=True)
class SurfaceHit:
    name: str
    distance: float
    position: Vec3


def _number(value: object, low: float, high: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("Expected finite numeric input")
    try:
        value = float(value)
    except (ValueError, OverflowError) as exc:
        raise ValueError("Expected finite numeric input") from exc
    if not math.isfinite(value) or not low <= value <= high:
        raise ValueError("Input outside supported range")
    return value


def _dimensions(width: int, height: int) -> tuple[int, int]:
    if (type(width) is not int or type(height) is not int
            or not 32 <= width <= 16384 or not 32 <= height <= 16384):
        raise ValueError("Unsupported viewport")
    return width, height


def _unrotate(point: Vec3, yaw: float, pitch: float) -> Vec3:
    """Inverse of the GLSL rotation: pitch about X after yaw about Y."""
    x, y, z = point
    cp, sp = math.cos(pitch), math.sin(pitch)
    cy, sy = math.cos(yaw), math.sin(yaw)
    yp = cp * y + sp * z
    zp = -sp * y + cp * z
    return (cy * x - sy * zp, yp, sy * x + cy * zp)


def _rotate(point: Vec3, yaw: float, pitch: float) -> Vec3:
    """Same rotation as the actual vertex shader."""
    x, y, z = point
    cy, sy = math.cos(yaw), math.sin(yaw)
    cp, sp = math.cos(pitch), math.sin(pitch)
    xp, zp = cy * x + sy * z, -sy * x + cy * z
    return (xp, cp * y - sp * zp, sp * y + cp * zp)


def screen_ray(x: object, y: object, width: int, height: int,
               yaw: object, pitch: object, zoom: object) -> Ray | None:
    """Convert Pygame top-left pixel coordinates to an object-space ray.

    For off-viewport *finite* coordinates return None (miss), not a clamped
    hit; malformed/nonfinite inputs raise ValueError. Uses pixel centres.
    """
    w, h = _dimensions(width, height)
    px = _number(x, -1e7, 1e7)
    py = _number(y, -1e7, 1e7)
    a = _number(yaw, -1.2, 1.2)
    b = _number(pitch, -.8, .8)
    distance = _number(zoom, 2.6, 5.0)
    if not (0 <= px < w and 0 <= py < h):
        return None
    ndc_x = 2.0 * (px + .5) / w - 1.0
    ndc_y = 1.0 - 2.0 * (py + .5) / h
    camera_origin: Vec3 = (0., 0., distance)
    camera_direction: Vec3 = (ndc_x * (w/h) / PERSPECTIVE_SCALE,
                              ndc_y / PERSPECTIVE_SCALE, -1.)
    origin = _unrotate(camera_origin, a, b)
    direction = _unrotate(camera_direction, a, b)
    norm = math.sqrt(sum(component * component for component in direction))
    return Ray(origin, tuple(c/norm for c in direction))


def project_point(point: Vec3, width: int, height: int,
                  yaw: object, pitch: object, zoom: object
                  ) -> tuple[float, float] | None:
    """Forward projection matching GPU shader; useful for test calibration."""
    w, h = _dimensions(width, height)
    a = _number(yaw, -1.2, 1.2)
    b = _number(pitch, -.8, .8)
    distance = _number(zoom, 2.6, 5.)
    if not isinstance(point, (tuple, list)) or len(point) != 3:
        raise ValueError("Invalid model point")
    p = tuple(_number(v, -10., 10.) for v in point)
    x, y, z = _rotate(p, a, b)
    depth = distance - z
    if not NEAR < depth < FAR:
        return None
    x_ndc = PERSPECTIVE_SCALE * x / (depth * (w/h))
    y_ndc = PERSPECTIVE_SCALE * y / depth
    return ((x_ndc + 1) * w / 2 - .5, (1 - y_ndc) * h / 2 - .5)


def _ellipsoid_hit(ray: Ray, radii: Vec3, center: Vec3,
                   label: str) -> SurfaceHit | None:
    q = tuple(ray.origin[i] - center[i] for i in range(3))
    scaled_d = [ray.direction[i]/radii[i] for i in range(3)]
    scaled_q = [q[i]/radii[i] for i in range(3)]
    A = sum(v*v for v in scaled_d)
    B = 2 * sum(scaled_q[i]*scaled_d[i] for i in range(3))
    C = sum(v*v for v in scaled_q) - 1
    disc = B*B - 4*A*C
    if disc < 0:
        return None
    root = math.sqrt(max(0., disc))
    valid = [t for t in ((-B-root)/(2*A), (-B+root)/(2*A)) if t >= NEAR]
    if not valid:
        return None
    t = min(valid)
    hit = tuple(ray.origin[i]+t*ray.direction[i] for i in range(3))
    return SurfaceHit(label, t, hit)


def _iris_hit(ray: Ray) -> SurfaceHit | None:
    if abs(ray.direction[2]) < 1e-10:
        return None
    t = (.03 - ray.origin[2]) / ray.direction[2]
    if t < NEAR:
        return None
    x = ray.origin[0]+t*ray.direction[0]
    y = ray.origin[1]+t*ray.direction[1]
    r2 = x*x + y*y
    if .29**2 <= r2 <= .66**2:
        return SurfaceHit("iris", t, (x,y,.03))
    return None


def pick_anatomy(x: object, y: object, width: int, height: int,
                 yaw: object, pitch: object, zoom: object,
                 phase: str = "CATARACT") -> SurfaceHit | None:
    """Pick nearest named selectable synthetic anatomy (not transparent cornea).

    World distance is along a normalized ray. Only the two selectable layers
    used by the current atlas are considered; this is not triangle-mesh
    picking and cannot be used as a surgical collision authority.
    """
    if not isinstance(phase, str) or phase not in {"CATARACT", "IOL"}:
        raise ValueError("Unknown synthetic atlas phase")
    ray = screen_ray(x,y,width,height,yaw,pitch,zoom)
    if ray is None:
        return None
    radii = (.43,.43,.18) if phase == "CATARACT" else (.41,.41,.06)
    inner = _ellipsoid_hit(ray, radii, (0.,0.,-.19),
                           "cloudy lens" if phase == "CATARACT" else "IOL")
    iris = _iris_hit(ray)
    hits = (hit for hit in (inner, iris) if hit is not None)
    return min(hits, key=lambda hit: hit.distance, default=None)
