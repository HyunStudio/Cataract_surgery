"""Schematic 3D signs of intra-operative complications and bleeding.

Each complication the surgeon can face also gets a *visible* sign in the 3D
operating field: a prolapsing iris at the main incision, a constricted
pupil, aqueous leaking from the wound, a gap with vitreous strands behind a
ruptured posterior capsule, a radial anterior capsule tear, a decentred lens
when the zonules give way, blood over the cornea, a layered hyphema, loss of
the red reflex (suprachoroidal haemorrhage), and the devices used to manage
them (iris hooks, capsular tension ring, wound sutures).

These are cosmetic, cached meshes positioned in the same normalized model
space as the rest of the synthetic eye. They are read from the authoritative
Game and can never change a phase, score, decision or replay. They are NOT
anatomical reconstructions or tissue-physics simulations.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import math

from .engine import MAIN_INCISION
from .geometry import Mesh, ellipsoid, iris_annulus

# Normalized model geometry shared with geometry.anterior_eye_meshes().
PUPIL_RADIUS = .29
IRIS_OUTER = .66
IRIS_DEPTH = .03
# Direction of the main incision in model space (eye y grows downwards,
# model y upwards): the entry target (.69, .46) is temporal, slightly superior.
WOUND_ANGLE = math.atan2(.5 - MAIN_INCISION[1], MAIN_INCISION[0] - .5)
# Anterior capsule tear runs out towards the upper right periphery.
TEAR_ANGLE = math.radians(60)
TEAR_START, TEAR_END, TEAR_END_EXTENDED = .238, .36, .46
# The lens (radius .43) is larger than the pupil (.29): it must shift more
# than .14 before its equator edge shows in the pupil, as in subluxation.
MAX_LENS_SHIFT = .19
LIVE_LENS_SHIFT = .16
PROLAPSE_PUPIL = .26
MIN_PUPIL = .18
LEVELS = 20            # blood levels are quantized so meshes stay cacheable


def _bounded(value: object, lower: float, upper: float, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"Invalid {field}")
    try:
        number = float(value)
    except (OverflowError, ValueError) as exc:
        raise ValueError(f"Invalid {field}") from exc
    if not math.isfinite(number) or not lower <= number <= upper:
        raise ValueError(f"Invalid {field}")
    return number


def _level(value: float) -> float:
    return round(round(max(0., min(1., value)) * LEVELS) / LEVELS, 4)


@dataclass(frozen=True, slots=True)
class ComplicationVisuals:
    """Renderer-facing state; 0 means 'not shown' for the integer levels."""
    pupil_radius: float = PUPIL_RADIUS     # < PUPIL_RADIUS: miosis ring shown
    iris_prolapse: int = 0                 # 1 prolapsing, 2 iris trauma
    wound_leak: bool = False
    capsule_rupture: bool = False
    rhexis_tear: int = 0                   # 1 tear, 2 tear extending
    lens_shift: float = 0.0                # zonular weakness/dialysis
    blood_film: float = 0.0                # blood over the cornea (0..1)
    hyphema: float = 0.0                   # layered blood in the chamber (0..1)
    reflex_loss: float = 0.0               # 1 - red reflex (suprachoroidal)
    iris_hooks: bool = False
    ctr: bool = False
    sutures: bool = False

    def check(self) -> None:
        _bounded(self.pupil_radius, MIN_PUPIL, PUPIL_RADIUS, "pupil radius")
        _bounded(self.lens_shift, 0., MAX_LENS_SHIFT, "lens shift")
        for value, name in ((self.blood_film, "blood film"), (self.hyphema, "hyphema"),
                            (self.reflex_loss, "red reflex loss")):
            _bounded(value, 0., 1., name)
        for value, upper, name in ((self.iris_prolapse, 2, "iris prolapse"),
                                   (self.rhexis_tear, 2, "rhexis tear")):
            if type(value) is not int or not 0 <= value <= upper:
                raise ValueError(f"Invalid {name} level")
        for value, name in ((self.wound_leak, "wound leak"),
                            (self.capsule_rupture, "capsule rupture"),
                            (self.iris_hooks, "iris hooks"), (self.ctr, "CTR"),
                            (self.sutures, "sutures")):
            if type(value) is not bool:
                raise ValueError(f"Invalid {name} flag")

    @property
    def any(self) -> bool:
        return (self.pupil_radius < PUPIL_RADIUS or self.iris_prolapse > 0
                or self.wound_leak or self.capsule_rupture or self.rhexis_tear > 0
                or self.lens_shift > 0 or self.blood_film > 0 or self.hyphema > 0
                or self.reflex_loss > 0 or self.iris_hooks or self.ctr or self.sutures)


def complication_visuals(game) -> ComplicationVisuals:
    """Read-only mapping from Game state to visible complication signs."""
    live = game.patient.alert
    if not isinstance(live, str) or len(live) > 80:
        raise ValueError("Invalid patient alert")
    showing = {live, *game.pending}
    kinds = {alert['kind'] for alert in game.alerts}
    flags = game.flags
    eye = game.eye
    pupil = _bounded(eye.pupil, 0., 1., "pupil")
    # Quantized to .01 so the miosis ring cache holds a handful of sizes.
    radius = round(max(MIN_PUPIL, min(PUPIL_RADIUS, PUPIL_RADIUS * (.25 + .75 * pupil))), 2)
    iris = 2 if 'iris_trauma' in flags else 1 if 'IRIS PROLAPSE' in showing else 0
    if iris == 1:
        radius = min(radius, PROLAPSE_PUPIL)     # the pupil peaks towards the wound
    tear = (2 if 'tear_extending' in flags else 1) if 'RHEXIS TEAR' in kinds else 0
    shift = 0.
    if 'zonular_dialysis' in flags:
        shift = MAX_LENS_SHIFT
    elif 'ZONULAR WEAKNESS' in showing and 'ctr_inserted' not in flags:
        shift = LIVE_LENS_SHIFT
    result = ComplicationVisuals(
        pupil_radius=radius, iris_prolapse=iris,
        wound_leak='WOUND LEAK RISK' in showing,
        capsule_rupture='CAPSULE INTEGRITY' in kinds,
        rhexis_tear=tear, lens_shift=shift,
        blood_film=_level(_bounded(eye.blood_film, 0., 1., "blood film")),
        hyphema=_level(_bounded(eye.hyphema, 0., 1., "hyphema")),
        reflex_loss=_level(1. - _bounded(eye.red_reflex, 0., 1., "red reflex")),
        iris_hooks='iris_hooks_placed' in flags,
        ctr='ctr_inserted' in flags,
        sutures=bool({'wound_sutured', 'wound_closed_emergently'} & flags))
    result.check()
    return result


def _flat_strip(name: str, angle: float, start: float, end: float,
                width: float, z: float, *, taper: float = .6, wiggle: float = .012) -> Mesh:
    """A thin radial ribbon facing the viewer (two triangles per segment)."""
    ca, sa = math.cos(angle), math.sin(angle)
    nx, ny = -sa * width / 2, ca * width / 2
    vertices, faces = [], []
    steps = 6
    for i in range(steps + 1):
        r = start + (end - start) * i / steps
        # Slight taper and wiggle so a tear reads as torn, not ruled.
        narrow = 1. - taper * i / steps
        offset = wiggle * math.sin(i * 2.1)
        cx, cy = r * ca - sa * offset, r * sa + ca * offset
        vertices += [(cx + nx * narrow, cy + ny * narrow, z),
                     (cx - nx * narrow, cy - ny * narrow, z)]
        if i:
            a, b = 2 * (i - 1), 2 * i
            faces += [(a, b, a + 1), (b, b + 1, a + 1)]
    mesh = Mesh(name, tuple(vertices), ((0., 0., 1.),) * len(vertices), tuple(faces))
    mesh.validate()
    return mesh


def _merge(name: str, parts: list[Mesh]) -> Mesh:
    vertices, normals, faces = [], [], []
    for part in parts:
        base = len(vertices)
        vertices += part.vertices
        normals += part.normals
        faces += [(a + base, b + base, c + base) for a, b, c in part.faces]
    mesh = Mesh(name, tuple(vertices), tuple(normals), tuple(faces))
    mesh.validate()
    return mesh


@lru_cache(maxsize=16)
def miosis_ring(pupil_radius: float) -> Mesh:
    """Iris-coloured annulus that narrows the visible pupil (cached by size)."""
    radius = _bounded(pupil_radius, MIN_PUPIL, PUPIL_RADIUS - .005, "pupil radius")
    mesh = iris_annulus(inner=radius, outer=PUPIL_RADIUS + .01,
                        depth=IRIS_DEPTH + .002, slices=64)
    return Mesh("miosis", mesh.vertices, mesh.normals, mesh.faces)


@lru_cache(maxsize=LEVELS + 1)
def hyphema_mesh(level: float) -> Mesh:
    """Blood layered at the bottom of the anterior chamber: a flat circular
    segment in front of the iris whose fluid level rises with `level`."""
    level = _bounded(level, .01, 1., "hyphema level")
    radius, z = IRIS_OUTER - .02, .075
    top = -radius + 2 * radius * min(.9, level)
    half = math.acos(max(-1., min(1., top / radius)))   # angle from +y axis
    # Arc from the left end of the fluid line, under the bottom, to the right.
    steps = 40
    start = math.pi / 2 + half
    end = 2.5 * math.pi - half
    rim = [(radius * math.cos(start + (end - start) * i / steps),
            radius * math.sin(start + (end - start) * i / steps), z) for i in range(steps + 1)]
    centre = (0., (top - radius) / 2, z)
    vertices = (centre, *rim)
    # Fan from inside the segment, closed along the fluid line (the chord).
    faces = (*((0, i, i + 1) for i in range(1, len(rim))), (0, len(rim), 1))
    mesh = Mesh("hyphema", vertices, ((0., 0., 1.),) * len(vertices), faces)
    mesh.validate()
    return mesh


@lru_cache(maxsize=1)
def complication_meshes() -> dict[str, Mesh]:
    """State-independent cosmetic meshes, built once per process."""
    wx, wy = math.cos(WOUND_ANGLE), math.sin(WOUND_ANGLE)
    prolapse = _merge("iris_prolapse", [
        ellipsoid("prolapse_a", (.085, .06, .05), center=(.63 * wx, .63 * wy, .07),
                  slices=18, stacks=10),
        ellipsoid("prolapse_b", (.05, .04, .04), center=(.71 * wx, .71 * wy + .02, .09),
                  slices=14, stacks=8),
    ])
    # Aqueous welling out of the main incision and running down the cornea.
    droplets = _merge("wound_leak", [
        _flat_strip("leak_streak", WOUND_ANGLE - .35, .60, .86, .05, .16),
        *(ellipsoid(f"drop_{i}", (.045 - .007 * i, .045 - .007 * i, .03),
                    center=((.64 + .07 * i) * wx + .02 * i, (.64 + .07 * i) * wy - .07 * i,
                            .17), slices=14, stacks=8)
          for i in range(4)),
    ])
    # Blood over the cornea from the incision, running inferiorly.
    blood = _merge("blood_film", [
        ellipsoid("blood_pool", (.11, .08, .012), center=(.66 * wx, .66 * wy, .17),
                  slices=20, stacks=6),
        _flat_strip("blood_run_a", WOUND_ANGLE - .55, .52, .80, .07, .175, taper=.3),
        _flat_strip("blood_run_b", WOUND_ANGLE - .9, .58, .78, .045, .175, taper=.5),
    ])
    gap = ellipsoid("pcr_gap", (.13, .085, .012), center=(-.02, -.05, .055),
                    slices=24, stacks=8)
    strands = _merge("vitreous", [
        _flat_strip(f"strand_{i}", math.radians(200 + 28 * i), .03, .19, .012, .07)
        for i in range(5)
    ])
    # Suprachoroidal haemorrhage: dark dome rising behind the lens, filling
    # the pupil where the red reflex used to be.
    dome = ellipsoid("sch_dome", (.24, .22, .012), center=(-.05, -.07, .045),
                     slices=28, stacks=8)
    tear = _flat_strip("rhexis_tear", TEAR_ANGLE, TEAR_START, TEAR_END, .03, .07)
    tear_long = _flat_strip("rhexis_tear_long", TEAR_ANGLE, TEAR_START,
                            TEAR_END_EXTENDED, .036, .07)
    ring = iris_annulus(inner=.40, outer=.42, depth=.05, slices=64)
    hooks = _merge("iris_hooks", [
        _flat_strip(f"hook_{k}", math.radians(45 + 90 * k), PUPIL_RADIUS - .01, IRIS_OUTER + .1,
                    .014, .08, taper=0., wiggle=0.)
        for k in range(4)
    ])
    sutures = _merge("sutures", [
        _flat_strip(f"suture_{k}", WOUND_ANGLE + k * .07, .60, .74, .012, .18,
                    taper=0., wiggle=0.)
        for k in (-1, 1)
    ])
    return {"iris_prolapse": prolapse, "wound_leak": droplets, "blood_film": blood,
            "pcr_gap": gap, "vitreous": strands, "sch_dome": dome,
            "rhexis_tear": tear, "rhexis_tear_long": tear_long,
            "ctr": Mesh("ctr", ring.vertices, ring.normals, ring.faces),
            "iris_hooks": hooks, "sutures": sutures}


# Display colours (RGB, alpha) per mesh; schematic, not tissue optics.
STYLE = {
    "miosis": ((.12, .45, .49), 1.0),
    "iris_prolapse": ((.55, .36, .27), 1.0),
    "iris_trauma": ((.38, .20, .17), 1.0),
    "wound_leak": ((.78, .95, 1.0), .92),
    "blood_film": ((.62, .07, .10), .8),
    "hyphema": ((.55, .05, .09), .9),
    "pcr_gap": ((.04, .05, .07), 1.0),
    "vitreous": ((.86, .90, .92), .75),
    "sch_dome": ((.30, .06, .08), .95),
    "rhexis_tear": ((.99, .30, .32), 1.0),
    "ctr": ((.86, .90, .94), 1.0),
    "iris_hooks": ((.88, .91, .95), 1.0),
    "sutures": ((.08, .08, .10), 1.0),
}
