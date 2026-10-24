"""Integer HUD magnification for 1440p/4K windows and side-panel wrapping.

Display-only behaviour: none of these paths may change the synthetic Game.
"""
import pytest

import ophthosim.gl_benchmark as bench
from ophthosim.engine import Phase
from ophthosim.frametime import FrameProfiler
from ophthosim.gl_preview import hud_scale
from ophthosim.gl_surgery import PHASE_NAMES, SurgeryHUD, phase_title_lines


@pytest.mark.parametrize("size,scale", [
    ((320, 240), 1), ((960, 640), 1), ((1280, 720), 1), ((1920, 1080), 1),
    ((1920, 1200), 1), ((2559, 1440), 1), ((2560, 1440), 2), ((3440, 1440), 2),
    ((2560, 1600), 2), ((3840, 2160), 3), ((5120, 2880), 3), ((7680, 4320), 3),
    ((3840, 1080), 1),  # ultrawide: height limits magnification
])
def test_hud_scale_is_integer_and_bounded(size, scale):
    assert hud_scale(*size) == scale
    logical = (size[0] // scale, size[1] // scale)
    # Never shrink the logical HUD below the authored layout (or the window).
    assert logical[0] >= min(size[0], 1280) and logical[1] >= min(size[1], 720)


@pytest.mark.parametrize("bad", [(0, 720), (1280, 0), (-1, 5), (1280.0, 720),
                                 (True, 720), ("1280", 720), (None, None)])
def test_hud_scale_rejects_invalid_sizes(bad):
    with pytest.raises(ValueError):
        hud_scale(*bad)


def test_logical_hud_keeps_authored_layout_at_4k():
    for size in ((2560, 1440), (3840, 2160)):
        scale = hud_scale(*size)
        assert (size[0] // scale, size[1] // scale) == (1280, 720)


def test_set_ui_scale_validation():
    hud = SurgeryHUD(bench.prepare_controller())
    assert hud.ui_scale == 1
    hud.set_ui_scale(3)
    assert hud.ui_scale == 3
    for bad in (0, 9, -1, 2.0, True, "2", None):
        with pytest.raises(ValueError):
            hud.set_ui_scale(bad)
    assert hud.ui_scale == 3


def test_cursor_marker_is_drawn_in_logical_hud_pixels():
    pygame = pytest.importorskip("pygame")
    pygame.init()
    try:
        controller = bench.prepare_controller()
        hud = SurgeryHUD(controller)
        bench.prepare_frame(controller, hud, 0, 3840, 2160)
        assert controller.last_pose is not None
        snapshot = controller.game.snapshot()
        hud.last_cursor = (2400, 1500)            # window pixels at 4K
        hud.set_ui_scale(3)
        surf = pygame.Surface((1280, 720), pygame.SRCALPHA)
        font = pygame.font.SysFont("segoeui", 20)
        large = pygame.font.SysFont("segoeui", 28, bold=True)
        hud.draw(pygame, surf, controller.view, 1280, 720, font, large)
        # pygame's radius-8, width-2 ring covers x offsets -8..-7 and +6..+7
        # around the logical centre (800, 500) = window (2400, 1500) / 3.
        assert surf.get_at((807, 500)).a > 0 and surf.get_at((792, 500)).a > 0
        assert surf.get_at((800, 500)).a == 0
        assert controller.game.snapshot() == snapshot
    finally:
        pygame.quit()


def test_phase_titles_wrap_between_words_in_two_lines():
    for phase in PHASE_NAMES:
        lines = phase_title_lines(phase)
        assert 1 <= len(lines) <= 2
        assert all(len(line) <= 21 for line in lines)
        assert " ".join(lines) == PHASE_NAMES[phase]
    assert phase_title_lines(Phase.ENTRY) == ("SIMULATED ENTRY", "TARGETS")


def test_benchmark_report_records_hud_scale():
    env = bench.environment(None)
    profiler = FrameProfiler(4)
    profiler.record("frame", 10.)
    for size, scale in (((1920, 1080), 1), ((3840, 2160), 3)):
        report = bench.build_report(profiler, size=size, seconds=1., warmup=0,
                                    env=env, state_unchanged=True, probes=1)
        assert report["hud_scale"] == scale
