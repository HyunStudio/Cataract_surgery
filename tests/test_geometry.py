"""Geometry-only tests run in CI without Pygame/OpenGL/graphics hardware."""
import math
import pytest

from ophthosim.geometry import (anterior_eye_meshes, cornea_dome, ellipsoid,
                                iris_annulus, ray_sphere_distance)


def _cross(a, b):
    return (a[1]*b[2] - a[2]*b[1],
            a[2]*b[0] - a[0]*b[2],
            a[0]*b[1] - a[1]*b[0])


def _orientation(mesh, face):
    a, b, c = (mesh.vertices[i] for i in face)
    ab = tuple(b[i] - a[i] for i in range(3))
    ac = tuple(c[i] - a[i] for i in range(3))
    v = _cross(ab, ac)
    normal = mesh.normals[face[0]]
    return sum(v[i] * normal[i] for i in range(3))


def test_anterior_eye_bundle_is_deterministic():
    one = anterior_eye_meshes()
    two = anterior_eye_meshes()
    assert set(one) == {"sclera", "iris", "lens", "iol", "cornea"}
    assert one == two
    for mesh in one.values():
        mesh.validate()
        assert all(math.isfinite(component) for vec in mesh.vertices for component in vec)


def test_mesh_face_indices_and_orientation():
    globe = ellipsoid("demo", (1, 1.1, .8), slices=16, stacks=8)
    ring = iris_annulus(slices=16)
    dome = cornea_dome(slices=16, stacks=6)
    for mesh in (globe, ring, dome):
        mesh.validate()
        # Correct outward/front-face winding on representative non-polar triangles.
        positives = sum(_orientation(mesh, tri) > 1e-10 for tri in mesh.faces)
        assert positives / len(mesh.faces) > .90


def test_iris_pupil_opening_is_not_filled():
    ring = iris_annulus(inner=.3, outer=.7)
    radial = [math.hypot(x, y) for x,y,z in ring.vertices]
    assert min(radial) == pytest.approx(.3)
    assert max(radial) == pytest.approx(.7)
    assert all(n == (0., 0., 1.) for n in ring.normals)


def test_cornea_front_surface():
    dome = cornea_dome()
    assert max(z for x,y,z in dome.vertices) == pytest.approx(.59)
    assert min(z for x,y,z in dome.vertices) > -.15


@pytest.mark.parametrize("radii", [
    (0,1,1), (-1,1,1), (math.nan,1,1), (math.inf,1,1),
    (10**400,1,1), (True,1,1)
])
def test_dirty_ellipsoid_axes_rejected(radii):
    with pytest.raises(ValueError):
        ellipsoid("bad", radii)


@pytest.mark.parametrize("slices,stacks", [
    (0,8), (7,8), (129,8), (16,0), (16,65), (True,8), (8,False),
    (1_000_000,1_000_000)
])
def test_dirty_mesh_resolution_rejected(slices, stacks):
    with pytest.raises(ValueError):
        ellipsoid("bad", (1,1,1), slices=slices, stacks=stacks)


def test_ray_sphere_intersections_and_misses():
    assert ray_sphere_distance((0,0,3), (0,0,-1), (0,0,0), 1) == pytest.approx(2)
    assert ray_sphere_distance((0,0,0), (1,0,0), (0,0,0), 1) == pytest.approx(1)
    assert ray_sphere_distance((0,0,3), (0,1,0), (0,0,0), 1) is None
    assert ray_sphere_distance((0,0,3), (0,0,1), (0,0,0), 1) is None


@pytest.mark.parametrize("d", [(0,0,0),(math.nan,0,0),(10**400,0,0)])
def test_dirty_ray_direction_rejected(d):
    with pytest.raises(ValueError):
        ray_sphere_distance((0,0,3), d, (0,0,0), 1)
