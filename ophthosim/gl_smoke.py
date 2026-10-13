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
            if not all(0. <= b <= 1. for b in center.barycentric):
                raise AssertionError("Invalid lens triangle barycentric coordinates")
            frame = atlas.render(view, 60., capture=True)
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
        if records[0]["sha256"] == records[1]["sha256"]:
            raise AssertionError("Lens/IOL scene images were identical")
        # Tiny render performance sample is diagnostic only (software GL,
        # no 5-minute benchmark, no published FPS target claim).
        durations = []
        atlas.clear_selection()
        for i in range(20):
            view.yaw = -.5 + i/20
            start = time.perf_counter()
            atlas.render(view, 60.)
            durations.append((time.perf_counter()-start)*1000)
        print(json.dumps({"status":"software-opengl-smoke-passed",
                          "renderer":atlas.ctx.info.get("GL_RENDERER","unknown"),
                          "version":atlas.ctx.version_code,
                          "frames":records,
                          "mean_frame_ms":round(statistics.mean(durations),2),
                          "claim_windows_gpu_tested":False},
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
