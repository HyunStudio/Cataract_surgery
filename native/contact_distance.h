// Bounded static capsule/triangle query. Independent implementation, no IPC sources.
// Unsigned distance alone does not establish side preservation or swept clearance.
#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <limits>

namespace membrane::contact {
using Real = long double;
using V = std::array<Real,3>;
inline V add(V a,V b) { return {a[0]+b[0],a[1]+b[1],a[2]+b[2]}; }
inline V sub(V a,V b) { return {a[0]-b[0],a[1]-b[1],a[2]-b[2]}; }
inline V mul(V a,Real s) { return {a[0]*s,a[1]*s,a[2]*s}; }
inline Real dot(V a,V b) { return a[0]*b[0]+a[1]*b[1]+a[2]*b[2]; }
inline V cross(V a,V b) { return {a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]}; }
inline Real clamp(Real t) { return std::max(Real(0),std::min(Real(1),t)); }

struct Candidate {
    V axis{}, surface{}, weights{};
    Real time=0, squared=0;
    int feature=0;
};
struct Result {
    // -1invalid;0regular;1axis intersects;2degenerate/numerically inconclusive;
    // 3distinct nearest witnesses/gradients are indistinguishable numerically.
    int status=-1;
    std::array<double,22> values{};
};

inline bool barycentric(V p,const std::array<V,3>& face,V normal,V& weights) {
    int omit=0;
    for (int i=1;i<3;++i) if (std::abs(normal[i])>std::abs(normal[omit])) omit=i;
    int i=(omit+1)%3,j=(omit+2)%3;
    V u=sub(face[1],face[0]),v=sub(face[2],face[0]),w=sub(p,face[0]);
    Real denominator=u[i]*v[j]-u[j]*v[i];
    if (denominator==0) return false;
    Real b=(w[i]*v[j]-w[j]*v[i])/denominator;
    Real c=(u[i]*w[j]-u[j]*w[i])/denominator;
    weights={1-b-c,b,c};
    return weights[0]>=0 && b>=0 && c>=0;
}

inline Result distance(const double* segment,const double* triangle,double radius) {
    Result out;
    if (!segment || !triangle || !std::isfinite(radius) || radius<=0 || radius>.3) return out;
    for (int i=0;i<6;++i) if (!std::isfinite(segment[i]) || std::abs(segment[i])>16) return out;
    for (int i=0;i<9;++i) if (!std::isfinite(triangle[i]) || std::abs(triangle[i])>16) return out;
    V a{segment[0],segment[1],segment[2]},b{segment[3],segment[4],segment[5]};
    std::array<V,3> face;
    for (int i=0;i<3;++i) face[i]={triangle[3*i],triangle[3*i+1],triangle[3*i+2]};
    V u=sub(b,a),normal=cross(sub(face[1],face[0]),sub(face[2],face[0]));
    // Cancellation in the oriented-volume predicate can also erase the tiny
    // displacement when world-space witnesses are reconstructed. In that case
    // do not report a definite plane/intersection result, even if its value is0.
    auto plane_inconclusive=[&](V point) {
        V e=sub(face[1],face[0]),f=sub(face[2],face[0]),p=sub(point,face[0]);
        Real permanent=0;
        for (int i=0;i<3;++i) {
            int j=(i+1)%3,k=(i+2)%3;
            permanent+=std::abs(p[i]*e[j]*f[k])+std::abs(p[i]*e[k]*f[j]);
        }
        Real bound=256*std::numeric_limits<Real>::epsilon()*permanent;
        return bound>0 && std::abs(dot(p,normal))<=bound;
    };
    bool uncertain_plane=plane_inconclusive(a)||plane_inconclusive(b);
    Real normal2=dot(normal,normal),longest2=0;
    for (int i=0;i<3;++i) longest2=std::max(longest2,dot(sub(face[(i+1)%3],face[i]),sub(face[(i+1)%3],face[i])));
    bool degenerate=std::sqrt(normal2)<=64*std::numeric_limits<Real>::epsilon()*longest2;
    std::array<Candidate,12> candidates;
    int count=0;
    auto append=[&](V axis,V surface,V weights,Real t,int feature) {
        Candidate c{axis,surface,weights,t,dot(sub(axis,surface),sub(axis,surface)),feature};
        candidates[count++]=c;
    };
    // Axis endpoints against triangle interior and each finite boundary edge.
    for (int end=0;end<2;++end) {
        V p=end?b:a,weights{};
        if (!degenerate) {
            V projected=sub(p,mul(normal,dot(sub(p,face[0]),normal)/normal2));
            if (barycentric(projected,face,normal,weights)) append(p,projected,weights,end,end);
        }
        for (int edge=0;edge<3;++edge) {
            int next=(edge+1)%3;
            V direction=sub(face[next],face[edge]); Real length2=dot(direction,direction);
            Real t=length2>0?clamp(dot(sub(p,face[edge]),direction)/length2):0;
            weights={0,0,0}; weights[edge]=1-t; weights[next]=t;
            append(p,add(face[edge],mul(direction,t)),weights,end,2+edge);
        }
    }
    // Axis interior against finite triangle boundary edges (including parallel).
    for (int edge=0;edge<3;++edge) {
        int next=(edge+1)%3;
        V v=sub(face[next],face[edge]),w=sub(a,face[edge]);
        Real aa=dot(u,u),ee=dot(v,v),bb=dot(u,v),cc=dot(u,w),ff=dot(v,w);
        Real s=0,t=0;
        if (aa==0) t=ee>0?clamp(ff/ee):0;
        else if (ee==0) s=clamp(-cc/aa);
        else {
            V product=cross(u,v); Real denominator=dot(product,product);
            if (denominator>0) s=clamp(dot(cross(v,w),product)/denominator);
            t=(bb*s+ff)/ee;
            if (t<0) { t=0; s=clamp(-cc/aa); }
            else if (t>1) { t=1; s=clamp((bb-cc)/aa); }
        }
        V weights{}; weights[edge]=1-t; weights[next]=t;
        append(add(a,mul(u,s)),add(face[edge],mul(v,t)),weights,s,2+edge);
    }
    // Edge/endpoint distances alone miss an axis crossing the face interior.
    if (!degenerate) {
        Real da=dot(sub(a,face[0]),normal),db=dot(sub(b,face[0]),normal);
        Real t=-1; V weights{};
        if (da!=db) t=da/(da-db);
        else if (da==0) {
            // Coplanar segment clipping in the triangle's oriented half-planes.
            Real lo=0,hi=1;
            for (int edge=0;edge<3 && lo<=hi;++edge) {
                V v=sub(face[(edge+1)%3],face[edge]);
                Real start=dot(cross(v,sub(a,face[edge])),normal);
                Real finish=dot(cross(v,sub(b,face[edge])),normal);
                if (start<0 && finish<0) { lo=1; hi=0; }
                else if (start<0) lo=std::max(lo,start/(start-finish));
                else if (finish<0) hi=std::min(hi,start/(start-finish));
            }
            if (lo<=hi) t=(lo+hi)/2;
        }
        if (t>=0 && t<=1) {
            V p=add(a,mul(u,t));
            if (barycentric(p,face,normal,weights)) append(p,p,weights,t,5);
        }
    }
    int best=0;
    for (int i=1;i<count;++i) if (candidates[i].squared<candidates[best].squared) best=i;
    const Candidate& c=candidates[best];
    V delta=sub(c.surface,c.axis);
    out.status=degenerate?2:(c.squared==0?1:0);
    if (uncertain_plane && (c.feature<=1 || c.feature==5 || c.squared==0)) out.status=2;
    out.values[0]=static_cast<double>(c.squared);
    out.values[1]=static_cast<double>(std::sqrt(c.squared)-radius);
    for (int axis=0;axis<3;++axis) {
        out.values[2+axis]=static_cast<double>(c.axis[axis]);
        out.values[5+axis]=static_cast<double>(c.surface[axis]);
        out.values[8+axis]=static_cast<double>(c.weights[axis]);
        for (int vertex=0;vertex<3;++vertex)
            out.values[11+3*vertex+axis]=static_cast<double>(2*c.weights[vertex]*delta[axis]);
    }
    out.values[20]=static_cast<double>(c.time); out.values[21]=c.feature;
    if (c.squared>0 && out.values[0]==0) out.status=2;
    if (out.status==0) {
        // Equal distance with distinct gradients has no unique ordinary derivative.
        Real tolerance=64*std::numeric_limits<Real>::epsilon()*std::max(Real(1),c.squared);
        for (int i=0;i<count;++i) if (std::abs(candidates[i].squared-c.squared)<=tolerance) {
            V d=sub(candidates[i].surface,candidates[i].axis);
            for (int vertex=0;vertex<3;++vertex) for (int axis=0;axis<3;++axis)
                // No absolute floor: tiny clearances/short segments can still
                // have distinct minimizers. Compare internal values, avoiding
                // a spurious difference from the public float64 conversion.
                if (2*candidates[i].weights[vertex]*d[axis]!=2*c.weights[vertex]*delta[axis])
                    out.status=3;
        }
    }
    for (double value:out.values) if (!std::isfinite(value)) { out.status=-1; break; }
    return out;
}
} // namespace membrane::contact
