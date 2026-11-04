"""Shared ideal-surgeon helpers for engine v3 tests.

They follow the real sequence: incisions with the right blades, viscoelastic,
capsulorhexis, hydrodissection, phaco, I/A, viscoelastic in the bag, IOL,
final checks; and they manage each assessed complication with its instrument.
"""
import math

from ophthosim.engine import COMPLICATIONS, FINAL_CHECKS, MAIN_INCISION, PREOP_CHECKS, Phase

SITES = {'incision': MAIN_INCISION, 'pupil': (.76, .5), 'centre': (.5, .5), None: (.5, .5)}


def arm(game, tool=None):
    """Hold `tool` (default: the current stage instrument)."""
    tool = tool or game.stage_tool
    if tool and game.tool != tool:
        assert game.action('tool', tool)


def use(game, tool, x=.5, y=.5):
    arm(game, tool)
    return game.action('use', x, y)


def manage(game):
    """Manage every pending complication with the right instrument."""
    for _ in range(6):
        if not game.pending or game.ending:
            return
        comp = COMPLICATIONS[game.pending[0]]
        if comp.remedy == 'escalate':
            assert game.action('escalate')
        else:
            assert use(game, comp.remedy, *SITES[comp.site])


def preop(game):
    for item in PREOP_CHECKS:
        assert game.action('verify', item)
    assert game.action('confirm')
    assert game.action('prepare')


def entry(game, ovd=True, *, stop_pending=True):
    for index, (x, y) in enumerate(game._entry_target):
        if index in game._entered:
            continue
        if game.patient.alert or (game.pending and stop_pending) or game.phase != Phase.ENTRY:
            return
        arm(game)
        game.action('touch', x, y)
        if ovd and not game.ovd_chamber and game.phase == Phase.ENTRY and not game.patient.alert:
            use(game, 'ovd_cannula')


def capsule(game):
    if not game.ovd_chamber:
        use(game, 'ovd_cannula')
    for i in range(24):
        if game.phase != Phase.CAPSULE or game.patient.alert or game.ending:
            return
        arm(game)
        a = (i + .5) * math.tau / 24
        game.action('trace', .5 + .28 * math.cos(a), .5 + .28 * math.sin(a))


def clear(game, phase, *, hydro=True, tick=False, stop_pending=True):
    if (phase == Phase.PHACO and hydro and not game.hydro_done
            and game.eye.opacity == 1.0 and game.phase == Phase.PHACO):
        assert use(game, 'hydro_cannula')
    for _ in range(800):
        if game.phase != phase or game.patient.alert or game.ending or (game.pending and stop_pending):
            return
        arm(game)
        game.action('remove', .5, .5)
        if tick:
            game.tick(1 / 60)


def iol(game, point=(.5, .5), *, ovd=True):
    if ovd and not game.ovd_bag:
        assert use(game, 'ovd_cannula')
    arm(game)
    game.action('place', *point)


def run_to(game, target=None, *, manage_pending=True, hydro=True, stop_at_alert=False):
    """Drive a game along the ideal path, assessing alerts immediately
    (or stopping at the first alert). Unmanaged complications are left
    pending when `manage_pending` is False."""
    for _ in range(80):
        if game.phase == target or game.ending:
            return
        if game.patient.alert:
            if stop_at_alert:
                return
            game.action('assess')
            continue
        if game.pending and manage_pending:
            manage(game)
            continue
        phase = game.phase
        if phase == Phase.PREOP:
            preop(game)
        elif phase == Phase.ENTRY:
            entry(game, stop_pending=manage_pending)
        elif phase == Phase.CAPSULE:
            capsule(game)
        elif phase in (Phase.PHACO, Phase.CORTEX):
            clear(game, phase, hydro=hydro, stop_pending=manage_pending)
        elif phase == Phase.IOL:
            iol(game)
        elif phase == Phase.CLOSE:
            if game._decentered and manage_pending:
                arm(game, 'iol_hook')
                game.action('place', .5, .5)
                continue
            for item in FINAL_CHECKS:
                if game.patient.alert or (game.pending and manage_pending):
                    break
                game.action('verify', item)


def use3d(controller, tool, x=.5, y=.5, width=1280, height=720):
    """Pick `tool` and click once at eye point (x, y) in the 3D viewport."""
    from ophthosim.input3d import eye_to_pixel
    if controller.game.tool != tool:
        assert controller.command('tool', tool)
    pixel = eye_to_pixel(x, y, controller.tool_depth, width, height, controller.view)
    assert pixel is not None
    return controller.pointer(*pixel, width, height, fresh_press=True)
