"""Interactive 3D viewport for a *mock* cataract surgery game.

The player is the operating surgeon. The strict ReplayGame remains the only
authority for every phase,
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
import sys

from .complications import CASE_KEYS, CASES, DECISIONS, narrate, step_marker
from .engine import ENDED, PHASES, Phase
from .gl_preview import GPUEyePreview, AnatomyAppearance, atlas_meshes
from .input3d import DEPTH_TOLERANCE, Surgery3DController, eye_to_pixel
from .replay import session_paths
from .signals import sample_trace
from .tool3d import visible_stylus
from .iol3d import iol_visual_deployment
from .capsule3d import capsule_display_state
from .vision3d import visual_feedback
from .surface_probe3d import SurfaceProbe, probe_surface

PHASE_NAMES = {
    Phase.PREOP: "PREOPERATIVE REVIEW",
    Phase.ANESTHESIA: "ANAESTHESIA & PREP",
    Phase.ENTRY: "INCISIONS",
    Phase.CAPSULE: "CAPSULORHEXIS",
    Phase.PHACO: "PHACOEMULSIFICATION",
    Phase.CORTEX: "CORTEX I/A",
    Phase.IOL: "IOL IMPLANTATION",
    Phase.CLOSE: "CLOSURE CHECKS",
    Phase.RECOVERY: "DEBRIEF",
    Phase.ABORTED: "PROCEDURE STOPPED",
    Phase.FAILED: "CRITICAL FAILURE",
}
OUTCOME_COLORS = {"SUCCESS": (126,224,176), "MANAGED": (142,211,233),
                  "COMPLICATED": (247,195,109), "SAFE_ABORT": (247,195,109),
                  "CRITICAL_FAILURE": (247,122,136)}


def wrap(text: str, width: int) -> list[str]:
    words, lines, cur = str(text).split(), [], ""
    for word in words:
        if cur and len(cur) + len(word) + 1 > width:
            lines.append(cur)
            cur = word
        else:
            cur = (cur + " " + word).strip()
    if cur:
        lines.append(cur)
    return lines
CHECKS = ("alignment", "wound", "handoff")
TICK = 1 / 60
# One held-instrument command per fixed simulation tick (see app.HELD_PHASES).
HELD_PHASES = (Phase.CAPSULE, Phase.PHACO, Phase.CORTEX)


class SurgeryHUD:
    """Visual-only overlay; it may never modify the Game or change a score."""

    def __init__(self, controller: Surgery3DController) -> None:
        self.controller = controller
        self.last_cursor: tuple[int, int] | None = None
        self.status = "You are the surgeon. Mock procedure - no clinical use."
        self.reduced_motion = False
        self.high_contrast = False
        # Prepared exactly once per rendered frame by the outer game loop.
        # HUD painting must never trigger a second expensive BVH query.
        self.frame_proximity: SurfaceProbe | None = None
        self._probe_phase: Phase | None = None
        self._probe_pose: tuple[float,float,float] | None = None
        self._probe_camera: tuple[float,float] | None = None
        self._narrated: tuple[int, int] = (id(controller.game), 1)

    def narrate(self) -> None:
        """Show the newest game event as the status line (display only)."""
        game = self.controller.game
        key, seen = self._narrated
        if key != id(game):
            seen = 1
        for event in game.events[seen:]:
            text = narrate(event)
            if text:
                self.status = text
        self._narrated = (id(game), len(game.events))

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

    # Fixed layout rows (left panel), shared with tests that sample pixels.
    PANEL_TOP = 138
    ROW = 27

    @classmethod
    def mesh_gap_rect(cls, width: int, height: int) -> tuple[int, int, int, int]:
        """Screen rectangle of the 'MESH GAP' label inside the left panel."""
        return (24, cls.PANEL_TOP + 13 * cls.ROW + 4, 228, cls.ROW)

    def draw(self, pg, surf, view, width: int, height: int, font, title) -> None:
        c = self.controller
        g = c.game
        light=(142,211,233)
        green=(126,224,176)
        amber=(247,195,109)
        red=(247,122,136)
        muted=(150,176,190)
        top=self.PANEL_TOP
        row=self.ROW
        panel_bottom=height-112
        # Side panels never overlap the bottom status line or key help, and
        # every label below is placed on a row inside its own panel.
        pg.draw.rect(surf, (12, 29, 42, 224), (12, top, 252, panel_bottom-top),
                     border_radius=10)
        pg.draw.rect(surf, (12, 29, 42, 224), (width-268, top, 256, 12*row+14),
                     border_radius=10)

        def label(text, x, y, *, color=(232, 240, 247), large=False):
            image = (title if large else font).render(str(text), True, color)
            surf.blit(image, (x, y))

        def meter(y, value, color, *, x=24, w=224):
            pg.draw.rect(surf, (35, 65, 77), (x, y, w, 8), border_radius=4)
            fill=round(w*min(1., max(0., value)))
            if fill:
                pg.draw.rect(surf, color, (x, y, fill, 8), border_radius=4)

        def y_at(index):
            return top + 8 + index*row

        # --- Left panel: the surgeon's task ---------------------------------
        label("YOU ARE THE SURGEON", 24, y_at(0), color=light)
        phase_label = PHASE_NAMES[g.phase]
        label(phase_label[:21], 24, y_at(1))
        if len(phase_label) > 21:
            label(phase_label[21:40], 24, y_at(2))
        step = PHASES.index(g.phase) + 1 if g.phase in PHASES else None
        label((f"Step {step}/{len(PHASES)}" if step else "Stopped")
              + f"   Score {g.score():03d}", 24, y_at(3), color=muted)

        target = c.target_depth
        hint = c.depth_hint()
        if target is None:
            label("Instrument idle", 24, y_at(4), color=muted)
        else:
            hint_text = {"OK": "DEPTH OK", "DEEPER": "DEPTH: Q / wheel down",
                         "SHALLOWER": "DEPTH: E / wheel up"}[hint]
            label(hint_text, 24, y_at(4), color=green if hint == "OK" else amber)
            # Depth gauge: -0.30 (deep, right) .. +0.20 (shallow, left).
            gx, gw = 24, 224
            def gauge(z):
                return gx + round((.2 - z) / .5 * gw)
            gy = y_at(5) + 6
            pg.draw.rect(surf, (35, 65, 77), (gx, gy, gw, 8), border_radius=4)
            lo, hi = gauge(target + DEPTH_TOLERANCE), gauge(target - DEPTH_TOLERANCE)
            pg.draw.rect(surf, (48, 120, 92), (lo, gy, max(2, hi-lo), 8), border_radius=4)
            tx = gauge(c.tool_depth)
            pg.draw.rect(surf, green if hint == "OK" else amber, (tx-2, gy-5, 5, 18))
            label(f"tip {c.tool_depth:+.2f}  target {target:+.2f}", 24, y_at(6),
                  color=muted)
        if c.last_contact is not None and not g.ending:
            kind=c.last_contact.status
            label(f"GUIDE: {kind}", 24, y_at(7),
                  color=green if kind=="TARGET" else amber if kind in
                        ("NEAR","VISITED") else red)

        # Real procedure sub-steps of this phase, in the panel, never over
        # the operative field.
        for i, (step_label, done, key_hint) in enumerate(g.checklist()[:4]):
            marker = step_marker(done, key_hint)
            text = f"{marker} {step_label}"
            label(text[:23], 24, y_at(8+i),
                  color=green if done else amber if marker != "[ ]" else light)
        if g.phase in (Phase.PHACO, Phase.CORTEX):
            warn = g.stress_warning
            label("TISSUE STRESS - recentre" if warn else "Tissue stress",
                  24, y_at(10), color=red if warn else muted)
            meter(y_at(11)+6, g.tissue_stress, red if warn else amber)
        if g.phase in (Phase.IOL, Phase.CLOSE, Phase.RECOVERY):
            label(f"IOL unfold {iol_visual_deployment(g):.0%}", 24, y_at(12),
                  color=green)

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
        if proximity is not None:
            x, y, _, _ = self.mesh_gap_rect(width, height)
            label(f"MESH GAP {proximity.status} {proximity.gap:.3f}u",
                  x, y, color=amber)

        # --- Right panel: synthetic monitor and display options -------------
        right = width-254
        label("PATIENT MONITOR", right, y_at(0)+2, color=light)
        label("SYNTHETIC VALUES", right, y_at(1)+2, color=amber)
        p = g.patient
        label(f"HR {p.heart_rate}   SpO2 {p.spo2}%", right, y_at(2)+4, color=green)
        label(f"NIBP {p.sbp}/{p.dbp}", right, y_at(3)+4, color=amber)
        label(p.alert[:22] if p.alert else "STATUS STABLE", right, y_at(4)+4,
              color=red if p.alert else green)
        wave = sample_trace("ecg", p.heart_rate, g.time, count=170)
        left = width-255
        base = y_at(7)
        pg.draw.lines(surf, green, False,
                      [(left+i, base-int(val*29)) for i,val in enumerate(wave)],2)
        pg.draw.line(surf, (54,100,122), (left,base+12), (width-34,base+12), 1)
        capsule_on, damage = capsule_display_state(g)
        if capsule_on:
            label(("CAPSULE ALERT" if damage >= .15 else "CAPSULE INTACT"),
                  right, y_at(8)+4, color=red if damage >= .15 else green)
        if self.reduced_motion or self.high_contrast:
            flags=("LOW MOTION  " if self.reduced_motion else "") + ("HIGH CONTRAST" if self.high_contrast else "")
            label(flags.strip(), right, y_at(10)+4, color=(255,238,155))

        # Targets projected using the same GLSL camera and ray-plane scale.
        if g.phase == Phase.ENTRY:
            for i,(x,y) in enumerate(g._entry_target):
                self._point(pg, surf, x,y,c, width,height,
                            green if i in g._entered else amber, r=9)
        elif g.phase == Phase.CAPSULE:
            for i in range(24):
                a=(i+.5)*math.tau/24
                self._point(pg, surf, .5+.28*math.cos(a),
                            .5+.28*math.sin(a),c,width,height,
                            green if i in g.eye.capsule_points else amber,r=3)
        elif g.phase == Phase.IOL:
            self._point(pg,surf,.5,.5,c,width,height,green,r=15)

        if g.phase in ENDED:
            outcome = g.outcome()
            headline, explain = g.outcome_title()
            lines = []
            for name, verdict in g.debrief():
                if name == "Result":
                    continue
                for j, part in enumerate(wrap(verdict, 33) or [""]):
                    lines.append((name if j == 0 else "", part))
            lines = lines[:7]
            box_h = 176 + 26*len(lines)
            box = (width//2-280, height//2-box_h//2, 560, box_h)
            pg.draw.rect(surf,(18,44,56,246),box,border_radius=12)
            pg.draw.rect(surf,(106,211,227,255),box,2,border_radius=12)
            bx, by = box[0]+22, box[1]+12
            label("SURGEON DEBRIEF", bx, by, color=light)
            label(headline, bx, by+26, large=True, color=OUTCOME_COLORS[outcome])
            label(explain, bx, by+68)
            score = ("Not scored - safe stop" if outcome == "SAFE_ABORT" else
                     "Score 0/100 (safety veto)" if outcome == "CRITICAL_FAILURE" else
                     f"Score {g.score()}/100 (synthetic game score)")
            label(score, bx, by+96, color=muted)
            for i,(name,verdict) in enumerate(lines):
                label(name[:19], bx, by+128+i*26, color=muted)
                label(verdict[:34], bx+200, by+128+i*26)
            label("S: save session   R: new case", bx, box[1]+box_h-36, color=amber)
        elif g.phase == Phase.PREOP and not g.patient.alert:
            brief = CASES[g.case]
            box = (width//2-280, height//2-110, 560, 214)
            pg.draw.rect(surf,(18,44,56,246),box,border_radius=12)
            pg.draw.rect(surf,(106,211,227,255),box,2,border_radius=12)
            bx, by = box[0]+22, box[1]+12
            label("CASE BRIEF - YOU ARE THE OPERATING SURGEON", bx, by, color=light)
            label(brief.title, bx, by+26, large=True)
            label(brief.patient, bx, by+68)
            for i, line in enumerate(wrap("Risk factors: " + brief.risks, 50)[:2]):
                label(line, bx, by+96+i*26, color=amber)
            label("SPACE time-out & begin   1-9 other case", bx, by+160, color=green)
        if g.patient.alert and not g.ending:
            comp = g.complication
            box = (width//2-290, height//2-130, 580, 262)
            pg.draw.rect(surf,(70,30,44,248),box,border_radius=12)
            pg.draw.rect(surf,red+(255,),box,2,border_radius=12)
            bx, by = box[0]+20, box[1]+12
            label("SAFETY HOLD - INSTRUMENTS STOPPED", bx, by, color=red)
            label(comp.title if comp else g.patient.alert, bx, by+26, large=True)
            if comp:
                for i, line in enumerate(wrap("You see: " + comp.signs, 52)[:2]):
                    label(line, bx, by+68+i*25, color=amber)
            if g.awaiting_decision and comp:
                options = ("Continue as before", comp.manage, comp.refer_result)
                for i, text in enumerate(options):
                    label(f"{i+1}  {text}"[:52], bx, by+130+i*28,
                          color=(red if i == 0 else green if i == 1 else light))
            else:
                label("A  assess the situation", bx, by+136, color=green)
                label("X  stop the procedure safely", bx, by+166, color=light)
        elif g.paused:
            label("PAUSED - ESC TO RESUME",width//2-110,height//2+70,color=amber)

        # Lower instructions remain visible in small windows.
        bottom=height-69
        pg.draw.rect(surf, (10,27,39,225), (12,bottom,width-24,58),
                     border_radius=10)
        instructions = (
            "SPACE time-out | MOUSE instrument | V OVD  D hydro | Q/E WHEEL depth | A assess",
            "1-3 decide/checks  ARROWS orbit  +/- zoom  M motion  H contrast  X stop  R  S",
        )
        for i,msg in enumerate(instructions):
            label(msg[:90],24,bottom+6+i*25,color=green if i==0 else amber)
        label(self.status[:72], 24, height-100, color=light)
        # Avoid displaying an earlier cursor after phase changes or restart.
        if self.last_cursor and c.last_pose is not None:
            pg.draw.circle(surf,green,self.last_cursor,8,2)

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
                 directory: str | Path = "session_logs") -> tuple[Path, Path]:
    """Save only synthetic logs; replay rejects incomplete journal exports."""
    root=Path(directory)
    trace=controller.game.export_jsonl()
    replay=controller.game.export_replay_jsonl()
    root.mkdir(parents=True,exist_ok=True)
    first,second=session_paths(root,f"gl3d_{controller.game.case}_{controller.game.seed}")
    first.write_text(trace,encoding="utf-8")
    second.write_text(replay,encoding="utf-8")
    return first,second


def run(case: str="normal",seed: int=7) -> None:
    try:
        import pygame
        import moderngl
    except ImportError as exc:
        raise SystemExit("Install: python -m pip install -r requirements-3d.txt") from exc
    pygame.init()
    atlas=None
    try:
        controller=Surgery3DController(case,seed)
        atlas=GPUEyePreview(pygame,moderngl,size=(1280,720))
        hud=SurgeryHUD(controller)
        current_atlas="CATARACT"
        clock=pygame.time.Clock()
        dragging=False
        drag_phase=None
        cursor=(0,0)
        running=True
        accumulator=0.
        while running:
            dt=min(clock.tick(60)/1000., .1)
            for event in pygame.event.get():
                g=controller.game
                if event.type==pygame.QUIT:
                    running=False
                elif event.type==pygame.MOUSEBUTTONUP and event.button==1:
                    dragging=False
                elif event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
                    dragging=True
                    drag_phase=g.phase
                    cursor=event.pos
                    hud.last_cursor=cursor
                    if g.phase not in HELD_PHASES:
                        controller.pointer(*cursor,*pygame.display.get_window_size(),
                                           fresh_press=True)
                elif event.type==pygame.MOUSEMOTION:
                    # Held tasks sample the cursor once per simulation tick.
                    cursor=event.pos
                    hud.last_cursor=cursor
                    if not dragging:
                        controller.inspect(*cursor,*pygame.display.get_window_size())
                elif event.type==pygame.MOUSEWHEEL and event.y:
                    # Wheel up raises the tip (shallower), wheel down lowers it.
                    controller.adjust_depth(1 if event.y > 0 else -1)
                    controller.inspect(*cursor,*pygame.display.get_window_size())
                elif event.type==pygame.KEYDOWN:
                    key=event.key
                    if key in (pygame.K_1,pygame.K_2,pygame.K_3) and g.awaiting_decision:
                        controller.command("decide",DECISIONS[key-pygame.K_1])
                    elif key==pygame.K_v:
                        controller.command("ovd")
                    elif key==pygame.K_d:
                        controller.command("hydro")
                    elif key==pygame.K_SPACE:
                        if g.phase==Phase.PREOP:
                            controller.command("confirm")
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
                    elif key==pygame.K_s and g.ending:
                        try:
                            first,second=save_session(controller)
                            hud.status=f"Saved {first.name} and {second.name}"
                        except (OSError,ValueError,RuntimeError) as exc:
                            hud.status=f"Export failed: {type(exc).__name__}"
                    elif key==pygame.K_m:
                        hud.reduced_motion=not hud.reduced_motion
                    elif key==pygame.K_h:
                        hud.high_contrast=not hud.high_contrast
                    elif key==pygame.K_q:
                        controller.adjust_depth(-1)
                    elif key==pygame.K_e:
                        controller.adjust_depth(1)
                    elif pygame.K_1<=key<=pygame.K_9:
                        number=key-pygame.K_1
                        if g.phase==Phase.PREOP and number < len(CASE_KEYS):
                            controller.restart(CASE_KEYS[number])
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

            # Fixed 60 Hz simulation steps: removal speed and tissue stress
            # are the same at 30 or 144 rendered frames per second.
            accumulator+=dt
            steps=0
            while accumulator>=TICK and steps<6:
                g=controller.game
                # Stop held gesture on a safety hold, an ending, or a new step
                # (instruments change between steps).
                if g.patient.alert or g.ending or g.paused or g.phase!=drag_phase:
                    dragging=False
                if dragging and g.phase in HELD_PHASES:
                    controller.pointer(*cursor,*pygame.display.get_window_size())
                controller.advance_clock(TICK)
                accumulator-=TICK
                steps+=1
            if steps>=6:
                accumulator=0.
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
            hud.narrate()
            hud.set_frame_proximity(proximity)
            atlas.render(controller.view,clock.get_fps(),overlay=hud,
                         appearance=AnatomyAppearance(eye.opacity,eye.cortex,
                                                      eye.iol_alignment,
                                                      iol_visual_deployment(controller.game),
                                                      capsule_damage, has_capsule),
                         tool_pose=visible_stylus(controller),
                         vision=feedback,
                         surface_probe=proximity,
                         contact=(controller.last_contact if not
                                  (controller.game.paused or controller.game.ending
                                   or controller.game.patient.alert) else None))
    finally:
        if atlas is not None:
            atlas.close()
        pygame.quit()


def main(argv=None) -> int:
    parser=argparse.ArgumentParser(description="Mock cataract surgery game: you are the surgeon (3D)")
    parser.add_argument("--case",choices=list(CASE_KEYS),default="normal")
    parser.add_argument("--seed",type=int,default=7)
    ns=parser.parse_args(argv)
    if isinstance(ns.seed,bool) or abs(ns.seed)>2**63-1:
        parser.error("seed must fit in bounded signed 64-bit range")
    run(ns.case,ns.seed)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
