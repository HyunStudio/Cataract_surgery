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
import sys

from .autosave import AUTOSAVE, load_autosave, write_autosave
from .engine import (CASES, DIFFICULTIES, ENDING_COMPLETE, ENDING_FAILED,
                     ENDING_MANAGED, FINAL_CHECKS, PREOP_CHECKS, TOOL_NAMES, Phase)
from .i18n import LANGUAGES, t
from .preview3d import draw_preview
from .replay import ReplayGame as Game
from .report import explain, save_session, timeline
from .signals import sample_trace

WIDTH, HEIGHT = 1280, 720
EYE_CX, EYE_CY, EYE_R = 640, 366, 222
FIELD = (275, 75, 690, 620)
TRAY = (292, 612, 656, 32)     # instrument tray inside the field, under the eye
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


def render_eye(pg, surf, model, clock_s, palette=None, *, animate=True):
    """Procedural pseudo-depth: cornea highlights, iris, pupil and lens layers."""
    c = palette or PALETTES['default']
    center = (EYE_CX, EYE_CY)
    eye = model.eye
    pg.draw.circle(surf, (5, 10, 18), (center[0]+7, center[1]+10), EYE_R+15)
    # Sclera with diffuse illumination shading.
    for r in range(EYE_R, 135, -4):
        blend = (EYE_R-r)/(EYE_R-135)
        value = int(123+70*blend)
        pg.draw.circle(surf, (value, value+7, min(255, value+13)), center, r)
    pg.draw.circle(surf, (48, 79, 85), center, 153)
    # Radial iris fibers with depth cues.
    for r in range(151, 98, -3):
        tt = (151-r)/53
        pg.draw.circle(surf, (int(21+18*tt), int(73+37*tt), int(80+20*tt)), center, r)
    for i in range(180):
        a = i*math.tau/180
        inner = 104 + 4*math.sin(i*1.73)
        outer = 145 + 4*math.sin(i*.67)
        pg.draw.line(surf, (52 + (i%5)*5, 111+(i%4)*6, 114+(i%3)*4),
                     (round(EYE_CX+math.cos(a)*inner),round(EYE_CY+math.sin(a)*inner)),
                     (round(EYE_CX+math.cos(a)*outer),round(EYE_CY+math.sin(a)*outer)), 1)
    # A constricted pupil narrows the visible (and usable) lens field.
    pupil = max(.3, min(1.0, eye.pupil))
    pupil_r = round(104 * (.25 + .75 * pupil))
    if pupil < 1:
        pg.draw.circle(surf, (40, 92, 96), center, 104)
    pg.draw.circle(surf, (10, 17, 27), center, pupil_r)
    # Synthetic cataract opacity. Display rings shrink smoothly with progress.
    if eye.opacity > 0:
        alpha = int(eye.opacity*188)
        overlay = pg.Surface((420,420),pg.SRCALPHA)
        pg.draw.circle(overlay, (200,187,136,alpha), (210,210), round(99*pupil_r/104))
        spin = clock_s*.005 if animate else 0.
        for i in range(12):
            a = i*math.tau/12 + spin
            p = (round(210+70*pupil_r/104*math.cos(a)),round(210+70*pupil_r/104*math.sin(a)))
            pg.draw.circle(overlay,(227,219,166,int(alpha*.7)),p,14+i%4*3)
        surf.blit(overlay, (EYE_CX-210,EYE_CY-210))
    if model.phase in {Phase.IOL, Phase.CLOSE, Phase.RECOVERY} and (
            eye.iol_alignment > 0 or model.phase == Phase.IOL):
        # Decentration is shown as a visible offset of the synthetic optic.
        shift = round(70 * (1 - eye.iol_alignment)) if model.phase != Phase.IOL else 0
        overlay = pg.Surface((260,260),pg.SRCALPHA)
        pg.draw.circle(overlay,(150,231,239,72),(130,130),105)
        pg.draw.circle(overlay,(215,253,255,145),(130,130),102,2)
        pg.draw.ellipse(overlay,(180,240,246,170), (54,28,152,204),2)
        surf.blit(overlay,(EYE_CX-130+shift,EYE_CY-130))
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
            pg.draw.circle(surf, c['muted'], center, round(low*EYE_R*2), 1)
            pg.draw.circle(surf, c['muted'], center, round(high*EYE_R*2), 1)
    if model.phase in (Phase.PHACO, Phase.CORTEX) and rules.guides:
        pg.draw.circle(surf, c['muted'], center, round(model.work_radius*EYE_R*2), 1)


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


def wrapped(text, width=27):
    words=str(text).split();lines=[];cur=''
    for word in words:
        if cur and len(cur)+len(word)+1>width:
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
        self.fonts={
            'tiny': pg.font.SysFont(FONT_NAMES,14),
            'base': pg.font.SysFont(FONT_NAMES,17),
            'medium': pg.font.SysFont(FONT_NAMES,22,bold=True),
            'title': pg.font.SysFont(FONT_NAMES,30,bold=True),
            'big': pg.font.SysFont('consolas',35,bold=True),
        }
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
        self._saved_phase=self.game.phase
        self._wrong_seen=0

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

    def autosave(self):
        try:
            write_autosave(self.game,self.autosave_path)
        except OSError:
            pass
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
                self.cycle_tool()
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
                self.pointer_action()
        elif event.type == pg.MOUSEBUTTONUP and event.button==1:
            self.drag=False
        elif event.type==pg.MOUSEMOTION:
            self.cursor=self.mapped(event.pos)
            if self.drag and self.game.phase==Phase.CAPSULE:
                self.pointer_action()

    def cycle_tool(self):
        current=self.game.tool
        index=(TOOL_NAMES.index(current)+1)%len(TOOL_NAMES) if current in TOOL_NAMES else 0
        self.game.action('tool',TOOL_NAMES[index])

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
            game.action('tool',TOOL_NAMES[min(len(TOOL_NAMES)-1,int((x-tx)//(tw/len(TOOL_NAMES))))])
            return
        if 280<=x<=962 and 88<=y<=638:
            a,b=to_eye(self.unzoom((x,y)))
            if game.phase==Phase.ENTRY:
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
        for i,line in enumerate(wrapped(self.text('goal.'+g.phase.value))[:4]):
            draw_text(pg,surf,self.fonts,line,(29,126+i*23),color=c['muted'])
        pg.draw.line(surf,(48,76,91),(29,224),(248,224),1)
        draw_text(pg,surf,self.fonts,f"{self.text('ui.difficulty')}: {self.text('difficulty.'+g.difficulty)}",
                  (29,234),size='tiny',color=c['muted'])
        if g.phase==Phase.PREOP:
            draw_text(pg,surf,self.fonts,f"{self.text('ui.select_case')} [1-9] · D",(29,256),size='tiny',color=c['accent'])
            draw_text(pg,surf,self.fonts,self.text('case.'+g.case),(29,276),size='base',color=c['ok'],max_chars=26)
            self.checklist(PREOP_CHECKS,g.eye.preop_checks)
        elif g.phase==Phase.CLOSE:
            if g._decentered:
                for i,line in enumerate(wrapped(self.text('hint.IOL DECENTRATION'))):
                    draw_text(pg,surf,self.fonts,line,(29,282+i*22),color=c['warn'])
            self.checklist(FINAL_CHECKS,g.eye.final_checks,numbered=True)
        else:
            rows=((self.text('bar.opacity'),g.eye.opacity,c['warn']),
                  (self.text('bar.cortex'),g.eye.cortex,c['accent']),
                  (self.text('bar.capsule'),g.eye.capsule_integrity,c['ok']),
                  (self.text('bar.iol'),g.eye.iol_alignment,c['accent']))
            for i,(label,val,color) in enumerate(rows):
                yy=262+i*56
                draw_text(pg,surf,self.fonts,f'{label}  {round(val*100)}%',(29,yy),color=c['muted'],size='tiny')
                bar(pg,surf,30,yy+22,215,val,color)
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
        tx,ty,tw,th=TRAY
        width=tw/len(TOOL_NAMES)
        required=g.required_tool
        for i,name in enumerate(TOOL_NAMES):
            rect=(round(tx+i*width)+2,ty,round(width)-4,th)
            selected=name==g.tool
            rounded(pg,s,(30,74,84) if selected else c['panel2'],rect,7)
            if name==required:
                pg.draw.rect(s,c['ok'] if selected else c['warn'],rect,2,border_radius=7)
            label=('> ' if selected else '')+self.text('tool.'+name)
            draw_text(pg,s,self.fonts,label,(rect[0]+8,ty+7),size='tiny',
                      color=c['text'] if selected else c['muted'],max_chars=18)

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
               else c['bad'] if g.ending==ENDING_FAILED else c['warn'])
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
        for i,line in enumerate(wrapped(self.text('ui.help.body'),66)+wrapped(self.text('ui.options'),66)):
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
            self.message=t(self.lang,'ui.wrong_tool',tool=t(self.lang,'tool.'+(g.required_tool or 'blade')))
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
        if not self.view_3d and g.phase in (Phase.PHACO,Phase.CORTEX):
            pt=(round(self.cursor[0]),round(self.cursor[1]))
            if self.drag:
                pg.draw.line(s,(156,206,217),(973,650),pt,5)
                pg.draw.circle(s,(219,245,241),pt,8,2)
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
        elif g.paused:
            rounded(pg,s,(35,55,75),(395,550,480,56))
            draw_text(pg,s,self.fonts,self.text('ui.paused'),(424,564),size='medium')
        if g.ending:
            self.draw_results()
        if self.show_help:
            self.draw_help()
        draw_text(pg,s,self.fonts,self.message+'   ·   F1',(24,704),size='tiny',color=c['muted'],max_chars=120)
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
    try:
        app=App(pygame,ns.case,ns.seed,ns.scale,ns.difficulty,ns.lang)
        if ns.resume:
            app.resume(ns.resume)
        app.run()
    finally:
        pygame.quit()
