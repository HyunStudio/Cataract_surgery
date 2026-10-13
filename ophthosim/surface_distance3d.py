"""Read-only 3D point-to-triangle *visual geometry* proximity.

A branch-and-bound BVH closest-point search over exactly the authored
synthetic mesh triangles. World coordinates and distances are UNITLESS.
Not a real surgical collision, physical contact force, tissue damage model,
tool guidance, anatomical metric, or authorization to advance any Game phase.

All query inputs are checked before visiting triangles. Degenerate triangles
fail closed to their bounded line-segments or vertices, without division by 0.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

from .geometry import Vec3
from .mesh_raycast import MeshIndex, _vec


@dataclass(frozen=True, slots=True)
class SurfaceDistance:
    name: str
    distance: float
    point: Vec3
    face_index: int
    barycentric: Vec3

    def check(self) -> None:
        if type(self.name) is not str or not self.name or len(self.name) > 80:
            raise ValueError("Invalid synthetic surface label")
        if type(self.face_index) is not int or self.face_index < 0:
            raise ValueError("Invalid synthetic triangle ID")
        if (isinstance(self.distance, bool) or
                not isinstance(self.distance, (int, float)) or
                not 0. <= self.distance <= 100. or
                not math.isfinite(self.distance)):
            raise ValueError("Invalid synthetic surface distance")
        _vec(self.point)
        b = _vec(self.barycentric,2.)
        if abs(sum(b)-1.) > 1e-8 or min(b) < -1e-8 or max(b) > 1+1e-8:
            raise ValueError("Invalid surface barycentrics")


def _sub(a: Vec3,b: Vec3) -> Vec3:
    return (a[0]-b[0],a[1]-b[1],a[2]-b[2])


def _dot(a: Vec3,b: Vec3) -> float:
    return a[0]*b[0]+a[1]*b[1]+a[2]*b[2]


def _segment_closest(p: Vec3,a: Vec3,b: Vec3
                    ) -> tuple[Vec3,float]:
    ab=_sub(b,a)
    length=_dot(ab,ab)
    t=min(1.,max(0.,_dot(_sub(p,a),ab)/length)) if length > 1e-18 else 0.
    return tuple(a[i]+t*ab[i] for i in range(3)),t


def _face_closest(p: Vec3,a: Vec3,b: Vec3,c: Vec3
                 ) -> tuple[Vec3,Vec3]:
    """Closest point and barycentric on a triangle (Ericson regions).

    Degenerate meshes use the nearest edge/vertex, not an ill-defined plane.
    """
    ab,ac=_sub(b,a),_sub(c,a)
    normal=(ab[1]*ac[2]-ab[2]*ac[1],
            ab[2]*ac[0]-ab[0]*ac[2],
            ab[0]*ac[1]-ab[1]*ac[0])
    if _dot(normal,normal) < 1e-20:
        choices=[]
        for u,v,weights in (
            (a,b,lambda t:(1.-t,t,0.)),
            (b,c,lambda t:(0.,1.-t,t)),
            (a,c,lambda t:(1.-t,0.,t)),
        ):
            q,t=_segment_closest(p,u,v)
            choices.append((_dot(_sub(p,q),_sub(p,q)),q,weights(t)))
        _,q,bary=min(choices,key=lambda item:item[0])
        return q,bary
    ap=_sub(p,a)
    d1,d2=_dot(ab,ap),_dot(ac,ap)
    if d1<=0 and d2<=0:
        return a,(1.,0.,0.)
    bp=_sub(p,b)
    d3,d4=_dot(ab,bp),_dot(ac,bp)
    if d3>=0 and d4<=d3:
        return b,(0.,1.,0.)
    vc=d1*d4-d3*d2
    if vc<=0 and d1>=0 and d3<=0:
        v=d1/(d1-d3)
        return tuple(a[i]+v*ab[i] for i in range(3)),(1.-v,v,0.)
    cp=_sub(p,c)
    d5,d6=_dot(ab,cp),_dot(ac,cp)
    if d6>=0 and d5<=d6:
        return c,(0.,0.,1.)
    vb=d5*d2-d1*d6
    if vb<=0 and d2>=0 and d6<=0:
        w=d2/(d2-d6)
        return tuple(a[i]+w*ac[i] for i in range(3)),(1.-w,0.,w)
    va=d3*d6-d5*d4
    if va<=0 and d4-d3>=0 and d5-d6>=0:
        delta=_sub(c,b)
        w=(d4-d3)/((d4-d3)+(d5-d6))
        return tuple(b[i]+w*delta[i] for i in range(3)),(0.,1.-w,w)
    denom=1./(va+vb+vc)
    v,w=vb*denom,vc*denom
    return tuple(a[i]+v*ab[i]+w*ac[i] for i in range(3)),(1.-v-w,v,w)


def _aabb_distance_squared(p: Vec3,low: Vec3,high: Vec3) -> float:
    return sum((max(low[i]-p[i],0.,p[i]-high[i]))**2 for i in range(3))


def nearest_triangle(index: MeshIndex, point: Vec3,
                     max_distance: float = 5.) -> SurfaceDistance | None:
    """Return the nearest real triangular mesh face to a bounded 3D point.

    This is a 3D Euclidean point-to-triangle distance (NOT ray picking).
    Traversal prunes AABBs which cannot improve the current nearest distance.
    No mesh mutation, no game action, no clinical distance units.
    """
    if not isinstance(index,MeshIndex):
        raise ValueError("Expected indexed synthetic mesh")
    p=_vec(point)
    if (isinstance(max_distance,bool) or not isinstance(max_distance,(int,float))
            or not 0.<=max_distance<=100.
            or not math.isfinite(max_distance)):
        raise ValueError("Invalid synthetic query radius")
    best_squared=max_distance*max_distance
    result=None
    stack=[index.root]
    while stack:
        node=stack.pop()
        if _aabb_distance_squared(p,node.low,node.high)>best_squared+1e-12:
            continue
        if node.faces:
            for face_index in node.faces:
                x,y,z=index.mesh.faces[face_index]
                surface,bary=_face_closest(p,index.mesh.vertices[x],
                                          index.mesh.vertices[y],
                                          index.mesh.vertices[z])
                dsq=_dot(_sub(p,surface),_sub(p,surface))
                if (dsq<=best_squared+1e-12 and
                    (result is None or dsq<best_squared-1e-12 or
                     (abs(dsq-best_squared)<=1e-12 and
                      face_index<result.face_index))):
                    best_squared=dsq
                    result=SurfaceDistance(index.mesh.name,math.sqrt(dsq),
                                            surface,face_index,bary)
        else:
            child_pairs=[]
            for child in (node.left,node.right):
                if child is not None:
                    dsq=_aabb_distance_squared(p,child.low,child.high)
                    if dsq<=best_squared+1e-12:
                        child_pairs.append((dsq,child))
            for _,child in sorted(child_pairs,key=lambda item:item[0],
                                  reverse=True):
                stack.append(child)
    if result is not None:
        result.check()
    return result
