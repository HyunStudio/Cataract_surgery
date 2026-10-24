"""Offline tests for the GL hardware-check helpers and the Windows fixes."""
import sys

import pytest

from ophthosim.gl_hardware_check import BACKGROUND, EXTREME_VIEWS, eye_extent, nonblank
from ophthosim.gl_preview import HUD_FONT_NAMES, fps_label


def frame(width, height, box=None, color=(200, 180, 120)):
    data = bytearray(bytes(BACKGROUND) * (width * height))
    if box:
        x0, y0, x1, y1 = box
        for y in range(y0, y1):
            for x in range(x0, x1):
                i = (y * width + x) * 3
                data[i:i+3] = bytes(color)
    return bytes(data)


def test_eye_extent_measures_the_drawn_region():
    data = frame(64, 48, (8, 8, 40, 40))
    w, h = eye_extent(data, 64, 48, stride=1)
    assert (w, h) == (32, 32)
    assert eye_extent(frame(64, 48), 64, 48) is None
    with pytest.raises(ValueError):
        eye_extent(b"\0" * 10, 64, 48)


def test_nonblank_detects_a_cleared_frame():
    assert not nonblank(frame(64, 48))
    assert nonblank(frame(64, 48, (0, 0, 32, 48)))


def test_extreme_views_cover_the_view_limits():
    yaws = {v[0] for v in EXTREME_VIEWS}
    pitches = {v[1] for v in EXTREME_VIEWS}
    zooms = {v[2] for v in EXTREME_VIEWS}
    assert yaws == {-1.2, 0., 1.2} and pitches == {-.8, 0., .8} and zooms == {2.6, 5.0}


@pytest.mark.parametrize("value,text", [(None, "FPS: --"), (0., "FPS: --"), (True, "FPS: --"),
                                        (float("nan"), "FPS: --"), (59.6, "FPS: 60")])
def test_fps_label_never_invents_a_frame_rate(value, text):
    assert fps_label(value) == text


def test_3d_hud_uses_the_same_hangul_capable_fonts_as_the_2d_app():
    from ophthosim.app import FONT_NAMES
    assert HUD_FONT_NAMES == FONT_NAMES
    assert HUD_FONT_NAMES.split(",")[0] == "malgungothic"


@pytest.mark.skipif(sys.platform != "win32", reason="Windows working-set reader")
def test_windows_memory_reader_returns_a_value():
    from ophthosim.frametime import process_rss_mb
    value = process_rss_mb("win32")
    assert value is not None and value > 1
