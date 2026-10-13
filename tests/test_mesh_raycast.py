"""True synthetic triangle intersections, BVH and hostile input checks.

This never tests real anatomical contact, force feedback, 3D surgical
progression or clinical accuracy. All meshes are schematic visual assets.
"""
import math
import random

import pytest

from ophthosim.geometry import Mesh, ellipsoid
from ophthosim.gl_preview import atlas_meshes
from ophthosim.mesh_raycast import (TriangleHit, build_index, pick_indexed, raycast)
from ophthosim.picking3d import Ray, project_point

W,H=1280,720


def single_triangle():
    return Mesh("triangle", ((-1.,-1.,0.),(1.,-1.,0.),(0.,1.,0.)),
                ((0.,0.,1.),)*3, ((0,1,2),))


def meshes(phase="CATARACT"):
    atlas=atlas_meshes(phase)
    return {name:build_index(atlas[name]) for name in ("iris","lens")}


def test_exact_face_barycentric_and_backface():
    index=build_index(single_triangle())
    forward=raycast(index,Ray((0,0,5),(0,0,-1)))
    assert isinstance(forward,TriangleHit)
    assert forward.name=="triangle"
    assert forward.face_index==0
    assert forward.distance==pytest.approx(5.)
    assert forward.position==pytest.approx((0,0,0))
    assert forward.barycentric==pytest.approx((.25,.25,.5))
    back=raycast(index,Ray((0,0,-5),(0,0,1)))
    assert back and back.distance==pytest.approx(5.)
    assert raycast(index,Ray((2,0,5),(0,0,-1))) is None
    assert raycast(index,Ray((0,0,5),(1,0,0))) is None


def test_degenerate_triangle_is_ignored():
    mesh=Mesh("degenerate",((0,0,0),(1,0,0),(2,0,0)),
              ((0,0,1),)*3,((0,1,2),))
    assert raycast(build_index(mesh),Ray((.5,0,1),(0,0,-1))) is None


def test_nearest_face_and_clipping_planes():
    mesh=Mesh("planes", ((-1.,-1.,0.),(1.,-1.,0.),(0.,1.,0.),
                         (-1.,-1.,1.),(1.,-1.,1.),(0.,1.,1.)),
              ((0.,0.,1.),)*6, ((0,1,2),(3,4,5)))
    index=build_index(mesh)
    hit=raycast(index,Ray((0,0,4),(0,0,-1)))
    assert hit and hit.distance==pytest.approx(3.)
    assert hit.face_index==1
    assert raycast(index,Ray((0,0,4),(0,0,-1)),near=3.2).face_index==0
    assert raycast(index,Ray((0,0,4),(0,0,-1)),near=3.2,far=3.8) is None


def test_bvh_tree_subdivides_and_gives_nearest_lens_hit():
    mesh=ellipsoid("lens",(.43,.43,.18),center=(0,0,-.19),
                   slices=16,stacks=8)
    idx=build_index(mesh)
    assert idx.root.left is not None
    assert idx.root.right is not None
    forward=raycast(idx,Ray((0,0,4),(0,0,-1)))
    assert forward and -.08 < forward.position[2] < .05
    assert abs(sum(forward.barycentric)-1.)<1e-9
    assert all(-1e-8 <= q <= 1+1e-8 for q in forward.barycentric)


@pytest.mark.parametrize("phase,label",[("CATARACT","cloudy lens"),("IOL","IOL")])
def test_rigid_scene_actual_mesh_center_selects_optic(phase,label):
    idx=meshes(phase)
    hit=pick_indexed(idx,639.5,359.5,W,H,0,0,3.6,phase)
    assert hit is not None and hit.name==label
    assert hit.face_index>=0
    assert hit.distance>0


def test_rigid_scene_iris_ring_not_pupil_and_offscreen_miss():
    idx=meshes()
    pixel=project_point((.5,0,.03),W,H,0,0,3.6)
    hit=pick_indexed(idx,*pixel,W,H,0,0,3.6,"CATARACT")
    assert hit and hit.name=="iris"
    assert hit.position[2]==pytest.approx(.03)
    assert pick_indexed(idx,-100,20,W,H,0,0,3.6,"CATARACT") is None
    assert pick_indexed(idx,1,1,W,H,0,0,3.6,"CATARACT") is None


def test_camera_orbit_and_zoom_still_pick_projected_iris():
    idx=meshes()
    for yaw,pitch,zoom in ((0,0,3.6),(.5,.27,3.1),(-.66,-.3,4.8)):
        pixel=project_point((.5,0,.03),W,H,yaw,pitch,zoom)
        hit=pick_indexed(idx,*pixel,W,H,yaw,pitch,zoom,"CATARACT")
        assert hit and hit.name=="iris"
        assert math.dist(hit.position,(.5,0,.03))<1e-8


def test_mesh_cache_is_per_scene_not_per_frame():
    # BVH is constructed from the very same triangle object used by the GPU
    # renderer. Repeating raycasts does not rebuild or mutate the tree.
    idx=meshes()
    before=idx["iris"].root
    for _ in range(40):
        pick_indexed(idx,639.5,359.5,W,H,0,0,3.6,"CATARACT")
    assert idx["iris"].root is before


@pytest.mark.parametrize("bad",[None,True,False,"x",float("nan"),
                                  float("inf"),-float("inf"),10**400,[],{}])
def test_bad_ray_component_rejected_before_search(bad):
    idx=build_index(single_triangle())
    with pytest.raises(ValueError):
        raycast(idx,Ray((0,0,bad),(0,0,-1)))
    with pytest.raises(ValueError):
        raycast(idx,Ray((0,0,1),(0,bad,-1)))


@pytest.mark.parametrize("bad",[None,True,False,"x",float("nan"),
                                  float("inf"),10**400,-1.])
def test_bad_ray_interval_rejected(bad):
    idx=build_index(single_triangle())
    with pytest.raises(ValueError):
        raycast(idx,Ray((0,0,4),(0,0,-1)),near=bad)
    with pytest.raises(ValueError):
        raycast(idx,Ray((0,0,4),(0,0,-1)),far=bad)


def test_zero_vector_rejected_and_invalid_mesh_budget():
    idx=build_index(single_triangle())
    with pytest.raises(ValueError):
        raycast(idx,Ray((0,0,1),(0,0,0)))
    for bad in (0,True,1.5,20001,None):
        with pytest.raises(ValueError):
            build_index(single_triangle(),max_faces=bad)
    with pytest.raises(ValueError):
        build_index(single_triangle(),max_faces=0)


def test_invalid_index_or_phase_rejected():
    idx=meshes()
    for bad in (None,True,{},[],1):
        with pytest.raises(ValueError):
            pick_indexed(idx,640,360,W,H,0,0,3.6,bad)
    with pytest.raises(ValueError):
        pick_indexed({},640,360,W,H,0,0,3.6,"IOL")
    with pytest.raises(ValueError):
        raycast("not-an-index",Ray((0,0,1),(0,0,-1)))


def test_400_seeded_ray_picks_finite_and_nearest():
    idx=meshes()
    rng=random.Random(42)
    for _ in range(400):
        hit=pick_indexed(idx,rng.uniform(-30,W+30),
                         rng.uniform(-30,H+30),W,H,
                         rng.uniform(-1.2,1.2),rng.uniform(-.8,.8),
                         rng.uniform(2.6,5),"CATARACT")
        if hit:
            assert hit.name in {"iris","cloudy lens"}
            assert 0.5<=hit.distance<=16
            assert math.isfinite(hit.distance)
            assert all(math.isfinite(q) for q in hit.position)
            assert sum(hit.barycentric)==pytest.approx(1.,abs=1e-8)
