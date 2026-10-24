"""Contents of the displays inside the 3D operating room.

Each function paints a pygame surface from the authoritative Game snapshot
(read-only): the vital-signs monitor, the phaco console, the surgical video
feed and the texture on the patient's eye. The video and the eye reuse the
2D procedural eye renderer, so complications and bleeding look the same in
every view. The phaco console shows qualitative bars only: no device
settings (docs/SAFETY.md).
"""
from __future__ import annotations

from .engine import Phase
from .i18n import t
from .room3d import SCREEN_PIXELS
from .signals import sample_trace

FONT_NAMES = 'malgungothic,applesdgothicneo,notosanscjkkr,nanumgothic,segoeui'
BG = (6, 10, 14)
GREEN = (92, 232, 140)
CYAN = (96, 214, 238)
AMBER = (246, 196, 104)
RED = (246, 98, 112)
TEXT = (226, 236, 242)
MUTED = (132, 156, 170)
BAR_KEYS = ("irrigation", "ultrasound", "vacuum", "flow")
BAR_COLOURS = (CYAN, AMBER, (196, 120, 246), GREEN)

_FONTS: dict[tuple[int, int, bool], object] = {}


_HOOKED: set[int] = set()


def _forget() -> None:
    """pygame.quit() invalidates fonts and surfaces: drop every cache."""
    _FONTS.clear()
    _CANVAS.clear()
    _HOOKED.clear()


def _hook(pg) -> None:
    if id(pg) not in _HOOKED:
        pg.register_quit(_forget)
        _HOOKED.add(id(pg))


def font(pg, size: int, bold: bool = False):
    key = (id(pg), size, bold)
    if key not in _FONTS:
        _hook(pg)
        _FONTS[key] = pg.font.SysFont(FONT_NAMES, size, bold=bold)
    return _FONTS[key]


def _text(pg, surf, text, xy, size, colour=TEXT, bold=False, anchor="topleft"):
    image = font(pg, size, bold).render(str(text), True, colour)
    rect = image.get_rect(**{anchor: xy})
    surf.blit(image, rect)
    return rect


def _trace(pg, surf, kind, rate, time_s, rect, colour):
    x, y, w, h = rect
    wave = sample_trace(kind, rate, time_s, count=max(2, w))
    pg.draw.lines(surf, colour, False,
                  [(x + i, y + h // 2 - round(v * h * .42)) for i, v in enumerate(wave)], 2)


def vitals_surface(pg, game, lang: str = "en"):
    w, h = SCREEN_PIXELS["vitals"]
    s = pg.Surface((w, h))
    s.fill(BG)
    p = game.patient
    _text(pg, s, t(lang, "ui.monitor"), (14, 8), 18, MUTED)
    _text(pg, s, t(lang, "ui.synthetic"), (w - 14, 8), 16, MUTED, anchor="topright")
    pg.draw.line(s, (40, 56, 66), (10, 36), (w - 10, 36), 1)
    rows = (("ECG", "ecg", p.heart_rate, GREEN, "HR", str(p.heart_rate)),
            ("Pleth", "pleth", p.heart_rate, CYAN, "SpO2", f"{p.spo2}"))
    for i, (label, kind, rate, colour, name, value) in enumerate(rows):
        top = 44 + i * 108
        _text(pg, s, label, (14, top), 16, colour)
        _trace(pg, s, kind, rate, game.time, (14, top + 18, w - 190, 82), colour)
        _text(pg, s, name, (w - 160, top), 18, colour)
        _text(pg, s, value, (w - 16, top + 14), 64, colour, bold=True, anchor="topright")
    top = 262
    pg.draw.line(s, (40, 56, 66), (10, top - 6), (w - 10, top - 6), 1)
    _text(pg, s, "NIBP", (14, top), 18, AMBER)
    _text(pg, s, f"{p.sbp}/{p.dbp}", (14, top + 20), 48, AMBER, bold=True)
    if p.alert:
        pg.draw.rect(s, (96, 26, 36), (w - 250, top, 236, 80), border_radius=6)
        _text(pg, s, "! " + t(lang, "alert." + p.alert), (w - 240, top + 10), 18, RED, bold=True)
        _text(pg, s, t(lang, "ui.safety_hold"), (w - 240, top + 44), 16, TEXT)
    else:
        _text(pg, s, t(lang, "ui.stable"), (w - 16, top + 30), 26, GREEN, anchor="topright")
    return s


def phaco_levels(game, active: bool) -> dict[str, float]:
    """Qualitative bar lengths (0..1) for the console display only."""
    phase = game.phase
    if game.ending or game.patient.alert:
        return dict.fromkeys(BAR_KEYS, 0.)
    if phase == Phase.PHACO:
        return {"irrigation": .8, "ultrasound": .6 if active else 0., "vacuum": .7 if active else .25,
                "flow": .6 if active else .3}
    if phase == Phase.CORTEX:
        return {"irrigation": .8, "ultrasound": 0., "vacuum": .55 if active else .2,
                "flow": .5 if active else .25}
    if phase in (Phase.CAPSULE, Phase.IOL, Phase.ENTRY):
        return {"irrigation": .3, "ultrasound": 0., "vacuum": 0., "flow": 0.}
    return dict.fromkeys(BAR_KEYS, 0.)


def phaco_lines(game, lang: str = "en") -> list[str]:
    """Every text shown on the console (tested to contain no numbers)."""
    return [t(lang, "screen.phaco_title"), t(lang, "phase." + game.phase.value),
            *(t(lang, "screen." + key) for key in BAR_KEYS), t(lang, "screen.no_settings")]


def phaco_surface(pg, game, lang: str = "en", active: bool = False):
    w, h = SCREEN_PIXELS["phaco"]
    s = pg.Surface((w, h))
    s.fill((14, 30, 54))
    title, step, *labels, note = phaco_lines(game, lang)
    pg.draw.rect(s, (24, 58, 102), (0, 0, w, 52))
    _text(pg, s, title, (16, 10), 26, TEXT, bold=True)
    _text(pg, s, step, (w - 16, 16), 20, AMBER, anchor="topright")
    levels = phaco_levels(game, active)
    for i, (key, label, colour) in enumerate(zip(BAR_KEYS, labels, BAR_COLOURS)):
        top = 72 + i * 62
        _text(pg, s, label, (18, top), 20, TEXT)
        pg.draw.rect(s, (30, 46, 70), (18, top + 28, w - 36, 18), border_radius=9)
        width = round((w - 36) * levels[key])
        if width:
            pg.draw.rect(s, colour, (18, top + 28, width, 18), border_radius=9)
    _text(pg, s, note, (w // 2, h - 12), 15, MUTED, anchor="midbottom")
    return s


_CANVAS: dict[int, tuple] = {}     # per pygame module: (canvas, cached drape background)


def field_surfaces(pg, game, lang: str = "en", animate: bool = True):
    """(video feed, eye texture) painted by the 2D procedural eye renderer."""
    from .app import EYE_CX, EYE_CY, EYE_R, PALETTES, draw_drape, draw_tool, render_eye
    cached = _CANVAS.get(id(pg))
    if cached is None:
        background = pg.Surface((1280, 720))
        background.fill((36, 92, 104))
        draw_drape(pg, background)        # static: painted once
        _hook(pg)
        cached = _CANVAS[id(pg)] = (pg.Surface((1280, 720)), background)
    canvas, background = cached
    canvas.blit(background, (0, 0))
    render_eye(pg, canvas, game, game.time, PALETTES["default"], animate=animate)
    r = SCREEN_PIXELS["eye"][0] // 2       # 256 px: the eye inside the speculum, unscaled
    # The eye texture gets no tool glyph: the 3D hands hold real instruments.
    eye = canvas.subsurface((EYE_CX - r, EYE_CY - r, 2 * r, 2 * r)).copy()
    operating = game.phase not in (Phase.PREOP, Phase.ANESTHESIA) and not game.ending
    if game.tool and operating:
        draw_tool(pg, canvas, game.tool, (EYE_CX + 40, EYE_CY + 20))
    vw, vh = SCREEN_PIXELS["video"]
    video = canvas.subsurface((EYE_CX - vw // 2, EYE_CY - vh // 2, vw, vh)).copy()
    pg.draw.rect(video, (8, 14, 20), (0, 0, vw, 34))
    _text(pg, video, f"{t(lang, 'screen.step')}: {t(lang, 'phase.' + game.phase.value)}", (12, 6),
          18, TEXT)
    _text(pg, video, t(lang, "screen.live"), (vw - 12, 6), 18, RED, anchor="topright")
    if game.patient.alert:
        pg.draw.rect(video, (96, 26, 36), (0, vh - 40, vw, 40))
        _text(pg, video, "! " + t(lang, "alert." + game.patient.alert), (12, vh - 32), 20, TEXT,
              bold=True)
    elif game.pending:
        pg.draw.rect(video, (70, 56, 24), (0, vh - 40, vw, 40))
        _text(pg, video, t(lang, "manage.title", alert=t(lang, "alert." + game.pending[0])),
              (12, vh - 32), 20, TEXT, bold=True)
    return video, eye


SCREEN_GROUPS = (("video", "eye"), ("vitals", "phaco"))


def all_screens(pg, game, lang: str = "en", *, active: bool = False, animate: bool = True,
                group: int | None = None):
    """Paint the displays; `group` (0 or 1) paints only half of them, so a
    game loop can spread the work over alternate refresh ticks."""
    out = {}
    if group in (None, 0):
        out["video"], out["eye"] = field_surfaces(pg, game, lang, animate)
    if group in (None, 1):
        out["vitals"] = vitals_surface(pg, game, lang)
        out["phaco"] = phaco_surface(pg, game, lang, active)
    return out
