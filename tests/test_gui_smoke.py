"""SDL dummy-display integration tests; executed by GitHub Actions with pygame installed."""
import os

os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')

import pytest

pygame = pytest.importorskip('pygame')
from ophthosim.app import App, to_eye, to_screen
from ophthosim.engine import Game, Phase


@pytest.fixture
def app():
    pygame.init()
    instance=App(pygame,scale=1)
    yield instance
    pygame.quit()


def test_first_frame_and_monitor(app):
    app.draw()
    os.makedirs('build/screenshots',exist_ok=True)
    pygame.image.save(app.canvas,'build/screenshots/01_preop.png')
    assert app.canvas.get_size()==(1280,720)
    assert app.screen.get_size()==(1280,720)
    assert app.canvas.get_at((0,0))[:3] == (7,18,30)


def test_all_phase_screens_render(app):
    for phase in Phase:
        app.game.phase=phase
        app.game.paused=False
        app.game.ending='SIMULATION COMPLETE' if phase==Phase.RECOVERY else ('SAFELY ABORTED' if phase==Phase.ABORTED else None)
        app.draw()
        if phase in (Phase.PHACO,Phase.IOL,Phase.RECOVERY):
            pygame.image.save(app.canvas,f'build/screenshots/{phase.value.lower()}.png')


def test_alert_and_pause_layers_render(app):
    app.game._alert('PATIENT MOTION')
    app.draw()
    assert app.game.paused
    assert app.game.action('assess')
    app.draw()
    assert app.game.action('pause')
    app.draw()


def test_resize_and_coordinate_mapping(app):
    app.screen=pygame.display.set_mode((1920,1080),pygame.RESIZABLE)
    assert app.mapped((960,540))==(640,360)
    app.draw()
    pt=(.52,.45)
    sx,sy=to_screen(pt)
    x,y=to_eye((sx,sy))
    assert abs(x-pt[0]) < .003
    assert abs(y-pt[1]) < .003


def test_ui_keyboard_case_selection_and_start(app):
    app.dispatch(pygame.event.Event(pygame.KEYDOWN,{'key':pygame.K_2}))
    assert app.game.case == 'motion'
    app.dispatch(pygame.event.Event(pygame.KEYDOWN,{'key':pygame.K_SPACE}))
    assert app.game.phase == Phase.ANESTHESIA
    app.dispatch(pygame.event.Event(pygame.KEYDOWN,{'key':pygame.K_SPACE}))
    assert app.game.phase == Phase.ENTRY
    app.draw()


def test_ui_dirty_mouse_coordinates_do_not_crash(app):
    app.dispatch(pygame.event.Event(pygame.KEYDOWN,{'key':pygame.K_SPACE}))
    app.dispatch(pygame.event.Event(pygame.KEYDOWN,{'key':pygame.K_SPACE}))
    for pos in [(-200,-200),(99999,99999),(0,0),(1920,1080)]:
        app.dispatch(pygame.event.Event(pygame.MOUSEBUTTONDOWN,{'pos':pos,'button':1}))
        app.dispatch(pygame.event.Event(pygame.MOUSEBUTTONUP,{'pos':pos,'button':1}))
        app.draw()
    assert app.game.phase==Phase.ENTRY