"""Procedural 3D operating room around the synthetic cataract case.

Pure Python geometry (no OpenGL needed): room, operating table, draped
patient, floor-stand microscope, vital-signs monitor, phaco console, video
monitor, instrument tray with the 15 game instruments, a seated surgeon whose
gloved hands hold the instrument currently in use, and a scrub nurse.

Units are metres with +y up. The patient lies along +z with the head near
z = 0; the surgeon sits at the head end (-z). All equipment is generic: no
manufacturer names, logos or device settings. Visual only: nothing here can
change the Game, a score or a replay.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
import math

from .geometry import Mesh

Vec = tuple[float, float, float]

# Colours are sRGB (0..1); the shader converts to linear light.
MATERIALS: dict[str, tuple[Vec, float, float]] = {   # colour, specular, emission
    "floor": ((.50, .55, .57), .18, 0.),
    "floor_line": ((.40, .44, .46), .1, 0.),
    "floor_shadow": ((.36, .40, .42), 0., 0.),
    "accent": ((.20, .52, .58), .1, 0.),
    "lips": ((.72, .45, .42), .2, 0.),
    "wall": ((.78, .83, .85), .04, 0.),
    "wall_panel": ((.70, .76, .79), .1, 0.),
    "ceiling": ((.86, .88, .90), 0., 0.),
    "ceiling_light": ((.95, .97, 1.), 0., .9),
    "window": ((.16, .24, .30), .8, 0.),
    "cabinet": ((.80, .83, .85), .35, 0.),
    "steel": ((.72, .74, .77), .95, 0.),
    "dark": ((.13, .14, .16), .35, 0.),
    "device": ((.91, .92, .93), .45, 0.),
    "device_trim": ((.55, .60, .66), .5, 0.),
    "rubber": ((.07, .07, .08), .15, 0.),
    "gown": ((.22, .42, .70), .06, 0.),
    "drape": ((.19, .40, .68), .06, 0.),
    "drape_dark": ((.14, .30, .55), .06, 0.),
    "skin": ((.87, .69, .58), .12, 0.),
    "glove": ((.94, .89, .77), .3, 0.),
    "cap": ((.30, .52, .80), .05, 0.),
    "mask": ((.70, .83, .92), .05, 0.),
    "hair": ((.12, .09, .07), .2, 0.),
    "pad": ((.20, .22, .26), .2, 0.),
    "blue_plastic": ((.14, .42, .84), .5, 0.),
    "white_plastic": ((.95, .95, .95), .4, 0.),
    "tubing": ((.86, .91, .93), .4, 0.),
    "glass": ((.74, .87, .94), .9, 0.),
    "lamp_led": ((1., 1., .96), 0., 1.6),
    "lamp_body": ((.88, .90, .92), .5, 0.),
    "screen_bezel": ((.10, .11, .13), .5, 0.),
    "status_led": ((.30, .95, .55), 0., 1.2),
}

ROOM = (-3.2, 3.2, 0., 3.0, -2.7, 3.6)            # x0, x1, y0, y1, z0, z1
EYE_POS: Vec = (-.032, 1.018, .03)                 # patient's right eye
EYE_RADIUS = .024                                   # visible eye + speculum disc
EYE_LIFT = .006                                     # disc height above the face
TABLE_TOP = .82


# --- small vector helpers -------------------------------------------------------
def _sub(a: Vec, b: Vec) -> Vec:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _add(a: Vec, b: Vec) -> Vec:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _scale(a: Vec, s: float) -> Vec:
    return (a[0] * s, a[1] * s, a[2] * s)


def _dot(a: Vec, b: Vec) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a: Vec, b: Vec) -> Vec:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _norm(a: Vec) -> Vec:
    length = math.sqrt(_dot(a, a))
    if length < 1e-12:
        raise ValueError("Zero-length vector")
    return (a[0] / length, a[1] / length, a[2] / length)


Mat3 = tuple[Vec, Vec, Vec]          # rows
IDENTITY: Mat3 = ((1., 0., 0.), (0., 1., 0.), (0., 0., 1.))


def _apply(m: Mat3, v: Vec) -> Vec:
    return (_dot(m[0], v), _dot(m[1], v), _dot(m[2], v))


def _matmul(a: Mat3, b: Mat3) -> Mat3:
    cols = list(zip(*b))
    return tuple(tuple(_dot(row, col) for col in cols) for row in a)   # type: ignore[return-value]


def euler(rx: float = 0., ry: float = 0., rz: float = 0.) -> Mat3:
    """Rotation R = Ry · Rx · Rz (yaw last), radians."""
    cx, sx, cy, sy, cz, sz = (math.cos(rx), math.sin(rx), math.cos(ry), math.sin(ry),
                              math.cos(rz), math.sin(rz))
    mx = ((1., 0., 0.), (0., cx, -sx), (0., sx, cx))
    my = ((cy, 0., sy), (0., 1., 0.), (-sy, 0., cy))
    mz = ((cz, -sz, 0.), (sz, cz, 0.), (0., 0., 1.))
    return _matmul(my, _matmul(mx, mz))


def align_y(direction: Vec) -> Mat3:
    """Rotation taking +y onto `direction` (Rodrigues)."""
    d = _norm(direction)
    c = d[1]
    if c > 1 - 1e-9:
        return IDENTITY
    if c < -1 + 1e-9:
        return ((1., 0., 0.), (0., -1., 0.), (0., 0., -1.))
    axis = _norm(_cross((0., 1., 0.), d))
    s = math.sqrt(max(0., 1 - c * c))
    x, y, z = axis
    t = 1 - c
    return ((t * x * x + c, t * x * y - s * z, t * x * z + s * y),
            (t * x * y + s * z, t * y * y + c, t * y * z - s * x),
            (t * x * z - s * y, t * y * z + s * x, t * z * z + c))


# --- geometry accumulator -------------------------------------------------------------
@dataclass
class Geo:
    vertices: list[Vec] = field(default_factory=list)
    normals: list[Vec] = field(default_factory=list)
    faces: list[tuple[int, int, int]] = field(default_factory=list)

    def extend(self, other: "Geo", rotation: Mat3 = IDENTITY, scale: Vec = (1., 1., 1.),
               offset: Vec = (0., 0., 0.)) -> "Geo":
        base = len(self.vertices)
        sx, sy, sz = scale
        for (x, y, z), (nx, ny, nz) in zip(other.vertices, other.normals):
            self.vertices.append(_add(_apply(rotation, (x * sx, y * sy, z * sz)), offset))
            n = (nx / sx, ny / sy, nz / sz)
            self.normals.append(_norm(_apply(rotation, n)))
        self.faces.extend((a + base, b + base, c + base) for a, b, c in other.faces)
        return self

    def mesh(self, name: str) -> Mesh:
        mesh = Mesh(name, tuple(self.vertices), tuple(self.normals), tuple(self.faces))
        mesh.validate()
        return mesh


@lru_cache(maxsize=None)
def box() -> Geo:
    """Unit cube centred at the origin (flat-shaded faces)."""
    g = Geo()
    for axis in range(3):
        for sign in (-1., 1.):
            n = [0., 0., 0.]
            n[axis] = sign
            u = [0., 0., 0.]
            v = [0., 0., 0.]
            u[(axis + 1) % 3] = .5
            v[(axis + 2) % 3] = .5
            centre = [c * .5 for c in n]
            base = len(g.vertices)
            for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                g.vertices.append(tuple(centre[i] + a * u[i] + b * v[i] for i in range(3)))
                g.normals.append(tuple(n))
            if sign > 0:
                g.faces += [(base, base + 1, base + 2), (base, base + 2, base + 3)]
            else:
                g.faces += [(base, base + 2, base + 1), (base, base + 3, base + 2)]
    return g


@lru_cache(maxsize=None)
def cylinder(segments: int = 20, top: float = 1., caps: bool = True) -> Geo:
    """Unit-radius cylinder (or cone with `top` radius) along +y, y in 0..1."""
    g = Geo()
    slope = 1. - top
    for i in range(segments + 1):
        a = math.tau * i / segments
        ca, sa = math.cos(a), math.sin(a)
        n = _norm((ca, slope, sa))
        g.vertices += [(ca, 0., sa), (ca * top, 1., sa * top)]
        g.normals += [n, n]
    for i in range(segments):
        a, b = 2 * i, 2 * i + 2
        g.faces += [(a, a + 1, b), (b, a + 1, b + 1)]
    if caps:
        for y, r, ny in ((0., 1., -1.), (1., top, 1.)):
            if r <= 1e-6:
                continue
            centre = len(g.vertices)
            g.vertices.append((0., y, 0.))
            g.normals.append((0., ny, 0.))
            for i in range(segments):
                a = math.tau * i / segments
                g.vertices.append((math.cos(a) * r, y, math.sin(a) * r))
                g.normals.append((0., ny, 0.))
            for i in range(segments):
                p, q = centre + 1 + i, centre + 1 + (i + 1) % segments
                g.faces.append((centre, q, p) if ny > 0 else (centre, p, q))
    return g


@lru_cache(maxsize=None)
def sphere(slices: int = 20, stacks: int = 12) -> Geo:
    g = Geo()
    for i in range(stacks + 1):
        t = math.pi * i / stacks
        for j in range(slices + 1):
            p = math.tau * j / slices
            v = (math.sin(t) * math.cos(p), math.cos(t), math.sin(t) * math.sin(p))
            g.vertices.append(v)
            g.normals.append(v)
    stride = slices + 1
    for i in range(stacks):
        for j in range(slices):
            a = i * stride + j
            b, c, d = a + 1, a + stride, a + stride + 1
            if i:
                g.faces.append((a, b, c))
            if i < stacks - 1:
                g.faces.append((b, d, c))
    return g


@lru_cache(maxsize=None)
def torus(major: float = 1., minor: float = .1, segments: int = 32, sides: int = 8) -> Geo:
    """Ring in the xz plane."""
    g = Geo()
    for i in range(segments + 1):
        a = math.tau * i / segments
        ca, sa = math.cos(a), math.sin(a)
        for j in range(sides + 1):
            b = math.tau * j / sides
            n = (ca * math.cos(b), math.sin(b), sa * math.cos(b))
            g.vertices.append((ca * (major + minor * math.cos(b)), minor * math.sin(b),
                               sa * (major + minor * math.cos(b))))
            g.normals.append(n)
    stride = sides + 1
    for i in range(segments):
        for j in range(sides):
            a = i * stride + j
            g.faces += [(a, a + 1, a + stride), (a + 1, a + stride + 1, a + stride)]
    return g


class Scene:
    """Geometry grouped by material (one draw call per material)."""

    def __init__(self) -> None:
        self.parts: dict[str, Geo] = {}

    def _geo(self, material: str) -> Geo:
        if material not in MATERIALS:
            raise ValueError(f"Unknown material {material!r}")
        return self.parts.setdefault(material, Geo())

    def box(self, material: str, size: Vec, centre: Vec, rotation: Mat3 = IDENTITY) -> None:
        self._geo(material).extend(box(), rotation, size, centre)

    def ellipsoid(self, material: str, radii: Vec, centre: Vec,
                  rotation: Mat3 = IDENTITY, detail: tuple[int, int] = (20, 12)) -> None:
        self._geo(material).extend(sphere(*detail), rotation, radii, centre)

    def rod(self, material: str, a: Vec, b: Vec, radius: float, *, top: float = 1.,
            segments: int = 16, caps: bool = True) -> None:
        """Cylinder (or cone) from point a to point b."""
        d = _sub(b, a)
        length = math.sqrt(_dot(d, d))
        if length < 1e-9:
            return
        self._geo(material).extend(cylinder(segments, top, caps), align_y(d),
                                   (radius, length, radius), a)

    def ring(self, material: str, centre: Vec, radius: float, thickness: float,
             rotation: Mat3 = IDENTITY) -> None:
        self._geo(material).extend(torus(1., thickness / radius), rotation,
                                   (radius, radius, radius), centre)

    def merge(self, other: "Scene") -> "Scene":
        for material, geo in other.parts.items():
            self._geo(material).extend(geo)
        return self

    def meshes(self) -> dict[str, Mesh]:
        return {material: geo.mesh(material) for material, geo in self.parts.items()
                if geo.faces}


# --- textured screens -------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class ScreenQuad:
    """A textured display: centre, facing direction (yaw/pitch), size."""
    name: str
    centre: Vec
    yaw: float           # 0 faces +z
    pitch: float         # tilt back (radians)
    width: float
    height: float

    @property
    def basis(self) -> tuple[Vec, Vec, Vec]:
        rotation = euler(-self.pitch, self.yaw, 0.)
        return (_apply(rotation, (1., 0., 0.)), _apply(rotation, (0., 1., 0.)),
                _apply(rotation, (0., 0., 1.)))

    def corners(self) -> tuple[Vec, Vec, Vec, Vec]:
        """Bottom-left, bottom-right, top-left, top-right."""
        right, up, _ = self.basis
        hw, hh = self.width / 2, self.height / 2
        c = self.centre
        return (_add(c, _add(_scale(right, -hw), _scale(up, -hh))),
                _add(c, _add(_scale(right, hw), _scale(up, -hh))),
                _add(c, _add(_scale(right, -hw), _scale(up, hh))),
                _add(c, _add(_scale(right, hw), _scale(up, hh))))

    def viewpoint(self, distance: float) -> tuple[Vec, Vec]:
        """Camera position in front of the screen and its target."""
        _, up, normal = self.basis
        return _add(self.centre, _add(_scale(normal, distance), _scale(up, .02))), self.centre


SCREENS: dict[str, ScreenQuad] = {
    "vitals": ScreenQuad("vitals", (-1.02, 1.62, -.28), math.radians(48), math.radians(6), .46, .32),
    "phaco": ScreenQuad("phaco", (.92, 1.30, -.02), math.radians(-38), math.radians(18), .36, .27),
    "video": ScreenQuad("video", (.82, 1.84, -.98), math.radians(-24), math.radians(4), .86, .49),
}
SCREEN_PIXELS = {"vitals": (512, 356), "phaco": (480, 360), "video": (768, 432), "eye": (512, 512)}


def eye_disc(segments: int = 48) -> tuple[list[Vec], list[tuple[float, float]], list[tuple[int, int, int]]]:
    """Textured disc on the patient's eye, facing +y. The texture's top edge
    points away from the surgeon (+z), so the surgeon sees it upright."""
    cx, cy, cz = EYE_POS
    vertices = [(cx, cy, cz)]
    uvs = [(.5, .5)]
    for i in range(segments):
        a = math.tau * i / segments
        x, z = math.cos(a), math.sin(a)
        vertices.append((cx - x * EYE_RADIUS, cy, cz + z * EYE_RADIUS))
        # Mirror x: seen from +y with +z up-screen, image right is -x.
        uvs.append((.5 + .5 * x, .5 - .5 * z))
    faces = [(0, 1 + (i + 1) % segments, 1 + i) for i in range(segments)]
    return vertices, uvs, faces


# --- instruments ---------------------------------------------------------------------------
TOOL_LENGTH = .12


def instrument(name: str) -> Scene:
    """Generic synthetic instrument in local space: the tip at the origin,
    the handle along +x. Shapes are recognisable stand-ins, not device CAD."""
    s = Scene()
    x = lambda a: (a, 0., 0.)   # noqa: E731 - local axis helper
    if name in ("keratome", "sideport"):
        s.rod("steel", x(.018), x(TOOL_LENGTH), .0035, segments=10)
        s.rod("device_trim", x(.06), x(.10), .0042, segments=10)
        width = .0032 if name == "keratome" else .0016
        s.box("steel", (.016, .0006, width), x(.009))
        s.rod("steel", x(.017), x(.022), .0012, segments=8)
    elif name in ("ovd_cannula", "hydro_cannula", "irrigation"):
        body = {"ovd_cannula": "white_plastic", "hydro_cannula": "glass", "irrigation": "glass"}[name]
        s.rod("steel", (0., .004, 0.), x(.022), .0005, segments=6)
        s.rod("steel", x(.022), x(.028), .0016, segments=8)
        s.rod(body, x(.028), x(.095), .0055, segments=14)
        s.rod("blue_plastic" if name == "hydro_cannula" else "white_plastic",
              x(.095), x(.125), .0018, segments=8)
        s.rod("white_plastic", x(.125), x(.128), .007, segments=14)
    elif name == "cystotome":
        s.rod("steel", (0., -.002, 0.), x(.002), .0004, segments=6)
        s.rod("steel", x(.002), x(.03), .0005, segments=6)
        s.rod("blue_plastic", x(.03), x(.036), .0018, segments=8)
        s.rod("white_plastic", x(.036), x(.10), .0045, segments=12)
    elif name in ("forceps", "suture"):
        for side in (-1, 1):
            s.rod("steel", (0., 0., side * .0006), (TOOL_LENGTH * .9, 0., side * .004), .0011,
                  segments=6)
        s.box("steel", (.012, .002, .009), x(TOOL_LENGTH * .9))
        if name == "suture":
            s.ring("dark", (0., 0., .002), .004, .0004, euler(math.pi / 2, 0., 0.))
    elif name in ("phaco", "ia", "cautery"):
        radius = {"phaco": .0072, "ia": .0058, "cautery": .005}[name]
        s.rod("steel", x(0.), x(.016), .0011 if name == "phaco" else .0009, segments=8)
        s.rod("tubing" if name == "phaco" else "steel", x(.016), x(.026), radius * .45,
              top=1.5, segments=12)
        s.rod("device" if name != "cautery" else "blue_plastic", x(.026), x(.13), radius,
              segments=18)
        s.rod("device_trim", x(.06), x(.07), radius * 1.06, segments=18)
        s.rod("tubing" if name != "cautery" else "dark", x(.13), x(.17), .0025, segments=8)
    elif name in ("injector", "ctr"):
        s.rod("white_plastic", x(0.), x(.012), .0014, top=2.2, segments=10)
        s.rod("white_plastic", x(.012), x(.10), .0062, segments=16)
        s.rod("steel", x(.10), x(.14), .0018, segments=8)
        s.rod("white_plastic", x(.14), x(.145), .008, segments=16)
        if name == "ctr":
            s.ring("glass", x(-.006), .005, .0004)
    elif name == "iol_hook":
        s.rod("steel", (0., -.0025, 0.), x(.003), .0004, segments=6)
        s.rod("steel", x(.003), x(.04), .0006, segments=6)
        s.rod("steel", x(.04), x(TOOL_LENGTH), .003, segments=10)
    elif name == "iris_hooks":
        for k in range(4):
            z = (k - 1.5) * .006
            s.rod("blue_plastic", (0., 0., z), (.03, 0., z), .0005, segments=6)
            s.rod("blue_plastic", (0., 0., z), (0., -.003, z), .0004, segments=6)
        s.box("white_plastic", (.04, .004, .03), x(.05))
    else:
        raise ValueError(f"Unknown instrument {name!r}")
    return s


def place_instrument(scene: Scene, name: str, tip: Vec, handle_dir: Vec,
                     roll: float = 0.) -> None:
    """Add instrument `name` with its tip at `tip`, handle along `handle_dir`."""
    d = _norm(handle_dir)
    # +x onto d: align +y to d, then turn the x axis into y first.
    rotation = _matmul(align_y(d), euler(0., roll, -math.pi / 2)) if roll else \
        _matmul(align_y(d), ((0., -1., 0.), (1., 0., 0.), (0., 0., 1.)))
    for material, geo in instrument(name).parts.items():
        scene._geo(material).extend(geo, rotation, (1., 1., 1.), tip)


# --- people -----------------------------------------------------------------------------
def _hand(scene: Scene, wrist: Vec, grip: Vec) -> None:
    """Gloved hand in a pencil grip from `wrist` to the instrument `grip`."""
    d = _sub(grip, wrist)
    mid = _add(wrist, _scale(d, .45))
    scene.ellipsoid("glove", (.026, .036, .019), mid, align_y(d))
    side = _norm(_cross(d, (0., 1., 0.)))
    for k, (spread, lift) in enumerate(((-.012, .006), (0., .010), (.012, .006))):
        base = _add(mid, _add(_scale(side, spread), (0., lift * .5, 0.)))
        tip = _add(grip, _add(_scale(side, spread * .35), (0., .004 + lift * .2, 0.)))
        scene.rod("glove", base, tip, .0075 - .001 * k, segments=10)
        scene.ellipsoid("glove", (.0072, .0072, .0072), tip, detail=(10, 6))
    thumb = _add(mid, _add(_scale(side, -.022), (0., -.008, 0.)))
    scene.rod("glove", thumb, _add(grip, _scale(side, -.006)), .0082, segments=10)
    scene.ellipsoid("glove", (.008, .008, .008), _add(grip, _scale(side, -.006)), detail=(10, 6))


def _person_head(scene: Scene, centre: Vec, facing: float, *, cap: str = "cap") -> None:
    rot = euler(0., facing, 0.)
    scene.ellipsoid("skin", (.085, .105, .095), centre, rot)
    scene.ellipsoid(cap, (.094, .08, .1), _add(centre, (0., .035, 0.)), rot)
    scene.ellipsoid(cap, (.09, .085, .07), _add(centre, _apply(rot, (0., .005, -.035))), rot)
    front = _apply(rot, (0., 0., 1.))
    scene.box("mask", (.13, .075, .03), _add(_add(centre, _scale(front, .085)), (0., -.03, 0.)), rot)
    for side in (-1, 1):            # eyes above the mask
        eye = _add(_add(centre, _scale(front, .083)),
                   _add(_scale(_apply(rot, (1., 0., 0.)), side * .03), (0., .018, 0.)))
        scene.ellipsoid("dark", (.009, .006, .004), eye, rot, detail=(10, 6))


def surgeon(tool: str | None, active_phase: bool) -> Scene:
    """Seated surgeon at the head end, looking into the microscope; the right
    hand holds `tool` with its tip at the eye."""
    s = Scene()
    cx, cz = 0., -.64
    # Stool.
    s.rod("dark", (cx, .52, cz), (cx, .58, cz), .22, segments=24)
    s.rod("steel", (cx, .1, cz), (cx, .52, cz), .03)
    for k in range(5):
        a = math.tau * k / 5
        foot = (cx + .26 * math.cos(a), .05, cz + .26 * math.sin(a))
        s.rod("steel", (cx, .1, cz), foot, .015, segments=8)
        s.ellipsoid("rubber", (.025, .025, .025), foot, detail=(10, 6))
    # Legs (gown trousers) and shoes.
    for side in (-1, 1):
        hip = (cx + side * .1, .62, cz + .02)
        knee = (cx + side * .13, .6, cz + .42)
        s.rod("gown", hip, knee, .065)
        s.rod("gown", knee, (cx + side * .13, .08, cz + .45), .055)
        s.box("dark", (.1, .07, .26), (cx + side * .13, .035, cz + .5))
    # Torso leaning towards the eyepieces.
    lean = euler(.22, 0., 0.)
    s.ellipsoid("gown", (.2, .31, .14), (cx, .92, cz + .04), lean)
    s.rod("gown", (cx, 1.16, cz + .09), (cx, 1.25, cz + .13), .05)
    head = (cx, 1.355, cz + .17)
    _person_head(s, head, 0.)
    # Arms to the hands at the patient's head.
    tool_name = tool or "phaco"
    right_grip = _add(EYE_POS, (-.055, .045, -.075))
    left_grip = _add(EYE_POS, (.075, .04, -.06))
    for side, grip in ((-1, right_grip), (1, left_grip)):
        shoulder = (cx + side * .2, 1.14, cz + .1)
        elbow = (cx + side * .25, .99, cz + .36)
        wrist = _add(grip, (side * .02, .03, -.11))
        s.ellipsoid("gown", (.07, .07, .07), shoulder, detail=(14, 8))
        s.rod("gown", shoulder, elbow, .055)
        s.rod("gown", elbow, wrist, .045)
        cuff = _norm(_sub(wrist, elbow))       # glove cuff overlaps the sleeve end
        s.rod("glove", _add(wrist, _scale(cuff, -.03)), _add(wrist, _scale(cuff, .012)), .036)
        _hand(s, wrist, grip)
    if tool is not None:
        tip = _add(EYE_POS, (-.012, .003, -.006))
        place_instrument(s, tool_name, tip, _sub(right_grip, tip))
    if active_phase:
        # Second instrument (chopper) in the left hand through the side port.
        tip = _add(EYE_POS, (.008, .003, -.01))
        s.rod("steel", tip, _add(tip, (.02, .012, -.012)), .0006, segments=6)
        s.rod("steel", _add(tip, (.02, .012, -.012)), _add(left_grip, (.02, .01, -.02)), .0028,
              segments=10)
    return s


def nurse() -> Scene:
    s = Scene()
    x, z = 1.12, 1.0
    for side in (-1, 1):
        s.rod("gown", (x, .06, z + side * .09), (x, .9, z + side * .08), .07)
        s.box("dark", (.24, .07, .1), (x - .05, .035, z + side * .09))
    s.ellipsoid("gown", (.15, .36, .22), (x, 1.18, z))
    head = (x - .02, 1.63, z)
    _person_head(s, head, -math.pi / 2)
    for side in (-1, 1):
        shoulder = (x, 1.42, z + side * .2)
        elbow = (x - .12, 1.16, z + side * .24)
        hand = (x - .36, 1.08, z + side * .1 - .25)
        s.rod("gown", shoulder, elbow, .05)
        s.rod("gown", elbow, hand, .042)
        s.ellipsoid("glove", (.045, .022, .03), hand, detail=(12, 8))
    return s


# --- the room ---------------------------------------------------------------------------------
def _room(s: Scene) -> None:
    x0, x1, y0, y1, z0, z1 = ROOM
    s.box("floor", (x1 - x0, .02, z1 - z0), ((x0 + x1) / 2, -.01, (z0 + z1) / 2))
    for k in range(int(x0 / .6), int(x1 / .6) + 1):
        s.box("floor_line", (.008, .002, z1 - z0), (k * .6, .001, (z0 + z1) / 2))
    for k in range(int(z0 / .6), int(z1 / .6) + 1):
        s.box("floor_line", (x1 - x0, .002, .008), ((x0 + x1) / 2, .001, k * .6))
    s.box("ceiling", (x1 - x0, .02, z1 - z0), ((x0 + x1) / 2, y1 + .01, (z0 + z1) / 2))
    for x in (-1.6, 0., 1.6):
        for z in (-1.4, .6, 2.6):
            s.box("ceiling_light", (1.1, .01, .55), (x, y1 - .005, z))
    walls = (((.02, y1, z1 - z0), (x0 - .01, y1 / 2, (z0 + z1) / 2)),
             ((.02, y1, z1 - z0), (x1 + .01, y1 / 2, (z0 + z1) / 2)),
             ((x1 - x0, y1, .02), ((x0 + x1) / 2, y1 / 2, z0 - .01)),
             ((x1 - x0, y1, .02), ((x0 + x1) / 2, y1 / 2, z1 + .01)))
    for size, centre in walls:
        s.box("wall", size, centre)
    # Teal accent band and dark skirting along the walls.
    for y, h, material in ((1.05, .08, "accent"), (.06, .12, "dark")):
        s.box(material, (.025, h, z1 - z0), (x0 + .002, y, (z0 + z1) / 2))
        s.box(material, (.025, h, z1 - z0), (x1 - .002, y, (z0 + z1) / 2))
        s.box(material, (x1 - x0, h, .025), ((x0 + x1) / 2, y, z1 - .002))
    # Soft contact shadows under the furniture (flat darker floor patches).
    for centre, radii in (((0., .95), (.55, 1.25)), ((-1.0, -.55), (.42, .42)),
                          ((.95, .1), (.36, .38)), ((0., -.62), (.34, .34)),
                          ((1.12, 1.0), (.3, .3)), ((1.0, .62), (.3, .3))):
        s.ellipsoid("floor_shadow", (radii[0], .0015, radii[1]), (centre[0], .0005, centre[1]),
                    detail=(28, 4))
    # Wall panels, cabinets with steel handles, a dark observation window.
    for k in range(5):
        x = -2.4 + k * 1.2
        s.box("cabinet", (1.1, 1.9, .45), (x, .95, z0 + .23))
        s.box("wall_panel", (1.08, .02, .44), (x, 1.0, z0 + .23))
        s.rod("steel", (x - .35, 1.35, z0 + .47), (x - .35, .65, z0 + .47), .008, segments=8)
        s.rod("steel", (x + .35, 1.35, z0 + .47), (x + .35, .65, z0 + .47), .008, segments=8)
    s.box("window", (.02, .9, 1.8), (x1 - .005, 1.7, -.4))
    s.box("wall_panel", (.03, 1.0, 1.9), (x1 - .01, 1.7, -.4))
    for k in range(3):
        z = 1.2 + k * .8
        s.box("cabinet", (.5, 1.1, .7), (x0 + .26, .55, z))
        s.rod("steel", (x0 + .52, .85, z - .2), (x0 + .52, .85, z + .2), .008, segments=8)
    # Supply trolley at the back right.
    s.box("steel", (.7, .02, .45), (2.2, .9, -1.6))
    s.box("steel", (.7, .02, .45), (2.2, .45, -1.6))
    for dx in (-.33, .33):
        for dz in (-.2, .2):
            s.rod("steel", (2.2 + dx, .05, -1.6 + dz), (2.2 + dx, .9, -1.6 + dz), .012, segments=8)
    s.box("blue_plastic", (.25, .12, .2), (2.05, .97, -1.6))
    s.box("white_plastic", (.2, .1, .18), (2.35, .96, -1.55))


def _table_and_patient(s: Scene) -> None:
    top = TABLE_TOP
    s.box("dark", (.6, .1, .9), (0., .05, .95))
    s.rod("steel", (0., .1, .95), (0., top - .1, .95), .11, segments=24)
    s.box("device_trim", (.56, .06, 2.0), (0., top - .07, .9))
    s.box("pad", (.54, .07, 1.9), (0., top - .01, .95))
    s.box("pad", (.26, .07, .26), (0., top - .01, -.12))             # headrest
    # Patient under the blue drape: body mound and drape hanging off the sides.
    s.ellipsoid("drape", (.25, .085, .78), (0., top + .03, 1.02), detail=(28, 14))
    s.ellipsoid("drape", (.2, .07, .16), (0., top + .03, .2), detail=(20, 10))     # shoulders
    s.box("drape", (.8, .012, 1.82), (0., top + .006, 1.0))
    for side in (-1, 1):
        s.box("drape", (.012, .36, 1.82), (side * .4, top - .174, 1.0))
    s.box("drape", (.8, .36, .012), (0., top - .174, 1.91))
    # Head: skin face, covered hair, nose, closed fellow eye, nasal cannula.
    head = (0., .928, .06)
    s.ellipsoid("skin", (.085, .095, .11), head, detail=(28, 16))
    s.ellipsoid("cap", (.092, .088, .08), (0., .93, -.025), detail=(24, 12))
    s.ellipsoid("skin", (.013, .02, .024), (0., 1.018, .088), euler(-.4, 0., 0.), detail=(12, 8))
    s.ellipsoid("skin", (.016, .006, .011), (.032, 1.016, .03), detail=(12, 6))
    s.rod("dark", (.020, 1.0175, .03), (.044, 1.0175, .03), .0009, segments=6)
    s.ellipsoid("hair", (.014, .0015, .0025), (.032, 1.014, .003), detail=(12, 6))   # brow
    s.ellipsoid("lips", (.017, .004, .006), (0., 1.0, .132), detail=(14, 6))
    for x in (-.088, .088):                                           # ears
        s.ellipsoid("skin", (.012, .03, .02), (x, .93, .05), detail=(12, 8))
    s.rod("tubing", (-.088, .95, .12), (-.012, 1.006, .112), .0028, segments=8)
    s.rod("tubing", (.088, .95, .12), (.012, 1.006, .112), .0028, segments=8)
    # Eye drape around the operative eye and a wire lid speculum.
    # Adhesive eye drape tenting over the face, open around the eye.
    ex, ey, ez = EYE_POS
    s._geo("drape").extend(cylinder(40, (EYE_RADIUS + .006) / .1, False), IDENTITY,
                           (.1, .038, .1), (ex, ey + EYE_LIFT - .039, ez))
    s.ring("steel", (ex, ey + EYE_LIFT + .0005, ez), EYE_RADIUS + .001, .0009)
    for side in (-1, 1):
        a = (EYE_POS[0] + .02, EYE_POS[1] + .003, EYE_POS[2] + side * .014)
        s.rod("steel", a, (a[0] + .035, a[1] - .004, a[2] + side * .012), .0009, segments=6)


def _microscope(s: Scene) -> None:
    bx, bz = -1.0, -.55
    s.box("device", (.62, .14, .62), (bx, .1, bz))
    for dx in (-.25, .25):
        for dz in (-.25, .25):
            s.rod("rubber", (bx + dx - .03, .04, bz + dz), (bx + dx + .03, .04, bz + dz), .04,
                  segments=12)
    s.rod("device", (bx, .17, bz), (bx, 1.92, bz), .075, segments=24)
    s.rod("device_trim", (bx, 1.2, bz), (bx, 1.26, bz), .08, segments=24)
    elbow = (-.42, 1.98, -.22)
    s.box("device", (.12, .12, .12), (bx, 1.95, bz))
    s.rod("device", (bx, 1.98, bz), elbow, .055, segments=18)
    carrier = (EYE_POS[0], 1.98, EYE_POS[2] - .05)
    s.rod("device", elbow, carrier, .05, segments=18)
    s.rod("device_trim", carrier, (carrier[0], 1.62, carrier[2]), .035, segments=16)
    head = (EYE_POS[0], 1.53, EYE_POS[2] - .02)
    s.rod("device", (head[0], 1.45, head[2]), (head[0], 1.6, head[2]), .09, segments=32)
    s.ellipsoid("device", (.09, .03, .09), (head[0], 1.6, head[2]), detail=(32, 8))
    s.rod("device_trim", (head[0], 1.555, head[2]), (head[0], 1.575, head[2]), .093, segments=32)
    s.box("device", (.12, .1, .12), (head[0], 1.53, head[2] - .1))
    s.rod("dark", (EYE_POS[0], 1.40, EYE_POS[2]), (EYE_POS[0], 1.45, EYE_POS[2]), .05,
          segments=24)
    s.ring("lamp_led", (EYE_POS[0], 1.399, EYE_POS[2]), .038, .004)
    # Binocular tube angled up towards the surgeon, eyepieces, handles.
    for side in (-1, 1):
        a = (EYE_POS[0] + side * .032, 1.56, head[2] - .1)
        b = (EYE_POS[0] + side * .032, 1.45, -.43)
        s.rod("device", a, b, .022, segments=14)
        s.rod("rubber", b, _add(b, (0., -.012, -.035)), .021, segments=14)
        s.rod("device_trim", (head[0] + side * .09, 1.5, head[2]), (head[0] + side * .17, 1.43, head[2] + .04),
              .012, segments=10)
    s.box("device", (.1, .08, .1), (head[0], 1.62, head[2] + .12))          # camera module


def _lamp(s: Scene) -> None:
    mount = (.25, ROOM[3], .7)
    s.rod("device", mount, (.25, 2.55, .7), .05)
    s.rod("device", (.25, 2.55, .7), (.1, 2.35, .25), .035)
    centre = lamp_position()
    rot = lamp_rotation()
    s.rod("lamp_body", _add(centre, _apply(rot, (0., .0, 0.))), _add(centre, _apply(rot, (0., .07, 0.))),
          .34, segments=40)
    s.rod("lamp_body", (.1, 2.35, .25), _add(centre, _apply(rot, (0., .07, 0.))), .03)
    for ring_r, count in ((.08, 6), (.17, 12), (.26, 18)):
        for k in range(count):
            a = math.tau * k / count
            led = _add(centre, _apply(rot, (ring_r * math.cos(a), -.002, ring_r * math.sin(a))))
            s.ellipsoid("lamp_led", (.025, .025, .025), led, rot, detail=(10, 6))
    s.ellipsoid("lamp_body", (.05, .03, .05), _add(centre, _apply(rot, (0., -.004, 0.))), rot)


def lamp_position() -> Vec:
    return (.05, 2.25, .32)


def lamp_rotation() -> Mat3:
    """Lamp face (local -y) pointing at the patient's eye."""
    return align_y(_sub(lamp_position(), EYE_POS))


def _monitor(s: Scene, screen: ScreenQuad, depth: float, mount: str) -> None:
    right, up, normal = screen.basis
    back = _add(screen.centre, _scale(normal, -depth / 2 - .002))
    rot = euler(-screen.pitch, screen.yaw, 0.)
    s.box("screen_bezel", (screen.width + .04, screen.height + .04, depth), back, rot)
    s.box("dark", (screen.width * .6, screen.height * .6, .05),
          _add(back, _scale(normal, -depth / 2 - .02)), rot)
    led = _add(screen.centre, _add(_scale(up, -screen.height / 2 - .012), _scale(right, screen.width / 2 - .02)))
    s.ellipsoid("status_led", (.004, .004, .004), _add(led, _scale(normal, .001)), detail=(8, 6))
    if mount == "pole":
        foot = (screen.centre[0] - normal[0] * .1, 0., screen.centre[2] - normal[2] * .1)
        s.rod("steel", foot, (foot[0], screen.centre[1] - .1, foot[2]), .02)
        s.rod("device_trim", (foot[0], screen.centre[1] - .1, foot[2]),
              _add(back, _scale(normal, -depth / 2 - .04)), .02)
        for k in range(5):
            a = math.tau * k / 5
            s.rod("steel", (foot[0], .06, foot[2]), (foot[0] + .25 * math.cos(a), .03, foot[2] + .25 * math.sin(a)),
                  .014, segments=8)
    elif mount == "ceiling":
        top = (screen.centre[0], ROOM[3], screen.centre[2] - .1)
        s.rod("device", top, (top[0], screen.centre[1] + screen.height / 2 + .1, top[2]), .035)
        s.rod("device", (top[0], screen.centre[1] + screen.height / 2 + .1, top[2]),
              _add(back, _scale(normal, -depth / 2 - .04)), .03)


def _phaco_console(s: Scene) -> None:
    x, z = .95, .1
    yaw = SCREENS["phaco"].yaw
    rot = euler(0., yaw, 0.)
    s.box("device", (.48, .9, .52), (x, .55, z), rot)
    s.box("device_trim", (.49, .05, .53), (x, .98, z), rot)
    s.box("device", (.44, .14, .4), (x, 1.07, z + .02), rot)
    for k in range(3):                                  # front drawer lines
        s.box("device_trim", (.42, .006, .005), _add((x, .35 + k * .18, z), _apply(rot, (0., 0., .262))), rot)
    for dx in (-.19, .19):
        for dz in (-.2, .2):
            s.ellipsoid("rubber", (.04, .04, .04), _add((x, .045, z), _apply(rot, (dx, 0., dz))), detail=(10, 6))
    # Cassette slot and tubing to the field.
    port = _add((x, .8, z), _apply(rot, (-.12, 0., .262)))
    s.box("dark", (.14, .1, .01), port, rot)
    s.rod("tubing", port, _add(port, (-.05, -.5, .05)), .004, segments=8)
    # IV pole with the irrigation bottle.
    pole = _add((x, 1.14, z), _apply(rot, (.16, 0., -.12)))
    s.rod("steel", pole, (pole[0], 2.05, pole[2]), .012, segments=10)
    s.rod("steel", (pole[0] - .1, 2.02, pole[2]), (pole[0] + .1, 2.02, pole[2]), .008, segments=8)
    s.rod("glass", (pole[0] - .08, 1.72, pole[2]), (pole[0] - .08, 1.95, pole[2]), .045, segments=18)
    s.rod("white_plastic", (pole[0] - .08, 1.95, pole[2]), (pole[0] - .08, 2.0, pole[2]), .02, segments=12)
    s.rod("glass", (pole[0] - .08, 1.62, pole[2]), (pole[0] - .08, 1.71, pole[2]), .01, segments=10)
    s.rod("tubing", (pole[0] - .08, 1.62, pole[2]), (x, 1.1, z), .0035, segments=8)
    # Foot pedal by the surgeon's right foot.
    s.box("dark", (.24, .06, .3), (-.2, .03, -.25), euler(-.12, 0., 0.))
    s.box("device_trim", (.2, .012, .22), (-.2, .065, -.24), euler(-.12, 0., 0.))
    s.rod("dark", (-.2, .03, -.1), (.8, .03, .2), .006, segments=6)


TRAY_CENTRE: Vec = (.45, 1.02, .62)
TRAY_TOOLS = ("keratome", "sideport", "ovd_cannula", "cystotome", "forceps", "hydro_cannula",
              "phaco", "ia", "injector", "iol_hook", "iris_hooks", "ctr", "cautery",
              "irrigation", "suture")


def _instrument_tray(s: Scene, held: str | None) -> None:
    cx, cy, cz = TRAY_CENTRE
    # Mayo stand: tray over the patient's chest, single post at the side.
    s.box("steel", (.62, .012, .44), (cx, cy, cz))
    for dz in (-.22, .22):
        s.box("steel", (.62, .03, .008), (cx, cy + .015, cz + dz))
    for dx in (-.31, .31):
        s.box("steel", (.008, .03, .44), (cx + dx, cy + .015, cz))
    s.box("drape", (.6, .004, .42), (cx, cy + .008, cz))
    s.rod("steel", (cx + .32, cy, cz), (cx + .55, cy - .02, cz), .015)
    s.rod("steel", (cx + .55, cy - .02, cz), (cx + .55, .06, cz), .02)
    s.box("steel", (.5, .03, .5), (cx + .55, .03, cz))
    # Instruments side by side, handles towards the nurse.
    for k, name in enumerate(TRAY_TOOLS):
        if name == held:
            continue
        z = cz - .2 + k * .4 / (len(TRAY_TOOLS) - 1)
        place_instrument(s, name, (cx - .2, cy + .014, z), (1., 0., 0.))
    s.box("steel", (.09, .02, .06), (cx + .2, cy + .02, cz + .16))        # small cup
    s.rod("steel", (cx + .21, cy + .012, cz - .15), (cx + .21, cy + .04, cz - .15), .03, segments=18)


@lru_cache(maxsize=1)
def static_room() -> dict[str, Mesh]:
    """Everything that never moves: room, table and patient, devices."""
    s = Scene()
    _room(s)
    _table_and_patient(s)
    _microscope(s)
    _lamp(s)
    _phaco_console(s)
    for name, mount in (("vitals", "pole"), ("phaco", None), ("video", "ceiling")):
        if mount is not None:
            _monitor(s, SCREENS[name], .05, mount)
    s.merge(nurse())
    return s.meshes()


@lru_cache(maxsize=64)
def dynamic_room(tool: str | None, active_phase: bool) -> dict[str, Mesh]:
    """Surgeon (hands follow the instrument in use) and the instrument tray."""
    if tool is not None and tool not in TRAY_TOOLS:
        raise ValueError(f"Unknown instrument {tool!r}")
    s = surgeon(tool, active_phase)
    _instrument_tray(s, tool)
    return s.meshes()


# --- cameras ------------------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class Camera:
    eye: Vec
    target: Vec
    fov: float = 50.       # vertical, degrees
    up: Vec = (0., 1., 0.)


def _screen_camera(name: str, distance: float, fov: float = 40.) -> Camera:
    eye, target = SCREENS[name].viewpoint(distance)
    return Camera(eye, target, fov)


CAMERAS: dict[str, Camera] = {
    "overview": Camera((-1.35, 1.95, 2.45), (.05, 1.05, -.1), 54.),
    "surgeon": Camera((-.42, 1.5, -.27), (-.03, 1.0, .06), 42.),
    # Straight down the microscope; image top points away from the surgeon.
    "scope": Camera((EYE_POS[0], EYE_POS[1] + .17, EYE_POS[2] - .004), EYE_POS, 19., (0., 0., 1.)),
    "monitor": _screen_camera("video", 1.25, 44.),
    # Gallery close-ups.
    "patient": Camera((.3, 1.22, .44), (-.01, .97, .05), 38.),
    "microscope": Camera((.6, 1.6, .95), (-.55, 1.32, -.35), 50.),
    "vitals": _screen_camera("vitals", .62, 46.),
    "phaco": Camera((.36, 1.44, .64), (.92, 1.12, -.02), 44.),
    "tray": Camera((.12, 1.6, 1.08), (.45, 1.02, .6), 40.),
    "hands": Camera((-.16, 1.22, -.17), (-.03, 1.02, .03), 42.),
}
VIEW_CYCLE = ("microscope_view", "scope", "overview", "surgeon", "monitor")


def perspective(fov_deg: float, aspect: float, near: float = .02, far: float = 30.) -> tuple:
    f = 1 / math.tan(math.radians(fov_deg) / 2)
    return ((f / aspect, 0., 0., 0.), (0., f, 0., 0.),
            (0., 0., (far + near) / (near - far), 2 * far * near / (near - far)),
            (0., 0., -1., 0.))


def look_at(eye: Vec, target: Vec, up: Vec = (0., 1., 0.)) -> tuple:
    f = _norm(_sub(target, eye))
    r = _norm(_cross(f, up))
    u = _cross(r, f)
    return ((r[0], r[1], r[2], -_dot(r, eye)), (u[0], u[1], u[2], -_dot(u, eye)),
            (-f[0], -f[1], -f[2], _dot(f, eye)), (0., 0., 0., 1.))


def matmul4(a: tuple, b: tuple) -> tuple:
    return tuple(tuple(sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4)) for i in range(4))


def view_projection(camera: Camera, aspect: float) -> tuple:
    if not (math.isfinite(aspect) and aspect > 0):
        raise ValueError("Invalid aspect ratio")
    return matmul4(perspective(camera.fov, aspect), look_at(camera.eye, camera.target, camera.up))


def column_major(m: tuple) -> tuple[float, ...]:
    return tuple(m[r][c] for c in range(4) for r in range(4))


def project(m: tuple, point: Vec) -> tuple[float, float] | None:
    """Normalized device x, y of a world point (None when behind the camera)."""
    x, y, z = point
    clip = [m[r][0] * x + m[r][1] * y + m[r][2] * z + m[r][3] for r in range(4)]
    if clip[3] <= 1e-9:
        return None
    return clip[0] / clip[3], clip[1] / clip[3]
