"""3D-to-game input adapter for a *synthetic* cataract interaction prototype.

The 3D scene uses a normalized educational eye plane and stage-specific
depth gates. These are not anatomical measurements or clinical tool physics.
Only the Game phase machine can mutate surgical state; the renderer cannot.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

from .engine import Phase
from .gl_preview import View
from .picking3d import project_point, screen_ray
from .replay import ReplayGame

# Screen-space educational task coordinates: 0..1 on each axis.
# 3D +Y is up, whereas the game coordinate +Y is down.
EYE_SCALE = 1.0
STAGE_DEPTH: dict[Phase, float] = {
    Phase.ENTRY: .04,
    Phase.CAPSULE: -.04,
    Phase.PHACO: -.14,
    Phase.CORTEX: -.18,
    Phase.IOL: -.17,
}
DEPTH_TOLERANCE = .055


@dataclass(frozen=True, slots=True)
class ToolPose:
    """Read-only world-space point and normalized semantic game location."""
    eye_x: float
    eye_y: float
    world_x: float
    world_y: float
    world_z: float


def eye_to_world(x: float, y: float, z: float) -> tuple[float, float, float]:
    """Map an educational task position to a 3D cursor target."""
    point = ReplayGame._xy(x, y)
    if point is None or isinstance(z, bool) or not isinstance(z, (int, float)):
        raise ValueError("Invalid synthetic eye coordinates")
    try:
        depth = float(z)
    except (OverflowError, ValueError) as exc:
        raise ValueError("Invalid synthetic depth") from exc
    if not math.isfinite(depth) or not -.3 <= depth <= .2:
        raise ValueError("Invalid synthetic depth")
    return ((point[0] - .5) * EYE_SCALE,
            (.5 - point[1]) * EYE_SCALE, depth)


def eye_to_pixel(x: float, y: float, z: float,
                 width: int, height: int, view: View
                 ) -> tuple[float, float] | None:
    view.check()
    return project_point(eye_to_world(x, y, z), width, height,
                         view.yaw, view.pitch, view.zoom)


def pointer_to_eye(x: Any, y: Any, width: int, height: int, view: View,
                   depth: float) -> ToolPose | None:
    """Intersect a viewport ray with the *selected* task plane, not anatomy.

    Out-of-viewport or off-eye inputs are rejected. Rays parallel to the
    active tool plane produce no hit. Never infer hits from a stale overlay.
    """
    view.check()
    # eye_to_world validates depth independently of the screen pointer.
    eye_to_world(.5, .5, depth)
    ray = screen_ray(x, y, width, height, view.yaw, view.pitch, view.zoom)
    if ray is None or abs(ray.direction[2]) < 1e-9:
        return None
    t = (depth - ray.origin[2]) / ray.direction[2]
    if not math.isfinite(t) or t < 0:
        return None
    world_x = ray.origin[0] + t * ray.direction[0]
    world_y = ray.origin[1] + t * ray.direction[1]
    u, v = .5 + world_x / EYE_SCALE, .5 - world_y / EYE_SCALE
    point = ReplayGame._xy(u, v)
    if point is None:
        return None
    return ToolPose(point[0], point[1], world_x, world_y, depth)


class Surgery3DController:
    """Semantic input adapter; never bypass the phase machine's safety locks.

    The preview camera is retained across cases; the currently selected
    educational depth is reset when the phase advances. Operators may offset
    it with Q/E; inaccurate depth clicks are ignored, not penalized.
    """

    def __init__(self, case: str = "normal", seed: int = 7) -> None:
        self.game = ReplayGame(case, seed)
        self.view = View(yaw=0., pitch=0., zoom=3.6)
        self.tool_depth = STAGE_DEPTH[Phase.ENTRY]
        self.last_pose: ToolPose | None = None
        self.depth_rejections = 0

    @property
    def target_depth(self) -> float | None:
        return STAGE_DEPTH.get(self.game.phase)

    def _sync(self, old_phase: Phase) -> None:
        if old_phase != self.game.phase:
            target = self.target_depth
            if target is not None:
                self.tool_depth = target
            self.last_pose = None
        self.view.phase = ("IOL" if self.game.phase in
                           (Phase.IOL, Phase.CLOSE, Phase.RECOVERY) else "CATARACT")

    def command(self, action: str, value: str | None = None) -> bool:
        if action not in {"confirm", "prepare", "assess", "pause", "abort", "verify"}:
            return False
        before = self.game.phase
        result = self.game.action(action, value if action == "verify" else None)
        self._sync(before)
        return result

    def adjust_depth(self, direction: int) -> float:
        if type(direction) is not int or direction not in (-1, 1):
            raise ValueError("Depth adjustment must be -1 or +1")
        self.tool_depth = round(max(-.3, min(.2, self.tool_depth + direction * .02)), 4)
        self.last_pose = None
        return self.tool_depth

    def pointer(self, x: Any, y: Any, width: int, height: int,
                *, fresh_press: bool = False) -> bool:
        phase = self.game.phase
        command = {Phase.ENTRY: "touch", Phase.CAPSULE: "trace",
                   Phase.PHACO: "remove", Phase.CORTEX: "remove",
                   Phase.IOL: "place"}.get(phase)
        if command is None or self.game.paused or self.game.patient.alert:
            return False
        # An IOL placement requires an explicit NEW click. Otherwise holding
        # a removal gesture through the cortex→IOL transition can accidentally
        # trigger lens placement, even though the phase gate itself is correct.
        if phase == Phase.IOL and fresh_press is not True:
            return False
        target = self.target_depth
        if target is None or abs(self.tool_depth - target) > DEPTH_TOLERANCE:
            self.depth_rejections += 1
            return False
        pose = pointer_to_eye(x, y, width, height, self.view, self.tool_depth)
        if pose is None:
            self.last_pose = None
            return False
        self.last_pose = pose
        result = self.game.action(command, pose.eye_x, pose.eye_y)
        self._sync(phase)
        return result

    def advance_clock(self, delta: float) -> None:
        self.game.tick(delta)

    def restart(self, case: str | None = None) -> None:
        scenario = self.game.case if case is None else case
        self.game = ReplayGame(scenario, self.game.seed)
        self.tool_depth = STAGE_DEPTH[Phase.ENTRY]
        self.last_pose = None
        self.depth_rejections = 0
        self._sync(Phase.ABORTED)
