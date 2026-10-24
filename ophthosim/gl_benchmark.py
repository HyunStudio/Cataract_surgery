"""Scripted frame-time benchmark of the experimental 3D surgery viewport.

Supports the GL08 checklist row on a physical desktop:
    python -m ophthosim.gl_benchmark --seconds 60 --size 1920x1080
    python -m ophthosim.gl_benchmark --seconds 60 --fullscreen

The workload hovers the synthetic stylus along a deterministic path in the
ENTRY phase while the camera orbits, so the per-frame nearest-triangle query,
contact ring, stylus, HUD texture upload and buffer swap all run every frame.
Hover never issues a Game action; the report asserts the synthetic Game
snapshot and replay journal are unchanged. Results are CPU-observed wall
clock intervals (vsync is not controlled), never clinical evidence.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
import platform
import sys
import time

from .frametime import (FrameProfiler, gl07_assessment, gl08_assessment,
                        is_software_renderer, memory_trend, process_rss_mb)
from .gl_preview import hud_scale
from .input3d import Surgery3DController, eye_to_pixel
from .surface_probe3d import SurfaceProbe, probe_surface
from .tool3d import visible_stylus
from .vision3d import visual_feedback

WORKLOAD = "entry-hover-orbit"
DEFAULT_OUT = Path("build/benchmark/gl-frametime.json")
MAX_FRAMES = 1_000_000
MAX_SECONDS = 3600.
MEMORY_SAMPLE_EVERY = 60  # measured frames between host-memory samples
# Rolling capacity for --seconds runs; reaching it ends the run early so the
# statistics always describe every measured frame.
SECONDS_CAPACITY = 250_000


@dataclass(frozen=True, slots=True)
class WorkloadFrame:
    """CPU-side inputs prepared for one benchmark frame."""
    tool_pose: tuple[float, float, float] | None
    proximity: SurfaceProbe | None


def camera_at(index: int) -> tuple[float, float]:
    """Deterministic bounded orbit inside View's yaw/pitch limits."""
    if type(index) is not int or index < 0:
        raise ValueError("Frame index must be a non-negative integer")
    return (round(.9 * math.sin(index * .011), 6),
            round(.35 * math.sin(index * .017 + .4), 6))


def hover_at(index: int) -> tuple[float, float]:
    """Normalized eye point looping past the synthetic entry targets."""
    if type(index) is not int or index < 0:
        raise ValueError("Frame index must be a non-negative integer")
    angle = index * .023
    return (.62 + .12 * math.cos(angle), .55 + .16 * math.sin(angle))


def prepare_controller(case: str = "normal", seed: int = 7) -> Surgery3DController:
    controller = Surgery3DController(case, seed)
    for _check in ("identity", "site", "iol_plan"): controller.command("verify", _check)
    if not (controller.command("confirm") and controller.command("prepare")):
        raise RuntimeError("Benchmark case did not reach the entry phase")
    return controller


def prepare_frame(controller: Surgery3DController, hud, index: int,
                  width: int, height: int,
                  profiler: FrameProfiler | None = None) -> WorkloadFrame:
    """Move camera and hover, then compute ONE shared proximity result."""
    controller.view.yaw, controller.view.pitch = camera_at(index)
    point = eye_to_pixel(*hover_at(index), controller.tool_depth,
                         width, height, controller.view)
    if point is not None:
        controller.inspect(*point, width, height)
    start = time.perf_counter()
    feedback = visual_feedback(controller.game,
                               reduced_motion=hud.reduced_motion,
                               high_contrast=hud.high_contrast)
    proximity = probe_surface(controller, feedback)
    hud.set_frame_proximity(proximity)
    if profiler is not None:
        profiler.record("probe", (time.perf_counter() - start) * 1000.)
    return WorkloadFrame(visible_stylus(controller), proximity)


def environment(ctx=None, pygame=None, moderngl=None) -> dict[str, object]:
    info = getattr(ctx, "info", None) or {}
    renderer = info.get("GL_RENDERER", "unknown")
    return {
        "os": platform.platform(),
        "python": platform.python_version(),
        "pygame": getattr(getattr(pygame, "version", None), "ver", None),
        "moderngl": getattr(moderngl, "__version__", None),
        "gl_renderer": renderer,
        "gl_vendor": info.get("GL_VENDOR", "unknown"),
        "gl_version": info.get("GL_VERSION", "unknown"),
        "software_renderer": is_software_renderer(renderer),
    }


def build_report(profiler: FrameProfiler, *, size: tuple[int, int],
                 seconds: float, warmup: int, env: dict[str, object],
                 state_unchanged: bool, probes: int,
                 memory: list[tuple[float, float]] | None = None,
                 scene_switch_every: int = 0, scene_switches: int = 0
                 ) -> dict[str, object]:
    frame = profiler.stats("frame")
    trend = memory_trend(memory or [])
    return {
        "benchmark": "ophthosim-gl-surgery-frametime",
        "workload": (WORKLOAD if not scene_switch_every
                     else f"{WORKLOAD}+scene-switch/{scene_switch_every}"),
        "scene_switches": scene_switches,
        "window_size": list(size),
        "hud_scale": hud_scale(*size),
        "warmup_frames": warmup,
        "frames_measured": profiler.count("frame"),
        "frames_with_proximity": probes,
        "measured_seconds": round(seconds, 3),
        "mean_fps": (round(frame.mean_fps, 2) if frame is not None
                     and math.isfinite(frame.mean_fps) else None),
        "sections": profiler.report(),
        "environment": env,
        "gl08": gl08_assessment(frame, size, seconds, env.get("gl_renderer")),
        "memory": trend.as_dict() if trend is not None else None,
        "gl07": gl07_assessment(trend, seconds, env.get("gl_renderer")),
        "timing_basis": "CPU wall clock incl. buffer swap; not GPU time",
        "vsync_controlled": False,
        "game_state_unchanged": state_unchanged,
        "clinical_validation": False,
    }


def run_benchmark(pygame, moderngl, *, size=(1920, 1080), frames=None,
                  seconds=60., warmup=30, fullscreen=False,
                  case="normal", seed=7, scene_switch_every=0
                  ) -> dict[str, object]:
    """Optional scene switching reallocates the atlas GPU meshes and BVHs
    every N measured frames (GL07 stress); those frames include that cost."""
    from .gl_preview import GPUEyePreview, AnatomyAppearance, atlas_meshes
    from .gl_surgery import SurgeryHUD

    controller = prepare_controller(case, seed)
    snapshot = controller.game.snapshot()
    journal = controller.game.export_replay_jsonl()
    hud = SurgeryHUD(controller)
    hud.status = "Frame-time benchmark: synthetic hover only, no actions"
    capacity = frames if frames is not None else SECONDS_CAPACITY
    profiler = FrameProfiler(capacity=capacity)
    atlas = GPUEyePreview(pygame, moderngl, size=size, fullscreen=fullscreen)
    try:
        eye = controller.game.eye
        appearance = AnatomyAppearance(eye.opacity, eye.cortex, eye.iol_alignment)
        index = measured = probes = 0
        total_ms = 0.
        began = previous = None
        memory: list[tuple[float, float]] = []
        switches = 0
        while True:
            if any(event.type == pygame.QUIT for event in pygame.event.get()):
                break
            width, height = pygame.display.get_window_size()
            if (scene_switch_every and measured and
                    measured % scene_switch_every == 0 and
                    switches < measured // scene_switch_every):
                controller.view.phase = ("IOL" if controller.view.phase == "CATARACT"
                                         else "CATARACT")
                atlas.set_meshes(atlas_meshes(controller.view.phase))
                switches += 1
            work = prepare_frame(controller, hud, index, width, height,
                                 profiler if index >= warmup else None)
            # Running mean only: sorting every sample each frame would
            # distort the very frame times being measured.
            fps = 1000. * measured / total_ms if total_ms > 0. else 0.
            start = time.perf_counter()
            atlas.render(controller.view, fps,
                         overlay=hud, appearance=appearance,
                         tool_pose=work.tool_pose, vision=None,
                         contact=controller.last_contact,
                         surface_probe=work.proximity)
            end = time.perf_counter()
            if index >= warmup:
                profiler.record("render", (end - start) * 1000.)
                if previous is None:
                    # Without warmup the first frame only anchors the clock.
                    began = end
                else:
                    if began is None:
                        began = previous
                    interval = (end - previous) * 1000.
                    profiler.record("frame", interval)
                    total_ms += interval
                    measured += 1
                    probes += work.proximity is not None
                    if measured % MEMORY_SAMPLE_EVERY == 1:
                        rss = process_rss_mb()
                        if rss is not None:
                            memory.append((end - began, rss))
            previous = end
            index += 1
            if measured >= capacity:
                break
            if frames is None and began is not None and end - began >= seconds:
                break
        elapsed = (previous - began) if began is not None else 0.
        controller.view.phase = "CATARACT"  # display-only; Game unaffected
        rss = process_rss_mb()
        if rss is not None and memory:
            memory.append((elapsed, rss))
        unchanged = (controller.game.snapshot() == snapshot and
                     controller.game.export_replay_jsonl() == journal)
        return build_report(profiler, size=pygame.display.get_window_size(),
                            seconds=elapsed, warmup=warmup,
                            env=environment(atlas.ctx, pygame, moderngl),
                            state_unchanged=unchanged, probes=probes,
                            memory=memory, scene_switch_every=scene_switch_every,
                            scene_switches=switches)
    finally:
        atlas.close()


def _size(text: str) -> tuple[int, int]:
    try:
        width, height = (int(part) for part in text.lower().split("x"))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("size must look like 1920x1080") from exc
    if not (320 <= width <= 7680 and 240 <= height <= 4320):
        raise argparse.ArgumentTypeError("size must be within 320x240..7680x4320")
    return width, height


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--size", type=_size, default=(1920, 1080))
    limit = parser.add_mutually_exclusive_group()
    limit.add_argument("--seconds", type=float, default=60.)
    limit.add_argument("--frames", type=int)
    parser.add_argument("--warmup", type=int, default=30)
    parser.add_argument("--fullscreen", action="store_true")
    parser.add_argument("--scene-switch-every", type=int, default=0,
                        help="GL07 stress: swap cataract/IOL meshes every N frames")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ns = parser.parse_args(argv)
    if ns.frames is not None and not 1 <= ns.frames <= MAX_FRAMES:
        parser.error(f"--frames must be within 1..{MAX_FRAMES}")
    if not (math.isfinite(ns.seconds) and 1. <= ns.seconds <= MAX_SECONDS):
        parser.error(f"--seconds must be within 1..{MAX_SECONDS:.0f}")
    if not 0 <= ns.warmup <= 10_000:
        parser.error("--warmup must be within 0..10000")
    if not (ns.scene_switch_every == 0 or 10 <= ns.scene_switch_every <= 100_000):
        parser.error("--scene-switch-every must be 0 or within 10..100000")
    # Keep stdout machine-readable: only the JSON report is printed there.
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    try:
        import pygame
        import moderngl
    except ImportError as exc:
        print(f"Install: python -m pip install -r requirements-3d.txt ({exc})",
              file=sys.stderr)
        return 2
    pygame.init()
    try:
        report = run_benchmark(pygame, moderngl, size=ns.size,
                               frames=ns.frames, seconds=ns.seconds,
                               warmup=ns.warmup, fullscreen=ns.fullscreen,
                               scene_switch_every=ns.scene_switch_every)
    finally:
        pygame.quit()
    ns.out.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(report, indent=2, sort_keys=True)
    ns.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    if not report["game_state_unchanged"] or report["frames_measured"] < 1:
        print("BENCHMARK INVALID: no frames or synthetic Game state changed",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
