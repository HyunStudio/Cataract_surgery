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
        from .surface_probe3d import probe_surface
        from .capsule3d import capsule_display_state
        from .vision3d import visual_feedback,VisualFeedback
        from .engine import PREOP_CHECKS
        from .complication3d import ComplicationVisuals, complication_visuals
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
            capsule_on, damage=capsule_display_state(ctrl.game)
            vision=visual_feedback(ctrl.game,
                reduced_motion=overlay.reduced_motion,
                high_contrast=overlay.high_contrast)
            proximity=probe_surface(ctrl,vision)
            overlay.set_frame_proximity(proximity)
            data = atlas.render(ctrl.view,None, capture=True, overlay=overlay,
                                appearance=AnatomyAppearance(e.opacity,e.cortex,e.iol_alignment,
                                                             iol_visual_deployment(ctrl.game),
                                                             damage,capsule_on),
                                tool_pose=visible_stylus(ctrl),
                                vision=visual_feedback(ctrl.game,
                                    reduced_motion=overlay.reduced_motion,
                                    high_contrast=overlay.high_contrast),
                                contact=(ctrl.last_contact if not ctrl.game.paused
                                         and not ctrl.game.ending else None),
                                surface_probe=proximity,
                                complications=complication_visuals(ctrl.game))
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

        def use(tool,x=.5,y=.5):
            # Situation/cannula instrument: pick it, one fresh press at (x, y).
            assert ctrl.command("tool",tool)
            return point(x,y,pressed=True)

        def clear_lens():
            # Hydrodissection first, then held phaco and I/A at 60 Hz.
            if (ctrl.game.phase==Phase.PHACO and not ctrl.game.hydro_done
                    and not ctrl.game.patient.alert):
                assert use("hydro_cannula")
            for _ in range(2000):
                if ctrl.game.phase not in (Phase.PHACO,Phase.CORTEX) or ctrl.game.patient.alert:
                    return
                point(.5,.5)
                ctrl.advance_clock(1/60)

        def entry_with_ovd():
            for index,(x,y) in enumerate(ctrl.game._entry_target):
                if ctrl.game.patient.alert:
                    return
                assert point(x,y,pressed=True)
                if index==0 and not ctrl.game.patient.alert:
                    assert use("ovd_cannula")

        # Complication and bleeding signs: identical camera, no HUD, each
        # sign must change the rendered eye and every sign must be distinct.
        base=atlas.render(ctrl.view,None,capture=True,overlay=None,
                          appearance=AnatomyAppearance(),complications=ComplicationVisuals())
        signs={
            "miosis":ComplicationVisuals(pupil_radius=.2),
            "iris-prolapse":ComplicationVisuals(iris_prolapse=1,pupil_radius=.26),
            "iris-trauma":ComplicationVisuals(iris_prolapse=2),
            "wound-leak":ComplicationVisuals(wound_leak=True),
            "capsule-rupture":ComplicationVisuals(capsule_rupture=True),
            "rhexis-tear":ComplicationVisuals(rhexis_tear=1),
            "rhexis-tear-extending":ComplicationVisuals(rhexis_tear=2),
            "zonular-shift":ComplicationVisuals(lens_shift=.16),
            "blood-film":ComplicationVisuals(blood_film=.6),
            "hyphema-low":ComplicationVisuals(hyphema=.3),
            "hyphema-high":ComplicationVisuals(hyphema=.7),
            "suprachoroidal":ComplicationVisuals(reflex_loss=.8),
            "iris-hooks":ComplicationVisuals(iris_hooks=True),
            "ctr":ComplicationVisuals(ctr=True),
            "sutures":ComplicationVisuals(sutures=True),
        }
        sign_hashes={}
        for name,visual in signs.items():
            data=atlas.render(ctrl.view,None,capture=True,overlay=None,
                              appearance=AnatomyAppearance(),complications=visual)
            if data==base:
                raise AssertionError(f"Complication sign not visible: {name}")
            sign_hashes[name]=hashlib.sha256(data).hexdigest()
            pygame.image.save(pygame.image.fromstring(data,(W,H),"RGB",True),
                              str(root/f"gl-sign-{name}.png"))
        if len(set(sign_hashes.values()))!=len(sign_hashes):
            raise AssertionError("Two complication signs rendered identically")

        # Isolate the actual 3D capsule layer. Identical camera and HUD,
        # only the *world-space ring* differs. Crop excludes interface text.
        for name,damage in (("capsule-intact",0.),("capsule-damaged",.45)):
            pixels=atlas.render(ctrl.view,None,capture=True,overlay=None,
                appearance=AnatomyAppearance(capsule_damage=damage,
                                             capsule_present=True))
            surface=pygame.image.fromstring(pixels,(W,H),"RGB",True)
            eye=surface.subsurface((W//2-100,H//2-100,200,200))
            eye_regions[name]=hashlib.sha256(pygame.image.tobytes(eye,"RGB")).hexdigest()
            pygame.image.save(surface,str(root/f"gl-surgery-{name}.png"))
        if eye_regions["capsule-intact"]==eye_regions["capsule-damaged"]:
            raise AssertionError("3D capsule tear not visible inside the eye region")

        # Isolate actual scene/haze visibility while keeping all anatomy,
        # phase and game input constant. This avoids HUD-only false positives.
        for name,vf in (("vision-clear",VisualFeedback()),
                        ("vision-hazy",VisualFeedback(haze=.48)),
                        ("vision-motion",VisualFeedback(motion_x=.04,motion_y=-.026))):
            data=atlas.render(ctrl.view,None,capture=True,overlay=None,
                appearance=AnatomyAppearance(), vision=vf)
            surf=pygame.image.fromstring(data,(W,H),"RGB",True)
            crop=surf.subsurface((W//2-100,H//2-100,200,200))
            eye_regions[name]=hashlib.sha256(pygame.image.tobytes(crop,"RGB")).hexdigest()
            pygame.image.save(surf,str(root/f"gl-surgery-{name}.png"))
        if eye_regions["vision-clear"] in (eye_regions["vision-hazy"],
                                            eye_regions["vision-motion"]):
            raise AssertionError("Synthetic eye motion/haze invisible in center-eye crop")

        # Zero-copy HUD upload (surface memory + texture swizzle + flipped
        # quad v) must match the explicit RGBA copy byte for byte on this
        # driver, and the full-window HUD surface must be reused.
        import ophthosim.gl_preview as gl_preview_module
        hud_kwargs=dict(capture=True,overlay=overlay,appearance=AnatomyAppearance(),
                        vision=VisualFeedback(haze=.3,high_contrast=True))
        direct=atlas.render(ctrl.view,None,**hud_kwargs)
        reused=atlas.hud_surface
        assert reused is not None
        assert atlas.render(ctrl.view,None,**hud_kwargs)==direct
        assert atlas.hud_surface is reused, "HUD surface reallocated per frame"
        original_swizzle=gl_preview_module.hud_swizzle
        gl_preview_module.hud_swizzle=lambda *args,**kwargs: None
        try:
            copied=atlas.render(ctrl.view,None,**hud_kwargs)
        finally:
            gl_preview_module.hud_swizzle=original_swizzle
        if copied!=direct:
            raise AssertionError("Zero-copy HUD upload differs from RGBA copy")
        hud_zero_copy=original_swizzle(reused.get_bitsize(),reused.get_pitch(),
                                       reused.get_width(),tuple(reused.get_masks()))

        for _check in ("identity", "site", "iol_plan"): ctrl.command("verify", _check)
        ctrl.command("confirm")
        ctrl.command("prepare")
        assert ctrl.game.phase == Phase.ENTRY
        frame("entry")
        for index, (x,y) in enumerate(ctrl.game._entry_target):
            assert point(x,y,pressed=True)
            if index == 0:
                assert use("ovd_cannula") and ctrl.game.ovd_chamber
                assert visible_stylus(ctrl) is not None
                # Verify mesh draws into GL pixels, not just a HUD cursor.
                e = ctrl.game.eye
                raw = atlas.render(ctrl.view,None,capture=True,overlay=overlay,
                    appearance=AnatomyAppearance(e.opacity,e.cortex,e.iol_alignment),
                    tool_pose=None)
                with_tool = atlas.render(ctrl.view,None,capture=True,overlay=overlay,
                    appearance=AnatomyAppearance(e.opacity,e.cortex,e.iol_alignment),
                    tool_pose=visible_stylus(ctrl))
                assert raw != with_tool, "Synthetic 3D instrument not visible in frame"
                assert ctrl.last_contact is not None
                # Same game, tool and HUD; compare eye-only pixels with and
                # without the GPU contact mesh (text label cannot pass).
                no_guide = atlas.render(ctrl.view,None,capture=True,overlay=overlay,
                    appearance=AnatomyAppearance(e.opacity,e.cortex,e.iol_alignment),
                    tool_pose=visible_stylus(ctrl),contact=None)
                guided = atlas.render(ctrl.view,None,capture=True,overlay=overlay,
                    appearance=AnatomyAppearance(e.opacity,e.cortex,e.iol_alignment),
                    tool_pose=visible_stylus(ctrl),contact=ctrl.last_contact)
                a=pygame.image.fromstring(no_guide,(W,H),"RGB",True)
                b=pygame.image.fromstring(guided,(W,H),"RGB",True)
                rect=(W//2-100,H//2-100,200,200)
                assert pygame.image.tobytes(a.subsurface(rect),"RGB") != (
                    pygame.image.tobytes(b.subsurface(rect),"RGB")), (
                    "3D contact ring did not change center-eye pixels")
                # Actual closest-triangle marker must modify the eye crop
                # without creating an extra game/replay event.
                from .surface_probe3d import probe_surface
                before=ctrl.game.snapshot()
                nearest=probe_surface(ctrl)
                assert nearest is not None and nearest.face_index>=0
                no_surface=atlas.render(ctrl.view,None,capture=True,overlay=None,
                    appearance=AnatomyAppearance(e.opacity,e.cortex,e.iol_alignment),
                    surface_probe=None)
                with_surface=atlas.render(ctrl.view,None,capture=True,overlay=None,
                    appearance=AnatomyAppearance(e.opacity,e.cortex,e.iol_alignment),
                    surface_probe=nearest)
                compare=(W//2-100,H//2-100,200,200)
                src=pygame.image.fromstring(no_surface,(W,H),"RGB",True)
                dst=pygame.image.fromstring(with_surface,(W,H),"RGB",True)
                assert pygame.image.tobytes(src.subsurface(compare),"RGB") != (
                    pygame.image.tobytes(dst.subsurface(compare),"RGB")), (
                    "Closest triangle marker not visible in eye-only pixels")
                assert ctrl.game.snapshot()==before
                frame("entry-stylus")
        assert ctrl.game.phase == Phase.CAPSULE
        frame("capsule")
        for n in range(24):
            if ctrl.game.phase!=Phase.CAPSULE:
                break
            angle = (n+.5)*math.tau/24
            point(.5+.28*math.cos(angle),.5+.28*math.sin(angle))
        assert ctrl.game.phase == Phase.PHACO
        frame("phaco")
        assert use("hydro_cannula")
        for _ in range(80):
            point(.5,.5)
            ctrl.advance_clock(1/60)
        frame("phaco-mid")
        clear_lens()
        assert ctrl.game.phase == Phase.IOL
        frame("iol")
        assert use("ovd_cannula") and ctrl.game.ovd_bag
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
        for _check in ("identity", "site", "iol_plan"): ctrl.command("verify", _check)
        ctrl.command("confirm")
        ctrl.command("prepare")
        for x,y in ctrl.game._entry_target:
            assert point(x,y,pressed=True)
        assert ctrl.game.phase == Phase.CAPSULE
        assert ctrl.game.patient.alert == "PATIENT MOTION"
        assert not point(.5,.5,pressed=True)
        frame("safety-hold")
        before_state=ctrl.game.snapshot()
        overlay.reduced_motion=True
        frame("safety-hold-reduced-motion")
        assert eye_regions["safety-hold"]!=eye_regions["safety-hold-reduced-motion"], (
            "Low-motion setting did not affect 3D eye displacement")
        assert ctrl.game.snapshot()==before_state, "Display option mutated game state"
        overlay.reduced_motion=False
        assert ctrl.command("abort")
        assert ctrl.game.phase == Phase.ABORTED
        frame("safe-abort")
        assert ReplayGame.replay_jsonl(ctrl.game.export_replay_jsonl()).ending == "SAFELY ABORTED"

        # Third deterministic scenario triggers an irreversible capsule hold.
        ctrl=Surgery3DController("capsule",seed=17)
        overlay=SurgeryHUD(ctrl)
        for _check in ("identity", "site", "iol_plan"): ctrl.command("verify", _check)
        ctrl.command("confirm")
        ctrl.command("prepare")
        entry_with_ovd()
        for n in range(24):
            if ctrl.game.phase!=Phase.CAPSULE:
                break
            angle=(n+.5)*math.tau/24
            point(.5+.28*math.cos(angle),.5+.28*math.sin(angle))
        clear_lens()
        assert ctrl.game.phase==Phase.PHACO
        assert ctrl.game.patient.alert=="CAPSULE INTEGRITY"
        assert capsule_display_state(ctrl.game)[0]
        assert not point(.5,.5,pressed=True)
        frame("capsule-safety-hold")
        assert ctrl.command("assess")
        assert ctrl.game.pending==["CAPSULE INTEGRITY"]
        frame("capsule-call-senior")
        assert ctrl.command("abort")
        assert ctrl.game.phase==Phase.ABORTED
        frame("capsule-safe-abort")
        assert ReplayGame.replay_jsonl(ctrl.game.export_replay_jsonl()).ending=="SAFELY ABORTED"

        # Fourth scenario: IOL decentration hold, 3D re-centring click, then
        # the explained "complication managed" result rendered through GL.
        ctrl=Surgery3DController("decenter",seed=17)
        overlay=SurgeryHUD(ctrl)
        for _check in PREOP_CHECKS: ctrl.command("verify", _check)
        ctrl.command("confirm")
        ctrl.command("prepare")
        entry_with_ovd()
        for n in range(24):
            if ctrl.game.phase!=Phase.CAPSULE:
                break
            angle=(n+.5)*math.tau/24
            point(.5+.28*math.cos(angle),.5+.28*math.sin(angle))
        clear_lens()
        assert use("ovd_cannula")
        assert point(.5,.5,pressed=True)
        assert ctrl.game.patient.alert=="IOL DECENTRATION"
        frame("decenter-hold")
        assert ctrl.command("assess")
        assert not ctrl.command("verify","alignment")
        frame("decenter-offset")
        assert point(.5,.5,pressed=True) and not ctrl.game._decentered
        frame("decenter-recentered")
        if eye_regions["decenter-offset"]==eye_regions["decenter-recentered"]:
            raise AssertionError("Re-centred 3D IOL not visible in eye region")
        for name in CHECKS:
            assert ctrl.command("verify",name)
        assert ctrl.game.ending=="COMPLICATION MANAGED"
        frame("decenter-managed-results")
        assert ReplayGame.replay_jsonl(ctrl.game.export_replay_jsonl()).snapshot()==ctrl.game.snapshot()

        if len(set(images.values())) != len(images):
            raise AssertionError("Distinct states rendered identical images")
        from .frametime import is_software_renderer
        renderer = atlas.ctx.info.get("GL_RENDERER", "unknown")
        kind = "software" if is_software_renderer(renderer) else "hardware"
        print(json.dumps({
            "status": f"{kind}-opengl-3d-surgery-integration-passed",
            "frame_hashes": images,
            "gl_renderer": renderer,
            "renderer_kind": kind,
            "scenario_count": 4,
            "complication_signs_distinct": sorted(sign_hashes),
            "decenter_recentering_visible": True,
            "motion_haze_center_crop_distinct": True,
            "reduced_motion_preserves_safety_hold": True,
            "contact_ring_center_region_distinct": True,
            "nearest_triangle_marker_center_crop_distinct": True,
            "capsule_center_region_healthy_vs_damage_distinct": True,
            "hud_upload_swizzle": hud_zero_copy or "copy-fallback",
            "hud_zero_copy_matches_rgba_copy": True,
            "windows_gpu_tested": sys.platform == "win32" and kind == "hardware",
            "clinical_validation": False,
        },sort_keys=True))
        return 0
    except Exception as exc:
        import traceback
        where = "; ".join(f"line {f.lineno}: {f.line}"
                          for f in traceback.extract_tb(exc.__traceback__)[-2:])
        print(f"3D SURGERY GL TEST FAILED: {type(exc).__name__}: {exc} ({where})",
              file=sys.stderr)
        return 1
    finally:
        if atlas is not None:
            atlas.close()
        pygame.quit()


if __name__=="__main__":
    raise SystemExit(main())
