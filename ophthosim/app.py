"""Pygame presentation for OphthoSim-AI.

Visuals are stylized, procedural 2.5D illustrations, NOT clinical graphics.
Requires pygame, and is intentionally independent of the headless simulation:
every screen is drawn from the same engine snapshot, and the UI can only
issue the engine's semantic actions.
"""
from __future__ import annotations

from array import array
import argparse
import math
import random
import sys

from .autosave import AUTOSAVE, BackgroundAutosave, load_autosave
from .engine import (CASES, COMPLICATIONS, DIFFICULTIES, ENDING_COMPLETE, ENDING_FAILED,
                     ENDING_MANAGED, ENDING_UNRESOLVED, FINAL_CHECKS, MAIN_INCISION,
                     PREOP_CHECKS, PROFILES, SITUATION_TOOLS, STEP_TOOLS, TOOL_NAMES,
                     USE_TOOLS, Phase)
from .i18n import LANGUAGES, t
from .preview3d import draw_preview
from .replay import ReplayGame as Game
from .report import explain, save_session, timeline
from .signals import sample_trace

WIDTH, HEIGHT = 1280, 720
EYE_CX, EYE_CY, EYE_R = 640, 366, 222
FIELD = (275, 75, 690, 620)
TRAY = (292, 597, 656, 50)     # instrument tray: procedure row + situation row
TRAY_ROWS = (STEP_TOOLS, SITUATION_TOOLS)
BG = (7, 18, 30)
PANEL = (16, 32, 47)
PANEL2 = (20, 42, 58)
TEXT = (221, 234, 241)
MUTED = (144, 170, 183)
CYAN = (106, 211, 227)
MINT = (95, 220, 167)
AMBER = (238, 182, 106)
RED = (239, 114, 133)

# Display palettes. Every state is also given as text, never colour alone.
PALETTES = {
    'default': {'bg': BG, 'panel': PANEL, 'panel2': PANEL2, 'text': TEXT, 'muted': MUTED,
                'accent': CYAN, 'ok': MINT, 'warn': AMBER, 'bad': RED},
    'contrast': {'bg': (0, 0, 0), 'panel': (0, 0, 0), 'panel2': (24, 24, 24),
                 'text': (255, 255, 255), 'muted': (225, 225, 225), 'accent': (0, 230, 255),
                 'ok': (120, 255, 160), 'warn': (255, 220, 0), 'bad': (255, 90, 90)},
    # Okabe-Ito colour-vision-deficiency-safe hues.
    'cvd': {'bg': BG, 'panel': PANEL, 'panel2': PANEL2, 'text': TEXT, 'muted': MUTED,
            'accent': (86, 180, 233), 'ok': (0, 158, 115), 'warn': (240, 228, 66),
            'bad': (213, 94, 0)},
}

# Synthetic microscope focus targets per phase (visual only, no scoring).
FOCUS_TARGET = {Phase.ENTRY: .3, Phase.CAPSULE: .42, Phase.PHACO: .55,
                Phase.CORTEX: .6, Phase.IOL: .5, Phase.CLOSE: .32}
# Cross-section depth of the active task (0 = cornea, 1 = posterior lens).
TASK_DEPTH = {Phase.ENTRY: .08, Phase.CAPSULE: .34, Phase.PHACO: .55,
              Phase.CORTEX: .7, Phase.IOL: .52, Phase.CLOSE: .1}
FONT_NAMES = 'malgungothic,applesdgothicneo,notosanscjkkr,nanumgothic,segoeui'

# Kept for backwards compatibility with older imports/tests.
PHASE_COPY = {phase: (t('en', f'phase.{phase.value}').upper(), t('en', f'goal.{phase.value}'))
              for phase in Phase}


def to_eye(pos):
    return ((pos[0] - EYE_CX) / (EYE_R * 2) + .5,
            (pos[1] - EYE_CY) / (EYE_R * 2) + .5)


def to_screen(point):
    return (round(EYE_CX + (point[0] - .5) * EYE_R * 2),
            round(EYE_CY + (point[1] - .5) * EYE_R * 2))


_TEXTURES: dict[tuple[int, int], object] = {}
LIMBUS_R = 152            # cornea/limbus radius in canvas pixels


def _polar(r, a):
    return (round(EYE_CX + r * math.cos(a)), round(EYE_CY + r * math.sin(a)))


def eye_texture(pg):
    """Static procedural eye: sclera with conjunctival vessels, limbus, iris
    stroma with crypts and collarette. Built once per pygame session."""
    key = (id(pg), EYE_R)
    if key in _TEXTURES:
        return _TEXTURES[key]
    size = EYE_R * 2 + 30
    tex = pg.Surface((size, size), pg.SRCALPHA)
    cx = cy = size // 2
    rng = random.Random(1307)            # fixed: identical texture every run
    for r in range(EYE_R, LIMBUS_R - 2, -3):
        blend = (EYE_R - r) / (EYE_R - LIMBUS_R)
        v = int(206 + 26 * blend)
        pg.draw.circle(tex, (v, v - 6, v - 14), (cx, cy), r)
    # Conjunctival / episcleral vessels: fine, slowly curving and fading
    # towards the limbus, with a few short side branches.
    vessels = pg.Surface((size, size), pg.SRCALPHA)
    for _ in range(18):
        a = rng.uniform(0, math.tau)
        r = EYE_R - 1
        bend = rng.uniform(-.012, .012)
        points = []
        while r > LIMBUS_R + 14:
            points.append((cx + r * math.cos(a), cy + r * math.sin(a)))
            r -= 4
            a += bend + rng.uniform(-.006, .006)
        for k in range(1, len(points)):
            fade = 1 - k / len(points)
            pg.draw.aaline(vessels, (168, 70, 72, round(40 + 90 * fade)), points[k - 1], points[k])
        if len(points) > 6 and rng.random() < .6:
            k = rng.randrange(2, len(points) // 2)
            side = rng.choice((-1, 1)) * .5
            bx, by = points[k]
            pg.draw.aaline(vessels, (168, 70, 72, 70), (bx, by),
                           (bx + 16 * math.cos(a + side + math.pi), by + 16 * math.sin(a + side + math.pi)))
    tex.blit(vessels, (0, 0))
    # Limbus: soft grey-blue transition ring.
    for i, r in enumerate(range(LIMBUS_R + 6, LIMBUS_R - 4, -1)):
        pg.draw.circle(tex, (96 - i * 3, 118 - i * 2, 128 - i, 255), (cx, cy), r)
    # Iris stroma: radial fibres in two tones, crypts and a collarette ring.
    for r in range(LIMBUS_R - 4, 98, -3):
        tt = (LIMBUS_R - 4 - r) / (LIMBUS_R - 102)
        pg.draw.circle(tex, (int(30 + 26 * tt), int(84 + 30 * tt), int(88 + 22 * tt)), (cx, cy), r)
    for i in range(240):
        a = i * math.tau / 240
        inner = 104 + 3 * math.sin(i * 1.73)
        outer = LIMBUS_R - 6 + 3 * math.sin(i * .67)
        tone = (60 + (i % 5) * 7, 118 + (i % 4) * 7, 116 + (i % 3) * 6)
        pg.draw.line(tex, tone, (cx + inner * math.cos(a), cy + inner * math.sin(a)),
                     (cx + outer * math.cos(a), cy + outer * math.sin(a)), 1)
    for _ in range(34):
        a = rng.uniform(0, math.tau)
        r = rng.uniform(116, 140)
        w, h = rng.uniform(5, 11), rng.uniform(3, 6)
        crypt = pg.Surface((24, 24), pg.SRCALPHA)
        pg.draw.ellipse(crypt, (22, 52, 58, 170), (12 - w / 2, 12 - h / 2, w, h))
        tex.blit(pg.transform.rotate(crypt, -math.degrees(a)),
                 (cx + r * math.cos(a) - 12, cy + r * math.sin(a) - 12))
    collarette = [(cx + (124 + 3 * math.sin(k * .9)) * math.cos(k * math.tau / 90),
                   cy + (124 + 3 * math.sin(k * .9)) * math.sin(k * math.tau / 90)) for k in range(90)]
    pg.draw.lines(tex, (128, 172, 156), True, collarette, 2)
    _TEXTURES[key] = tex
    return tex


def _drape_layer(pg):
    """Static drape sheet with the eye opening (built once per session)."""
    key = (id(pg), 'drape')
    if key not in _TEXTURES:
        fx, fy, fw, fh = FIELD
        drape = pg.Surface((fw, fh), pg.SRCALPHA)
        drape.fill((36, 92, 104, 255))
        for k in range(0, fw + 60, 22):
            pg.draw.line(drape, (44, 104, 116, 255), (k, 0), (k - 60, fh), 1)
        mask = pg.Surface((fw, fh), pg.SRCALPHA)
        pg.draw.rect(mask, (255, 255, 255, 255), (0, 0, fw, fh), border_radius=16)
        pg.draw.circle(mask, (0, 0, 0, 0), (EYE_CX - fx, EYE_CY - fy), EYE_R + 34)
        drape.blit(mask, (0, 0), special_flags=pg.BLEND_RGBA_MIN)
        _TEXTURES[key] = drape
    return _TEXTURES[key]


def draw_drape(pg, surf, palette=None):
    """Sterile drape and lid speculum around the operative eye (synthetic)."""
    fx, fy, fw, fh = FIELD
    surf.blit(_drape_layer(pg), (fx, fy))
    # Lid margins retracted by the speculum (pink skin edge).
    pg.draw.circle(surf, (186, 128, 124), (EYE_CX, EYE_CY), EYE_R + 30, 10)
    # Wire lid speculum: blades hooked over the upper and lower lid margins,
    # arms running out to the nasal side under the drape.
    surf.set_clip(pg.Rect(FIELD))
    steel = (196, 204, 212)
    ring = (EYE_CX - EYE_R - 34, EYE_CY - EYE_R - 34, (EYE_R + 34) * 2, (EYE_R + 34) * 2)
    for mid in (math.pi / 2, -math.pi / 2):          # pygame arcs: y axis up
        pg.draw.arc(surf, steel, ring, mid - .55, mid + .55, 4)
        for end in (mid - .55, mid + .55):
            x = EYE_CX + (EYE_R + 32) * math.cos(end)
            y = EYE_CY - (EYE_R + 32) * math.sin(end)
            if x < EYE_CX:
                pg.draw.line(surf, steel, (x, y), (fx + 14, EYE_CY + (y - EYE_CY) * .35), 3)
    surf.set_clip(None)


def _incision_point(r=LIMBUS_R):
    a = math.atan2(MAIN_INCISION[1] - .5, MAIN_INCISION[0] - .5)
    return _polar(r, a), a


def render_eye(pg, surf, model, clock_s, palette=None, *, animate=True):
    """Procedural operative field: textured eye, lens layers, blood and
    complication signs. Synthetic illustration, not clinical imagery."""
    c = palette or PALETTES['default']
    center = (EYE_CX, EYE_CY)
    eye = model.eye
    kinds = {a['kind'] for a in model.alerts}
    live = model.patient.alert
    pending = set(model.pending)
    flags = model.flags
    # Zonular weakness: the whole lens/bag sits off-centre.
    shift = 0
    if 'zonular_dialysis' in flags:
        shift = 22
    elif live == 'ZONULAR WEAKNESS' or 'ZONULAR WEAKNESS' in pending:
        shift = 14
    pg.draw.circle(surf, (5, 10, 18), (center[0]+7, center[1]+10), EYE_R+15)
    tex = eye_texture(pg)
    surf.blit(tex, (EYE_CX - tex.get_width() // 2, EYE_CY - tex.get_height() // 2))
    # A constricted pupil narrows the visible (and usable) lens field.
    pupil = max(.3, min(1.0, eye.pupil))
    pupil_r = round(104 * (.25 + .75 * pupil))
    if pupil < 1:
        pg.draw.circle(surf, (52, 104, 106), center, 104)
    pg.draw.circle(surf, (10, 17, 27), center, pupil_r)
    # Red reflex: the fundus glow through the clearing lens (lost with SCH).
    glow = (1 - eye.opacity * .85) * eye.red_reflex
    if glow > .05 and model.phase not in (Phase.PREOP, Phase.ANESTHESIA):
        reflex = pg.Surface((pupil_r * 2, pupil_r * 2), pg.SRCALPHA)
        for k in range(pupil_r, 0, -4):
            alpha = round(150 * glow * (1 - k / pupil_r * .6))
            pg.draw.circle(reflex, (196, 82, 44, alpha), (pupil_r + shift, pupil_r), k)
        surf.blit(reflex, (EYE_CX - pupil_r, EYE_CY - pupil_r))
    if eye.red_reflex < .5 and model.phase not in (Phase.PREOP, Phase.ANESTHESIA):
        # Suprachoroidal haemorrhage: dark dome rising behind the lens.
        dome = pg.Surface((pupil_r * 2, pupil_r * 2), pg.SRCALPHA)
        pg.draw.circle(dome, (70, 22, 26, 210), (round(pupil_r * .6), round(pupil_r * 1.4)),
                       round(pupil_r * 1.05))
        mask = pg.Surface((pupil_r * 2, pupil_r * 2), pg.SRCALPHA)
        pg.draw.circle(mask, (255, 255, 255, 255), (pupil_r, pupil_r), pupil_r)
        dome.blit(mask, (0, 0), special_flags=pg.BLEND_RGBA_MIN)
        surf.blit(dome, (EYE_CX - pupil_r, EYE_CY - pupil_r))
    # Synthetic cataract opacity. Display rings shrink smoothly with progress.
    if eye.opacity > 0:
        alpha = int(eye.opacity*188)
        overlay = pg.Surface((420,420),pg.SRCALPHA)
        pg.draw.circle(overlay, (200,187,136,alpha), (210+shift,210), round(99*pupil_r/104))
        spin = clock_s*.005 if animate else 0.
        for i in range(12):
            a = i*math.tau/12 + spin
            p = (round(210+shift+70*pupil_r/104*math.cos(a)),round(210+70*pupil_r/104*math.sin(a)))
            pg.draw.circle(overlay,(227,219,166,int(alpha*.7)),p,14+i%4*3)
        surf.blit(overlay, (EYE_CX-210,EYE_CY-210))
    if shift:
        # Equator of the subluxated lens shows in the pupil.
        pg.draw.arc(surf, (210, 214, 190), (EYE_CX - 96 + shift, EYE_CY - 96, 192, 192),
                    math.radians(120), math.radians(240), 2)
    if 'CAPSULE INTEGRITY' in kinds and model.phase not in (Phase.PREOP,):
        # Posterior capsule opening: dark gap with vitreous strands.
        veil = pg.Surface((220,220),pg.SRCALPHA)
        pg.draw.ellipse(veil,(20,24,30,160),(70,90,90,60))
        for k in range(5):
            pg.draw.arc(veil,(205,215,220,130),(60+k*8,70+k*6,100,80),.4,2.6,2)
        surf.blit(veil,(EYE_CX-110,EYE_CY-110))
    if 'RHEXIS TEAR' in kinds:
        a = math.radians(300)
        long = 'tear_extending' in flags
        start = to_screen((.5+.28*math.cos(a), .5+.28*math.sin(a)))
        end = to_screen((.5+(.46 if long else .40)*math.cos(a+.08), .5+(.46 if long else .40)*math.sin(a+.08)))
        pg.draw.line(surf, c['bad'], start, end, 3)
    if 'ctr_inserted' in flags:
        pg.draw.circle(surf, (214, 226, 232), (EYE_CX + shift, EYE_CY), 88, 1)
    if model.phase in {Phase.IOL, Phase.CLOSE, Phase.RECOVERY} and (
            eye.iol_alignment > 0 or model.phase == Phase.IOL):
        # Decentration is shown as a visible offset of the synthetic optic.
        dshift = round(70 * (1 - eye.iol_alignment)) if model.phase != Phase.IOL else 0
        overlay = pg.Surface((260,260),pg.SRCALPHA)
        pg.draw.circle(overlay,(150,231,239,72),(130,130),105)
        pg.draw.circle(overlay,(215,253,255,145),(130,130),102,2)
        pg.draw.ellipse(overlay,(180,240,246,170), (54,28,152,204),2)
        surf.blit(overlay,(EYE_CX-130+dshift+shift,EYE_CY-130))
    if 'iris_hooks_placed' in flags:
        for k in range(4):
            a = math.radians(45 + 90 * k)
            tip = _polar(pupil_r + 2, a)
            pg.draw.line(surf, (226, 232, 238), _polar(LIMBUS_R + 8, a), tip, 2)
            pg.draw.circle(surf, (226, 232, 238), tip, 3, 1)
    # Hyphema: blood layering at the bottom of the anterior chamber.
    if eye.hyphema > .02:
        layer = pg.Surface((LIMBUS_R * 2, LIMBUS_R * 2), pg.SRCALPHA)
        height = round(LIMBUS_R * 2 * min(.85, eye.hyphema * 1.1))
        top = LIMBUS_R * 2 - height
        pg.draw.rect(layer, (150, 24, 32, 185), (0, top, LIMBUS_R * 2, height))
        pg.draw.rect(layer, (110, 14, 22, 220), (0, top + height * .55, LIMBUS_R * 2, height))
        pg.draw.line(layer, (190, 60, 64, 200), (0, top), (LIMBUS_R * 2, top), 2)   # meniscus
        mask = pg.Surface((LIMBUS_R * 2, LIMBUS_R * 2), pg.SRCALPHA)
        pg.draw.circle(mask, (255, 255, 255, 255), (LIMBUS_R, LIMBUS_R), LIMBUS_R - 2)
        layer.blit(mask, (0, 0), special_flags=pg.BLEND_RGBA_MIN)
        surf.blit(layer, (EYE_CX - LIMBUS_R, EYE_CY - LIMBUS_R))
    # Iris prolapse at the main incision (darker once traumatised).
    if live == 'IRIS PROLAPSE' or 'IRIS PROLAPSE' in pending or 'iris_trauma' in flags:
        (px, py), a = _incision_point(LIMBUS_R + 12)
        tone = (98, 58, 50) if 'iris_trauma' in flags else (58, 112, 108)
        # Pupil peaked towards the wound, iris knuckle bulging out of it.
        pg.draw.polygon(surf, (10, 17, 27), [_polar(pupil_r - 6, a - .22), _polar(pupil_r + 26, a),
                                             _polar(pupil_r - 6, a + .22)])
        knuckle = pg.Surface((52, 34), pg.SRCALPHA)
        pg.draw.ellipse(knuckle, (*tone, 255), (0, 0, 52, 34))
        for k in range(7):
            pg.draw.line(knuckle, (tone[0] + 30, tone[1] + 30, tone[2] + 24, 255),
                         (8 + k * 6, 5), (12 + k * 5, 29), 1)
        pg.draw.ellipse(knuckle, (20, 40, 44, 255), (0, 0, 52, 34), 2)
        knuckle = pg.transform.rotate(knuckle, -math.degrees(a) - 90)
        surf.blit(knuckle, knuckle.get_rect(center=(px, py)))
    # Blood from the incision spreading over the cornea.
    if eye.blood_film > .02:
        (bx, by), a = _incision_point()
        film = pg.Surface((EYE_R * 2, EYE_R * 2), pg.SRCALPHA)
        ox, oy = bx - (EYE_CX - EYE_R), by - (EYE_CY - EYE_R)
        for k in range(7):
            radius = round((14 + k * 9) * (.5 + eye.blood_film))
            alpha = round(170 * eye.blood_film * (1 - k / 8))
            pg.draw.circle(film, (156, 24, 32, alpha), (round(ox - k * 9), round(oy + k * 13)), radius)
        surf.blit(film, (EYE_CX - EYE_R, EYE_CY - EYE_R))
    if live == 'WOUND LEAK RISK' or 'WOUND LEAK RISK' in pending:
        (wx, wy), _ = _incision_point(LIMBUS_R - 4)
        for k in range(4):
            pg.draw.circle(surf, (190, 228, 246), (wx + 6 + k * 6, wy + 8 + k * 10), 5 - k // 2)
    if 'wound_sutured' in flags or 'wound_closed_emergently' in flags:
        (sx, sy), a = _incision_point()
        for k in (-1, 1):
            pg.draw.line(surf, (24, 26, 30), (sx - 7, sy + k * 5 - 6), (sx + 7, sy + k * 5 + 6), 2)
    # Reflection and anterior corneal specular glint.
    transparent = pg.Surface((EYE_R*2+20,EYE_R*2+20),pg.SRCALPHA)
    pg.draw.ellipse(transparent,(240,254,255,46), (88,53,158,72))
    pg.draw.arc(transparent,(200,249,255,90),(30,35,385,380), .65, 2.35, 5)
    surf.blit(transparent,(EYE_CX-EYE_R-10,EYE_CY-EYE_R-10))
    # Corneal haze: static frosted veil (never flashing).
    if eye.cornea_clarity < 1 and model.phase not in (Phase.RECOVERY, Phase.ABORTED, Phase.FAILED):
        veil = pg.Surface((EYE_R*2, EYE_R*2), pg.SRCALPHA)
        pg.draw.circle(veil, (214, 224, 226, round(190*(1-eye.cornea_clarity))),
                       (EYE_R, EYE_R), EYE_R-4)
        surf.blit(veil, (EYE_CX-EYE_R, EYE_CY-EYE_R))
    rules = model.rules
    if model.phase == Phase.ENTRY:
        for i,pt in enumerate(model._entry_target):
            pos = to_screen(pt)
            done = i in model._entered
            pg.draw.circle(surf, c['ok'] if done else c['warn'], pos, 11, 3)
            pg.draw.circle(surf,(240,237,211),pos,3)
            if rules.guides and not done:
                pg.draw.circle(surf, c['warn'], pos, round(rules.entry_radius*EYE_R*2), 1)
    if model.phase == Phase.CAPSULE:
        for n in range(24):
            a = (n+.5)*math.tau/24
            p = to_screen((.5+math.cos(a)*.28,.5+math.sin(a)*.28))
            pg.draw.circle(surf, c['ok'] if n in eye.capsule_points else c['warn'],p,5)
        if rules.guides:
            low, high = rules.capsule_band
            if not model.ovd_chamber:
                low, high = low + .03, high - .03
            pg.draw.circle(surf, c['muted'], center, round(low*EYE_R*2), 1)
            pg.draw.circle(surf, c['muted'], center, round(high*EYE_R*2), 1)
    if model.phase in (Phase.PHACO, Phase.CORTEX) and rules.guides:
        pg.draw.circle(surf, c['muted'], center, round(model.work_radius*EYE_R*2), 1)


TOOL_STYLE = {   # (shaft colour, width, tip radius) for the cursor glyph
    'keratome': ((214, 220, 226), 3, 0), 'sideport': ((214, 220, 226), 2, 0),
    'ovd_cannula': ((180, 206, 230), 2, 2), 'cystotome': ((214, 220, 226), 2, 0),
    'forceps': ((200, 206, 214), 2, 3), 'hydro_cannula': ((170, 210, 236), 2, 2),
    'phaco': ((226, 232, 238), 6, 5), 'ia': ((200, 222, 238), 5, 4),
    'injector': ((150, 210, 226), 7, 4), 'iol_hook': ((214, 220, 226), 2, 3),
    'iris_hooks': ((226, 232, 238), 2, 3), 'ctr': ((214, 226, 232), 3, 6),
    'cautery': ((236, 170, 120), 3, 3), 'irrigation': ((170, 210, 236), 3, 3),
    'suture': ((40, 44, 52), 2, 2),
}


def draw_tool(pg, surf, tool, point):
    """Instrument held at the cursor (shaft entering from the temporal side)."""
    colour, width, tip = TOOL_STYLE.get(tool, ((219, 245, 241), 2, 3))
    x, y = round(point[0]), round(point[1])
    pg.draw.line(surf, colour, (x + 70, y + 60), (x, y), width)
    if tip:
        pg.draw.circle(surf, colour, (x, y), tip, 0 if tool in ('phaco', 'ia') else 1)


class FontSet(dict):
    """The app's fonts plus a bounded cache of rendered labels: most HUD
    text is identical from frame to frame, and re-rendering ~45 labels per
    frame cost about a quarter of the 60 fps budget."""
    LIMIT = 2048

    def __init__(self, fonts):
        super().__init__(fonts)
        self._rendered = {}
        self._wrapped = {}

    def render(self, size, text, color):
        key = (size, text, tuple(color))
        image = self._rendered.get(key)
        if image is None:
            if len(self._rendered) >= self.LIMIT:
                self._rendered.clear()
            image = self._rendered[key] = self[size].render(text, True, color)
        return image

    def wrapped(self, text, size, max_px):
        key = (text, size, max_px)
        lines = self._wrapped.get(key)
        if lines is None:
            if len(self._wrapped) >= self.LIMIT:
                self._wrapped.clear()
            lines = self._wrapped[key] = wrapped(text, font=self[size], max_px=max_px)
        return lines


def draw_text(pg, surf, fonts, text, xy, *, color=TEXT, size='base', max_chars=None):
    text = str(text) if max_chars is None else str(text)[:max_chars]
    out = (fonts.render(size, text, color) if isinstance(fonts, FontSet)
           else fonts[size].render(text, True, color))
    surf.blit(out, xy)


def rounded(pg,surf,color,rect,r=10,border=0):
    pg.draw.rect(surf,color,rect,border_radius=r,width=border)


def bar(pg,surf,x,y,w,value,color):
    rounded(pg,surf,(35,65,77),(x,y,w,8),4)
    rounded(pg,surf,color,(x,y,max(0,int(w*min(1,max(0,value)))),8),4)


def wrapped(text, width=27, font=None, max_px=None):
    """Word wrap. With `font`, wrap by rendered width (`max_px`, else `width`
    average Latin characters): Hangul glyphs are about twice as wide, so a
    character count let Korean lines spill out of their panel."""
    if font is not None:
        budget=max_px if max_px is not None else width*font.size('n')[0]
        too_long=lambda line: font.size(line)[0]>budget
    else:
        too_long=lambda line: len(line)>width
    words=str(text).split();lines=[];cur=''
    for word in words:
        if cur and too_long(cur+' '+word):
            lines.append(cur);cur=word
        else:
            cur=(cur+' '+word).strip()
    if cur:
        lines.append(cur)
    return lines


def waveform(pg, surf, origin, tick, color, heart_rate, kind='ecg', count=238):
    """Visualize synthetic patient-dependent signals, not clinical telemetry."""
    x, y = origin
    values = sample_trace(kind, heart_rate, tick, count=count)
    points = [(x+i, y-round(v*(21 if kind=='ecg' else 12)))
              for i,v in enumerate(values)]
    pg.draw.lines(surf, color, False, points, 2)


class Sounds:
    """Short synthesized tones; silently disabled if no audio device exists.

    Alerts use one gentle two-tone cue per new alert, never a repeating siren,
    and every audible state is also shown as text.
    """

    def __init__(self, pg) -> None:
        self.enabled = True
        self.tones = {}
        try:
            if not pg.mixer.get_init():
                pg.mixer.init()
            freq, size, channels = pg.mixer.get_init()
            if abs(size) != 16:
                raise RuntimeError('unsupported mixer format')
            for name, notes in (('alert', ((660, .16), (0, .05), (523, .2))),
                                ('ok', ((880, .06),)), ('end', ((523, .12), (659, .12), (784, .2)))):
                samples = array('h')
                for hz, seconds in notes:
                    count = int(freq * seconds)
                    for i in range(count):
                        fade = min(1., i / 200, (count - i) / 200) if count > 400 else 1.
                        value = int(9000 * fade * math.sin(math.tau * hz * i / freq)) if hz else 0
                        samples.extend([value] * channels)
                self.tones[name] = pg.mixer.Sound(buffer=samples.tobytes())
        except Exception:   # no device, dummy driver, unusual format
            self.tones = {}

    def play(self, name: str) -> None:
        if self.enabled and name in self.tones:
            try:
                self.tones[name].play()
            except Exception:
                pass


class App:
    def __init__(self, pg, case='normal', seed=7, scale=1.0, difficulty='standard', lang='en'):
        self.pg = pg
        self.game=Game(case,seed,difficulty)
        self.screen=pg.display.set_mode((round(WIDTH*scale),round(HEIGHT*scale)),pg.RESIZABLE)
        pg.display.set_caption('OphthoSim-AI | Cataract Microsurgery (Educational Prototype)')
        self.canvas=pg.Surface((WIDTH,HEIGHT))
        self.clock=pg.time.Clock()
        self.fonts=FontSet({
            'tiny': pg.font.SysFont(FONT_NAMES,14),
            'micro': pg.font.SysFont(FONT_NAMES,13),
            'base': pg.font.SysFont(FONT_NAMES,17),
            'medium': pg.font.SysFont(FONT_NAMES,22,bold=True),
            'title': pg.font.SysFont(FONT_NAMES,30,bold=True),
            'big': pg.font.SysFont('consolas',35,bold=True),
        })
        self.running=True
        self.cursor=(0,0)
        self._acc=0.0
        self.lang=lang if lang in LANGUAGES else 'en'
        self.message=t(self.lang,'ui.disclaimer')
        self.drag=False
        self.quality='2.5D'
        self.view_3d=False
        self.view_yaw=.2
        self.view_pitch=.13
        self.zoom=1.0
        self.focus=.45
        self.high_contrast=False
        self.colour_safe=False
        self.reduced_motion=False
        self.show_help=False
        self.sounds=Sounds(pg)
        self._alerts_heard=0
        self._ending_heard=False
        self.light=1.0
        self.autosave_path=AUTOSAVE
        self.autosaver=BackgroundAutosave()
        self._saved_phase=self.game.phase
        self._wrong_seen=0
        self._drag_phase=None

    def resume(self, path=None):
        """Replace the current case with a verified autosave (if any)."""
        try:
            self.game=load_autosave(path or self.autosave_path)
        except (OSError, ValueError) as exc:
            self.message=t(self.lang,'ui.resume_failed',error=exc.__class__.__name__)
            return False
        self._alerts_heard=len(self.game.alerts)
        self._ending_heard=bool(self.game.ending)
        self._saved_phase=self.game.phase
        self._wrong_seen=self.game.wrong_tool
        self.message=t(self.lang,'ui.resumed')
        return True

    def autosave(self, wait=False):
        """Queue a recovery point (written off the frame loop)."""
        self.autosaver.submit(self.game,self.autosave_path)
        if wait:
            self.autosaver.flush()
        self._saved_phase=self.game.phase

    # --- state helpers -------------------------------------------------
    @property
    def palette(self):
        if self.high_contrast:
            return PALETTES['contrast']
        return PALETTES['cvd' if self.colour_safe else 'default']

    def new_game(self, case=None, difficulty=None):
        self.game=Game(case or self.game.case,self.game.seed,difficulty or self.game.difficulty)
        self._alerts_heard=0
        self._ending_heard=False
        self._wrong_seen=0
        self.zoom=1.0
        self.message=t(self.lang,'ui.new_case')

    def mapped(self, raw):
        w,h=self.screen.get_size()
        if not w or not h:
            return (0,0)
        return (raw[0]*WIDTH/w,raw[1]*HEIGHT/h)

    def _crop(self):
        """Source rectangle of the field magnified by the microscope zoom."""
        fx,fy,fw,fh=FIELD
        cw,ch=fw/self.zoom,fh/self.zoom
        cx=min(max(EYE_CX,fx+cw/2),fx+fw-cw/2)
        cy=min(max(EYE_CY,fy+ch/2),fy+fh-ch/2)
        return cx-cw/2,cy-ch/2,cw,ch

    def unzoom(self, point):
        """Canvas point inside the zoomed field -> unzoomed canvas point."""
        if self.zoom == 1.0:
            return point
        fx,fy,_,_=FIELD
        x0,y0,_,_=self._crop()
        return (x0+(point[0]-fx)/self.zoom, y0+(point[1]-fy)/self.zoom)

    def focus_error(self):
        if self.game.difficulty == 'tutorial':
            return 0.0      # tutorial auto-focus
        target=FOCUS_TARGET.get(self.game.phase)
        return 0.0 if target is None else abs(self.focus-target)

    # --- input ------------------------------------------------------------
    def dispatch(self,event):
        pg=self.pg
        g=self.game
        if event.type==pg.QUIT:
            self.autosave()
            self.running=False
        elif event.type==pg.VIDEORESIZE:
            self.screen=pg.display.set_mode((max(640,event.w),max(360,event.h)),pg.RESIZABLE)
        elif event.type==pg.MOUSEWHEEL and not self.drag:
            self.set_zoom(self.zoom+.1*event.y)
        elif event.type==pg.KEYDOWN:
            key=event.key
            if key==pg.K_ESCAPE:
                g.action('pause')
            elif key==pg.K_x:
                g.action('abort')
            elif key==pg.K_a:
                g.action('assess')
            elif key==pg.K_r:
                self.new_game()
            elif key==pg.K_g:
                self.view_3d=not self.view_3d
                self.drag=False
                self.message=t(self.lang,'ui.preview3d' if self.view_3d else 'ui.back_2d')
            elif self.view_3d and key in (pg.K_j,pg.K_l,pg.K_i,pg.K_k):
                if key in (pg.K_j,pg.K_l):
                    self.view_yaw=max(-1.2,min(1.2,self.view_yaw+(-.10 if key==pg.K_j else .10)))
                else:
                    self.view_pitch=max(-.9,min(.9,self.view_pitch+(.10 if key==pg.K_i else -.10)))
            elif key==pg.K_l:
                self.lang=LANGUAGES[(LANGUAGES.index(self.lang)+1)%len(LANGUAGES)]
                self.message=t(self.lang,'ui.disclaimer')
            elif key==pg.K_h:
                self.high_contrast=not self.high_contrast
            elif key==pg.K_c:
                self.colour_safe=not self.colour_safe
            elif key==pg.K_m:
                self.reduced_motion=not self.reduced_motion
            elif key==pg.K_s:
                self.sounds.enabled=not self.sounds.enabled
                self.message=t(self.lang,'ui.sound_on' if self.sounds.enabled else 'ui.sound_off')
            elif key==pg.K_F1:
                self.show_help=not self.show_help
            elif key in (pg.K_EQUALS,pg.K_PLUS,pg.K_KP_PLUS):
                self.set_zoom(self.zoom+.1)
            elif key in (pg.K_MINUS,pg.K_KP_MINUS):
                self.set_zoom(self.zoom-.1)
            elif key==pg.K_t:
                self.cycle_tool(-1 if getattr(event,'mod',0) & pg.KMOD_SHIFT else 1)
            elif key==pg.K_v:
                self.quick_use('ovd_cannula')
            elif key==pg.K_b:
                g.action('escalate')
            elif key==pg.K_d and g.phase==Phase.PHACO:
                self.quick_use('hydro_cannula')
            elif key==pg.K_n and g.phase==Phase.PREOP and not g.eye.preop_checks:
                self.new_game(case=CASES[(CASES.index(g.case)+1)%len(CASES)])
            elif key==pg.K_COMMA:
                self.light=round(max(.5,self.light-.1),2)
            elif key==pg.K_PERIOD:
                self.light=round(min(1.3,self.light+.1),2)
            elif key==pg.K_LEFTBRACKET:
                self.focus=round(max(0.,self.focus-.05),2)
            elif key==pg.K_RIGHTBRACKET:
                self.focus=round(min(1.,self.focus+.05),2)
            elif key==pg.K_e and g.ending:
                self.save()
            elif key==pg.K_SPACE:
                self.start_next()
            elif key==pg.K_d and g.phase==Phase.PREOP and not g.eye.preop_checks:
                levels=tuple(DIFFICULTIES)
                self.new_game(difficulty=levels[(levels.index(g.difficulty)+1)%len(levels)])
            elif pg.K_1<=key<=pg.K_9 and g.phase==Phase.PREOP and not g.eye.preop_checks:
                index=key-pg.K_1
                if index < len(CASES):
                    self.new_game(case=CASES[index])
            elif pg.K_1<=key<=pg.K_3 and g.phase==Phase.CLOSE:
                g.action('verify',FINAL_CHECKS[key-pg.K_1])
        elif event.type == pg.MOUSEBUTTONDOWN:
            self.cursor=self.mapped(event.pos)
            if event.button==1:
                self.drag=True
                self._drag_phase=self.game.phase
                self.pointer_action()
        elif event.type == pg.MOUSEBUTTONUP and event.button==1:
            self.drag=False
        elif event.type==pg.MOUSEMOTION:
            self.cursor=self.mapped(event.pos)
            if self.drag and self.held_ok() and self.game.phase==Phase.CAPSULE:
                self.pointer_action()

    def cycle_tool(self, step=1):
        current=self.game.tool
        index=((TOOL_NAMES.index(current)+step)%len(TOOL_NAMES) if current in TOOL_NAMES
               else 0 if step > 0 else len(TOOL_NAMES)-1)
        self.game.action('tool',TOOL_NAMES[index])

    def quick_use(self, tool):
        """Key shortcut: pick `tool` and use it once at the centre of the field."""
        g=self.game
        if g.tool != tool and not g.action('tool',tool):
            return False
        return g.action('use',.5,.5)

    def held_ok(self):
        """A held drag stops at a phase change or a safety hold; the surgeon
        must press again, so a stage action never carries into the next one."""
        g=self.game
        if g.patient.alert or g.ending or g.phase != self._drag_phase:
            self.drag=False
        return self.drag and not self.view_3d and g.tool not in USE_TOOLS

    def held_input(self):
        """Fixed-step (1/60 s) held instrument work in phaco and I/A."""
        if self.drag and self.held_ok() and self.game.phase in {Phase.PHACO,Phase.CORTEX}:
            self.pointer_action()

    def tray_slots(self):
        tx,ty,tw,th=TRAY
        row_h=(th-4)//2
        for row,names in enumerate(TRAY_ROWS):
            width=tw/len(names)
            for i,name in enumerate(names):
                yield name,(round(tx+i*width)+2,ty+row*(row_h+4),round(width)-4,row_h)

    def set_zoom(self, value):
        # Zoom is locked while a tool drag is in progress.
        if not self.drag:
            self.zoom=round(max(1.0,min(1.8,value)),2)

    def start_next(self):
        g=self.game
        if g.phase==Phase.PREOP:
            # Space checks the next item; the case starts only after all three.
            for item in PREOP_CHECKS:
                if item not in g.eye.preop_checks:
                    if g.action('verify',item):
                        self.sounds.play('ok')
                    return
            g.action('confirm')
        elif g.phase==Phase.ANESTHESIA:
            g.action('prepare')

    def pointer_action(self):
        # This view is an explanatory 3D visualization, not a surgical picking
        # mode; never mis-map CPU-projected triangles into 2D task coordinates.
        if self.view_3d:
            return
        x,y=self.cursor
        game=self.game
        if game.patient.alert:
            if x>=955 and y>=550:
                game.action('assess')
            return
        if game.phase==Phase.PREOP and x<252:
            for i,item in enumerate(PREOP_CHECKS):
                if 343+i*62<y<393+i*62:
                    game.action('verify',item)
                    return
        if game.phase in {Phase.PREOP,Phase.ANESTHESIA} and x<252 and y>554:
            self.start_next()
            return
        if game.phase==Phase.CLOSE and x<250 and not game._decentered:
            for i,key in enumerate(FINAL_CHECKS):
                if 343+i*62<y<393+i*62:
                    game.action('verify',key)
            return
        if game.ending:
            if x>975 and y>595:
                self.save()
            return
        tx,ty,tw,th=TRAY
        if tx<=x<tx+tw and ty<=y<ty+th:
            for name,(rx,ry,rw,rh) in self.tray_slots():
                if rx-2<=x<rx+rw+2 and ry-2<=y<ry+rh+2:
                    game.action('tool',name)
            return
        if 280<=x<=962 and 88<=y<=638:
            a,b=to_eye(self.unzoom((x,y)))
            if game.tool in USE_TOOLS:
                game.action('use',a,b)
            elif game.phase==Phase.ENTRY:
                game.action('touch',a,b)
            elif game.phase==Phase.CAPSULE:
                game.action('trace',a,b)
            elif game.phase in {Phase.PHACO,Phase.CORTEX}:
                game.action('remove',a,b)
            elif game.phase==Phase.IOL or (game.phase==Phase.CLOSE and game._decentered):
                game.action('place',a,b)

    def save(self):
        # Deliberately no personal patient identifiers; synthetic logs only.
        try:
            paths=save_session(self.game,'session_logs',lang=self.lang)
            self.message=t(self.lang,'ui.exported',path=paths[0].parent)
        except (OSError, RuntimeError, ValueError) as exc:
            self.message=t(self.lang,'ui.export_failed',error=exc.__class__.__name__)

    # --- drawing ----------------------------------------------------------
    def text(self, key, **values):
        return t(self.lang, key, **values)

    def draw_sidebar(self):
        pg=self.pg;surf=self.canvas;c=self.palette;g=self.game
        rounded(pg,surf,c['panel'],(15,75,250,620),14)
        draw_text(pg,surf,self.fonts,self.text('phase.'+g.phase.value).upper(),(29,96),color=c['accent'],size='base',max_chars=26)
        for i,line in enumerate(self.fonts.wrapped(self.text('goal.'+g.phase.value),'base',215)[:4]):
            draw_text(pg,surf,self.fonts,line,(29,126+i*23),color=c['muted'])
        pg.draw.line(surf,(48,76,91),(29,224),(248,224),1)
        draw_text(pg,surf,self.fonts,f"{self.text('ui.difficulty')}: {self.text('difficulty.'+g.difficulty)}",
                  (29,234),size='tiny',color=c['muted'])
        if g.phase==Phase.PREOP:
            draw_text(pg,surf,self.fonts,f"{self.text('ui.select_case')} [1-9 / N] · D",(29,256),size='tiny',color=c['accent'])
            draw_text(pg,surf,self.fonts,self.text('case.'+g.case),(29,276),size='base',color=c['ok'],max_chars=26)
            self.checklist(PREOP_CHECKS,g.eye.preop_checks)
        elif g.phase==Phase.CLOSE:
            if g._decentered:
                for i,line in enumerate(self.fonts.wrapped(self.text('hint.IOL DECENTRATION'),'base',215)):
                    draw_text(pg,surf,self.fonts,line,(29,282+i*22),color=c['warn'])
            self.checklist(FINAL_CHECKS,g.eye.final_checks,numbered=True)
        else:
            rows=((self.text('bar.opacity'),g.eye.opacity,c['warn']),
                  (self.text('bar.cortex'),g.eye.cortex,c['accent']),
                  (self.text('bar.capsule'),g.eye.capsule_integrity,c['ok']),
                  (self.text('bar.iol'),g.eye.iol_alignment,c['accent']),
                  (self.text('bar.visibility'),g.eye.visibility,
                   c['ok'] if g.eye.visibility>=.75 else c['warn']),
                  (self.text('bar.stress'),g.tissue_stress,
                   c['bad'] if g.stress_warning else c['muted']))
            for i,(label,val,color) in enumerate(rows):
                yy=256+i*38
                draw_text(pg,surf,self.fonts,f'{label}  {round(val*100)}%',(29,yy),color=c['muted'],size='tiny')
                bar(pg,surf,30,yy+19,215,val,color)
            self.cross_section(pg,surf,(27,492,225,148))
        if g.phase in (Phase.PREOP,Phase.ANESTHESIA):
            rounded(pg,surf,(24,104,111),(28,573,223,59),10)
            draw_text(pg,surf,self.fonts,self.text('ui.next'),(39,590),size='base')
        draw_text(pg,surf,self.fonts,self.text('ui.pause_abort'),(27,653),size='tiny',color=c['muted'])

    def checklist(self, items, done, numbered=False):
        pg=self.pg;surf=self.canvas;c=self.palette
        for i,key in enumerate(items):
            yy=343+i*62
            rounded(pg,surf,c['panel2'],(27,yy,225,50))
            mark='[x] ' if key in done else '[ ] '
            prefix=f'{i+1} ' if numbered else ''
            draw_text(pg,surf,self.fonts,prefix+mark+self.text('check.'+key),(37,yy+14),
                      color=c['ok'] if key in done else c['text'],max_chars=28)

    def cross_section(self, pg, surf, rect):
        """Synchronized side view of the same snapshot (synthetic geometry)."""
        c=self.palette;g=self.game
        x,y,w,h=rect
        rounded(pg,surf,c['panel2'],rect,8)
        draw_text(pg,surf,self.fonts,self.text('ui.depth'),(x+8,y+4),size='tiny',color=c['muted'])
        top=y+26;bottom=y+h-10;mid=x+w//2
        depth=lambda d: round(top+d*(bottom-top))
        pg.draw.arc(surf,(160,220,235),(x+18,top-6,w-36,70),.25,math.pi-.25,2)          # cornea
        iris_y=depth(.28)
        pupil=round(42*(.25+.75*g.eye.pupil))
        pg.draw.line(surf,(70,140,140),(x+16,iris_y),(mid-pupil,iris_y),4)
        pg.draw.line(surf,(70,140,140),(mid+pupil,iris_y),(x+w-16,iris_y),4)
        lens=pg.Rect(0,0,110,depth(.92)-depth(.32));lens.center=(mid,(depth(.32)+depth(.92))//2)
        fill=pg.Surface(lens.size,pg.SRCALPHA)
        pg.draw.ellipse(fill,(200,187,136,round(40+170*g.eye.opacity)),fill.get_rect())
        surf.blit(fill,lens.topleft)
        capsule_color=c['ok'] if g.eye.capsule_integrity>=.85 else c['bad']
        pg.draw.ellipse(surf,capsule_color,lens,2 if g.eye.capsule_integrity>=.85 else 1)
        if g.phase in (Phase.CLOSE,Phase.RECOVERY) or (g.phase==Phase.IOL and g.eye.iol_alignment>0):
            shift=round(30*(1-g.eye.iol_alignment))
            pg.draw.line(surf,(180,240,246),(mid-40+shift,depth(.55)),(mid+40+shift,depth(.55)),3)
        task=TASK_DEPTH.get(g.phase)
        if task is not None:
            ty=depth(task)
            pg.draw.line(surf,c['warn'],(x+8,ty),(x+18,ty),2)              # task depth band
            ex,_=to_eye(self.unzoom(self.cursor))
            tip=(round(x+16+max(0.,min(1.,ex))*(w-32)),ty)
            pg.draw.line(surf,(219,245,241),(tip[0]+26,y+24),tip,2)         # synthetic tool
            pg.draw.circle(surf,c['accent'],tip,3)

    def draw_monitor(self):
        pg=self.pg;s=self.canvas;g=self.game;p=g.patient;c=self.palette
        rounded(pg,s,c['panel'],(976,75,290,620),14)
        draw_text(pg,s,self.fonts,self.text('ui.monitor').upper(),(990,95),color=c['accent'])
        draw_text(pg,s,self.fonts,self.text('ui.synthetic').upper(),(990,125),color=c['muted'],size='tiny')
        rounded(pg,s,c['panel2'],(990,165,260,145))
        draw_text(pg,s,self.fonts,'ECG / HR', (1004,179),color=c['ok'])
        draw_text(pg,s,self.fonts,str(p.heart_rate), (1005,208),size='big',color=c['ok'])
        waveform(pg,s,(997,281),g.time,c['ok'],p.heart_rate)
        rounded(pg,s,c['panel2'],(990,324,260,91))
        draw_text(pg,s,self.fonts,'NIBP', (1005,339),color=c['warn'])
        draw_text(pg,s,self.fonts,f'{p.sbp} / {p.dbp}',(1005,362),size='big',color=c['warn'])
        rounded(pg,s,c['panel2'],(990,426,260,90))
        draw_text(pg,s,self.fonts,'SpO2', (1005,439),color=c['accent'])
        draw_text(pg,s,self.fonts,f'{p.spo2}%',(1005,461),size='big',color=c['accent'])
        waveform(pg,s,(1094,500),g.time,c['accent'],p.heart_rate,'pleth',145)
        col=c['bad'] if p.alert else c['ok']
        rounded(pg,s,(61,32,47) if p.alert else (25,67,60),(990,531,260,97))
        draw_text(pg,s,self.fonts,self.text('ui.status').upper(), (1004,539),color=col)
        status=self.text('alert.'+p.alert) if p.alert else self.text('ui.stable')
        draw_text(pg,s,self.fonts,('! ' if p.alert else '')+status, (1004,566),color=col,size='medium',max_chars=23)
        if p.alert:
            draw_text(pg,s,self.fonts,self.text('ui.assess_or_abort'),(999,603),size='tiny',color=c['text'])
        draw_text(pg,s,self.fonts,self.text('ui.synthetic'), (990,660),color=c['muted'],size='tiny')

    def draw_field(self):
        pg=self.pg;s=self.canvas;g=self.game;c=self.palette
        rounded(pg,s,(13,31,45),FIELD,16)
        pg.draw.circle(s,(30,65,71),(EYE_CX,EYE_CY),243)
        if self.view_3d:
            draw_preview(pg,s,g.phase.value,g.eye.opacity,g.eye.iol_alignment,
                         self.view_yaw,self.view_pitch)
            return
        draw_drape(pg,s,c)
        render_eye(pg,s,g,g.time,c,animate=not self.reduced_motion)
        fx,fy,fw,fh=FIELD
        if self.zoom > 1.0:
            crop=pg.Rect(*map(round,self._crop()))
            s.blit(pg.transform.smoothscale(s.subsurface(crop).copy(),(fw,fh)),(fx,fy))
        if self.light != 1.0:
            # Synthetic microscope illumination (visual only).
            field=s.subsurface(FIELD)
            if self.light < 1.0:
                v=round(255*self.light)
                field.fill((v,v,v),special_flags=pg.BLEND_MULT)
            else:
                v=round(255*(self.light-1.0)*.6)
                field.fill((v,v,v),special_flags=pg.BLEND_ADD)
        error=self.focus_error()
        if error > .12:
            # Out-of-focus microscope: low-pass by down/up sampling (visual only).
            factor=1+min(6.,(error-.12)*24)
            area=s.subsurface(FIELD).copy()
            small=pg.transform.smoothscale(area,(max(1,round(fw/factor)),max(1,round(fh/factor))))
            s.blit(pg.transform.smoothscale(small,(fw,fh)),(fx,fy))

    def draw_tray(self):
        pg=self.pg;s=self.canvas;g=self.game;c=self.palette
        # Highlight the needed instrument only where hints are allowed.
        required=g.required_tool if (g.rules.tool_hints or not g.pending) else None
        for name,rect in self.tray_slots():
            selected=name==g.tool
            rounded(pg,s,(30,74,84) if selected else c['panel2'],rect,6)
            if name==required:
                pg.draw.rect(s,c['ok'] if selected else c['warn'],rect,2,border_radius=6)
            label=self._tray_label(('>' if selected else '')+self.text('short.'+name),rect[2]-6)
            draw_text(pg,s,self.fonts,label,(rect[0]+3,rect[1]+4),size='micro',
                      color=c['text'] if selected else c['muted'])

    def _tray_label(self, label, max_px):
        """Instrument name cut to its slot width (cached per language)."""
        key = (label, max_px)
        cache = self.__dict__.setdefault('_tray_cache', {})
        if key not in cache:
            font = self.fonts['micro']
            text = label
            while font.size(text)[0] > max_px and len(text) > 2:
                text = text[:-1]
            cache[key] = text
        return cache[key]

    def draw_pending(self):
        """Assessed complication still awaiting management (no timer)."""
        pg=self.pg;s=self.canvas;g=self.game;c=self.palette
        label=g.pending[0]
        comp=COMPLICATIONS[label]
        rounded(pg,s,(70,46,40) if comp.major else (52,52,38),(352,516,570,76),10)
        draw_text(pg,s,self.fonts,'! '+self.text('manage.title',alert=self.text('alert.'+label)),
                  (372,523),color=c['bad'] if comp.major else c['warn'],size='medium',max_chars=46)
        if comp.remedy=='escalate':
            line=self.text('manage.escalate')
        elif g.rules.tool_hints:
            line=self.text('manage.tool',tool=self.text('tool.'+comp.remedy),
                           site=self.text('site.'+(comp.site or 'centre')))
        else:
            line=self.text('manage.choose')
        draw_text(pg,s,self.fonts,line,(374,551),size='base',max_chars=64)
        sub=(self.text('manage.major') if comp.major and comp.remedy!='escalate'
             else self.text('ui.in_hand',tool=self.text('tool.'+g.tool)) if g.tool
             else self.text('ui.no_tool'))
        draw_text(pg,s,self.fonts,sub,(374,572),size='tiny',color=c['text'],max_chars=90)

    def draw_chart(self):
        """Pre-operative synthetic patient chart (no real person)."""
        pg=self.pg;s=self.canvas;g=self.game;c=self.palette
        profile=PROFILES[g.case]
        card=pg.Surface((300,170),pg.SRCALPHA)
        pg.draw.rect(card,(*c['panel'],232),(0,0,300,170),border_radius=10)
        s.blit(card,(292,108))
        pg.draw.rect(s,c['accent'],(292,108,300,170),1,border_radius=10)
        draw_text(pg,s,self.fonts,self.text('chart.title'),(304,116),size='tiny',color=c['accent'])
        draw_text(pg,s,self.fonts,f"{self.text('case.'+g.case)} · {self.text('chart.age',age=profile.age)}",
                  (304,136),size='base',max_chars=30)
        none=self.text('chart.none')
        rows=((self.text('chart.conditions'),
               ', '.join(self.text('cond.'+k) for k in profile.conditions) or none),
              (self.text('chart.medications'),
               ', '.join(self.text('med.'+k) for k in profile.medications) or none))
        yy=162
        for label,value in rows:
            draw_text(pg,s,self.fonts,label,(304,yy),size='tiny',color=c['muted'])
            for line in self.fonts.wrapped(value,'tiny',276)[:2]:
                yy+=17
                draw_text(pg,s,self.fonts,line,(312,yy),size='tiny')
            yy+=21
        draw_text(pg,s,self.fonts,self.text('chart.baseline',hr=profile.heart_rate,
                  sbp=profile.sbp,dbp=profile.dbp),(304,254),size='tiny',color=c['ok'],max_chars=44)

    def draw_alert(self):
        pg=self.pg;s=self.canvas;g=self.game;c=self.palette
        rounded(pg,s,(87,41,52),(352,520,570,104),10)
        draw_text(pg,s,self.fonts,'! '+self.text('ui.safety_hold'),(372,530),color=c['bad'],size='medium',max_chars=46)
        draw_text(pg,s,self.fonts,self.text('alert.'+g.patient.alert)+' — '+self.text('hint.'+g.patient.alert),
                  (374,562),size='base',max_chars=62)
        limit=g.rules.alert_timeout
        timer=(self.text('ui.hold_timer',s=f'{g.alert_elapsed:.0f}',limit=f'{limit:.0f}')
               if limit is not None else self.text('ui.hold_untimed'))
        draw_text(pg,s,self.fonts,self.text('ui.assess_or_abort')+'   ·   '+timer,(374,592),size='tiny',color=c['text'])
        if limit is not None:
            bar(pg,s,700,598,200,1-g.alert_elapsed/limit,c['warn'])

    def draw_results(self):
        pg=self.pg;s=self.canvas;g=self.game;c=self.palette
        rounded(pg,s,(14,43,57),(300,92,650,580),19)
        pg.draw.rect(s,c['accent'],(300,92,650,580),2,border_radius=19)
        color=(c['ok'] if g.ending in (ENDING_COMPLETE,ENDING_MANAGED)
               else c['bad'] if g.ending in (ENDING_FAILED,ENDING_UNRESOLVED) else c['warn'])
        title=self.text('ending.'+g.ending)
        size='title' if self.fonts['title'].size(title)[0] <= 600 else 'medium'
        draw_text(pg,s,self.fonts,title,(326,112 if size=='title' else 118),size=size,color=color,max_chars=48)
        draw_text(pg,s,self.fonts,f"{self.text('ui.score')}  {g.score()} / 100",(328,156),size='medium')
        draw_text(pg,s,self.fonts,self.text('ui.breakdown'),(328,196),color=c['accent'])
        for i,row in enumerate(explain(g,self.lang)):
            yy=222+i*48
            draw_text(pg,s,self.fonts,row['label'],(328,yy),size='base',max_chars=24)
            draw_text(pg,s,self.fonts,f"{row['points']:.0f}/{row['max']}",(560,yy),size='base',color=c['ok'])
            bar(pg,s,630,yy+8,290,row['points']/row['max'],c['ok'])
            draw_text(pg,s,self.fonts,row['reasons'][0],(338,yy+22),size='tiny',color=c['muted'],max_chars=84)
        draw_text(pg,s,self.fonts,self.text('ui.timeline'),(328,468),color=c['accent'])
        for i,row in enumerate(timeline(g,self.lang)[-7:]):
            draw_text(pg,s,self.fonts,f"{row['t']:6.1f}s  {row['text']}",(338,494+i*20),size='tiny',
                      color=c['bad'] if row['critical'] else c['text'],max_chars=86)
        draw_text(pg,s,self.fonts,f"{self.text('ui.export')}    {self.text('ui.retry')}    ·  "
                  +self.text('ui.not_clinical'),(328,640),size='tiny',color=c['muted'],max_chars=92)

    def draw_help(self):
        pg=self.pg;s=self.canvas;c=self.palette
        rounded(pg,s,(10,28,40),(330,150,600,170),14)
        pg.draw.rect(s,c['accent'],(330,150,600,170),2,border_radius=14)
        draw_text(pg,s,self.fonts,self.text('ui.help'),(350,164),size='medium',color=c['accent'])
        for i,line in enumerate(wrapped(self.text('ui.help.body'),font=self.fonts['base'],max_px=560)
                                +wrapped(self.text('ui.options'),font=self.fonts['base'],max_px=560)):
            draw_text(pg,s,self.fonts,line,(352,200+i*22),size='base')

    def draw(self):
        pg=self.pg;s=self.canvas;g=self.game;c=self.palette
        if len(g.alerts) > self._alerts_heard:
            self._alerts_heard=len(g.alerts)
            self.sounds.play('alert')
        if g.ending and not self._ending_heard:
            self._ending_heard=True
            self.sounds.play('end')
        if g.wrong_tool > self._wrong_seen:
            self._wrong_seen=g.wrong_tool
            needed=g.required_tool or g.stage_tool
            self.message=(t(self.lang,'ui.wrong_tool',tool=t(self.lang,'tool.'+needed)) if needed
                          else t(self.lang,'ui.disclaimer'))
        if g.phase != self._saved_phase:
            self.autosave()
        s.fill(c['bg'])
        draw_text(pg,s,self.fonts,'OPHTHOSIM', (24,21),size='title',color=c['accent'])
        draw_text(pg,s,self.fonts,'AI  /  CATARACT MICROSURGERY', (237,31),color=c['muted'])
        draw_text(pg,s,self.fonts,('3D MESH PREVIEW (CPU)' if self.view_3d
                                   else '2.5D EDUCATIONAL BUILD'),(1002,29),color=c['ok'],size='tiny')
        self.draw_field()
        # Microscope masks / aperture.
        pg.draw.circle(s,(58,103,115),(EYE_CX,EYE_CY),239,2)
        focus='—' if FOCUS_TARGET.get(g.phase) is None else ('OK' if self.focus_error()<=.12 else '~')
        draw_text(pg,s,self.fonts,('ROTATABLE 3D MESH PREVIEW - NON-INTERACTIVE' if self.view_3d
                                   else f"MICROSCOPE • {self.text('ui.zoom')} {self.zoom:.1f}x • "
                                        f"{self.text('ui.focus')} {focus} • "
                                        f"{self.text('ui.light')} {round(self.light*100)}%"),
                  (289,90),size='tiny',color=c['accent'])
        if self.view_3d:
            draw_text(pg,s,self.fonts,'J/L Orbit  I/K Tilt  G Return to surgery',
                      (372,609),size='base',color=c['accent'])
        if not self.view_3d and g.phase==Phase.PREOP and not g.ending:
            self.draw_chart()
        x,y=self.cursor
        if (not self.view_3d and g.tool and not g.ending and 280<=x<=962 and 88<=y<=590
                and g.phase not in (Phase.PREOP,Phase.ANESTHESIA)):
            draw_tool(pg,s,g.tool,self.cursor)
            if self.drag:
                pg.draw.circle(s,(219,245,241),(round(x),round(y)),8,2)
        if not self.view_3d and (g.phase==Phase.IOL or (g.phase==Phase.CLOSE and g._decentered)):
            pg.draw.circle(s,c['accent'],(EYE_CX,EYE_CY),26,1)
            pg.draw.line(s,c['accent'],(EYE_CX-38,EYE_CY),(EYE_CX+38,EYE_CY),1)
        if not self.view_3d:
            self.draw_tray()
        self.draw_sidebar();self.draw_monitor()
        modes=' '.join(m for m,on in (('HC',self.high_contrast),('CVD',self.colour_safe),
                                         ('LOW-MOTION',self.reduced_motion),
                                         ('MUTE',not self.sounds.enabled)) if on)
        draw_text(pg,s,self.fonts,f"{self.text('case.'+g.case)} | {self.text('difficulty.'+g.difficulty)} | "
                  f"{g.phase.value} | {self.text('ui.score')} {g.score()} | SEED {g.seed} | {self.lang.upper()} {modes}",
                  (291,654),size='tiny',color=c['muted'],max_chars=100)
        if g.patient.alert:
            self.draw_alert()
        elif g.pending and not g.ending:
            self.draw_pending()
        elif g.paused:
            rounded(pg,s,(35,55,75),(395,550,480,56))
            draw_text(pg,s,self.fonts,self.text('ui.paused'),(424,564),size='medium')
        if g.ending:
            self.draw_results()
        if self.show_help:
            self.draw_help()
        # y=699 keeps the descenders inside the 720 px canvas (704 clipped them).
        draw_text(pg,s,self.fonts,self.message+'   ·   F1',(24,699),size='tiny',color=c['muted'],max_chars=120)
        size=self.screen.get_size()
        # Scale only when the window differs from the 1280x720 canvas.
        self.screen.blit(s if size==s.get_size() else pg.transform.smoothscale(s,size),(0,0))
        pg.display.flip()

    def run(self):
        pg=self.pg
        while self.running:
            dt=min(self.clock.tick(60)/1000,.1)
            for event in pg.event.get():
                self.dispatch(event)
            self._acc+=dt
            loops=0
            while self._acc>=1/60 and loops<6:
                self.held_input()
                self.game.tick(1/60)
                self._acc-=1/60
                loops+=1
            if loops>=6:
                self._acc=0
            self.draw()


def main(argv=None):
    parser=argparse.ArgumentParser(description='Educational 2.5D cataract surgery game')
    parser.add_argument('--case', choices=list(CASES),default='normal')
    parser.add_argument('--difficulty', choices=list(DIFFICULTIES),default='standard')
    parser.add_argument('--lang', choices=list(LANGUAGES),default='en')
    parser.add_argument('--seed',type=int,default=7)
    parser.add_argument('--scale',type=float,default=1.0)
    parser.add_argument('--resume',nargs='?',const=str(AUTOSAVE),default=None,
                        help='continue a verified autosave (default session_logs/autosave.replay.jsonl)')
    ns=parser.parse_args(argv)
    if not math.isfinite(ns.scale) or not .5<=ns.scale<=3:
        parser.error('--scale must be between 0.5 and 3')
    if abs(ns.seed) > 2**63-1:
        parser.error('seed must fit in a signed 64-bit integer')
    try:
        import pygame
    except ImportError:
        print('Pygame is missing. Install with: python -m pip install -r requirements.txt',file=sys.stderr)
        raise SystemExit(2)
    pygame.init()
    app=None
    try:
        app=App(pygame,ns.case,ns.seed,ns.scale,ns.difficulty,ns.lang)
        if ns.resume:
            app.resume(ns.resume)
        app.run()
    finally:
        if app is not None:
            app.autosaver.close()
        pygame.quit()
