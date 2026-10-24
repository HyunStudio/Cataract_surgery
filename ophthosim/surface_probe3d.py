"""Visual-only synthetic tool-to-mesh proximity in 3D surgery mode.

The metric is UNITLESS and intentionally never changes a surgical Game
action, score, safety alert, or replay log. It is not an instrument collision
authority, physical force model or surgical/clinical guidance system.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import math

from .engine import Phase
from .geometry import anterior_eye_meshes, Vec3
from .iol_pick3d import deformed_iol_mesh
from .mesh_raycast import build_index
from .picking3d import _unrotate
from .surface_distance3d import nearest_triangle
from .tool3d import visible_stylus
from .vision3d import VisualFeedback

STATES = frozenset(("CLOSE", "NEAR", "FAR"))
# CLOSE is only active while a decentered IOL is repositioned (the
# controller exposes no target depth otherwise, so no stylus is shown).
ACTIVE_PHASES = frozenset((Phase.ENTRY, Phase.CAPSULE, Phase.PHACO,
                           Phase.CORTEX, Phase.IOL, Phase.CLOSE))


@dataclass(frozen=True, slots=True)
class SurfaceProbe:
    status: str
    name: str
    gap: float
    point: Vec3
    face_index: int

    def check(self) -> None:
        if self.status not in STATES:
            raise ValueError("Invalid synthetic mesh proximity class")
        if not isinstance(self.name,str) or self.name not in ("iris","lens","IOL"):
            raise ValueError("Invalid synthetic mesh target")
        if (isinstance(self.gap,bool) or not isinstance(self.gap,(int,float))
                or not 0<=self.gap<=5 or not math.isfinite(self.gap)):
            raise ValueError("Invalid synthetic mesh gap")
        if type(self.face_index) is not int or self.face_index < 0:
            raise ValueError("Invalid synthetic mesh face")
        if not isinstance(self.point,tuple) or len(self.point)!=3:
            raise ValueError("Invalid synthetic surface point")
        if any(isinstance(x,bool) or not isinstance(x,(int,float))
               or not -2<=x<=2 or not math.isfinite(x) for x in self.point):
            raise ValueError("Invalid synthetic surface point")


@lru_cache(maxsize=1)
def _static_indexes():
    """Immutable authored iris and cataract-lens mesh indexes."""
    m=anterior_eye_meshes()
    return {key:build_index(m[key]) for key in ("iris","lens")}


@lru_cache(maxsize=8)
def _iol_index(deployment: float, alignment: float):
    """Private cache; caller has validated the two synthetic state values."""
    return build_index(deformed_iol_mesh(deployment,alignment))


def probe_surface(controller, vision: VisualFeedback | None = None
                  ) -> SurfaceProbe | None:
    """Read nearest synthetic triangle to a visible, safely gated tool tip.

    Scene motion in GLSL translates rendered anatomy in CAMERA space but not
    the tool. Inverse rotation of that displacement gives the equivalent
    comparison point against original unshifted object-space meshes.
    Return coordinates remain on the original anatomy; the GPU may add the
    same visual scene shift when displaying a marker over that point.
    """
    game=controller.game
    if game.phase not in ACTIVE_PHASES:
        return None
    pos=visible_stylus(controller)
    if pos is None:
        return None
    if vision is not None:
        if not isinstance(vision,VisualFeedback):
            raise ValueError("Invalid visual feedback")
        vision.check()
        delta=_unrotate((vision.motion_x,vision.motion_y,0.),
                         controller.view.yaw,controller.view.pitch)
        pos=tuple(pos[i]-delta[i] for i in range(3))
    indexes=_static_indexes()
    choices=[indexes["iris"]]
    if controller.view.phase=="IOL":
        # The synthetic IOL is folded in its active insertion stage.
        from .iol3d import iol_visual_deployment
        deployment=iol_visual_deployment(game)
        alignment=game.eye.iol_alignment
        from .iol_pick3d import _fraction
        deployment=_fraction(deployment,"deployment")
        alignment=_fraction(alignment,"alignment")
        choices.append(_iol_index(deployment,alignment))
    elif game.eye.opacity > .001 or game.eye.cortex > .001:
        choices.append(indexes["lens"])
    hits=[h for index in choices
          if (h:=nearest_triangle(index,pos,max_distance=3.)) is not None]
    if not hits:
        return None
    hit=min(hits,key=lambda item:(item.distance,item.name,item.face_index))
    label="IOL" if hit.name in ("iol","optic") else hit.name
    level=("CLOSE" if hit.distance<=.04 else "NEAR"
           if hit.distance<=.14 else "FAR")
    probe=SurfaceProbe(level,label,hit.distance,hit.point,hit.face_index)
    probe.check()
    return probe
