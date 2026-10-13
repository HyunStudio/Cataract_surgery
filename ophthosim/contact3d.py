"""Read-only world-space contact guide for the synthetic 3D training game.

This is NOT an anatomical collision detector, clinical force-feedback system,
instrument contact model, or surgical guidance. Every action remains governed
by the existing deterministic Game state machine. The guide only highlights
whether the *educational* normalized task location is in an active region.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import math
from typing import TYPE_CHECKING

from .engine import Phase
from .geometry import Mesh

if TYPE_CHECKING:
    from .input3d import ToolPose

CONTACT_STATES = frozenset({"TARGET", "VISITED", "NEAR", "OUTSIDE",
                            "DEPTH", "HOLD", "INACTIVE"})
ACTIVATED = frozenset((Phase.ENTRY, Phase.CAPSULE, Phase.PHACO,
                       Phase.CORTEX, Phase.IOL))


@dataclass(frozen=True, slots=True)
class ContactGuide:
    status: str
    location: tuple[float, float, float] | None = None

    def check(self) -> None:
        if self.status not in CONTACT_STATES:
            raise ValueError("Invalid guide state")
        if self.location is not None:
            if not isinstance(self.location, tuple) or len(self.location) != 3:
                raise ValueError("Invalid guide location")
            for v in self.location:
                if (isinstance(v, bool) or not isinstance(v, (int, float))
                        or not -1. <= v <= 1. or not math.isfinite(v)):
                    raise ValueError("Invalid guide location")
        if self.status in {"DEPTH", "HOLD", "INACTIVE", "OUTSIDE"} and self.location:
            raise ValueError("Unsafe guide cannot retain stale world position")


def _valid_depth(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("Invalid synthetic tool depth")
    if not -.3 <= value <= .2:
        raise ValueError("Invalid synthetic tool depth")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("Invalid synthetic tool depth")
    return result


def contact_guide(game, pose: ToolPose | None,
                  tool_depth: object, target_depth: object | None) -> ContactGuide:
    """Map a validated synthetic pointer onto its current stage target.

    No interaction is performed; _entered and capsule_points are only read.
    The bounded target rings are illustrative, not anatomical surfaces.
    """
    depth = _valid_depth(tool_depth)
    if not isinstance(game.phase, Phase):
        raise ValueError("Invalid synthetic phase")
    if game.paused or game.patient.alert or game.ending:
        return ContactGuide("HOLD")
    if game.phase not in ACTIVATED or target_depth is None:
        return ContactGuide("INACTIVE")
    expected = _valid_depth(target_depth)
    if abs(depth - expected) > .055:
        return ContactGuide("DEPTH")
    if pose is None:
        return ContactGuide("OUTSIDE")
    values = (pose.eye_x, pose.eye_y, pose.world_x, pose.world_y, pose.world_z)
    if any(isinstance(v, bool) or not isinstance(v, (int, float))
           or not -1. <= v <= 1. or not math.isfinite(v) for v in values):
        raise ValueError("Invalid tool pose")
    if not 0. <= pose.eye_x <= 1. or not 0. <= pose.eye_y <= 1.:
        return ContactGuide("OUTSIDE")
    if abs(pose.world_z - depth) > 1e-6:
        return ContactGuide("DEPTH")
    u, v = pose.eye_x, pose.eye_y
    r = math.hypot(u - .5, v - .5)
    status = "NEAR"
    if game.phase == Phase.ENTRY:
        distances = tuple((math.hypot(u-tx, v-ty), i)
                          for i, (tx,ty) in enumerate(game._entry_target))
        distance, nearest = min(distances)
        if distance < .09:
            status = "VISITED" if nearest in game._entered else "TARGET"
        elif distance >= .18:
            status = "NEAR" if distance < .28 else "OUTSIDE"
    elif game.phase == Phase.CAPSULE:
        # Same safe annulus as the engine: narrower in a shallow chamber.
        low, high = game.RHEXIS_BAND if game.ovd_chamber else game.RHEXIS_BAND_SHALLOW
        if low < r < high:
            angle = (math.atan2(v-.5, u-.5) + math.tau) % math.tau
            bin_index = int(angle / math.tau * 24) % 24
            status = "VISITED" if bin_index in game.eye.capsule_points else "TARGET"
        elif r > .48:
            status = "OUTSIDE"
    elif game.phase in (Phase.PHACO, Phase.CORTEX):
        status = "TARGET" if r < game.work_radius else ("NEAR" if r < .46 else "OUTSIDE")
    elif game.phase == Phase.IOL:
        # Existing Game accepts misaligned placement and reports its score;
        # show nearby points as NEAR but never override that engine decision.
        status = "TARGET" if r < .116 else ("NEAR" if r < .28 else "OUTSIDE")
    location = (pose.world_x, pose.world_y, pose.world_z)
    result = ContactGuide(status, location if status not in {"OUTSIDE"} else None)
    result.check()
    return result


@lru_cache(maxsize=1)
def guide_ring_mesh() -> Mesh:
    """A nonphysical GPU indicator ring with no allocations per frame."""
    segments = 32
    vertices = []
    faces = []
    for i in range(segments + 1):
        a = i * math.tau / segments
        for radius in (.035, .052):
            vertices.append((radius*math.cos(a),
                             radius*math.sin(a), 0.))
        if i:
            k = 2*(i-1)
            faces.extend(((k,k+2,k+1),(k+2,k+3,k+1)))
    mesh = Mesh("synthetic_contact_guide",
                tuple(vertices), ((0.,0.,1.),)*len(vertices),
                tuple(faces))
    mesh.validate()
    return mesh
