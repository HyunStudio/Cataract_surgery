"""Automated *software OpenGL* integration exercise of the 3D cataract game.

Runs on Xvfb/Mesa in CI. It tests the rendered scene, shared phase state,
synthetic complication hold, GUI labels and complete replay. It is NOT a
physical GPU, validated medical training, or manually tested desktop UX.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import sys


def main() -> int:
    try:
        import pygame
        import moderngl
        from .engine import Phase
        from .gl_preview import GPUEyePreview, AnatomyAppearance, atlas_meshes
        from .gl_surgery import SurgeryHUD, CHECKS
        from .input3d import Surgery3DController, eye_to_pixel
        from .replay import ReplayGame
        from .iol3d import iol_visual_deployment
        from .tool3d import visible_stylus
    except ImportError as exc:
        print(f"Optional GL dependency missing: {exc}", file=sys.stderr)
        return 2

    pygame.init()
    atlas = None
    try:
        W, H = 960, 640
        atlas = GPUEyePreview(pygame, moderngl, size=(W,H))
        ctrl = Surgery3DController(seed=17)
        overlay = SurgeryHUD(ctrl)
        atlas_state = "CATARACT"
        images = {}
        eye_regions = {}
        root = Path("build/screenshots")
        root.mkdir(parents=True, exist_ok=True)

        def frame(name):
            nonlocal atlas_state
            if ctrl.view.phase != atlas_state:
                atlas_state = ctrl.view.phase
                atlas.set_meshes(atlas_meshes(atlas_state))
            e=ctrl.game.eye
            data = atlas.render(ctrl.view, 60., capture=True, overlay=overlay,
                                appearance=AnatomyAppearance(e.opacity,e.cortex,e.iol_alignment,
                                                             iol_visual_deployment(ctrl.game)),
                                tool_pose=visible_stylus(ctrl))
            if data is None or len(data) != W*H*3:
                raise AssertionError(f"Frame readback missing: {name}")
            if max(data[::97]) - min(data[::97]) < 20:
                raise AssertionError(f"Frame uniform/blank: {name}")
            images[name] = hashlib.sha256(data).hexdigest()
            surface = pygame.image.fromstring(data, (W,H), "RGB", True)
            # Exclude sidebar/bottom HUD so a changed label cannot falsely
            # pass as a genuinely unfolded 3D IOL mesh.
            central_eye = surface.subsurface((W//2-100, H//2-100, 200, 200))
            eye_regions[name] = hashlib.sha256(pygame.image.tobytes(
                central_eye, "RGB")).hexdigest()
            pygame.image.save(surface, str(root / f"gl-surgery-{name}.png"))

        def point(x,y,*,pressed=False):
            pixel = eye_to_pixel(x,y,ctrl.tool_depth,W,H,ctrl.view)
            if pixel is None:
                raise AssertionError("3D target not visible")
            return ctrl.pointer(*pixel,W,H,fresh_press=pressed)

        ctrl.command("confirm")
        ctrl.command("prepare")
        assert ctrl.game.phase == Phase.ENTRY
        frame("entry")
        for index, (x,y) in enumerate(ctrl.game._entry_target):
            assert point(x,y,pressed=True)
            if index == 0:
                assert visible_stylus(ctrl) is not None
                # Verify mesh draws into GL pixels, not just a HUD cursor.
                e = ctrl.game.eye
                raw = atlas.render(ctrl.view,60.,capture=True,overlay=overlay,
                    appearance=AnatomyAppearance(e.opacity,e.cortex,e.iol_alignment),
                    tool_pose=None)
                with_tool = atlas.render(ctrl.view,60.,capture=True,overlay=overlay,
                    appearance=AnatomyAppearance(e.opacity,e.cortex,e.iol_alignment),
                    tool_pose=visible_stylus(ctrl))
                assert raw != with_tool, "Synthetic 3D instrument not visible in frame"
                frame("entry-stylus")
        assert ctrl.game.phase == Phase.CAPSULE
        frame("capsule")
        for n in range(24):
            angle = (n+.5)*math.tau/24
            point(.5+.28*math.cos(angle),.5+.28*math.sin(angle))
        assert ctrl.game.phase == Phase.PHACO
        frame("phaco")
        for _ in range(20):
            point(.5,.5)
        frame("phaco-mid")
        for _ in range(62):
            point(.5,.5)
        assert ctrl.game.phase == Phase.IOL
        frame("iol")
        # Held mouse input must NOT silently place IOL.
        assert not point(.5,.5)
        assert point(.5,.5,pressed=True)
        assert ctrl.game.phase == Phase.CLOSE
        frame("iol-placement")
        # Synthetic game time, not wall time, drives the 3D unfolding shader.
        for _ in range(15):
            ctrl.advance_clock(.05)
        frame("iol-unfolding")
        for _ in range(15):
            ctrl.advance_clock(.05)
        frame("iol-deployed")
        if eye_regions["iol-placement"] == eye_regions["iol-unfolding"] or (
                eye_regions["iol-unfolding"] == eye_regions["iol-deployed"]):
            raise AssertionError("Central 3D IOL geometry did not visually unfold")
        for name in CHECKS:
            assert ctrl.command("verify",name)
        assert ctrl.game.phase == Phase.RECOVERY
        assert ctrl.game.score() == 100
        frame("recovery")
        recovered = ReplayGame.replay_jsonl(ctrl.game.export_replay_jsonl())
        assert recovered.snapshot() == ctrl.game.snapshot()

        # Eventful second case proves the same renderer can draw safety holds.
        ctrl = Surgery3DController("motion",seed=17)
        overlay = SurgeryHUD(ctrl)
        ctrl.command("confirm")
        ctrl.command("prepare")
        for x,y in ctrl.game._entry_target:
            assert point(x,y,pressed=True)
        assert ctrl.game.phase == Phase.CAPSULE
        assert ctrl.game.patient.alert == "PATIENT MOTION"
        assert not point(.5,.5,pressed=True)
        frame("safety-hold")
        assert ctrl.command("abort")
        assert ctrl.game.phase == Phase.ABORTED
        frame("safe-abort")
        assert ReplayGame.replay_jsonl(ctrl.game.export_replay_jsonl()).ending == "SAFELY ABORTED"

        if len(set(images.values())) != len(images):
            raise AssertionError("Distinct states rendered identical images")
        print(json.dumps({
            "status": "software-opengl-3d-surgery-integration-passed",
            "frame_hashes": images,
            "gl_renderer": atlas.ctx.info.get("GL_RENDERER", "unknown"),
            "scenario_count": 2,
            "windows_gpu_tested": False,
            "clinical_validation": False,
        },sort_keys=True))
        return 0
    except Exception as exc:
        print(f"3D SURGERY GL TEST FAILED: {type(exc).__name__}: {exc}",
              file=sys.stderr)
        return 1
    finally:
        if atlas is not None:
            atlas.close()
        pygame.quit()


if __name__=="__main__":
    raise SystemExit(main())
