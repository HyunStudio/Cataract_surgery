"""Headless tests: 3D picking math, shader alignment and dirty input behavior."""
import math
import random
import pytest
from ophthosim.picking3d import (screen_ray, project_point, pick_anatomy,
                                 _rotate, _unrotate, _ellipsoid_hit, Ray)

W,H = 1280,720


@pytest.mark.parametrize("phase,expected", [("CATARACT","cloudy lens"),("IOL","IOL")])
def test_central_ray_selects_target_lens(phase,expected):
    hit = pick_anatomy(639.5,359.5,W,H,0,0,3.6,phase)
    assert hit is not None and hit.name == expected
    assert math.isfinite(hit.distance) and hit.distance > 0
    assert hit.position[2] < .03


def test_outer_iris_ring_and_outside_miss():
    # Project an actual iris point using the GLSL-matched transform.
    x,y = project_point((.5,0,.03),W,H,0,0,3.6)
    hit = pick_anatomy(x,y,W,H,0,0,3.6)
    assert hit is not None and hit.name == "iris"
    assert pick_anatomy(1,1,W,H,0,0,3.6) is None
    assert pick_anatomy(-12,10,W,H,0,0,3.6) is None


def test_projection_roundtrip_after_orbit_and_zoom():
    point=(.43,.12,.03)
    for yaw,pitch,zoom in ((0,0,3.6),(.5,.32,3.8),(-.6,-.4,4.2)):
        pixel=project_point(point,W,H,yaw,pitch,zoom)
        assert pixel is not None
        ray=screen_ray(*pixel,W,H,yaw,pitch,zoom)
        assert ray is not None
        dx=tuple(point[i]-ray.origin[i] for i in range(3))
        t=sum(dx[i]*ray.direction[i] for i in range(3))
        reconstructed=tuple(ray.origin[i]+t*ray.direction[i] for i in range(3))
        assert math.dist(point,reconstructed) < 1e-10


@pytest.mark.parametrize("yaw,pitch",[(0,0),(.2,.1),(-1.1,.7),(.6,-.4)])
def test_rotation_inverse(yaw,pitch):
    p=(.42,-.23,.71)
    assert _unrotate(_rotate(p,yaw,pitch),yaw,pitch) == pytest.approx(p,abs=1e-12)


def test_ray_norm_always_one_and_nearest_iris_wins():
    for yaw,pitch in ((0,0),(.5,-.2),(-.5,.3)):
        pos=project_point((.5,0,.03),W,H,yaw,pitch,3.6)
        assert pos is not None
        ray=screen_ray(*pos,W,H,yaw,pitch,3.6)
        assert sum(c*c for c in ray.direction) == pytest.approx(1.)
        hit=pick_anatomy(*pos,W,H,yaw,pitch,3.6)
        assert hit is not None and hit.name == "iris"


def test_safe_ray_origin_inside_ellipsoid():
    hit=_ellipsoid_hit(Ray((0,0,0),(0,0,1)),(1,1,1),(0,0,0),"sphere")
    assert hit and hit.distance == pytest.approx(1)


@pytest.mark.parametrize("value",[None,True,False,"oops",float("nan"),
                                  float("inf"),float("-inf"),10**400,[],{}])
def test_malformed_pointer_values_rejected(value):
    with pytest.raises(ValueError):
        screen_ray(value,10,W,H,0,0,3.6)
    with pytest.raises(ValueError):
        screen_ray(10,value,W,H,0,0,3.6)


@pytest.mark.parametrize("size",[-5,0,12,16385,False,True,1.0,10**400])
def test_bad_viewport_sizes_rejected(size):
    with pytest.raises(ValueError):
        screen_ray(1,1,size,H,0,0,3.6)
    with pytest.raises(ValueError):
        project_point((0,0,0),W,size,0,0,3.6)


@pytest.mark.parametrize("bad", [float("nan"),float("inf"),10**400,True,None])
def test_malformed_angles_and_zoom_rejected(bad):
    with pytest.raises(ValueError):
        pick_anatomy(10,10,W,H,bad,0,3.6)
    with pytest.raises(ValueError):
        pick_anatomy(10,10,W,H,0,bad,3.6)
    with pytest.raises(ValueError):
        pick_anatomy(10,10,W,H,0,0,bad)


def test_malformed_phase_and_model_point_rejected():
    for bad in (None, True, [], {}, 1, ""):
        with pytest.raises(ValueError):
            pick_anatomy(10,10,W,H,0,0,3.6,bad)
    for bad in (None, (1,2), (1,2,10**400), (float("nan"),0,0)):
        with pytest.raises(ValueError):
            project_point(bad,W,H,0,0,3.6)


def test_seeded_fuzz_hits_always_finite():
    rng=random.Random(303)
    for _ in range(2000):
        px=rng.uniform(-100,W+100);py=rng.uniform(-100,H+100)
        a=rng.uniform(-1.2,1.2);b=rng.uniform(-.8,.8);z=rng.uniform(2.6,5)
        hit=pick_anatomy(px,py,W,H,a,b,z,rng.choice(("CATARACT","IOL")))
        if hit is not None:
            assert hit.name in {"iris","cloudy lens","IOL"}
            assert math.isfinite(hit.distance)
            assert all(math.isfinite(c) for c in hit.position)
