"""Operating-room geometry, cameras and display textures (no OpenGL needed)."""
import math
import os

import pytest

from ophthosim.gl_preview import pack_mesh
from ophthosim.room3d import (CAMERAS, EYE_POS, EYE_RADIUS, MATERIALS, ROOM, SCREEN_PIXELS,
                              SCREENS, TRAY_TOOLS, VIEW_CYCLE, align_y, dynamic_room, euler,
                              eye_disc, instrument, look_at, project, static_room,
                              view_projection)
from ophthosim.engine import TOOL_NAMES


def _inside_room(meshes, margin=.05):
    x0, x1, y0, y1, z0, z1 = ROOM
    for mesh in meshes.values():
        for x, y, z in mesh.vertices:
            assert x0 - margin <= x <= x1 + margin and y0 - margin <= y <= y1 + margin
            assert z0 - margin <= z <= z1 + margin


def test_static_room_is_valid_inside_the_room_and_packable():
    meshes = static_room()
    assert set(meshes) <= set(MATERIALS)
    _inside_room(meshes)
    total = 0
    for mesh in meshes.values():
        mesh.validate()
        total += pack_mesh(mesh)[2] // 3
    assert 1_000 < total < 150_000


@pytest.mark.parametrize("tool", [None, *TRAY_TOOLS])
def test_people_and_tray_for_every_instrument(tool):
    meshes = dynamic_room(tool, tool in ("phaco", "ia"))
    _inside_room(meshes)
    for mesh in meshes.values():
        pack_mesh(mesh)


def test_tray_holds_exactly_the_game_instruments():
    assert set(TRAY_TOOLS) == set(TOOL_NAMES)
    with pytest.raises(ValueError):
        dynamic_room("scalpel", False)


def _near_eye(meshes, radius):
    return any(math.dist(v, EYE_POS) < radius for m in meshes.values() for v in m.vertices)


def test_held_instrument_tip_reaches_the_eye():
    assert not _near_eye(dynamic_room(None, False), .016)
    for tool in TRAY_TOOLS:
        assert _near_eye(dynamic_room(tool, False), .016), tool


@pytest.mark.parametrize("name", TRAY_TOOLS)
def test_instruments_have_the_tip_at_the_origin(name):
    meshes = instrument(name).meshes()
    xs = [v[0] for m in meshes.values() for v in m.vertices]
    assert min(xs) > -.012 and .03 < max(xs) < .2
    assert any(math.dist(v, (0., 0., 0.)) < .006 for m in meshes.values() for v in m.vertices)


def test_rotations_are_orthonormal():
    for m in (euler(.3, -1.1, .4), align_y((.2, -.9, .4)), align_y((0., -1., 0.))):
        for i in range(3):
            for j in range(3):
                dot = sum(m[i][k] * m[j][k] for k in range(3))
                assert dot == pytest.approx(1. if i == j else 0., abs=1e-9)


@pytest.mark.parametrize("name", list(CAMERAS))
def test_cameras_are_finite(name):
    m = view_projection(CAMERAS[name], 16 / 9)
    assert all(math.isfinite(v) for row in m for v in row)


@pytest.mark.parametrize("name", ["surgeon", "scope", "hands", "patient", "overview"])
def test_eye_is_framed(name):
    x, y = project(view_projection(CAMERAS[name], 16 / 9), EYE_POS)
    assert abs(x) < .35 and abs(y) < .45


@pytest.mark.parametrize("name", ["vitals", "monitor"])
def test_screen_cameras_face_their_screen(name):
    screen = SCREENS["video" if name == "monitor" else name]
    m = view_projection(CAMERAS[name], 16 / 9)
    x, y = project(m, screen.centre)
    assert abs(x) < .1 and abs(y) < .1
    for corner in screen.corners():
        cx, cy = project(m, corner)
        assert abs(cx) < 1 and abs(cy) < 1          # whole display in view


def test_scope_view_matches_the_2d_field_orientation():
    m = view_projection(CAMERAS["scope"], 16 / 9)
    cx, cy = project(m, EYE_POS)
    right = project(m, (EYE_POS[0] - .01, EYE_POS[1], EYE_POS[2]))      # world -x
    top = project(m, (EYE_POS[0], EYE_POS[1], EYE_POS[2] + .01))        # world +z
    assert right[0] > cx and top[1] > cy


def test_eye_disc_texture_orientation():
    vertices, uvs, faces = eye_disc()
    assert all(0 <= u <= 1 and 0 <= v <= 1 for u, v in uvs)
    far = max(range(len(vertices)), key=lambda i: vertices[i][2])          # +z: image top
    right = min(range(len(vertices)), key=lambda i: vertices[i][0])        # -x: image right
    assert uvs[far][1] == pytest.approx(0, abs=.01) and uvs[right][0] == pytest.approx(1, abs=.01)
    assert max(math.dist(v, EYE_POS) for v in vertices) == pytest.approx(EYE_RADIUS)
    assert all(len(set(f)) == 3 for f in faces)


def test_look_at_rejects_a_degenerate_up_vector():
    with pytest.raises(ValueError):
        look_at((0., 1., 0.), (0., 0., 0.))


def test_view_cycle():
    assert VIEW_CYCLE[0] == "microscope_view"
    assert all(name in CAMERAS for name in VIEW_CYCLE[1:])


# --- displays (SDL dummy) -------------------------------------------------------------
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")


@pytest.fixture
def pg():
    pygame = pytest.importorskip("pygame")
    pygame.init()
    yield pygame
    pygame.quit()


def _game(case, stop_at_alert=True):
    import surgeon_helpers as H
    from ophthosim.replay import ReplayGame
    g = ReplayGame(case, 7, "standard")
    H.run_to(g, stop_at_alert=stop_at_alert)
    return g


def test_display_sizes_and_groups(pg):
    from ophthosim.screens3d import all_screens
    g = _game("normal", False)
    screens = all_screens(pg, g, "ko")
    assert {k: s.get_size() for k, s in screens.items()} == SCREEN_PIXELS
    assert set(all_screens(pg, g, "en", group=0)) == {"video", "eye"}
    assert set(all_screens(pg, g, "en", group=1)) == {"vitals", "phaco"}


def test_vitals_and_video_show_the_alert(pg):
    from ophthosim.screens3d import field_surfaces, vitals_surface
    from ophthosim.replay import ReplayGame
    quiet = ReplayGame("hyphema", 7, "standard")
    alert = _game("hyphema")
    assert alert.patient.alert == "HYPHEMA"
    a = pg.image.tobytes(vitals_surface(pg, quiet, "en"), "RGB")
    b = pg.image.tobytes(vitals_surface(pg, alert, "en"), "RGB")
    assert a != b
    video, eye = field_surfaces(pg, alert, "en")
    r, g_, b_ = video.get_at((5, video.get_height() - 5))[:3]
    assert r > g_ and r > b_                      # red alert banner on the feed
    # Hyphema: the lower chamber of the eye texture is red.
    r, g_, b_ = eye.get_at((eye.get_width() // 2, int(eye.get_height() * .72)))[:3]
    assert r > g_ + 40


def test_phaco_console_has_no_device_settings(pg):
    from ophthosim.engine import Phase
    from ophthosim.screens3d import phaco_levels, phaco_lines, phaco_surface
    g = _game("normal", False)
    for lang in ("en", "ko"):
        assert not any(ch.isdigit() for line in phaco_lines(g, lang) for ch in line)
    import surgeon_helpers as H
    from ophthosim.replay import ReplayGame
    p = ReplayGame("normal", 7, "standard")
    H.run_to(p, Phase.PHACO)
    idle, busy = phaco_levels(p, False), phaco_levels(p, True)
    assert busy["ultrasound"] > idle["ultrasound"] == 0
    assert all(0 <= v <= 1 for v in busy.values())
    alert = _game("vitals")
    assert set(phaco_levels(alert, True).values()) == {0.}
    assert phaco_surface(pg, p, "ko", True).get_size() == SCREEN_PIXELS["phaco"]
