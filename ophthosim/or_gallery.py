"""Render the 3D operating-room gallery (the ten panels of the v4 concept).

    python -m ophthosim.or_gallery --out build/or_gallery --lang ko

Every panel is a real-time render of the procedural scene on this machine's
GPU, taken from one deterministic mid-phaco game state; panel 2 is the
playable microscope view with its HUD. The images are synthetic educational
renders, not photographs, and carry no manufacturer design or setting.
Exit code 1 if a panel is blank or two panels are identical.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

from .i18n import LANGUAGES

PANELS = (   # key, camera (None = microscope game view), KO title, KO subtitle, EN title, EN subtitle
    ("overview", "overview", "수술실 전체 환경 (3D)", "절차적 3D 모델링 수술실",
     "Operating room (3D)", "Procedurally modelled theatre"),
    ("scope", "scope", "수술 현미경 시야 (3D)", "현미경 접안 시야 · 수정체 유화 단계",
     "Microscope view (3D)", "Through the eyepieces during phaco"),
    ("patient", "patient", "환자 모델 (3D)", "수술대에 누운 환자 (멸균포 적용)",
     "Patient model (3D)", "Draped patient on the table"),
    ("microscope", "microscope", "수술 현미경 (3D)", "바닥 스탠드형 안과 현미경",
     "Surgical microscope (3D)", "Floor-stand ophthalmic microscope"),
    ("vitals", "vitals", "바이탈 모니터 (3D)", "심박·산소포화도·혈압 실시간",
     "Vital signs monitor (3D)", "Live HR, SpO2 and blood pressure"),
    ("phaco", "phaco", "수술 장비 Phaco (3D)", "상대 수준 막대 · 설정값 없음",
     "Phaco console (3D)", "Relative levels only, no settings"),
    ("monitor", "monitor", "수술 영상 모니터 (3D)", "현재 수술 시야 실시간 송출",
     "Video monitor (3D)", "Live feed of the operative field"),
    ("tray", "tray", "수술도구 세트 (3D)", "게임 기구 15종",
     "Instrument set (3D)", "The 15 game instruments"),
    ("hands", "hands", "써전 손 (3D)", "손에 든 기구가 게임 상태를 따름",
     "Surgeon's hands (3D)", "The held instrument follows the game"),
    ("views", None, "시점 예시 (3D)", "C 키로 시점 전환",
     "Viewpoints (3D)", "Press C to switch"),
)
VIEW_THUMBS = (("overview", "수술실 전경", "Room"), ("surgeon", "집도의 시점", "Surgeon"),
               ("monitor", "모니터 시점", "Monitor"))
SHEET = (1536, 1024)
LAYOUT = {   # panel key -> (x, y, w, h) on the sheet
    "overview": (0, 0, 976, 445), "scope": (976, 0, 560, 445),
    "patient": (0, 445, 307, 300), "microscope": (307, 445, 307, 300),
    "vitals": (614, 445, 307, 300), "phaco": (921, 445, 307, 300),
    "monitor": (1228, 445, 308, 300),
    "tray": (0, 745, 640, 279), "hands": (640, 745, 360, 279), "views": (1000, 745, 536, 279),
}


def _fill(pg, image, size):
    """Scale `image` to cover `size`, centre-cropping the overflow."""
    w, h = image.get_size()
    tw, th = size
    scale = max(tw / w, th / h)
    scaled = pg.transform.smoothscale(image, (math.ceil(w * scale), math.ceil(h * scale)))
    sw, sh = scaled.get_size()
    return scaled.subsurface(((sw - tw) // 2, (sh - th) // 2, tw, th)).copy()


def _caption(pg, surf, number, title, subtitle, fonts):
    big, small = fonts
    lines = (big.render(f"{number}. {title}", True, (255, 255, 255)),
             small.render(subtitle, True, (226, 232, 238)))
    w = max(line.get_width() for line in lines) + 24
    h = sum(line.get_height() for line in lines) + 14
    box = pg.Surface((w, h), pg.SRCALPHA)
    box.fill((10, 16, 24, 196))
    surf.blit(box, (8, 8))
    surf.blit(lines[0], (20, 13))
    surf.blit(lines[1], (20, 15 + lines[0].get_height()))


def drive_to_phaco(controller, width: int, height: int):
    """Deterministic mid-phaco state reached with real 3D clicks."""
    from .engine import Phase
    from .input3d import eye_to_pixel
    g = controller.game

    def point(x, y, fresh=False):
        pixel = eye_to_pixel(x, y, controller.tool_depth, width, height, controller.view)
        return pixel is not None and controller.pointer(*pixel, width, height, fresh_press=fresh)

    def use(tool, x=.5, y=.5):
        controller.command("tool", tool)
        return point(x, y, True)

    for item in ("identity", "site", "iol_plan"):
        controller.command("verify", item)
    controller.command("confirm")
    controller.command("prepare")
    for index, (x, y) in enumerate(g._entry_target):
        point(x, y, True)
        if index == 0:
            use("ovd_cannula")
    for n in range(24):
        if g.phase != Phase.CAPSULE:
            break
        a = (n + .5) * math.tau / 24
        point(.5 + .28 * math.cos(a), .5 + .28 * math.sin(a))
    use("hydro_cannula")
    for _ in range(110):
        point(.5, .5)
        controller.advance_clock(1 / 60)
    if g.phase != Phase.PHACO:
        raise AssertionError(f"Gallery state not in PHACO: {g.phase}")
    return g


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Render the 3D operating-room gallery")
    parser.add_argument("--out", default="build/or_gallery")
    parser.add_argument("--lang", choices=list(LANGUAGES), default="ko")
    ns = parser.parse_args(argv)
    try:
        import pygame
        import moderngl
    except ImportError:
        print("Install: python -m pip install -r requirements-3d.txt", file=sys.stderr)
        return 2
    from .gl_preview import AnatomyAppearance, GPUEyePreview, atlas_meshes
    from .gl_room import RoomRenderer
    from .gl_surgery import SurgeryHUD, room_frame
    from .input3d import Surgery3DController
    from .iol3d import iol_visual_deployment
    from .tool3d import visible_stylus
    from .complication3d import complication_visuals
    from .capsule3d import capsule_display_state
    from .vision3d import visual_feedback

    out = Path(ns.out)
    out.mkdir(parents=True, exist_ok=True)
    W, H = 1280, 720
    pygame.init()
    atlas = room = None
    try:
        atlas = GPUEyePreview(pygame, moderngl, size=(W, H))
        room = RoomRenderer(atlas.ctx, moderngl, pygame)
        controller = Surgery3DController("normal", seed=7)
        game = drive_to_phaco(controller, W, H)
        hud = SurgeryHUD(controller)
        hud.lang = ns.lang
        room_frame(room, game, ns.lang, pygame)
        renders = {}

        def grab(data):
            if data is None or len(data) != W * H * 3:
                raise AssertionError("Frame readback failed")
            return pygame.image.fromstring(data, (W, H), "RGB", True)

        cameras = {key: cam for key, cam, *_ in PANELS if cam} | {k: k for k, *_ in VIEW_THUMBS}
        for key, camera in cameras.items():
            renders[key] = grab(atlas.render_room(room, camera, None, capture=True))
        atlas.set_meshes(atlas_meshes(controller.view.phase))
        e = game.eye
        capsule_on, damage = capsule_display_state(game)
        renders["microscope_view"] = grab(atlas.render(
            controller.view, None, capture=True, overlay=hud,
            appearance=AnatomyAppearance(e.opacity, e.cortex, e.iol_alignment,
                                         iol_visual_deployment(game), damage, capsule_on),
            tool_pose=visible_stylus(controller), vision=visual_feedback(game),
            complications=complication_visuals(game)))
        hashes = {}
        for key, image in renders.items():
            raw = pygame.image.tobytes(image, "RGB")
            sample = raw[::997]
            if max(sample) - min(sample) < 40:
                raise AssertionError(f"Panel looks blank: {key}")
            hashes[key] = hashlib.sha256(raw).hexdigest()
            pygame.image.save(image, str(out / f"panel-{key}.png"))
        if len(set(hashes.values())) != len(hashes):
            raise AssertionError("Two gallery panels rendered identically")

        from .screens3d import font
        fonts = (font(pygame, 22, True), font(pygame, 15))
        sheet = pygame.Surface(SHEET)
        sheet.fill((12, 14, 18))
        ko = ns.lang == "ko"
        for number, (key, _cam, kt, ks, et, es) in enumerate(PANELS, 1):
            x, y, w, h = LAYOUT[key]
            if key == "views":
                tile = pygame.Surface((w, h))
                tw = w // 3
                for i, (thumb, kl, el) in enumerate(VIEW_THUMBS):
                    part = _fill(pygame, renders[thumb], (tw - 4, h - 4))
                    label = fonts[0].render(kl if ko else el, True, (255, 255, 255))
                    plate = pygame.Surface((label.get_width() + 20, label.get_height() + 8),
                                           pygame.SRCALPHA)
                    plate.fill((10, 16, 24, 210))
                    part.blit(plate, ((part.get_width() - plate.get_width()) // 2, h - 54))
                    part.blit(label, ((part.get_width() - label.get_width()) // 2, h - 50))
                    tile.blit(part, (i * tw + 2, 2))
            else:
                tile = _fill(pygame, renders[key], (w - 4, h - 4))
            _caption(pygame, tile, number, kt if ko else et, ks if ko else es, fonts)
            sheet.blit(tile, (x + 2, y + 2))
        sheet_path = out / f"or_gallery_{ns.lang}.png"
        pygame.image.save(sheet, str(sheet_path))
        from .frametime import is_software_renderer
        renderer = atlas.ctx.info.get("GL_RENDERER", "unknown")
        print(json.dumps({
            "status": "operating-room-gallery-rendered",
            "renderer": renderer,
            "renderer_kind": "software" if is_software_renderer(renderer) else "hardware",
            "panels": sorted(hashes), "sheet": str(sheet_path), "synthetic": True,
        }, ensure_ascii=False, sort_keys=True))
        return 0
    except Exception as exc:
        print(f"OR GALLERY FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    finally:
        if room is not None:
            room.release()
        if atlas is not None:
            atlas.close()
        pygame.quit()


if __name__ == "__main__":
    raise SystemExit(main())
