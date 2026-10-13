"""Pygame presentation for OphthoSim-AI.

The player is the operating surgeon of a mock cataract procedure. Visuals are
stylized, procedural 2.5D illustrations, NOT clinical graphics. Requires
pygame, and is intentionally independent of the headless simulation.
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path
import sys

from .complications import CASE_KEYS, CASES, DECISIONS, narrate, step_marker
from .engine import Phase
from .replay import ReplayGame as Game, session_paths
from .preview3d import draw_preview
from .signals import sample_trace

WIDTH, HEIGHT = 1280, 720
EYE_CX, EYE_CY, EYE_R = 640, 366, 222
BG = (7, 18, 30)
PANEL = (16, 32, 47)
PANEL2 = (20, 42, 58)
TEXT = (221, 234, 241)
MUTED = (144, 170, 183)
CYAN = (106, 211, 227)
MINT = (95, 220, 167)
AMBER = (238, 182, 106)
RED = (239, 114, 133)
TICK = 1 / 60
# Held-instrument phases: one command per fixed simulation tick, never per
# mouse event or rendered frame, so progress and stress do not depend on FPS
# or mouse polling rate.
HELD_PHASES = {Phase.CAPSULE, Phase.PHACO, Phase.CORTEX}

# Second-person briefings: the player is the operating surgeon.
PHASE_COPY = {
    Phase.PREOP: ('PREOPERATIVE REVIEW', 'Read the case brief, pick a case (1-9), then do the time-out.'),
    Phase.ANESTHESIA: ('ANAESTHESIA & PREP', 'Topical anaesthesia, antiseptic prep, drape and speculum.'),
    Phase.ENTRY: ('INCISIONS', 'Click the 3 incision sites, then inject viscoelastic (V).'),
    Phase.CAPSULE: ('CAPSULORHEXIS', 'Inject OVD (V) if needed, then drag round the ring. Never pull out.'),
    Phase.PHACO: ('PHACOEMULSIFICATION', 'Hydrodissect first (D), then hold on the nucleus inside the pupil.'),
    Phase.CORTEX: ('CORTEX I/A', 'Hold on the inner lens to aspirate the cortex. Stay central.'),
    Phase.IOL: ('IOL IMPLANTATION', 'Fill the bag with OVD (V), then click once at the optical centre.'),
    Phase.CLOSE: ('CLOSURE CHECKS', 'Verify IOL, wound seal and handoff (click or 1-3).'),
    Phase.RECOVERY: ('DEBRIEF', 'Mock procedure complete. Press E to export your session.'),
    Phase.ABORTED: ('PROCEDURE STOPPED', 'You stopped the mock procedure safely. Press R for a new case.'),
    Phase.FAILED: ('CRITICAL FAILURE', 'A major complication was ignored. Press R for a new case.'),
}
OUTCOME_COLORS = {'SUCCESS': MINT, 'MANAGED': CYAN, 'COMPLICATED': AMBER,
                  'SAFE_ABORT': AMBER, 'CRITICAL_FAILURE': RED}
CHECK_KEYS = ('alignment', 'wound', 'handoff')


def wrap(text, width):
    """Greedy word wrap by character count (fonts here are near-monospace)."""
    words = str(text).split()
    lines, cur = [], ''
    for word in words:
        if cur and len(cur) + len(word) + 1 > width:
            lines.append(cur)
            cur = word
        else:
            cur = (cur + ' ' + word).strip()
    if cur:
        lines.append(cur)
    return lines


def to_eye(pos):
    return ((pos[0] - EYE_CX) / (EYE_R * 2) + .5,
            (pos[1] - EYE_CY) / (EYE_R * 2) + .5)


def to_screen(point):
    return (round(EYE_CX + (point[0] - .5) * EYE_R * 2),
            round(EYE_CY + (point[1] - .5) * EYE_R * 2))


def render_eye(pg, surf, model, clock_s):
    """Procedural pseudo-depth: cornea highlights, iris, pupil and lens layers."""
    center = (EYE_CX, EYE_CY)
    pg.draw.circle(surf, (5, 10, 18), (center[0]+7, center[1]+10), EYE_R+15)
    # Sclera with diffuse illumination shading.
    for r in range(EYE_R, 135, -4):
        blend = (EYE_R-r)/(EYE_R-135)
        value = int(123+70*blend)
        pg.draw.circle(surf, (value, value+7, min(255, value+13)), center, r)
    pg.draw.circle(surf, (48, 79, 85), center, 153)
    # Radial iris fibers with depth cues.
    for r in range(151, 98, -3):
        t = (151-r)/53
        pg.draw.circle(surf, (int(21+18*t), int(73+37*t), int(80+20*t)), center, r)
    for i in range(180):
        a = i*math.tau/180
        inner = 104 + 4*math.sin(i*1.73)
        outer = 145 + 4*math.sin(i*.67)
        pg.draw.line(surf, (52 + (i%5)*5, 111+(i%4)*6, 114+(i%3)*4),
                     (round(EYE_CX+math.cos(a)*inner),round(EYE_CY+math.sin(a)*inner)),
                     (round(EYE_CX+math.cos(a)*outer),round(EYE_CY+math.sin(a)*outer)), 1)
    # Pupil: shrinks when the iris is prolapsing or traumatised (miosis).
    pupil = round(104 * min(1., model.work_radius / model.WORK_RADIUS))
    pg.draw.circle(surf, (10, 17, 27), center, pupil)
    # Synthetic cataract opacity. Display rings shrink smoothly with progress.
    if model.eye.opacity > 0:
        alpha = int(model.eye.opacity*188)
        overlay = pg.Surface((420,420),pg.SRCALPHA)
        pg.draw.circle(overlay, (200,187,136,alpha), (210,210), 99)
        for i in range(12):
            a = i*math.tau/12 + clock_s*.005
            p = (round(210+70*math.cos(a)),round(210+70*math.sin(a)))
            pg.draw.circle(overlay,(227,219,166,int(alpha*.7)),p,14+i%4*3)
        surf.blit(overlay, (EYE_CX-210,EYE_CY-210))
    if model.phase in {Phase.IOL, Phase.CLOSE, Phase.RECOVERY}:
        overlay = pg.Surface((260,260),pg.SRCALPHA)
        pg.draw.circle(overlay,(150,231,239,72),(130,130),105)
        pg.draw.circle(overlay,(215,253,255,145),(130,130),102,2)
        pg.draw.ellipse(overlay,(180,240,246,170), (54,28,152,204),2)
        surf.blit(overlay,(EYE_CX-130,EYE_CY-130))
    # Reflection and anterior corneal specular glint.
    transparent = pg.Surface((EYE_R*2+20,EYE_R*2+20),pg.SRCALPHA)
    pg.draw.ellipse(transparent,(240,254,255,46), (88,53,158,72))
    pg.draw.arc(transparent,(200,249,255,90),(30,35,385,380), .65, 2.35, 5)
    surf.blit(transparent,(EYE_CX-EYE_R-10,EYE_CY-EYE_R-10))
    history = model.alert_history
    live = model.patient.alert
    if model.ovd_chamber and model.phase in {Phase.ENTRY, Phase.CAPSULE}:
        sheen = pg.Surface((300,300),pg.SRCALPHA)
        pg.draw.circle(sheen,(150,225,240,34),(150,150),148)
        surf.blit(sheen,(EYE_CX-150,EYE_CY-150))
    if 'RHEXIS TEAR' in history:
        # Radial run-out of the capsulorhexis edge towards the periphery.
        a = math.radians(300)
        start = to_screen((.5+.28*math.cos(a), .5+.28*math.sin(a)))
        end = to_screen((.5+.42*math.cos(a+.08), .5+.42*math.sin(a+.08)))
        pg.draw.line(surf, RED, start, end, 3)
    if 'CAPSULE INTEGRITY' in history and model.phase not in {Phase.PREOP}:
        # Posterior capsule opening: dark gap with vitreous strands.
        veil = pg.Surface((220,220),pg.SRCALPHA)
        pg.draw.ellipse(veil,(20,24,30,150),(70,90,90,60))
        for k in range(5):
            pg.draw.arc(veil,(205,215,220,120),(60+k*8,70+k*6,100,80),.4,2.6,2)
        surf.blit(veil,(EYE_CX-110,EYE_CY-110))
    if 'IRIS PROLAPSE' in history and (live == 'IRIS PROLAPSE' or 'iris_trauma' in model.flags):
        tip = to_screen((.80, .46))
        pg.draw.ellipse(surf,(92,70,58),(tip[0]-8,tip[1]-16,30,30))
        pg.draw.ellipse(surf,(120,92,70),(tip[0]-2,tip[1]-10,18,18))
    if live == 'WOUND LEAK':
        for k in range(4):
            drop = to_screen((.74+k*.025, .47+k*.02))
            pg.draw.circle(surf,(170,220,240),drop,4)
    if live == 'ZONULAR WEAKNESS':
        pg.draw.circle(surf,AMBER,(center[0]+6,center[1]),106,2)
    if model.phase == Phase.ENTRY:
        for i,pt in enumerate(model._entry_target):
            pos = to_screen(pt)
            color = MINT if i in model._entered else AMBER
            pg.draw.circle(surf,color,pos,11,3)
            pg.draw.circle(surf,(240,237,211),pos,3)
    if model.phase == Phase.CAPSULE:
        for n in range(24):
            a = (n+.5)*math.tau/24  # centre of the engine's scoring segment n
            p = to_screen((.5+math.cos(a)*.28,.5+math.sin(a)*.28))
            pg.draw.circle(surf, MINT if n in model.eye.capsule_points else AMBER,p,5)


def draw_text(pg, surf, fonts, text, xy, *, color=TEXT, size='base', max_chars=None):
    if max_chars is not None:
        text = str(text)[:max_chars]
    out=fonts[size].render(str(text), True, color)
    surf.blit(out, xy)


def rounded(pg,surf,color,rect,r=10,border=0):
    pg.draw.rect(surf,color,rect,border_radius=r,width=border)


def bar(pg,surf,x,y,w,value,color):
    rounded(pg,surf,(35,65,77),(x,y,w,8),4)
    rounded(pg,surf,color,(x,y,max(0,int(w*min(1,max(0,value)))),8),4)


def waveform(pg, surf, origin, tick, color, heart_rate, kind='ecg', count=238):
    """Visualize synthetic patient-dependent signals, not clinical telemetry."""
    x, y = origin
    values = sample_trace(kind, heart_rate, tick, count=count)
    points = [(x+i, y-round(v*(21 if kind=='ecg' else 12)))
              for i,v in enumerate(values)]
    pg.draw.lines(surf, color, False, points, 2)


class App:
    def __init__(self, pg, case='normal', seed=7, scale=1.0):
        self.pg = pg
        self.game=Game(case,seed)
        self.screen=pg.display.set_mode((round(WIDTH*scale),round(HEIGHT*scale)),pg.RESIZABLE)
        pg.display.set_caption('OphthoSim-AI | Cataract Microsurgery (Educational Prototype)')
        self.canvas=pg.Surface((WIDTH,HEIGHT))
        self.clock=pg.time.Clock()
        self.fonts={
            'tiny': pg.font.SysFont('segoeui',14),
            'base': pg.font.SysFont('segoeui',17),
            'medium': pg.font.SysFont('segoeui',22,bold=True),
            'title': pg.font.SysFont('segoeui',30,bold=True),
            'big': pg.font.SysFont('consolas',35,bold=True),
        }
        self.running=True
        self.cursor=(0,0)
        self._acc=0.0
        self.message='You are the surgeon. Mock procedure - not for clinical use.'
        self._narrated=(id(self.game),1)
        self._option_rects=[]
        self._drag_phase=None
        self.drag=False
        self.quality='2.5D'
        self.view_3d=False
        self.view_yaw=.2
        self.view_pitch=.13

    def mapped(self, raw):
        w,h=self.screen.get_size()
        if not w or not h:
            return (0,0)
        return (raw[0]*WIDTH/w,raw[1]*HEIGHT/h)

    def dispatch(self,event):
        pg=self.pg
        if event.type==pg.QUIT:
            self.running=False
        elif event.type==pg.VIDEORESIZE:
            self.screen=pg.display.set_mode((max(640,event.w),max(360,event.h)),pg.RESIZABLE)
        elif event.type==pg.KEYDOWN:
            if event.key in (pg.K_1,pg.K_2,pg.K_3) and self.game.awaiting_decision:
                # Decision after assessing a complication: 1 continue, 2 manage, 3 stop.
                self.game.action('decide',DECISIONS[event.key-pg.K_1])
            elif event.key==pg.K_ESCAPE:
                self.game.action('pause')
            elif event.key==pg.K_x:
                self.game.action('abort')
            elif event.key==pg.K_a:
                self.game.action('assess')
            elif event.key==pg.K_r:
                self.game=Game(self.game.case,self.game.seed)
                self.message='New synthetic case started.'
            elif event.key==pg.K_g:
                self.view_3d=not self.view_3d
                self.drag=False
                self.message=('3D mesh preview: J/L orbit horizontally, I/K tilt, G to return.'
                              if self.view_3d else 'Returned to the 2.5D interactive surgical view.')
            elif self.view_3d and event.key in (pg.K_j,pg.K_l,pg.K_i,pg.K_k):
                if event.key in (pg.K_j,pg.K_l):
                    self.view_yaw=max(-1.2,min(1.2,self.view_yaw+(-.10 if event.key==pg.K_j else .10)))
                else:
                    self.view_pitch=max(-.9,min(.9,self.view_pitch+(.10 if event.key==pg.K_i else -.10)))
            elif event.key==pg.K_e and self.game.ending:
                self.save()
            elif event.key==pg.K_SPACE:
                self.start_next()
            elif event.key==pg.K_v:
                self.game.action('ovd')
            elif event.key==pg.K_d:
                self.game.action('hydro')
            elif pg.K_1<=event.key<=pg.K_9 and self.game.phase==Phase.PREOP:
                idx=event.key-pg.K_1
                if idx<len(CASE_KEYS):
                    self.game=Game(CASE_KEYS[idx],self.game.seed)
            elif event.key in (pg.K_1,pg.K_2,pg.K_3) and self.game.phase==Phase.CLOSE:
                self.game.action('verify',CHECK_KEYS[event.key-pg.K_1])
        elif event.type == pg.MOUSEBUTTONDOWN:
            self.cursor=self.mapped(event.pos)
            if event.button==1:
                self.drag=True
                self._drag_phase=self.game.phase
                if self.game.phase not in HELD_PHASES:
                    self.pointer_action()
        elif event.type == pg.MOUSEBUTTONUP and event.button==1:
            self.drag=False
        elif event.type==pg.MOUSEMOTION:
            # Held tasks sample the latest cursor once per simulation tick.
            self.cursor=self.mapped(event.pos)
        self.narrate()

    def narrate(self):
        """Show the newest event as a short status message (display only)."""
        key,seen=self._narrated
        if key!=id(self.game):
            seen=1
        for event in self.game.events[seen:]:
            text=narrate(event)
            if text:
                self.message=text
        self._narrated=(id(self.game),len(self.game.events))

    def start_next(self):
        if self.game.phase==Phase.PREOP:
            self.game.action('confirm')
        elif self.game.phase==Phase.ANESTHESIA:
            self.game.action('prepare')

    def pointer_action(self):
        # This view is an explanatory 3D visualization, not a surgical picking
        # mode; never mis-map CPU-projected triangles into 2D task coordinates.
        if self.view_3d:
            return
        x,y=self.cursor
        game=self.game
        if game.patient.alert:
            if game.awaiting_decision:
                for choice,(rx,ry,rw,rh) in zip(DECISIONS,self._option_rects):
                    if rx<=x<=rx+rw and ry<=y<=ry+rh:
                        game.action('decide',choice)
            elif x>=955 and y>=550:
                game.action('assess')
            return
        if game.phase in {Phase.PREOP,Phase.ANESTHESIA} and x<252 and y>554:
            self.start_next()
            return
        if game.phase==Phase.CLOSE and x<250:
            for i,key in enumerate(('alignment','wound','handoff')):
                if 343+i*62<y<393+i*62:
                    game.action('verify',key)
            return
        if game.ending:
            if x>975 and y>595:
                self.save()
            return
        if 280<=x<=962 and 88<=y<=638:
            a,b=to_eye((x,y))
            if game.phase==Phase.ENTRY:
                game.action('touch',a,b)
            elif game.phase==Phase.CAPSULE:
                game.action('trace',a,b)
            elif game.phase in {Phase.PHACO,Phase.CORTEX}:
                game.action('remove',a,b)
            elif game.phase==Phase.IOL:
                game.action('place',a,b)

    def tick_once(self):
        """Advance one fixed simulation step, applying a held instrument first."""
        g=self.game
        # Instruments change between steps: a held gesture never carries over
        # into the next phase (e.g. finishing the rhexis must not start phaco).
        if g.patient.alert or g.ending or g.paused or g.phase!=self._drag_phase:
            self.drag=False
        if self.drag and g.phase in HELD_PHASES:
            self.pointer_action()
        self.game.tick(TICK)
        self.narrate()

    def save(self):
        # Deliberately no personal patient identifiers; synthetic logs only.
        root=Path('session_logs')
        try:
            # Build both exports first so a refused replay never leaves a
            # lone trace file behind. Legacy Game objects in tests may
            # intentionally lack the replay API.
            trace=self.game.export_jsonl()
            replay=(self.game.export_replay_jsonl()
                    if hasattr(self.game, 'export_replay_jsonl') else None)
            root.mkdir(parents=True,exist_ok=True)
            path,replay_path=session_paths(root,f'case_{self.game.case}_seed_{self.game.seed}')
            path.write_text(trace,encoding='utf-8')
            if replay is not None:
                replay_path.write_text(replay,encoding='utf-8')
                self.message=f'Exported {path.name} and {replay_path.name}'
            else:
                self.message=f'Exported synthetic trace: {path}'
        except (OSError, RuntimeError, ValueError) as exc:
            self.message=f'Export failed: {exc.__class__.__name__}'

    def draw_sidebar(self):
        pg=self.pg
        surf=self.canvas
        rounded(pg,surf,PANEL,(15,75,250,620),14)
        draw_text(pg,surf,self.fonts,'YOUR TASK, SURGEON', (29,96),color=CYAN)
        title,desc=PHASE_COPY[self.game.phase]
        # Long step names drop to the base size so they stay inside the panel.
        size='medium' if self.fonts['medium'].size(title)[0]<=225 else 'base'
        draw_text(pg,surf,self.fonts,title,(29,130 if size=='base' else 128),size=size,max_chars=24)
        def wrapped(text,width=27):
            words=text.split();lines=[];cur=''
            for word in words:
                if len(cur)+len(word)+1>width:
                    lines.append(cur);cur=word
                else:cur=(cur+' '+word).strip()
            if cur:lines.append(cur)
            return lines
        for i,line in enumerate(wrapped(desc)):
            draw_text(pg,surf,self.fonts,line,(29,164+i*23),color=MUTED)
        pg.draw.line(surf,(48,76,91),(29,250),(248,250),1)
        g=self.game
        if g.phase==Phase.PREOP:
            draw_text(pg,surf,self.fonts,'SELECT CASE  [1-9]',(29,262),color=CYAN)
            for i,key in enumerate(CASE_KEYS):
                draw_text(pg,surf,self.fonts,f'{i+1} {CASES[key].title}',(32,290+i*28),
                          color=MINT if g.case==key else TEXT,max_chars=26)
        elif g.phase==Phase.CLOSE:
            draw_text(pg,surf,self.fonts,'CLOSURE CHECKS', (29,282),color=CYAN)
            for i,(label,done,hint) in enumerate(g.checklist()):
                yy=343+i*62
                rounded(pg,surf,PANEL2,(27,yy,225,50))
                draw_text(pg,surf,self.fonts,('✓  ' if done else '□  ')+label,(37,yy+14),color=MINT if done else TEXT)
        else:
            draw_text(pg,surf,self.fonts,'PROCEDURE STEPS',(29,262),color=CYAN)
            for i,(label,done,hint) in enumerate(g.checklist()[:4]):
                marker=step_marker(done,hint)
                draw_text(pg,surf,self.fonts,f'{marker} {label}',(32,290+i*26),
                          color=MINT if done else AMBER if marker!='[ ]' else TEXT,max_chars=26)
            for i,(label,val,color) in enumerate((('Lens opacity',g.eye.opacity,AMBER),('Cortex remaining',g.eye.cortex,CYAN),('Capsule integrity',g.eye.capsule_integrity,MINT),('IOL alignment',g.eye.iol_alignment,CYAN))):
                yy=400+i*40
                draw_text(pg,surf,self.fonts,label,(29,yy),color=MUTED,size='tiny')
                bar(pg,surf,30,yy+20,215,val,color)
            if g.phase in (Phase.PHACO,Phase.CORTEX):
                stress=g.tissue_stress
                warn=g.stress_warning
                draw_text(pg,surf,self.fonts,'Tissue stress',(29,560),color=RED if warn else MUTED,size='tiny')
                bar(pg,surf,30,580,215,stress,RED if warn else AMBER)
        if g.phase in (Phase.PREOP,Phase.ANESTHESIA):
            rounded(pg,surf,(24,104,111),(28,573,223,59),10)
            draw_text(pg,surf,self.fonts,'SPACE / CLICK TO CONFIRM',(39,590),size='base')
        if not g.ending:
            draw_text(pg,surf,self.fonts,'ESC Pause   X Stop safely',(27,653),size='tiny',color=MUTED)

    def draw_monitor(self):
        pg=self.pg;s=self.canvas;g=self.game;p=g.patient
        rounded(pg,s,PANEL,(976,75,290,620),14)
        draw_text(pg,s,self.fonts,'PATIENT MONITOR',(990,95),color=CYAN)
        draw_text(pg,s,self.fonts,'SYNTHETIC / NON-CLINICAL',(990,125),color=MUTED,size='tiny')
        rounded(pg,s,PANEL2,(990,165,260,145))
        draw_text(pg,s,self.fonts,'ECG / HR', (1004,179),color=MINT)
        draw_text(pg,s,self.fonts,str(p.heart_rate), (1005,208),size='big',color=MINT)
        waveform(pg,s,(997,281),g.time,MINT,p.heart_rate)
        rounded(pg,s,PANEL2,(990,324,260,91))
        draw_text(pg,s,self.fonts,'NIBP', (1005,339),color=AMBER)
        draw_text(pg,s,self.fonts,f'{p.sbp} / {p.dbp}',(1005,362),size='big',color=AMBER)
        rounded(pg,s,PANEL2,(990,426,260,90))
        draw_text(pg,s,self.fonts,'SpO2', (1005,439),color=CYAN)
        draw_text(pg,s,self.fonts,f'{p.spo2}%',(1005,461),size='big',color=CYAN)
        waveform(pg,s,(1094,500),g.time,CYAN,p.heart_rate,'pleth',145)
        col=RED if p.alert else MINT
        rounded(pg,s,(61,32,47) if p.alert else (25,67,60),(990,531,260,97))
        draw_text(pg,s,self.fonts,'STATUS', (1004,539),color=col)
        draw_text(pg,s,self.fonts,p.alert or 'STABLE', (1004,566),color=col,size='medium',max_chars=20)
        if p.alert:
            draw_text(pg,s,self.fonts,('1-3 / CLICK  Decide   X Stop safely' if g.awaiting_decision
                                       else 'A / CLICK  Assess   X Stop safely'),(999,603),size='tiny',color=TEXT)
        else:
            draw_text(pg,s,self.fonts,'Cooperation: stable',(1004,604),color=MUTED,size='tiny')
        draw_text(pg,s,self.fonts,'No real patient measurements', (990,660),color=MUTED,size='tiny')

    def draw(self):
        pg=self.pg;s=self.canvas;g=self.game
        s.fill(BG)
        draw_text(pg,s,self.fonts,'OPHTHOSIM', (24,21),size='title',color=CYAN)
        draw_text(pg,s,self.fonts,'AI  /  MOCK CATARACT SURGERY  -  YOU ARE THE SURGEON', (237,31),color=MUTED)
        draw_text(pg,s,self.fonts,('3D MESH PREVIEW (CPU)' if self.view_3d
                                   else '2.5D EDUCATIONAL BUILD'),(1002,29),color=MINT,size='tiny')
        rounded(pg,s,(13,31,45),(275,75,690,620),16)
        pg.draw.circle(s,(30,65,71),(EYE_CX,EYE_CY),243)
        if self.view_3d:
            draw_preview(pg,s,g.phase.value,g.eye.opacity,g.eye.iol_alignment,
                         self.view_yaw,self.view_pitch)
        else:
            render_eye(pg,s,g,g.time)
        # Microscope masks / aperture.
        pg.draw.circle(s,(58,103,115),(EYE_CX,EYE_CY),239,2)
        draw_text(pg,s,self.fonts,('ROTATABLE 3D MESH PREVIEW - NON-INTERACTIVE' if self.view_3d
                                   else 'MICROSCOPE  •  SYNTHETIC MODEL'),(289,90),size='tiny',color=CYAN)
        if self.view_3d:
            draw_text(pg,s,self.fonts,'J/L Orbit  I/K Tilt  G Return to surgery',
                      (372,609),size='base',color=CYAN)
        if not self.view_3d and g.phase in (Phase.PHACO,Phase.CORTEX):
            pt=(round(self.cursor[0]),round(self.cursor[1]))
            if self.drag:
                pg.draw.line(s,(156,206,217),(973,650),pt,5)
                pg.draw.circle(s,(219,245,241),pt,8,2)
        if not self.view_3d and g.phase==Phase.IOL:
            pg.draw.circle(s,CYAN,(EYE_CX,EYE_CY),26,1)
            pg.draw.line(s,CYAN,(EYE_CX-38,EYE_CY),(EYE_CX+38,EYE_CY),1)
        self.draw_sidebar();self.draw_monitor()
        # Footer and alerts.
        draw_text(pg,s,self.fonts,f'CASE: {g.case.upper()}   |   PHASE: {g.phase.value}   |   SCORE: {g.score()}   |   SEED: {g.seed}',(291,654),size='tiny',color=MUTED)
        self._option_rects=[]
        if g.phase==Phase.PREOP and not g.patient.alert and not self.view_3d:
            self.draw_case_brief()
        if g.patient.alert and not g.ending:
            self.draw_complication_card()
        elif g.paused:
            rounded(pg,s,(35,55,75),(395,550,480,56))
            draw_text(pg,s,self.fonts,'PAUSED — ESC to continue',(424,564),size='medium')
        elif g.stress_warning and g.phase in (Phase.PHACO,Phase.CORTEX):
            rounded(pg,s,(78,52,36),(372,556,530,52),10)
            draw_text(pg,s,self.fonts,'TISSUE STRESS — bring the tip back to the centre',
                      (390,571),color=AMBER)
        if g.ending:
            box=(338,120,602,430)
            rounded(pg,s,(14,43,57),box,19)
            pg.draw.rect(s,CYAN,box,2,border_radius=19)
            outcome=g.outcome()
            headline,explain=g.outcome_title()
            draw_text(pg,s,self.fonts,'SURGEON DEBRIEF',(372,138),color=CYAN)
            draw_text(pg,s,self.fonts,headline,(370,162),size='title',color=OUTCOME_COLORS[outcome])
            draw_text(pg,s,self.fonts,explain,(372,204),color=TEXT)
            score=('Not scored - safe stop' if outcome=='SAFE_ABORT' else
                   'SCORE 0 / 100 (safety veto)' if outcome=='CRITICAL_FAILURE' else
                   f'SIMULATED SCORE   {g.score()} / 100')
            draw_text(pg,s,self.fonts,score,(372,234),size='medium')
            rows=[]
            for label,verdict in g.debrief():
                if label=='Result':
                    continue
                for j,part in enumerate(wrap(verdict,38) or ['']):
                    rows.append((label if j==0 else '',part))
            for i,(label,verdict) in enumerate(rows[:8]):
                yy=276+i*26
                draw_text(pg,s,self.fonts,label,(372,yy),color=MUTED,max_chars=26)
                draw_text(pg,s,self.fonts,verdict,(584,yy),max_chars=40)
            draw_text(pg,s,self.fonts,'E: Export session    R: New case',(372,496),color=MUTED)
            draw_text(pg,s,self.fonts,'Synthetic game score. No patient outcome or clinical skill is implied.',
                      (372,524),size='tiny',color=MUTED)
        draw_text(pg,s,self.fonts,self.message,(24,699),size='tiny',color=MUTED,max_chars=105)
        out=pg.transform.smoothscale(s,self.screen.get_size())
        self.screen.blit(out,(0,0))
        pg.display.flip()

    def draw_case_brief(self):
        pg=self.pg;s=self.canvas;g=self.game
        brief=CASES[g.case]
        box=(338,170,602,236)
        rounded(pg,s,(14,43,57),box,16)
        pg.draw.rect(s,CYAN,box,2,border_radius=16)
        draw_text(pg,s,self.fonts,'CASE BRIEF  -  YOU ARE THE OPERATING SURGEON',(362,186),color=CYAN)
        draw_text(pg,s,self.fonts,brief.title,(362,214),size='medium')
        draw_text(pg,s,self.fonts,brief.patient,(362,250),color=TEXT)
        for i,line in enumerate(wrap('Risk factors: '+brief.risks,60)[:2]):
            draw_text(pg,s,self.fonts,line,(362,280+i*24),color=AMBER)
        draw_text(pg,s,self.fonts,'SPACE: time-out, then begin.   1-9: choose another case',(362,344),color=MINT)
        draw_text(pg,s,self.fonts,'Synthetic case. Not a real patient.',(362,374),size='tiny',color=MUTED)

    def draw_complication_card(self):
        pg=self.pg;s=self.canvas;g=self.game
        comp=g.complication
        title=comp.title if comp else g.patient.alert
        box=(330,150,618,330)
        rounded(pg,s,(64,30,42),box,16)
        pg.draw.rect(s,RED,box,2,border_radius=16)
        draw_text(pg,s,self.fonts,'SAFETY HOLD  -  INSTRUMENTS STOPPED',(354,166),color=RED)
        draw_text(pg,s,self.fonts,title,(354,192),size='title',color=TEXT)
        if comp:
            draw_text(pg,s,self.fonts,f'During: {comp.stage}',(354,236),size='tiny',color=MUTED)
            for i,line in enumerate(wrap('What you see: '+comp.signs,62)[:3]):
                draw_text(pg,s,self.fonts,line,(354,260+i*23),color=AMBER)
        if g.awaiting_decision and comp:
            options=(('1','Continue as before'),('2',comp.manage),('3',comp.refer_result))
            for i,(key,label) in enumerate(options):
                rect=(350,336+i*40,578,34)
                self._option_rects.append(rect)
                rounded(pg,s,PANEL2,rect,8)
                draw_text(pg,s,self.fonts,f'{key}   {label}',(364,343+i*40),max_chars=60)
        else:
            draw_text(pg,s,self.fonts,'A   Assess the situation',(364,350),color=MINT)
            draw_text(pg,s,self.fonts,'X   Stop the procedure safely',(364,382),color=MUTED)
            if comp and not comp.decision:
                draw_text(pg,s,self.fonts,'The team settles the patient once you assess.',(364,420),size='tiny',color=MUTED)

    def run(self):
        pg=self.pg
        while self.running:
            dt=min(self.clock.tick(60)/1000,.1)
            for event in pg.event.get():
                self.dispatch(event)
            self._acc+=dt
            loops=0
            while self._acc>=TICK and loops<6:
                self.tick_once()
                self._acc-=TICK
                loops+=1
            if loops>=6:
                self._acc=0
            self.draw()


def main(argv=None):
    parser=argparse.ArgumentParser(description='Educational 2.5D cataract surgery game')
    parser.add_argument('--case', choices=list(CASE_KEYS),default='normal')
    parser.add_argument('--seed',type=int,default=7)
    parser.add_argument('--scale',type=float,default=1.0)
    ns=parser.parse_args(argv)
    if not math.isfinite(ns.scale) or not .5<=ns.scale<=3:
        parser.error('--scale must be between 0.5 and 3')
    try:
        import pygame
    except ImportError:
        print('Pygame is missing. Install with: python -m pip install -r requirements.txt',file=sys.stderr)
        raise SystemExit(2)
    pygame.init()
    try:
        App(pygame,ns.case,ns.seed,ns.scale).run()
    finally:
        pygame.quit()