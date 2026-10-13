"""Bounded triangle-mesh ray inspection of *synthetic* 3D geometry.

Actual Moller-Trumbore face intersections, with prebuilt immutable BVH nodes
and a root AABB reject. Read-only: this module NEVER issues game actions,
modifies Game state, simulates tissue forces or claims medical precision.

Only the rigid static iris/lens atlas is supported; animated/deformed IOL and
camera-space motion are NOT currently collision-authoritative. Transparent
cornea and synthetic sclera backdrop are excluded from inspection.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

from .geometry import Mesh, Vec3
from .picking3d import Ray, screen_ray

_EPS = 1e-10


def _vec(value: object, bound: float = 100.) -> Vec3:
    if not isinstance(value, (tuple, list)) or len(value) != 3:
        raise ValueError("Expected a 3D vector")
    values = []
    for part in value:
        if (isinstance(part, bool) or not isinstance(part, (int, float))
                or not -bound <= part <= bound):
            raise ValueError("Invalid triangle ray vector")
        number = float(part)
        if not math.isfinite(number):
            raise ValueError("Invalid triangle ray vector")
        values.append(number)
    return tuple(values)


def _dot(x: Vec3, y: Vec3) -> float:
    return x[0]*y[0]+x[1]*y[1]+x[2]*y[2]


def _sub(x: Vec3, y: Vec3) -> Vec3:
    return (x[0]-y[0],x[1]-y[1],x[2]-y[2])


def _cross(x: Vec3, y: Vec3) -> Vec3:
    return (x[1]*y[2]-x[2]*y[1],x[2]*y[0]-x[0]*y[2],
            x[0]*y[1]-x[1]*y[0])


@dataclass(frozen=True,slots=True)
class TriangleHit:
    name: str
    distance: float
    position: Vec3
    face_index: int
    barycentric: Vec3


@dataclass(frozen=True,slots=True)
class BVHNode:
    low: Vec3
    high: Vec3
    left: "BVHNode | None" = None
    right: "BVHNode | None" = None
    faces: tuple[int,...] = ()


@dataclass(frozen=True,slots=True)
class MeshIndex:
    mesh: Mesh
    root: BVHNode
    face_bounds: tuple[tuple[Vec3,Vec3], ...]


def _bounds(vertices: tuple[Vec3,...], face: tuple[int,int,int]
            ) -> tuple[Vec3,Vec3]:
    points = [vertices[i] for i in face]
    return (tuple(min(p[axis] for p in points) for axis in range(3)),
            tuple(max(p[axis] for p in points) for axis in range(3)))


def build_index(mesh: Mesh, *, max_faces: int = 20000) -> MeshIndex:
    """Build balanced immutable bounding-volume hierarchy once per mesh load."""
    if not isinstance(mesh, Mesh):
        raise ValueError("Expected mesh")
    if type(max_faces) is not int or not 1 <= max_faces <= 20000:
        raise ValueError("Invalid mesh search budget")
    if (len(mesh.vertices) > 30000 or len(mesh.faces) > max_faces
            or not mesh.faces):
        raise ValueError("Mesh exceeds supported CPU picking budget")
    mesh.validate()
    boxes = tuple(_bounds(mesh.vertices,face) for face in mesh.faces)

    def build(ids: list[int]) -> BVHNode:
        low = tuple(min(boxes[i][0][axis] for i in ids) for axis in range(3))
        high = tuple(max(boxes[i][1][axis] for i in ids) for axis in range(3))
        if len(ids) <= 8:
            return BVHNode(low,high,faces=tuple(ids))
        spreads = tuple(high[i]-low[i] for i in range(3))
        axis=max(range(3),key=lambda i:spreads[i])
        ids.sort(key=lambda i:(boxes[i][0][axis]+boxes[i][1][axis],i))
        middle=len(ids)//2
        return BVHNode(low,high,build(ids[:middle]),build(ids[middle:]))
    return MeshIndex(mesh,build(list(range(len(mesh.faces)))),boxes)


def _box_entry(origin: Vec3, direction: Vec3,
               low: Vec3, high: Vec3,
               near: float, far: float) -> float | None:
    """Ray/slab entry; handles rays parallel to a face and origin inside box."""
    first, last=near, far
    for i in range(3):
        o,d=origin[i],direction[i]
        if abs(d) < _EPS:
            if o < low[i]-_EPS or o > high[i]+_EPS:
                return None
            continue
        a=(low[i]-o)/d
        b=(high[i]-o)/d
        first=max(first,min(a,b))
        last=min(last,max(a,b))
        if first > last+_EPS:
            return None
    return first


def _triangle(origin: Vec3, direction: Vec3,
              v0: Vec3, v1: Vec3, v2: Vec3,
              near: float, far: float) -> tuple[float,Vec3] | None:
    """Double-sided ray-triangle intersection; degenerates fail closed."""
    e1,e2=_sub(v1,v0),_sub(v2,v0)
    p=_cross(direction,e2)
    determinant=_dot(e1,p)
    if abs(determinant)<_EPS:
        return None
    inv=1.0/determinant
    ray=_sub(origin,v0)
    u=_dot(ray,p)*inv
    if u < -_EPS or u > 1+_EPS:
        return None
    q=_cross(ray,e1)
    v=_dot(direction,q)*inv
    if v < -_EPS or u+v > 1+_EPS:
        return None
    t=_dot(e2,q)*inv
    if t < near or t > far:
        return None
    return t,(1-u-v,u,v)


def raycast(index: MeshIndex, ray: Ray, *,
            near: float = 0.00001, far: float = 20.) -> TriangleHit | None:
    """Nearest actual face hit. Inputs validated before any triangle iteration."""
    if not isinstance(index, MeshIndex) or not isinstance(ray,Ray):
        raise ValueError("Invalid raycast arguments")
    origin=_vec(ray.origin)
    direction=_vec(ray.direction)
    magnitude=math.sqrt(_dot(direction,direction))
    if magnitude < _EPS:
        raise ValueError("Ray direction cannot be zero")
    direction=tuple(d/magnitude for d in direction)
    if (isinstance(near,bool) or not isinstance(near,(float,int)) or
            not 0 <= near <= 100. or not math.isfinite(near)):
        raise ValueError("Invalid near plane")
    if (isinstance(far,bool) or not isinstance(far,(float,int)) or
            not 0 < far <= 100. or not math.isfinite(far) or near >= far):
        raise ValueError("Invalid far plane")
    if _box_entry(origin,direction,index.root.low,index.root.high,near,far) is None:
        return None
    best=far
    answer=None
    stack=[index.root]
    while stack:
        node=stack.pop()
        if _box_entry(origin,direction,node.low,node.high,near,best) is None:
            continue
        if node.faces:
            for i in node.faces:
                a,b,c=index.mesh.faces[i]
                hit=_triangle(origin,direction,index.mesh.vertices[a],
                              index.mesh.vertices[b],index.mesh.vertices[c],
                              near,best)
                if hit is None:
                    continue
                dist,bary=hit
                if answer is None or dist < best-1e-9 or (
                        abs(dist-best)<=1e-9 and i < answer.face_index):
                    best=dist
                    position=tuple(origin[j]+dist*direction[j] for j in range(3))
                    answer=TriangleHit(index.mesh.name,dist,position,i,bary)
        else:
            children=[]
            for child in (node.left,node.right):
                if child is not None:
                    entry=_box_entry(origin,direction,child.low,child.high,near,best)
                    if entry is not None:
                        children.append((entry,child))
            # LIFO visits nearest box first; the ray still checks all nearer
            # overlapping candidates before returning.
            for _,child in sorted(children,key=lambda v:v[0],reverse=True):
                stack.append(child)
    return answer


def pick_indexed(meshes: dict[str,MeshIndex], x: object, y: object,
                 width: int,height: int,yaw: object,pitch: object,zoom: object,
                 phase: str) -> TriangleHit | None:
    """Return nearest actual rigid iris/lens triangle from screen coordinates.

    No simulated sclera/cornea picking, GPU-deformed IOL or tissue collision.
    The standalone atlas uses the default *unfolded* IOL mesh; passing an
    animated simulation's appearance state is explicitly unsupported.
    """
    if type(phase) is not str or phase not in {"CATARACT","IOL"}:
        raise ValueError("Invalid atlas phase")
    if not isinstance(meshes,dict) or set(meshes)!={"iris","lens"}:
        raise ValueError("Expected precisely the two selectable mesh indexes")
    if not all(isinstance(item,MeshIndex) for item in meshes.values()):
        raise ValueError("Invalid mesh index")
    ray=screen_ray(x,y,width,height,yaw,pitch,zoom)
    if ray is None:
        return None
    hits=[hit for hit in (raycast(index,ray,near=.5,far=16.)
                          for index in meshes.values()) if hit is not None]
    if not hits:
        return None
    best=min(hits,key=lambda hit:(hit.distance,hit.name,hit.face_index))
    label=("cloudy lens" if phase=="CATARACT" else "IOL") if best.name=="lens" else best.name
    return TriangleHit(label,best.distance,best.position,best.face_index,
                       best.barycentric)
