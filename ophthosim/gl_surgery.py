"""Interactive 3D viewport for *synthetic* cataract game states.

The existing strict ReplayGame remains the only authority for every phase,
alert, score and safe abort. OpenGL only renders visual anatomy; a normalized
ray/plane adapter translates mouse input into pre-existing educational tasks.

Launch on a compatible OpenGL desktop:
    python -m ophthosim.gl_surgery --case normal
The clinical realism and surgical skills represented here are NOT validated.
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path
import textwrap

from .autosave import AUTOSAVE, BackgroundAutosave, load_autosave
from .engine import (CASES, COMPLICATIONS, DIFFICULTIES, ENDING_COMPLETE, ENDING_FAILED,
                     ENDING_MANAGED, ENDING_UNRESOLVED, PREOP_CHECKS, PROFILES, TOOL_NAMES,
                     Phase)
from .i18n import LANGUAGES, t
from .report import explain, save_session as save_report, timeline
from .gl_preview import GPUEyePreview, AnatomyAppearance, atlas_meshes
from .input3d import Surgery3DController, eye_to_pixel
from .signals import sample_trace
from .tool3d import visible_stylus
from .iol3d import iol_visual_deployment
from .capsule3d import capsule_display_state
from .complication3d import complication_visuals
from .room3d import VIEW_CYCLE
from .vision3d import visual_feedback
from .surface_probe3d import SurfaceProbe, probe_surface
from .frametime import FrameProfiler, FrameStats

PHASE_NAMES = {
    Phase.PREOP: "CASE / PREOPERATIVE REVIEW",
    Phase.ANESTHESIA: "ANESTHESIA CHECK / PREPARATION",
    Phase.ENTRY: "SIMULATED ENTRY TARGETS",
    Phase.CAPSULE: "CIRCULAR CAPSULE TASK",
    Phase.PHACO: "CLOUDY LENS REMOVAL",
    Phase.CORTEX: "RESIDUAL MATERIAL CLEANUP",
    Phase.IOL: "IOL POSITIONING",
    Phase.CLOSE: "FINAL VERIFICATION",
    Phase.RECOVERY: "RESULT / RECOVERY",
    Phase.ABORTED: "SAFE STOP",
    Phase.FAILED: "CRITICAL FAILURE / REVIEW",
}
CHECKS = ("alignment", "wound", "handoff")


def phase_title_lines(phase: Phase, width: int = 21,
                      lang: str = "en") -> tuple[str, ...]:
    """At most two side-panel lines, broken between words, never mid-word."""
    name = PHASE_NAMES[phase] if lang == "en" else t(lang, f"phase.{phase.value}")
    lines = textwrap.wrap(name, width, break_long_words=False)
    return tuple(lines[:2])


class SurgeryHUD:
    """Visual-only overlay; it may never modify the Game or change a score."""

    def __init__(self, controller: Surgery3DController) -> None:
        self.controller = controller
        self.last_cursor: tuple[int, int] | None = None  # window pixels
        self.ui_scale = 1
        self.status = ""            # empty: the localized disclaimer
        # "microscope_view" operates; the operating-room views only observe.
        self.camera = VIEW_CYCLE[0]
        self.lang = "en"
        self.reduced_motion = False
        self.high_contrast = False
        # F3 frame-time readout: CPU wall-clock statistics, display only.
        self.show_perf = False
        self.perf: FrameStats | None = None
        # Prepared exactly once per rendered frame by the outer game loop.
        # HUD painting must never trigger a second expensive BVH query.
        self.frame_proximity: SurfaceProbe | None = None
        self._probe_phase: Phase | None = None
        self._probe_pose: tuple[float,float,float] | None = None
        self._probe_camera: tuple[float,float] | None = None

    # --- cached text: the HUD repaints every frame, and rendering ~40
    # Hangul-capable labels per frame alone held the 3D view near 30 fps.
    TEXT_CACHE_LIMIT = 2048

    def _cache(self, name: str) -> dict:
        cache = self.__dict__.setdefault(name, {})
        if len(cache) >= self.TEXT_CACHE_LIMIT:
            cache.clear()
        return cache

    def _text(self, font, text: str, color):
        cache = self._cache("_rendered")
        key = (font, text, tuple(color))     # holds the font: no id reuse
        if key not in cache:
            cache[key] = font.render(text, True, color)
        return cache[key]

    def _fit(self, font, text: str, max_px: int) -> str:
        cache = self._cache("_fitted")
        key = (font, text, max_px)
        if key not in cache:
            fitted = text
            while font.size(fitted)[0] > max_px and len(fitted) > 2:
                fitted = fitted[:-1]
            cache[key] = fitted
        return cache[key]

    def _wrap(self, font, text: str, max_px: int) -> tuple[str, ...]:
        """Wrap by rendered width (Hangul is wider than Latin text)."""
        cache = self._cache("_wrapped")
        key = (font, text, max_px)
        if key not in cache:
            rows, line = [], ""
            for word in text.split(" "):
                trial = f"{line} {word}".strip()
                if font is not None and font.size(trial)[0] > max_px and line:
                    rows.append(line)
                    line = word
                else:
                    line = trial
            cache[key] = (*rows, line)
        return cache[key]

    @staticmethod
    def card_rect(width: int, height: int) -> tuple[int, int, int, int]:
        """Hold / management / chart card: low in the field so the eye and
        the complication sign stay visible while the surgeon decides."""
        # Between the side panels (12..259 and width-267..), at most 600 wide.
        w = max(400, min(600, width-548))
        return (width//2-w//2, height-252, w, 114)

    @staticmethod
    def tray_slots(width: int, height: int):
        """One instrument row above the status line (display + hit areas)."""
        slot = (width-48)/len(TOOL_NAMES)
        for i, name in enumerate(TOOL_NAMES):
            yield name, (round(24+i*slot)+1, height-130, round(slot)-2, 26)

    def set_ui_scale(self, scale: int) -> None:
        """Logical HUD magnification chosen by the renderer for this frame."""
        if type(scale) is not int or not 1 <= scale <= 8:
            raise ValueError("HUD scale must be a small positive integer")
        self.ui_scale = scale

    def set_frame_proximity(self, result: SurfaceProbe | None) -> None:
        """Attach a non-mutating proximity observation to this exact phase."""
        if result is not None:
            if not isinstance(result, SurfaceProbe):
                raise ValueError("Expected a validated synthetic surface probe")
            result.check()
            if visible_stylus(self.controller) is None:
                raise ValueError("Cannot display stale tool proximity")
        self.frame_proximity = result
        self._probe_phase = self.controller.game.phase if result is not None else None
        self._probe_pose = visible_stylus(self.controller) if result is not None else None
        self._probe_camera = ((self.controller.view.yaw, self.controller.view.pitch)
                              if result is not None else None)

    def draw(self, pg, surf, view, width: int, height: int, font, title) -> None:
        c = self.controller
        self._font = font
        g = c.game
        # The atlas drawing underneath remains available in all modes.
        # The translucent HUD panels do not need an independent GL context.
        pg.draw.rect(surf, (12, 29, 42, 224), (12, 176, 247, 270),
                     border_radius=10)
        pg.draw.rect(surf, (12, 29, 42, 224), (width-267, 176, 255, 270),
                     border_radius=10)
        def label(text, x, y, *, color=(232, 240, 247), large=False):
            surf.blit(self._text(title if large else font, str(text), color), (x, y))
        light=(142,211,233)
        green=(126,224,176)
        amber=(247,195,109)
        red=(247,122,136)
        lang = self.lang
        room = self.camera != VIEW_CYCLE[0]
        label(t(lang, 'case.'+g.case)[:24], 24, 189, color=light)
        # Long titles wrap at word boundaries to avoid spilling onto the iris.
        for i, line in enumerate(phase_title_lines(g.phase, lang=lang)):
            label(line, 24, 221+23*i)
        label(f"{g.phase.value} · {t(lang, 'difficulty.'+g.difficulty)}"[:24], 24, 285)
        label(f"{t(lang, 'ui.score')}: {g.score():03d}", 24, 316)
        if g.phase == Phase.PREOP:
            # Pre-op checklist replaces the tool readout until the case starts.
            for i, item in enumerate(PREOP_CHECKS):
                done = item in g.eye.preop_checks
                label((("[x] " if done else "[ ] ") + t(lang, "check."+item))[:26],
                      24, 350+i*28, color=green if done else amber)
            label(t(lang, "hud.preop_keys")[:34], 24, 437, color=light)
        elif not room:
            label(t(lang, "hud.tool_z", z=f"{c.tool_depth:+.2f}"), 24, 350, color=green)
        required = g.required_tool
        if not g.ending and g.phase != Phase.PREOP:
            current = (t(lang, "ui.in_hand", tool=t(lang, "tool."+g.tool)) if g.tool
                       else t(lang, "ui.no_tool"))
            label(f"{current} [T]"[:40], 24, 128,
                  color=green if required is None or g.tool == required else amber)
        if c.last_contact is not None:
            kind=c.last_contact.status
            label(t(lang, "hud.guide", s=kind), 24, 151,
                  color=green if kind=="TARGET" else amber if kind in
                        ("NEAR","VISITED") else red)
        # Proximity is visual-only, expressed in unitless model coordinates;
        # no physical contact or surgical action is inferred from this label.
        # Read the prepared frame observation; never recalculate proximity
        # in this text overlay. Old results are suppressed on phase changes,
        # safety holds, finished cases and a missing live stylus position.
        proximity=(self.frame_proximity if (
            self._probe_phase == g.phase and
            not g.paused and not g.patient.alert and not g.ending and
            self._probe_pose is not None and
            visible_stylus(c) == self._probe_pose and
            self._probe_camera == (c.view.yaw,c.view.pitch)) else None)
        if proximity is not None and self.show_perf:    # diagnostic (F3)
            label(t(lang, "hud.gap", s=proximity.status, gap=f"{proximity.gap:.3f}"),
                  width//2-155, 128, color=amber)
        capsule_on, damage = capsule_display_state(g)
        if capsule_on:
            label(t(lang, "hud.capsule_alert" if damage >= .15 else "hud.capsule_ok"),
                  24, 433, color=red if damage >= .15 else green)
        if g.phase in (Phase.IOL, Phase.CLOSE, Phase.RECOVERY):
            label(t(lang, "hud.iol_deploy", p=f"{iol_visual_deployment(g):.0%}"),
                  width//2-104, 152, color=green)
        target = c.target_depth
        if g.phase != Phase.PREOP and not room:
            label(t(lang, "hud.target_z", z=f"{target:+.2f}") if target is not None
                  else t(lang, "hud.inactive"), 24, 378, color=light)
            label(t(lang, "hud.depth_keys"), 24, 410, color=amber)

        label(t(lang, "ui.monitor").upper(), width-254, 189, color=light)
        label(t(lang, "ui.synthetic"), width-254, 220, color=amber)
        p = g.patient
        label(f"HR {p.heart_rate}   SpO2 {p.spo2}%", width-254, 253, color=green)
        label(f"NIBP {p.sbp}/{p.dbp}", width-254, 284, color=amber)
        status = t(lang, "alert."+p.alert) if p.alert else t(lang, "ui.stable")
        label(f"{t(lang, 'ui.status')}: {status}"[:22], width-254, 316,
              color=red if p.alert else green)
        wave = sample_trace("ecg", p.heart_rate, g.time, count=170)
        left = width-255
        pg.draw.lines(surf, green, False,
                      [(left+i, 403-int(val*29)) for i,val in enumerate(wave)],2)
        pg.draw.line(surf, (54,100,122), (left,415), (width-34,415), 1)

        view_lines = [(t(lang, "view.label", name=t(lang, "view."+self.camera)),
                       (255,238,155) if room else light)]
        if room and not g.ending and g.phase not in (Phase.PREOP, Phase.ANESTHESIA):
            view_lines.append((t(lang, "view.room_input"), amber))
        if room:
            # Room scenes are bright: give the view caption its own plate.
            plate_w = max(self._text(font, text, colour).get_width()
                          for text, colour in view_lines) + 20
            pg.draw.rect(surf, (10,27,39,215), (width//2-160, 88, plate_w, 8+24*len(view_lines)),
                         border_radius=8)
        for i, (text, colour) in enumerate(view_lines):
            label(text, width//2-150, 92+24*i, color=colour)
        # Targets projected using the same GLSL camera and ray-plane scale.
        if room:
            pass        # microscope-space markers do not belong to room cameras
        elif g.phase == Phase.ENTRY:
            for i,(x,y) in enumerate(g._entry_target):
                self._point(pg, surf, x,y,c, width,height,
                            green if i < g.eye.entry_hits else amber, r=9)
        elif g.phase == Phase.CAPSULE:
            for i in range(24):
                a=(i+.5)*math.tau/24
                self._point(pg, surf, .5+.28*math.cos(a),
                            .5+.28*math.sin(a),c,width,height,
                            green if i in g.eye.capsule_points else amber,r=3)
        elif g.phase in (Phase.PHACO,Phase.CORTEX):
            value = g.eye.opacity if g.phase == Phase.PHACO else g.eye.cortex
            label(t(lang, "hud.remaining", p=f"{value:.0%}"), width//2-92,
                  152, color=amber)
        elif g.phase == Phase.IOL or c.target_depth is not None and g.phase == Phase.CLOSE:
            self._point(pg,surf,.5,.5,c,width,height,green,r=15)

        if g.phase == Phase.CLOSE and not (g.patient.alert or g.pending or g.ending):
            # Kept clear of the instrument row and the instruction bar below.
            for i,key in enumerate(CHECKS):
                done = key in g.eye.final_checks
                label(f"{i+1} {t(lang, 'check.'+key)} "+t(lang, "hud.done" if done else "hud.pending"),
                      width//2-105,height-222+i*26,color=green if done else amber)

        # Lower instructions remain visible in small windows.
        bottom=height-69
        pg.draw.rect(surf,(10,27,39,225),(12,bottom,width-24,58),
                     border_radius=10)
        for i,msg in enumerate((t(lang, "hud.keys1"), t(lang, "hud.keys2"))):
            label(msg[:110],24,bottom+6+i*25,color=green if i==0 else amber)
        if not g.ending and g.phase not in (Phase.PREOP, Phase.ANESTHESIA):
            self._draw_tray(pg, surf, width, height, font, light, green, amber)
        if self.status:          # the disclaimer itself is in the header
            label(self.status[:72], 24, height-100, color=light)
        if self.show_perf:
            perf = self.perf
            label((f"FRAME {perf.mean_ms:.1f} ms  P95 {perf.p95_ms:.1f} ms (CPU)"
                   if perf is not None else "FRAME TIME: measuring..."),
                  width-420, height-100, color=light)
        if self.reduced_motion or self.high_contrast:
            flags=("LOW MOTION " if self.reduced_motion else "") + ("HIGH CONTRAST" if self.high_contrast else "")
            label(flags.strip(), width//2-115, 110, color=(255,238,155))
        # Avoid displaying an earlier cursor after phase changes or restart.
        if self.last_cursor and c.last_pose is not None and not room:
            cursor=tuple(v//self.ui_scale for v in self.last_cursor)
            pg.draw.circle(surf,green,cursor,8,2)
        self._draw_common(pg, surf, width, height, label, light, green, amber, red)

    def _draw_tray(self, pg, surf, width, height, font, light, green, amber):
        g = self.controller.game
        # The needed instrument is highlighted only where hints are allowed.
        required = g.required_tool if (g.rules.tool_hints or not g.pending) else None
        for name, rect in self.tray_slots(width, height):
            selected = name == g.tool
            pg.draw.rect(surf, (34,82,92,235) if selected else (12,29,42,215), rect,
                         border_radius=6)
            if name == required:
                pg.draw.rect(surf, green if selected else amber, rect, 2, border_radius=6)
            text = self._fit(font, t(self.lang, "short."+name), rect[2]-6)
            image = self._text(font, text, (232,240,247) if selected else light)
            surf.blit(image, (rect[0]+3, rect[1]+(rect[3]-image.get_height())//2))

    def _draw_card(self, pg, surf, width, height, label, lines, fill, edge):
        box = self.card_rect(width, height)
        pg.draw.rect(surf, fill, box, border_radius=10)
        pg.draw.rect(surf, edge, box, 2, border_radius=10)
        font = getattr(self, "_font", None)
        rows = [(line, color) for text, color in lines
                for line in self._wrap(font, text, box[2]-28)]
        for i, (text, color) in enumerate(rows[:4]):
            label(text, box[0]+14, box[1]+6+i*26, color=color)

    def _draw_common(self, pg, surf, width, height, label, light, green, amber, red):
        c = self.controller
        g = c.game
        lang = self.lang
        if g.ending:
            self._draw_results(pg, surf, width, height, label, light, green, amber, red)
        if g.patient.alert and not g.ending:
            limit = g.rules.alert_timeout
            timer = (t(lang, "ui.hold_timer", s=f"{g.alert_elapsed:.0f}", limit=f"{limit:.0f}")
                     if limit is not None else t(lang, "ui.hold_untimed"))
            self._draw_card(pg, surf, width, height, label, (
                ("! "+t(lang, "ui.safety_hold"), red),
                (t(lang, "alert."+g.patient.alert), (232,240,247)),
                (t(lang, "hint."+g.patient.alert), light),
                (t(lang, "ui.assess_or_abort")+"  ·  "+timer, amber)),
                (91,35,49,240), red+(255,))
        elif g.pending and not g.ending:
            name = g.pending[0]
            comp = COMPLICATIONS[name]
            if comp.remedy == "escalate":
                how = t(lang, "manage.escalate")
            elif g.rules.tool_hints:
                how = t(lang, "manage.tool", tool=t(lang, "tool."+comp.remedy),
                        site=t(lang, "site."+(comp.site or "centre")))
            else:
                how = t(lang, "manage.choose")
            sub = (t(lang, "manage.major") if comp.major and comp.remedy != "escalate"
                   else t(lang, "ui.in_hand", tool=t(lang, "tool."+g.tool)) if g.tool
                   else t(lang, "ui.no_tool"))
            self._draw_card(pg, surf, width, height, label, (
                ("! "+t(lang, "manage.title", alert=t(lang, "alert."+name)),
                 red if comp.major else amber),
                (how, (232,240,247)), (sub, light)),
                (70,46,40,236) if comp.major else (52,52,38,236),
                (red if comp.major else amber)+(255,))
        elif g.phase == Phase.PREOP and not g.ending:
            profile = PROFILES[g.case]
            none = t(lang, "chart.none")
            self._draw_card(pg, surf, width, height, label, (
                (f"{t(lang, 'chart.title')} · {t(lang, 'case.'+g.case)} · "
                 f"{t(lang, 'chart.age', age=profile.age)}", light),
                (f"{t(lang, 'chart.conditions')}: "
                 + (", ".join(t(lang, "cond."+k) for k in profile.conditions) or none),
                 (232,240,247)),
                (f"{t(lang, 'chart.medications')}: "
                 + (", ".join(t(lang, "med."+k) for k in profile.medications) or none),
                 (232,240,247)),
                (t(lang, "chart.baseline", hr=profile.heart_rate, sbp=profile.sbp,
                   dbp=profile.dbp), green)),
                (12,29,42,232), light+(255,))
        elif g.paused and not g.ending:
            label(t(lang, "ui.paused"),width//2-110,height//2+70,color=amber)

    def _draw_results(self, pg, surf, width, height, label, light, green, amber, red):
        """Explained score and recent timeline, drawn over the finished case."""
        g = self.controller.game
        lang = self.lang
        x, y = width//2-300, height//2-215
        pg.draw.rect(surf,(16,44,58,246),(x,y,600,410),border_radius=14)
        pg.draw.rect(surf,light,(x,y,600,410),2,border_radius=14)
        color = (green if g.ending in (ENDING_COMPLETE, ENDING_MANAGED)
                 else red if g.ending in (ENDING_FAILED, ENDING_UNRESOLVED) else amber)
        label(t(lang, "ending."+g.ending)[:40], x+20, y+14, color=color)
        label(f"{t(lang, 'ui.score')}: {g.score()} / 100", x+20, y+44)
        for i, row in enumerate(explain(g, lang)):
            yy = y+80+i*44
            label(f"{row['label'][:22]}  {row['points']:.0f}/{row['max']}", x+20, yy,
                  color=green if row['points'] >= row['max'] else amber)
            label(row['reasons'][0][:58], x+34, yy+20, color=light)
        for i, row in enumerate(timeline(g, lang)[-3:]):
            label(f"{row['t']:6.1f}s {row['text']}"[:60], x+20, y+306+i*24,
                  color=red if row["critical"] else (232,240,247))
        label(f"S: {t(lang, 'ui.export')[2:]}   R: {t(lang, 'ui.retry')[2:]}"[:50],
              x+20, y+380, color=amber)

    @staticmethod
    def _point(pg,surf,x,y,c,width,height,color,r=6):
        if c.target_depth is None:
            return
        point=eye_to_pixel(x,y,c.target_depth,width,height,c.view)
        if point is None:
            return
        px,py=round(point[0]),round(point[1])
        if 0 <= px < width and 0 <= py < height:
            pg.draw.circle(surf,color,(px,py),r,2)


def save_session(controller: Surgery3DController,
                 directory: str | Path = "session_logs",
                 lang: str = "en") -> tuple[Path, Path]:
    """Save only synthetic logs; replay rejects incomplete journal exports."""
    root=Path(directory)
    trace=controller.game.export_jsonl()
    replay=controller.game.export_replay_jsonl()
    root.mkdir(parents=True,exist_ok=True)
    basename=f"gl3d_{controller.game.case}_{controller.game.seed}"
    first=root/f"{basename}.jsonl"
    second=root/f"{basename}.replay.jsonl"
    first.write_text(trace,encoding="utf-8")
    second.write_text(replay,encoding="utf-8")
    # Explained report, events CSV and metrics CSV share the same session.
    save_report(controller.game, root, prefix="gl3d", lang=lang)
    return first,second


def cycle_tool(controller: Surgery3DController, step: int = 1) -> bool:
    """T / Shift+T: select the next / previous instrument (engine-validated)."""
    current = controller.game.tool
    index = ((TOOL_NAMES.index(current)+step) % len(TOOL_NAMES) if current in TOOL_NAMES
             else 0 if step > 0 else len(TOOL_NAMES)-1)
    return controller.command("tool", TOOL_NAMES[index])


def cycle_view(hud: SurgeryHUD) -> str:
    """C key: microscope (operate) -> operating room -> surgeon -> monitor."""
    hud.camera = VIEW_CYCLE[(VIEW_CYCLE.index(hud.camera)+1) % len(VIEW_CYCLE)]
    return hud.camera


def room_frame(room, game, lang: str, pygame, group: int | None = None) -> None:
    """Refresh the room's people and display contents from the Game
    (`group` 0/1 refreshes half of the displays; None all of them)."""
    from .screens3d import all_screens
    active = game.phase in (Phase.PHACO, Phase.CORTEX) and not game.ending
    room.set_people(game.tool, active)
    room.set_screens(all_screens(pygame, game, lang, active=active, group=group))


def quick_use(controller: Surgery3DController, tool: str) -> bool:
    """V (viscoelastic) / D (hydrodissection): pick `tool`, use it at the centre."""
    if controller.game.tool != tool and not controller.command("tool", tool):
        return False
    return controller.command("use")


def tray_pick(controller: Surgery3DController, x: int, y: int,
              width: int, height: int) -> bool:
    """Mouse click on the instrument row; False when the click is elsewhere."""
    g = controller.game
    if g.ending or g.phase in (Phase.PREOP, Phase.ANESTHESIA):
        return False
    for name, (rx, ry, rw, rh) in SurgeryHUD.tray_slots(width, height):
        if rx <= x < rx+rw and ry <= y < ry+rh:
            controller.command("tool", name)
            return True
    return False


def resume_controller(controller: Surgery3DController,
                      path=AUTOSAVE) -> bool:
    """Swap in a verified autosaved game; the caller reports failures."""
    game = load_autosave(path)
    controller.game = game
    controller.tool_depth = controller.target_depth or controller.tool_depth
    controller.last_pose = None
    controller.last_contact = None
    controller._sync(Phase.PREOP if game.phase != Phase.PREOP else Phase.ABORTED)
    return True


def advance_preop(controller: Surgery3DController) -> bool:
    """SPACE in PREOP: tick the next checklist item, then start the case."""
    g = controller.game
    for item in PREOP_CHECKS:
        if item not in g.eye.preop_checks:
            return controller.command("verify", item)
    return controller.command("confirm")


def run(case: str="normal",seed: int=7,difficulty: str="standard",
        lang: str="en",resume: str | None=None) -> None:
    try:
        import pygame
        import moderngl
    except ImportError as exc:
        raise SystemExit("Install: python -m pip install -r requirements-3d.txt") from exc
    pygame.init()
    atlas=None
    room=None
    autosaver=None
    try:
        from .app import Sounds
        controller=Surgery3DController(case,seed,difficulty)
        atlas=GPUEyePreview(pygame,moderngl,size=(1280,720))
        hud=SurgeryHUD(controller)
        hud.lang=lang if lang in LANGUAGES else "en"
        sounds=Sounds(pygame)
        autosaver=BackgroundAutosave()
        if resume:
            try:
                resume_controller(controller,resume)
                hud.status=t(hud.lang,"ui.resumed")
            except (OSError,ValueError) as exc:
                hud.status=t(hud.lang,"ui.resume_failed",error=type(exc).__name__)
        heard_alerts=len(controller.game.alerts)
        heard_ending=bool(controller.game.ending)
        saved_phase=controller.game.phase
        current_atlas="CATARACT"
        clock=pygame.time.Clock()
        profiler=FrameProfiler(capacity=600)
        frames=0
        dragging=False
        drag_phase=None
        room_refresh=0.
        room_group=0
        cursor=(0,0)
        running=True
        while running:
            elapsed_ms=clock.tick(60)
            dt=min(elapsed_ms/1000., .05)
            if frames:
                profiler.record("frame",min(elapsed_ms,10_000))
            frames+=1
            if hud.show_perf and frames%30==0:
                hud.perf=profiler.stats("frame")
            for event in pygame.event.get():
                g=controller.game
                if event.type==pygame.QUIT:
                    autosaver.submit(controller.game)
                    running=False
                elif event.type==pygame.MOUSEBUTTONUP and event.button==1:
                    dragging=False
                elif event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
                    cursor=event.pos
                    hud.last_cursor=cursor
                    if tray_pick(controller,*cursor,*pygame.display.get_window_size()):
                        continue
                    if hud.camera != VIEW_CYCLE[0]:
                        continue        # room views observe; operate under the microscope
                    dragging=True
                    drag_phase=g.phase
                    controller.pointer(*cursor,*pygame.display.get_window_size(),
                                       fresh_press=True)
                elif event.type==pygame.MOUSEMOTION:
                    cursor=event.pos
                    hud.last_cursor=cursor
                    if hud.camera != VIEW_CYCLE[0]:
                        pass
                    elif dragging and g.phase==Phase.CAPSULE:
                        controller.pointer(*cursor,*pygame.display.get_window_size())
                    else:
                        controller.inspect(*cursor,*pygame.display.get_window_size())
                elif event.type==pygame.KEYDOWN:
                    key=event.key
                    if key==pygame.K_SPACE:
                        if g.phase==Phase.PREOP:
                            advance_preop(controller)
                        elif g.phase==Phase.ANESTHESIA:
                            controller.command("prepare")
                    elif key==pygame.K_a:
                        controller.command("assess")
                    elif key==pygame.K_x:
                        controller.command("abort")
                    elif key==pygame.K_ESCAPE:
                        controller.command("pause")
                    elif key==pygame.K_r:
                        controller.restart()
                        hud.last_cursor=None
                        dragging=False
                        heard_alerts=0
                        heard_ending=False
                    elif key==pygame.K_t:
                        cycle_tool(controller,-1 if event.mod & pygame.KMOD_SHIFT else 1)
                    elif key==pygame.K_c:
                        cycle_view(hud)
                        dragging=False
                    elif key==pygame.K_v:
                        quick_use(controller,"ovd_cannula")
                    elif key==pygame.K_b:
                        controller.command("escalate")
                    elif key==pygame.K_d and g.phase==Phase.PHACO:
                        quick_use(controller,"hydro_cannula")
                    elif key==pygame.K_n and g.phase==Phase.PREOP and not g.eye.preop_checks:
                        controller.restart(CASES[(CASES.index(g.case)+1)%len(CASES)])
                    elif key==pygame.K_l:
                        hud.lang=LANGUAGES[(LANGUAGES.index(hud.lang)+1)%len(LANGUAGES)]
                    elif key==pygame.K_d and g.phase==Phase.PREOP and not g.eye.preop_checks:
                        levels=tuple(DIFFICULTIES)
                        controller.restart(difficulty=levels[(levels.index(g.difficulty)+1)%len(levels)])
                    elif key==pygame.K_s and g.ending:
                        try:
                            first,second=save_session(controller,lang=hud.lang)
                            hud.status=f"Saved {first.name} and {second.name}"
                        except (OSError,ValueError,RuntimeError) as exc:
                            hud.status=f"Export failed: {type(exc).__name__}"
                    elif key==pygame.K_m:
                        hud.reduced_motion=not hud.reduced_motion
                    elif key==pygame.K_h:
                        hud.high_contrast=not hud.high_contrast
                    elif key==pygame.K_F3:
                        hud.show_perf=not hud.show_perf
                        hud.perf=profiler.stats("frame")
                    elif key==pygame.K_q:
                        controller.adjust_depth(-1)
                    elif key==pygame.K_e:
                        controller.adjust_depth(1)
                    elif pygame.K_1<=key<=pygame.K_9:
                        number=key-pygame.K_1
                        if g.phase==Phase.PREOP and not g.eye.preop_checks:
                            if number < len(CASES):
                                controller.restart(CASES[number])
                        elif g.phase==Phase.CLOSE and number < 3:
                            controller.command("verify",CHECKS[number])
                    elif key in (pygame.K_LEFT,pygame.K_RIGHT,
                                 pygame.K_UP,pygame.K_DOWN):
                        controller.view.key({
                            pygame.K_LEFT:"left",pygame.K_RIGHT:"right",
                            pygame.K_UP:"up",pygame.K_DOWN:"down"}[key])
                    elif key in (pygame.K_EQUALS,pygame.K_PLUS,pygame.K_KP_PLUS):
                        controller.view.key("zoom_in")
                    elif key in (pygame.K_MINUS,pygame.K_KP_MINUS):
                        controller.view.key("zoom_out")

            # Stop held gesture when a critical alert or a complete case occurs.
            g=controller.game
            if len(g.alerts) > heard_alerts:
                heard_alerts=len(g.alerts)
                sounds.play("alert")
            if g.ending and not heard_ending:
                heard_ending=True
                sounds.play("end")
            if g.phase != saved_phase:
                saved_phase=g.phase
                autosaver.submit(g)          # written off the frame loop
            if g.patient.alert or g.ending or g.paused or g.phase != drag_phase:
                dragging=False    # a held gesture never carries into a new step
            if dragging and g.phase in (Phase.PHACO,Phase.CORTEX):
                controller.pointer(*cursor,*pygame.display.get_window_size())
            controller.advance_clock(dt)
            if hud.camera != VIEW_CYCLE[0]:
                # Operating-room views: displays refresh at about 10 Hz.
                if room is None:
                    from .gl_room import RoomRenderer
                    room=RoomRenderer(atlas.ctx,moderngl,pygame)
                    room_frame(room,controller.game,hud.lang,pygame)
                    room_refresh=0.
                room_refresh-=dt
                if room_refresh<=0.:
                    # Alternate halves: each display refreshes at about 10 Hz
                    # without one long frame painting all of them.
                    room_group=1-room_group
                    room_frame(room,controller.game,hud.lang,pygame,room_group)
                    room_refresh=.05
                hud.set_frame_proximity(None)
                atlas.render_room(room,hud.camera,clock.get_fps(),overlay=hud)
                continue
            if controller.view.phase != current_atlas:
                current_atlas=controller.view.phase
                atlas.set_meshes(atlas_meshes(current_atlas))
                atlas.clear_selection()
            eye=controller.game.eye
            has_capsule, capsule_damage = capsule_display_state(controller.game)
            feedback=visual_feedback(controller.game,
                reduced_motion=hud.reduced_motion,
                high_contrast=hud.high_contrast)
            proximity=probe_surface(controller,feedback)
            hud.set_frame_proximity(proximity)
            atlas.render(controller.view,clock.get_fps(),overlay=hud,
                         appearance=AnatomyAppearance(eye.opacity,eye.cortex,
                                                      eye.iol_alignment,
                                                      iol_visual_deployment(controller.game),
                                                      capsule_damage, has_capsule),
                         tool_pose=visible_stylus(controller),
                         vision=feedback,
                         surface_probe=proximity,
                         complications=complication_visuals(controller.game),
                         contact=(controller.last_contact if not
                                  (controller.game.paused or controller.game.ending
                                   or controller.game.patient.alert) else None))
    finally:
        if autosaver is not None:
            autosaver.close()
        if room is not None:
            room.release()
        if atlas is not None:
            atlas.close()
        pygame.quit()


def main(argv=None) -> int:
    parser=argparse.ArgumentParser(description="Experimental 3D synthetic cataract game")
    parser.add_argument("--case",choices=list(CASES),default="normal")
    parser.add_argument("--difficulty",choices=list(DIFFICULTIES),default="standard")
    parser.add_argument("--lang",choices=list(LANGUAGES),default="en")
    parser.add_argument("--seed",type=int,default=7)
    parser.add_argument("--resume",nargs="?",const=str(AUTOSAVE),default=None,
                        help="continue a verified autosave")
    ns=parser.parse_args(argv)
    if isinstance(ns.seed,bool) or abs(ns.seed)>2**63-1:
        parser.error("seed must fit in bounded signed 64-bit range")
    run(ns.case,ns.seed,ns.difficulty,ns.lang,ns.resume)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
