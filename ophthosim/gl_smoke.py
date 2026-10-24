"""SDL/Xvfb + Mesa OpenGL smoke test, intentionally separate from unit tests.

This can validate shader compilation and framebuffer output on Linux software
OpenGL. It cannot validate physical Windows GPU drivers or surgical fidelity.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import statistics
import sys
import time


def main() -> int:
    try:
        import pygame
        import moderngl
        from .gl_preview import GPUEyePreview, View, atlas_meshes
        from .picking3d import project_point
    except ImportError as exc:
        print(f"GL smoke requires pygame and moderngl: {exc}",file=sys.stderr)
        return 2

    pygame.init()
    atlas = None
    try:
        atlas = GPUEyePreview(pygame, moderngl, size=(800, 600))
        view = View(yaw=0, pitch=0, zoom=3.6)
        records = []
        for phase in ("CATARACT", "IOL"):
            view.phase = phase
            atlas.set_meshes(atlas_meshes(phase))
            # Inspect a projected point on the iris. Does not change state.
            hit_pos = project_point((.5,0,.03),800,600,0,0,3.6)
            assert hit_pos is not None
            hit = atlas.select(tuple(int(round(v)) for v in hit_pos), view)
            if hit is None or hit.name != "iris" or hit.face_index < 0:
                raise AssertionError("Triangle BVH did not pick an actual iris face")
            if abs(sum(hit.barycentric)-1.) > 1e-8:
                raise AssertionError("Invalid triangle barycentric coordinates")
            center = atlas.select((399,299), view)
            expected = "cloudy lens" if phase == "CATARACT" else "IOL"
            if center is None or center.name != expected or center.face_index < 0:
                raise AssertionError("Triangle BVH did not pick the intended lens")
            if not all(-1e-9 <= b <= 1.+1e-9 for b in center.barycentric):
                raise AssertionError("Invalid lens triangle barycentric coordinates")
            frame = atlas.render(view, None, capture=True)
            if not frame or len(frame) != 800 * 600 * 3:
                raise AssertionError("OpenGL framebuffer readback invalid")
            # Nonblank image check: a gradient/colored scene should span
            # multiple byte values, unlike cleared framebuffer.
            if max(frame[::83]) - min(frame[::83]) < 20:
                raise AssertionError("OpenGL rendering appears blank")
            out = Path("build/screenshots")
            out.mkdir(parents=True, exist_ok=True)
            picture = pygame.image.fromstring(frame, (800,600), "RGB", True)
            pygame.image.save(picture, str(out / f"gl-{phase.lower()}.png"))
            records.append({"phase":phase,
                            "sha256":hashlib.sha256(frame).hexdigest(),
                            "pick":hit.name,
                            "iris_face":hit.face_index,
                            "optic_face":center.face_index,
                            "optic_label":center.name})
        # Verify the *geometry* changes in eye-only pixels, not merely
        # a HUD label, when the standalone atlas cycles 1 -> 0 -> .5 -> 1.
        view.phase="IOL"
        view.iol_deployment=1.
        atlas.clear_selection()
        unfolded=atlas.render(view,60.,capture=True)
        pt=project_point((.25,0.,-.19),800,600,0,0,3.6)
        assert pt is not None
        hit_full=atlas.select(pt,view)
        if hit_full is None or hit_full.name!="IOL":
            raise AssertionError("Unfolded optic was not triangle-pickable")
        view.key("fold")
        assert view.iol_deployment==0.
        hit_folded=atlas.select(pt,view)
        if hit_folded is not None:
            raise AssertionError("Folded IOL incorrectly retains unfolded shape")
        atlas.clear_selection()
        folded=atlas.render(view,60.,capture=True)
        view.key("fold")
        assert view.iol_deployment==.5
        middle=atlas.render(view,60.,capture=True)
        def center_bytes(frame):
            surf=pygame.image.fromstring(frame,(800,600),"RGB",True)
            return pygame.image.tobytes(surf.subsurface((300,200,200,200)),"RGB")
        if len({hashlib.sha256(center_bytes(frame)).hexdigest()
                for frame in (unfolded,folded,middle)})!=3:
            raise AssertionError("Fold/unfold not visible in central IOL geometry")
        out=Path("build/screenshots")
        for name,frame in (("gl-iol-folded",folded),("gl-iol-half",middle)):
            pygame.image.save(pygame.image.fromstring(frame,(800,600),"RGB",True),
                              str(out/f"{name}.png"))
        view.key("fold")
        assert view.iol_deployment==1.
        records.append({"phase":"IOL_FOLD_PICK",
                        "full":"IOL",
                        "folded":"miss",
                        "eye_crop_distinct":True})
        if records[0]["sha256"] == records[1]["sha256"]:
            raise AssertionError("Lens/IOL scene images were identical")
        # Tiny render performance sample is diagnostic only (software GL,
        # no 5-minute benchmark, no published FPS target claim).
        durations = []
        atlas.clear_selection()
        for i in range(20):
            view.yaw = -.5 + i/20
            start = time.perf_counter()
            atlas.render(view, None)
            durations.append((time.perf_counter()-start)*1000)
        from .frametime import is_software_renderer
        renderer = atlas.ctx.info.get("GL_RENDERER","unknown")
        kind = "software" if is_software_renderer(renderer) else "hardware"
        print(json.dumps({"status":f"{kind}-opengl-smoke-passed",
                          "renderer":renderer,
                          "renderer_kind":kind,
                          "version":atlas.ctx.version_code,
                          "frames":records,
                          "mean_frame_ms":round(statistics.mean(durations),2),
                          "claim_windows_gpu_tested":sys.platform == "win32" and kind == "hardware"},
                         sort_keys=True))
        return 0
    except Exception as exc:
        print(f"OPENGL SMOKE FAILED: {type(exc).__name__}: {exc}",file=sys.stderr)
        return 1
    finally:
        if atlas is not None:
            atlas.close()
        pygame.quit()


if __name__ == "__main__":
    raise SystemExit(main())
