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
import sys

from .engine import Phase
from .gl_preview import GPUEyePreview, AnatomyAppearance, atlas_meshes
from .input3d import Surgery3DController, eye_to_pixel
from .signals import sample_trace

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
}
CHECKS = ("alignment", "wound", "handoff")


class SurgeryHUD:
    """Visual-only overlay; it may never modify the Game or change a score."""

    def __init__(self, controller: Surgery3DController) -> None:
        self.controller = controller
        self.last_cursor: tuple[int, int] | None = None
        self.status = "Synthetic training experiment. No clinical use."

    def draw(self, pg, surf, view, width: int, height: int, font, title) -> None:
        c = self.controller
        g = c.game
        # The atlas drawing underneath remains available in all modes.
        # The translucent HUD panels do not need an independent GL context.
        pg.draw.rect(surf, (12, 29, 42, 224), (12, 176, 247, 270),
                     border_radius=10)
        pg.draw.rect(surf, (12, 29, 42, 224), (width-267, 176, 255, 270),
                     border_radius=10)
        def label(text, x, y, *, color=(232, 240, 247), large=False):
            image = (title if large else font).render(str(text), True, color)
            surf.blit(image, (x, y))
        light=(142,211,233)
        green=(126,224,176)
        amber=(247,195,109)
        red=(247,122,136)
        label("CURRENT PROCEDURE", 24, 189, color=light)
        phase_label = PHASE_NAMES[g.phase]
        # Long titles are split to avoid spilling onto the iris.
        label(phase_label[:21], 24, 221)
        if len(phase_label) > 21:
            label(phase_label[21:40], 24, 244)
        label(f"Phase: {g.phase.value}", 24, 285)
        label(f"Score (synthetic): {g.score():03d}", 24, 316)
        label(f"Tool z: {c.tool_depth:+.2f}", 24, 350, color=green)
        target = c.target_depth
        label(f"Target z: {target:+.2f}" if target is not None
              else "Tool inactive", 24, 378, color=light)
        label("Q/E adjust depth", 24, 410, color=amber)

        label("PATIENT MONITOR", width-254, 189, color=light)
        label("SYNTHETIC VALUES", width-254, 220, color=amber)
        p = g.patient
        label(f"HR {p.heart_rate}   SpO2 {p.spo2}%", width-254, 253, color=green)
        label(f"NIBP {p.sbp}/{p.dbp}", width-254, 284, color=amber)
        label(f"STATUS {p.alert or 'STABLE'}"[:22], width-254, 316,
              color=red if p.alert else green)
        wave = sample_trace("ecg", p.heart_rate, g.time, count=170)
        left = width-255
        pg.draw.lines(surf, green, False,
                      [(left+i, 403-int(val*29)) for i,val in enumerate(wave)],2)
        pg.draw.line(surf, (54,100,122), (left,415), (width-34,415), 1)

        # Targets projected using the same GLSL camera and ray-plane scale.
        if g.phase == Phase.ENTRY:
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
            label(f"REMAINING: {value:.0%}", width//2-92,
                  height-114, color=amber)
        elif g.phase == Phase.IOL:
            self._point(pg,surf,.5,.5,c,width,height,green,r=15)

        if g.phase in (Phase.RECOVERY,Phase.ABORTED):
            pg.draw.rect(surf,(26,58,69,243),
                         (width//2-228,height//2-72,456,132),border_radius=12)
            label(g.ending or "SIMULATED RESULT",width//2-187,height//2-45,
                  color=green if g.phase==Phase.RECOVERY else amber)
            label("S: save JSONL  R: restart",width//2-187,height//2-4)
        if g.phase == Phase.CLOSE:
            for i,key in enumerate(CHECKS):
                label(f"{i+1} {key.upper()} "+("DONE" if key in g.eye.final_checks
                      else "PENDING"),width//2-105,height-134+i*26,
                      color=green if key in g.eye.final_checks else amber)
        if g.patient.alert:
            pg.draw.rect(surf,(91,35,49,245),
                         (width//2-210,height//2-39,420,84),border_radius=9)
            label("SAFETY HOLD: "+g.patient.alert,width//2-198,height//2-24,
                  color=red)
            label("A: assess   X: safe abort",width//2-198,height//2+7)
        elif g.paused:
            label("PAUSED - ESC TO RESUME",width//2-110,height//2+70,color=amber)

        # Lower instructions remain visible in small windows.
        bottom=height-69
        pg.draw.rect(surf,(10,27,39,225),(12,bottom,width-24,58),
                     border_radius=10)
        instructions = (
            "SPACE next  |  MOUSE surgical task  |  1-3 final checks  |  A assess",
            "ARROWS orbit  +/- zoom  Q/E depth  X abort  ESC pause  R restart",
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
    basename=f"gl3d_{controller.game.case}_{controller.game.seed}"
    first=root/f"{basename}.jsonl"
    second=root/f"{basename}.replay.jsonl"
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
        cursor=(0,0)
        running=True
        while running:
            dt=min(clock.tick(60)/1000., .05)
            for event in pygame.event.get():
                g=controller.game
                if event.type==pygame.QUIT:
                    running=False
                elif event.type==pygame.MOUSEBUTTONUP and event.button==1:
                    dragging=False
                elif event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
                    dragging=True
                    cursor=event.pos
                    hud.last_cursor=cursor
                    controller.pointer(*cursor,*pygame.display.get_window_size(),
                                       fresh_press=True)
                elif event.type==pygame.MOUSEMOTION:
                    cursor=event.pos
                    hud.last_cursor=cursor
                    if dragging and g.phase==Phase.CAPSULE:
                        controller.pointer(*cursor,*pygame.display.get_window_size())
                elif event.type==pygame.KEYDOWN:
                    key=event.key
                    if key==pygame.K_SPACE:
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
                    elif key==pygame.K_q:
                        controller.adjust_depth(-1)
                    elif key==pygame.K_e:
                        controller.adjust_depth(1)
                    elif key in (pygame.K_1,pygame.K_2,pygame.K_3,pygame.K_4):
                        number=key-pygame.K_1
                        if g.phase==Phase.PREOP:
                            controller.restart(("normal","motion","vitals","capsule")[number])
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
            if g.patient.alert or g.ending or g.paused:
                dragging=False
            if dragging and g.phase in (Phase.PHACO,Phase.CORTEX):
                controller.pointer(*cursor,*pygame.display.get_window_size())
            controller.advance_clock(dt)
            if controller.view.phase != current_atlas:
                current_atlas=controller.view.phase
                atlas.set_meshes(atlas_meshes(current_atlas))
                atlas.clear_selection()
            eye=controller.game.eye
            atlas.render(controller.view,clock.get_fps(),overlay=hud,
                         appearance=AnatomyAppearance(eye.opacity,eye.cortex,
                                                      eye.iol_alignment))
    finally:
        if atlas is not None:
            atlas.close()
        pygame.quit()


def main(argv=None) -> int:
    parser=argparse.ArgumentParser(description="Experimental 3D synthetic cataract game")
    parser.add_argument("--case",choices=["normal","motion","vitals","capsule"],default="normal")
    parser.add_argument("--seed",type=int,default=7)
    ns=parser.parse_args(argv)
    if isinstance(ns.seed,bool) or abs(ns.seed)>2**63-1:
        parser.error("seed must fit in bounded signed 64-bit range")
    run(ns.case,ns.seed)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
