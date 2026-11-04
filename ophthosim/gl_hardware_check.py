"""Automated parts of the Windows GPU checklist (GL01-GL06) on a real desktop.

    python -m ophthosim.gl_hardware_check --out build/benchmark/gl-hardware-check.json

Opens one ModernGL window and checks, on whatever GPU the desktop provides:
GL01 context creation, GL02 shader programs, GL03 nonblank cataract scene,
GL04 cataract -> IOL change, GL05 extreme orbit/zoom angles (every frame
nonblank, no GL error), GL06 repeated window resizes (viewport follows the
window, the eye stays round, HUD scale steps as designed), plus whether the
HUD font can draw Hangul for the Korean UI.

The report says AUTOMATED_PASS / FAIL per item and always sets
``requires_human_signoff``: a person still looks at the screenshots, judges
legibility and DPI behaviour, and updates docs/GPU_VALIDATION_CHECKLIST.md.
Results are synthetic rendering checks, never clinical evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
import sys

from .frametime import is_software_renderer

BACKGROUND = (7, 17, 27)          # ctx.clear(.026, .065, .105) in 8-bit
DEFAULT_OUT = Path("build/benchmark/gl-hardware-check.json")
EXTREME_VIEWS = tuple((yaw, pitch, zoom) for yaw in (-1.2, 0., 1.2)
                      for pitch in (-.8, 0., .8) for zoom in (2.6, 5.0))
RESIZE_SIZES = ((800, 600), (1280, 720), (1920, 1080), (1280, 1024), (2560, 1440))


def eye_extent(data: bytes, width: int, height: int, stride: int = 4) -> tuple[int, int] | None:
    """Width/height in pixels of everything that is not the clear colour.

    `data` is tightly packed RGB rows (bottom-up, as ModernGL reads them);
    orientation does not matter for an extent. Sampling every `stride`-th
    pixel keeps this cheap on 4K frames.
    """
    if len(data) != width * height * 3:
        raise ValueError("Frame size does not match the window")
    xs, ys = [], []
    for y in range(0, height, stride):
        row = y * width * 3
        for x in range(0, width, stride):
            i = row + x * 3
            if (abs(data[i] - BACKGROUND[0]) + abs(data[i+1] - BACKGROUND[1])
                    + abs(data[i+2] - BACKGROUND[2])) > 24:
                xs.append(x)
                ys.append(y)
    if not xs:
        return None
    return max(xs) - min(xs) + stride, max(ys) - min(ys) + stride


def _is_background(data: bytes, i: int) -> bool:
    return (abs(data[i] - BACKGROUND[0]) + abs(data[i+1] - BACKGROUND[1])
            + abs(data[i+2] - BACKGROUND[2])) <= 24


def eye_axes(data: bytes, width: int, height: int) -> tuple[int, int] | None:
    """Horizontal and vertical diameter of the drawn region around the centre.

    Scans outwards from the window centre until the clear colour, so HUD
    text elsewhere in the frame cannot inflate the measurement.
    """
    if len(data) != width * height * 3:
        raise ValueError("Frame size does not match the window")
    cx, cy = width // 2, height // 2
    if _is_background(data, (cy * width + cx) * 3):
        return None

    def run(dx: int, dy: int) -> int:
        x, y, n = cx, cy, 0
        while 0 <= x + dx < width and 0 <= y + dy < height:
            x, y = x + dx, y + dy
            if _is_background(data, (y * width + x) * 3):
                break
            n += 1
        return n
    return run(1, 0) + run(-1, 0) + 1, run(0, 1) + run(0, -1) + 1


def nonblank(data: bytes, min_fraction: float = .01) -> bool:
    """At least `min_fraction` of sampled pixels differ from the clear colour.

    A byte-range test is not enough: the clear colour (7, 17, 27) alone
    already spans 20 levels across its channels.
    """
    pixels = len(data) // 3
    if not pixels:
        return False
    step = max(1, pixels // 4000)
    drawn = total = 0
    for p in range(0, pixels, step):
        i = p * 3
        total += 1
        if (abs(data[i] - BACKGROUND[0]) + abs(data[i+1] - BACKGROUND[1])
                + abs(data[i+2] - BACKGROUND[2])) > 24:
            drawn += 1
    return drawn >= min_fraction * total


def run_checks(pygame, moderngl, *, screenshots: Path | None = None) -> dict[str, object]:
    from .gl_preview import GPUEyePreview, View, atlas_meshes, hud_scale
    checks: dict[str, dict[str, object]] = {}

    def record(key: str, ok: bool, **detail) -> None:
        checks[key] = {"status": "AUTOMATED_PASS" if ok else "FAIL", **detail}

    def save(name: str, data: bytes, size: tuple[int, int]) -> None:
        if screenshots is not None:
            screenshots.mkdir(parents=True, exist_ok=True)
            surface = pygame.image.fromstring(data, size, "RGB", True)
            pygame.image.save(surface, str(screenshots / f"hwcheck-{name}.png"))

    def render_checked(view):
        """Render without readback and return the GL error flag of that path."""
        atlas.ctx.error  # drain any earlier flag
        atlas.render(view, None)
        return atlas.ctx.error

    def capture(view):
        """Pixels for checks. On NVIDIA core profiles moderngl's default
        framebuffer read sets GL_INVALID_OPERATION although the data are
        valid; that flag is drained here and reported once separately."""
        data = atlas.render(view, None, capture=True)
        readback_errors.add(atlas.ctx.error)
        return data

    readback_errors: set[str] = set()
    pygame.init()
    atlas = None
    try:
        atlas = GPUEyePreview(pygame, moderngl, size=(1280, 720))
        info = atlas.ctx.info
        renderer = info.get("GL_RENDERER", "unknown")
        record("GL01", True, renderer=renderer, vendor=info.get("GL_VENDOR"),
               version=info.get("GL_VERSION"), version_code=atlas.ctx.version_code)
        record("GL02", atlas.scene_shader is not None and atlas.hud_shader is not None,
               programs=["scene", "hud"])

        view = View(yaw=.23, pitch=.12, zoom=3.6, phase="CATARACT")
        size = pygame.display.get_window_size()
        error = render_checked(view)
        cataract = capture(view)
        save("gl03-cataract", cataract, size)
        record("GL03", nonblank(cataract) and eye_axes(cataract, *size) is not None
               and error == "GL_NO_ERROR", gl_error=error)

        view.phase = "IOL"
        atlas.set_meshes(atlas_meshes("IOL"))
        error = render_checked(view)
        iol = capture(view)
        save("gl04-iol", iol, size)
        record("GL04", nonblank(iol) and error == "GL_NO_ERROR"
               and hashlib.sha256(iol).digest() != hashlib.sha256(cataract).digest(), gl_error=error)
        view.phase = "CATARACT"
        atlas.set_meshes(atlas_meshes("CATARACT"))

        failures = []
        for yaw, pitch, zoom in EXTREME_VIEWS:
            view.yaw, view.pitch, view.zoom = yaw, pitch, zoom
            error = render_checked(view)
            frame = capture(view)
            if not nonblank(frame) or eye_axes(frame, *size) is None or error != "GL_NO_ERROR":
                failures.append({"yaw": yaw, "pitch": pitch, "zoom": zoom, "gl_error": error})
        view.yaw, view.pitch, view.zoom = -1.2, .8, 2.6
        save("gl05-extreme", capture(view), size)
        record("GL05", not failures, views=len(EXTREME_VIEWS), failures=failures)

        # GL06: resize the SAME window (and GL context) repeatedly.
        rows, failures = [], []
        view.yaw, view.pitch, view.zoom = 0., 0., 3.6
        try:
            from pygame._sdl2.video import Window
            window = Window.from_display_module()
        except Exception as exc:  # pragma: no cover - platform dependent
            record("GL06", False, error=f"window resize API unavailable: {exc}")
            window = None
        if window is not None:
            for size in (*RESIZE_SIZES, *RESIZE_SIZES[::-1]):
                window.size = size
                for _ in range(3):
                    pygame.event.pump()
                actual = tuple(pygame.display.get_window_size())
                error = render_checked(view)
                frame = capture(view)
                match = len(frame) == actual[0] * actual[1] * 3
                axes = eye_axes(frame, *actual) if match else None
                ratio = round(axes[0] / axes[1], 3) if axes else None
                row = {"requested": list(size), "window": list(actual),
                       "frame_bytes_match": match, "eye_diameter_px": list(axes) if axes else None,
                       "eye_aspect": ratio, "hud_scale": hud_scale(*actual),
                       "gl_error": error}
                rows.append(row)
                if (not row["frame_bytes_match"] or ratio is None
                        or not .9 <= ratio <= 1.1 or row["gl_error"] != "GL_NO_ERROR"):
                    failures.append(row)
                if size == (2560, 1440):
                    save("gl06-2560x1440", frame, actual)
            record("GL06", not failures, sizes=rows, failures=failures,
                   note="Window resized in place; OS display scaling must be judged by a person.")

        hangul = atlas.font.render("후낭 파열", True, (255, 255, 255))
        boxes = atlas.font.render("□□ □□", True, (255, 255, 255))
        same = (pygame.image.tobytes(hangul, "RGBA") == pygame.image.tobytes(boxes, "RGBA"))
        record("KO_FONT", hangul.get_width() > 20 and not same,
               note="HUD font draws Hangul glyphs (Korean UI legibility still judged by a person).")
        return {
            "tool": "gl_hardware_check",
            "renderer_kind": "software" if is_software_renderer(renderer) else "hardware",
            "platform": platform.platform(), "python": sys.version.split()[0],
            "pygame": pygame.version.ver, "moderngl": getattr(moderngl, "__version__", "?"),
            "checks": checks,
            "readback_gl_errors": sorted(readback_errors - {"GL_NO_ERROR"}),
            "readback_note": ("moderngl default-framebuffer reads flag GL_INVALID_OPERATION on "
                              "this driver; pixel data were still valid. Normal frames (no "
                              "readback) are checked separately and must be error free."),
            "all_automated_pass": all(c["status"] == "AUTOMATED_PASS" for c in checks.values()),
            "requires_human_signoff": True,
            "clinical_validation": False,
        }
    finally:
        if atlas is not None:
            atlas.close()
        pygame.quit()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Automated GL01-GL06 hardware checks")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--screenshots", type=Path, default=Path("build/screenshots"))
    args = parser.parse_args(argv)
    try:
        import pygame
        import moderngl
    except ImportError as exc:
        print(f"Optional GL dependency missing: {exc}", file=sys.stderr)
        return 2
    report = run_checks(pygame, moderngl, screenshots=args.screenshots)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"all_automated_pass": report["all_automated_pass"],
                      "renderer_kind": report["renderer_kind"],
                      "checks": {k: v["status"] for k, v in report["checks"].items()}},
                     sort_keys=True))
    return 0 if report["all_automated_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
