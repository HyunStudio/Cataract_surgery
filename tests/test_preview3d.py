"""Non-GPU checks for 3D mesh projection and adversarial inputs."""
import math
import random
import pytest
from ophthosim.preview3d import build_preview, preview_meshes, project, rotate


def test_mesh_preview_is_nonempty_deterministic_and_bounded():
    a = build_preview("PREOP", 1., 0.)
    assert a == build_preview("PREOP", 1., 0.)
    faces, lines = a
    assert len(faces) > 100 and len(lines) > 30
    assert all(0 <= c <= 255 for face in faces for c in face.color)
    assert all(-10000 < v < 10000 for f in faces for pt in f.points for v in pt)
    assert all(faces[i].depth <= faces[i+1].depth for i in range(len(faces)-1))


def test_real_3d_rotation_changes_projected_image():
    a = build_preview("PHACO", .8, 0., yaw=0, pitch=0)
    b = build_preview("PHACO", .8, 0., yaw=.45, pitch=.27)
    assert a != b
    assert project((0, 0, 0), 0, 0) == (640, 366)
    assert rotate((1, 0, 0), 0, 0) == pytest.approx((1, 0, 0))


def test_model_switches_to_iol_and_alignment_affects_projection():
    before = build_preview("PHACO", .5, .0)
    after = build_preview("IOL", .0, 1.0)
    decentered = build_preview("IOL", .0, .0)
    assert before != after
    assert after != decentered


def test_caching_not_rebuilding_meshes_each_frame():
    assert preview_meshes() is preview_meshes()


@pytest.mark.parametrize("bad", [None, True, "oops", float("nan"),
                                 float("inf"), -float("inf"), 10**400])
def test_dirty_inputs_rejected(bad):
    with pytest.raises(ValueError):
        project((0,0,0), bad, .0)
    with pytest.raises(ValueError):
        build_preview("PHACO", bad, .0)


@pytest.mark.parametrize("yaw,pitch", [(1.3,0),(-1.3,0),(0,.95),(0,-.95)])
def test_dirty_angles_rejected(yaw,pitch):
    with pytest.raises(ValueError):
        build_preview("PHACO", .3, .0, yaw, pitch)


def test_bad_centers_and_camera_parameters_rejected():
    for center in [(0.5,0), (100000,0), (False,0), (0,), (0,0,0)]:
        with pytest.raises(ValueError):
            project((0,0,0),0,0,center=center)
    for focal in [0, -1, float("nan"), 10**400]:
        with pytest.raises(ValueError):
            project((0,0,0),0,0,focal=focal)


def test_100_seeded_valid_previews_no_crash():
    rng = random.Random(101)
    for _ in range(100):
        yaw, pitch = rng.uniform(-.9,.9), rng.uniform(-.7,.7)
        frames, lines = build_preview("IOL", rng.random(), rng.random(), yaw,pitch)
        assert frames and lines
