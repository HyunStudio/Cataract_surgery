"""Pygame presentation for OphthoSim-AI.

Visuals are stylized, procedural 2.5D illustrations, NOT clinical graphics.
Requires pygame, and is intentionally independent of the headless simulation.
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path
import sys

from .engine import Phase
from .replay import ReplayGame as Game

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

PHASE_COPY = {
    Phase.PREOP: ('PREOPERATIVE REVIEW', 'Confirm the simulated case before proceeding.'),
    Phase.ANESTHESIA: ('ANESTHESIA & PREPARATION', 'Confirm anesthesia-team readiness; no real medication actions.'),
    Phase.ENTRY: ('SURGICAL ENTRY', 'Select the three glowing abstract approach targets.'),
    Phase.CAPSULE: ('CAPSULAR PRECISION', 'Hold left mouse button and trace the dotted circular guide.'),
    Phase.PHACO: ('LENS FRAGMENTATION', 'Hold left mouse on the cloudy lens to reduce opacity.'),
    Phase.CORTEX: ('RESIDUAL LENS CLEANUP', 'Hold left mouse on the inner lens to clear residual material.'),
    Phase.IOL: ('INTRAOCULAR LENS', 'Click near the optical center to align the synthetic IOL.'),
    Phase.CLOSE: ('FINAL SAFETY CHECKS', 'Review alignment, wound and handoff on the left panel.'),
    Phase.RECOVERY: ('RECOVERY & RESULTS', 'Simulation completed. Press E to export a synthetic JSONL log.'),
    Phase.ABORTED: ('SAFE ABORT', 'The simulation ended safely. Press R for a new case.'),
}


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
    pg.draw.circle(surf, (10, 17, 27), center, 104)
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
    if model.phase == Phase.ENTRY:
        for i,pt in enumerate(model._entry_target):
            pos = to_screen(pt)
            color = MINT if i < model.eye.entry_hits else AMBER
            pg.draw.circle(surf,color,pos,11,3)
            pg.draw.circle(surf,(240,237,211),pos,3)
    if model.phase == Phase.CAPSULE:
        for n in range(24):
            a = n*math.tau/24
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


def waveform(pg,surf,origin,tick,color):
    x,y=origin
    points=[]
    for i in range(280):
        phase=((i+tick*110)*.019)%1
        def spike(q,c,width):
            return max(0,1-abs(q-c)/width)
        v=spike(phase,.23,.025)*1.8-spike(phase,.20,.02)*.3-spike(phase,.27,.03)*.55+spike(phase,.62,.09)*.13
        points.append((x+i,y-int(v*20)))
    pg.draw.lines(surf,color,False,points,2)


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
        self.message='Educational synthetic simulation — not for clinical use.'
        self.drag=False
        self.quality='2.5D'

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
            if event.key==pg.K_ESCAPE:
                self.game.action('pause')
            elif event.key==pg.K_x:
                self.game.action('abort')
            elif event.key==pg.K_a:
                self.game.action('assess')
            elif event.key==pg.K_r:
                self.game=Game(self.game.case,self.game.seed)
                self.message='New synthetic case started.'
            elif event.key==pg.K_e and self.game.ending:
                self.save()
            elif event.key==pg.K_SPACE:
                self.start_next()
            elif event.key in (pg.K_1,pg.K_2,pg.K_3,pg.K_4) and self.game.phase==Phase.PREOP:
                idx=event.key-pg.K_1
                self.game=Game(('normal','motion','vitals','capsule')[idx],self.game.seed)
        elif event.type == pg.MOUSEBUTTONDOWN:
            self.cursor=self.mapped(event.pos)
            if event.button==1:
                self.drag=True
                self.pointer_action()
        elif event.type == pg.MOUSEBUTTONUP and event.button==1:
            self.drag=False
        elif event.type==pg.MOUSEMOTION:
            self.cursor=self.mapped(event.pos)
            if self.drag and self.game.phase==Phase.CAPSULE:
                self.pointer_action()

    def start_next(self):
        if self.game.phase==Phase.PREOP:
            self.game.action('confirm')
        elif self.game.phase==Phase.ANESTHESIA:
            self.game.action('prepare')

    def pointer_action(self):
        x,y=self.cursor
        game=self.game
        if game.patient.alert:
            if x>=955 and y>=550:
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

    def save(self):
        # Deliberately no personal patient identifiers; synthetic logs only.
        root=Path('session_logs')
        root.mkdir(parents=True,exist_ok=True)
        path=root/f'case_{self.game.case}_seed_{self.game.seed}.jsonl'
        try:
            path.write_text(self.game.export_jsonl(),encoding='utf-8')
            # Saved separately: one trace for analysis and one verifiable
            # accepted-command replay. Legacy Game objects in tests may
            # intentionally lack the replay API.
            if hasattr(self.game, 'export_replay_jsonl'):
                replay_path=root/f'case_{self.game.case}_seed_{self.game.seed}.replay.jsonl'
                replay_path.write_text(self.game.export_replay_jsonl(),encoding='utf-8')
                self.message=f'Exported trace and replay to {root}'
            else:
                self.message=f'Exported synthetic trace: {path}'
        except (OSError, RuntimeError, ValueError) as exc:
            self.message=f'Export failed: {exc.__class__.__name__}'

    def draw_sidebar(self):
        pg=self.pg
        surf=self.canvas
        rounded(pg,surf,PANEL,(15,75,250,620),14)
        draw_text(pg,surf,self.fonts,'SURGICAL TASK', (29,96),color=CYAN)
        title,desc=PHASE_COPY[self.game.phase]
        draw_text(pg,surf,self.fonts,title,(29,128),size='medium',max_chars=22)
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
            draw_text(pg,surf,self.fonts,'SELECT CASE  [1–4]',(29,279),color=CYAN)
            for i,name in enumerate(('1 Normal','2 Patient motion','3 Vital alert','4 Capsule alert')):
                draw_text(pg,surf,self.fonts,name,(32,313+i*35),color=MINT if g.case==('normal','motion','vitals','capsule')[i] else TEXT)
        elif g.phase==Phase.CLOSE:
            draw_text(pg,surf,self.fonts,'FINAL CHECKS', (29,282),color=CYAN)
            for i,(key,label) in enumerate((('alignment','IOL alignment'),('wound','Wound stability'),('handoff','Patient handoff'))):
                yy=343+i*62
                rounded(pg,surf,PANEL2,(27,yy,225,50))
                draw_text(pg,surf,self.fonts,('✓  ' if key in g.eye.final_checks else '□  ')+label,(37,yy+14),color=MINT if key in g.eye.final_checks else TEXT)
        else:
            for i,(label,val,color) in enumerate((('Lens opacity',g.eye.opacity,AMBER),('Cortex remaining',g.eye.cortex,CYAN),('Capsule integrity',g.eye.capsule_integrity,MINT),('IOL alignment',g.eye.iol_alignment,CYAN))):
                yy=281+i*66
                draw_text(pg,surf,self.fonts,label,(29,yy),color=MUTED)
                bar(pg,surf,30,yy+25,215,val,color)
        if g.phase in (Phase.PREOP,Phase.ANESTHESIA):
            rounded(pg,surf,(24,104,111),(28,573,223,59),10)
            draw_text(pg,surf,self.fonts,'SPACE / CLICK TO NEXT',(39,590),size='base')
        draw_text(pg,surf,self.fonts,'ESC Pause   X Safe abort',(27,653),size='tiny',color=MUTED)

    def draw_monitor(self):
        pg=self.pg;s=self.canvas;g=self.game;p=g.patient
        rounded(pg,s,PANEL,(976,75,290,620),14)
        draw_text(pg,s,self.fonts,'PATIENT MONITOR',(990,95),color=CYAN)
        draw_text(pg,s,self.fonts,'SYNTHETIC / NON-CLINICAL',(990,125),color=MUTED,size='tiny')
        rounded(pg,s,PANEL2,(990,165,260,145))
        draw_text(pg,s,self.fonts,'ECG / HR', (1004,179),color=MINT)
        draw_text(pg,s,self.fonts,str(p.heart_rate), (1005,208),size='big',color=MINT)
        waveform(pg,s,(997,281),g.time,MINT)
        rounded(pg,s,PANEL2,(990,324,260,91))
        draw_text(pg,s,self.fonts,'NIBP', (1005,339),color=AMBER)
        draw_text(pg,s,self.fonts,f'{p.sbp} / {p.dbp}',(1005,362),size='big',color=AMBER)
        rounded(pg,s,PANEL2,(990,426,260,90))
        draw_text(pg,s,self.fonts,'SpO2', (1005,439),color=CYAN)
        draw_text(pg,s,self.fonts,f'{p.spo2}%',(1005,461),size='big',color=CYAN)
        col=RED if p.alert else MINT
        rounded(pg,s,(61,32,47) if p.alert else (25,67,60),(990,531,260,97))
        draw_text(pg,s,self.fonts,'STATUS', (1004,539),color=col)
        draw_text(pg,s,self.fonts,p.alert or 'STABLE', (1004,566),color=col,size='medium',max_chars=23)
        if p.alert:
            draw_text(pg,s,self.fonts,'A / CLICK  Assess or X Abort',(999,603),size='tiny',color=TEXT)
        else:
            draw_text(pg,s,self.fonts,'Cooperation: stable',(1004,604),color=MUTED,size='tiny')
        draw_text(pg,s,self.fonts,'No real patient measurements', (990,660),color=MUTED,size='tiny')

    def draw(self):
        pg=self.pg;s=self.canvas;g=self.game
        s.fill(BG)
        draw_text(pg,s,self.fonts,'OPHTHOSIM', (24,21),size='title',color=CYAN)
        draw_text(pg,s,self.fonts,'AI  /  CATARACT MICROSURGERY', (237,31),color=MUTED)
        draw_text(pg,s,self.fonts,'2.5D EDUCATIONAL BUILD',(1002,29),color=MINT,size='tiny')
        rounded(pg,s,(13,31,45),(275,75,690,620),16)
        pg.draw.circle(s,(30,65,71),(EYE_CX,EYE_CY),243)
        render_eye(pg,s,g,g.time)
        # Microscope masks / aperture.
        pg.draw.circle(s,(58,103,115),(EYE_CX,EYE_CY),239,2)
        draw_text(pg,s,self.fonts,'MICROSCOPE  •  SYNTHETIC MODEL',(289,90),size='tiny',color=CYAN)
        if g.phase in (Phase.PHACO,Phase.CORTEX):
            pt=(round(self.cursor[0]),round(self.cursor[1]))
            if self.drag:
                pg.draw.line(s,(156,206,217),(973,650),pt,5)
                pg.draw.circle(s,(219,245,241),pt,8,2)
        if g.phase==Phase.IOL:
            pg.draw.circle(s,CYAN,(EYE_CX,EYE_CY),26,1)
            pg.draw.line(s,CYAN,(EYE_CX-38,EYE_CY),(EYE_CX+38,EYE_CY),1)
        self.draw_sidebar();self.draw_monitor()
        # Footer and alerts.
        draw_text(pg,s,self.fonts,f'CASE: {g.case.upper()}   |   PHASE: {g.phase.value}   |   SCORE: {g.score()}   |   SEED: {g.seed}',(291,654),size='tiny',color=MUTED)
        if g.patient.alert:
            rounded(pg,s,(87,41,52),(362,548,550,67),10)
            draw_text(pg,s,self.fonts,'SAFETY HOLD — REVIEW PATIENT STATE', (382,565),color=RED,size='medium')
            draw_text(pg,s,self.fonts,'Press A to assess  ·  X to safely abort', (386,595),size='base')
        elif g.paused:
            rounded(pg,s,(35,55,75),(395,550,480,56))
            draw_text(pg,s,self.fonts,'PAUSED — ESC to continue',(424,564),size='medium')
        if g.ending:
            rounded(pg,s,(14,43,57),(338,222,602,274),19)
            pg.draw.rect(s,CYAN,(338,222,602,274),2,border_radius=19)
            draw_text(pg,s,self.fonts,g.ending,(388,267),size='title',color=MINT if g.phase==Phase.RECOVERY else AMBER)
            draw_text(pg,s,self.fonts,f'SIMULATED SCORE   {g.score()} / 100',(393,329),size='medium')
            draw_text(pg,s,self.fonts,'E: Export log    R: Retry    X: Safe abort',(392,387),color=MUTED)
            draw_text(pg,s,self.fonts,'No patient outcome or clinical skill is implied.',(390,432),size='base')
        draw_text(pg,s,self.fonts,self.message,(24,704),size='tiny',color=MUTED,max_chars=105)
        out=pg.transform.smoothscale(s,self.screen.get_size())
        self.screen.blit(out,(0,0))
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
                self.game.tick(1/60)
                self._acc-=1/60
                loops+=1
            if loops>=6:
                self._acc=0
            if self.drag and self.game.phase in {Phase.PHACO,Phase.CORTEX}:
                self.pointer_action()
            self.draw()


def main(argv=None):
    parser=argparse.ArgumentParser(description='Educational 2.5D cataract surgery game')
    parser.add_argument('--case', choices=['normal','motion','vitals','capsule'],default='normal')
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