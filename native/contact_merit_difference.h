// Conservative numerical merit-change intervals for valid represented geometry.
// Test-only shim is separate; no product C ABI is added by this header.
#pragma once
#include "contact_guard.h"
#include <cstring>

namespace membrane::merit {
using Quad=__float128;
using Bits=__uint128_t;
struct Interval {
    Quad lo=0,hi=0;
    Interval()=default;
    Interval(Quad x):lo(x),hi(x) {}
    Interval(Quad a,Quad b):lo(a),hi(b) {}
};
using Vec=std::array<Quad,3>;
using IVec=std::array<Interval,3>;
inline double represented_coordinate(double previous,double current,double time) {
    return time==1?current:static_cast<double>((1-contact::Real(time))*previous+contact::Real(time)*current);
}
inline bool finite(Quad x) { return __builtin_isfinite(x); }
inline bool finite(Interval x) { return finite(x.lo) && finite(x.hi) && x.lo<=x.hi; }
inline Quad adjacent(Quad value,bool upward) {
    static_assert(sizeof(Quad)==16,"IEEE binary128 is required by the pinned compiler");
    if (!finite(value)) return value;
    Bits bits=0; std::memcpy(&bits,&value,sizeof(bits));
    if (value==0) bits=upward?Bits(1):((Bits(1)<<127)|Bits(1));
    else if ((value>0)==upward) ++bits;
    else --bits;
    std::memcpy(&value,&bits,sizeof(bits)); return value;
}
inline Quad down(Quad x) { return adjacent(x,false); }
inline Quad up(Quad x) { return adjacent(x,true); }
inline Interval operator+(Interval a,Interval b) { return {down(a.lo+b.lo),up(a.hi+b.hi)}; }
inline Interval operator-(Interval a,Interval b) { return {down(a.lo-b.hi),up(a.hi-b.lo)}; }
inline Interval operator-(Interval a) { return {-a.hi,-a.lo}; }
inline Interval operator*(Interval a,Interval b) {
    std::array<Quad,4> values{a.lo*b.lo,a.lo*b.hi,a.hi*b.lo,a.hi*b.hi};
    return {down(*std::min_element(values.begin(),values.end())),up(*std::max_element(values.begin(),values.end()))};
}
inline Interval divide(Interval a,Interval positive) {
    if (!(positive.lo>0)) return {-Quad(__builtin_inf()),Quad(__builtin_inf())};
    return a*Interval(down(Quad(1)/positive.hi),up(Quad(1)/positive.lo));
}
inline Interval square(Interval a) {
    Quad maximum=std::max(a.lo*a.lo,a.hi*a.hi);
    Quad minimum=a.lo<=0 && a.hi>=0?Quad(0):std::min(a.lo*a.lo,a.hi*a.hi);
    return {minimum==0?Quad(0):down(minimum),up(maximum)};
}
inline Interval positive(Interval a) { return {std::max(Quad(0),a.lo),std::max(Quad(0),a.hi)}; }
inline Vec sub(Vec a,Vec b) { return {a[0]-b[0],a[1]-b[1],a[2]-b[2]}; }
inline Vec add(Vec a,Vec b) { return {a[0]+b[0],a[1]+b[1],a[2]+b[2]}; }
inline Vec mul(Vec a,Quad t) { return {a[0]*t,a[1]*t,a[2]*t}; }
inline Quad dot(Vec a,Vec b) { return a[0]*b[0]+a[1]*b[1]+a[2]*b[2]; }
inline Vec cross(Vec a,Vec b) { return {a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]}; }
inline IVec intervals(Vec a) { return {Interval(a[0]),Interval(a[1]),Interval(a[2])}; }
inline IVec add(IVec a,IVec b) { return {a[0]+b[0],a[1]+b[1],a[2]+b[2]}; }
inline IVec sub(IVec a,IVec b) { return {a[0]-b[0],a[1]-b[1],a[2]-b[2]}; }
inline IVec mul(IVec a,Interval t) { return {a[0]*t,a[1]*t,a[2]*t}; }
inline Interval dot(IVec a,IVec b) { return a[0]*b[0]+a[1]*b[1]+a[2]*b[2]; }
inline Interval norm2(IVec a) { return square(a[0])+square(a[1])+square(a[2]); }
inline Vec read(const double* a,int offset) { return {a[offset],a[offset+1],a[offset+2]}; }
inline Quad clamp(Quad x) { return std::max(Quad(0),std::min(Quad(1),x)); }

// Newton only proposes a root. The outward squared comparisons certify both
// endpoints, so no binary128 libm or unchecked sqrt error assumption is needed.
inline bool root(Interval value,Interval& result) {
    if (!finite(value) || value.hi<0) return false;
    value.lo=std::max(Quad(0),value.lo);
    if (value.hi==0) { result=Interval(0); return true; }
    auto endpoint=[](Quad input,bool upper,Quad& output) {
        if (input==0) { output=0; return true; }
        Quad proposal=Quad(std::sqrt(static_cast<long double>(input)));
        if (!(proposal>0) || !finite(proposal)) return false;
        for (int i=0;i<3;++i) proposal=(proposal+input/proposal)/2;
        for (int i=0;i<16;++i) {
            Quad rounded=proposal*proposal;
            if (upper?down(rounded)>=input:up(rounded)<=input) { output=proposal; return true; }
            proposal=adjacent(proposal,upper);
        }
        return false;
    };
    return endpoint(value.lo,false,result.lo) && endpoint(value.hi,true,result.hi);
}

struct Parameters { Quad axis=0,s=0,u=0; };
// Nested convex coordinates are feasible by construction for encoded s/u in
// [0,1], even when three separately rounded barycentric weights would not sum1.
inline IVec point(const std::array<IVec,3>& face,Parameters q) {
    return add(face[0],mul(add(mul(sub(face[1],face[0]),Interval(1)-Interval(q.u)),
                                 mul(sub(face[2],face[0]),Interval(q.u))),Interval(q.s)));
}
inline bool parameters(const double* axis,const double* face,const contact::Result& query,Parameters& q) {
    Vec a=read(axis,0),b=read(axis,3),v0=read(face,0),v1=read(face,3),v2=read(face,6);
    int feature=static_cast<int>(query.values[21]);
    Quad w1=0,w2=0;
    if (feature==0 || feature==1) {
        q.axis=feature;
        Vec e=sub(v1,v0),f=sub(v2,v0),w=sub(feature?b:a,v0);
        Quad ee=dot(e,e),ef=dot(e,f),ff=dot(f,f),we=dot(w,e),wf=dot(w,f);
        Quad determinant=ee*ff-ef*ef;
        if (!(determinant>0) || !finite(determinant)) return false;
        w1=(we*ff-wf*ef)/determinant; w2=(wf*ee-we*ef)/determinant;
    } else if (feature>=2 && feature<=4) {
        int edge=feature-2,next=(edge+1)%3;
        Vec vertices[3]={v0,v1,v2},u=sub(b,a),v=sub(vertices[next],vertices[edge]),w=sub(a,vertices[edge]);
        Quad aa=dot(u,u),ee=dot(v,v),bb=dot(u,v),cc=dot(u,w),ff=dot(v,w),t=0;
        if (aa==0) { q.axis=0; t=ee>0?clamp(ff/ee):0; }
        else if (ee==0) q.axis=clamp(-cc/aa);
        else {
            Vec product=cross(u,v); Quad determinant=dot(product,product);
            q.axis=determinant>0?clamp(dot(cross(v,w),product)/determinant):0;
            t=(bb*q.axis+ff)/ee;
            if (t<0) { t=0; q.axis=clamp(-cc/aa); }
            else if (t>1) { t=1; q.axis=clamp((bb-cc)/aa); }
        }
        Quad weights[3]={0,0,0}; weights[edge]=1-t; weights[next]=t; w1=weights[1]; w2=weights[2];
    } else return false;
    Quad sum=w1+w2;
    q.s=clamp(sum); q.u=sum>0?clamp(w2/sum):0; q.axis=clamp(q.axis);
    return finite(q.s) && finite(q.u) && finite(q.axis);
}

struct Witness {
    IVec normal;
    Interval squared;
    Quad error=0;
};
inline Witness witness(const double* axis,const double* face,Parameters q) {
    IVec origin=intervals(read(axis,0)),axis_delta=sub(intervals(read(axis,3)),origin);
    std::array<IVec,3> vertices;
    for (int j=0;j<3;++j) vertices[j]=sub(intervals(read(face,3*j)),origin);
    IVec surface=point(vertices,q),segment=mul(axis_delta,Interval(q.axis));
    IVec normal=sub(surface,segment);
    Interval support(dot(normal,sub(vertices[0],surface)));
    for (int j=1;j<3;++j) {
        Interval value=dot(normal,sub(vertices[j],surface));
        support={std::min(support.lo,value.lo),std::min(support.hi,value.hi)};
    }
    Interval end0=dot(normal,segment),end1=dot(normal,sub(segment,axis_delta));
    support=support+Interval(std::min(end0.lo,end1.lo),std::min(end0.hi,end1.hi));
    Quad error=std::max(Quad(0),(-Interval(2)*support).hi);
    return {normal,norm2(normal),error};
}
inline Interval squared_bounds(const Witness& w) {
    return {std::max(Quad(0),down(w.squared.lo-w.error)),w.squared.hi};
}
inline Interval fixed_change(const double* before,const double* after,Parameters q,const Witness& old) {
    std::array<IVec,3> delta;
    for (int j=0;j<3;++j) delta[j]=sub(intervals(read(after,3*j)),intervals(read(before,3*j)));
    IVec moved=point(delta,q);
    return Interval(2)*dot(old.normal,moved)+norm2(moved);
}
inline Interval phr_change(Quad g,Quad delta,double multiplier,double penalty) {
    if (delta==0) return Interval(0);
    Interval mu=Interval(multiplier)-Interval(penalty)*Interval(g);
    Interval first=positive(mu),last=positive(mu-Interval(penalty)*Interval(delta));
    return divide((last-first)*(last+first),Interval(2)*Interval(penalty));
}

// AABB lower distances certify inactivity at BOTH states. This routine is also
// usable before the expensive helper when both full evaluations already passed.
inline bool inactive_box(const double* before,const double* after,const double* axis,double radius,double multiplier,double penalty) {
    using guard::Bound;
    if (!(penalty>0) || !std::isfinite(penalty) || multiplier<0 || !std::isfinite(multiplier)) return false;
    long double ratio=static_cast<long double>(multiplier)/penalty;
    Bound threshold=Bound(radius*radius)*(Bound(1)+Bound(guard::down(ratio),guard::up(ratio)));
    for (const double* face:{before,after}) {
        Bound lower(0);
        for (int k=0;k<3;++k) {
            long double flo=std::min({face[k],face[3+k],face[6+k]}),fhi=std::max({face[k],face[3+k],face[6+k]});
            long double alo=std::min(axis[k],axis[3+k]),ahi=std::max(axis[k],axis[3+k]);
            Bound gap=Bound(flo)-Bound(ahi),other=Bound(alo)-Bound(fhi);
            long double distance=std::max({0.L,gap.lo,other.lo});
            lower=lower+Bound(distance)*Bound(distance);
        }
        if (!(lower.lo>threshold.hi)) return false;
    }
    return true;
}

inline bool bounded_contact_change(const double* before,const double* after,const double* axis,
    double radius,double multiplier,double penalty,Parameters q0,Parameters q1,Interval& result) {
    if (!before || !after || !axis || multiplier<0 || !std::isfinite(multiplier) || !(penalty>0) ||
        !std::isfinite(penalty) || !(radius*radius>0) || !std::isfinite(radius*radius)) return false;
    for (Parameters q:{q0,q1}) for (Quad value:{q.axis,q.s,q.u})
        if (!finite(value) || value<0 || value>1) return false;
    for (int k=0;k<9;++k) if (!std::isfinite(before[k]) || !std::isfinite(after[k]) || std::abs(before[k])>16 || std::abs(after[k])>16) return false;
    for (int k=0;k<6;++k) if (!std::isfinite(axis[k]) || std::abs(axis[k])>16) return false;
    Witness old0=witness(axis,before,q0),new1=witness(axis,after,q1),old1=witness(axis,before,q1);
    Interval radius2(radius*radius);
    Interval oldg=divide(squared_bounds(old0),radius2)-Interval(1);
    Interval newg=divide(squared_bounds(new1),radius2)-Interval(1);
    Interval threshold=divide(Interval(multiplier),Interval(penalty));
    if (oldg.lo>=threshold.hi && newg.lo>=threshold.hi) { result=Interval(0); return true; }
    Interval lower=divide(fixed_change(before,after,q1,old1)-Interval(new1.error),radius2);
    Interval upper=divide(fixed_change(before,after,q0,old0)+Interval(old0.error),radius2);
    if (!finite(oldg) || !finite(lower) || !finite(upper) || lower.lo>upper.hi) return false;
    // For fixed delta<0 the convex PHR increment decreases in oldg; for delta>0
    // it increases. Choose the old-gap endpoint separately for each bound.
    Interval high=phr_change(lower.lo<0?oldg.lo:oldg.hi,lower.lo,multiplier,penalty);
    Interval low=phr_change(upper.hi>0?oldg.lo:oldg.hi,upper.hi,multiplier,penalty);
    Interval answer(low.lo,high.hi);
    if (!finite(answer)) return false;
    result=answer; return true;
}

inline bool contact_change(const double* before,const double* after,const double* axis,
                           double radius,double multiplier,double penalty,Interval& result) {
    if (!before || !after || !axis || multiplier<0 || !std::isfinite(multiplier) || !(penalty>0) ||
        !std::isfinite(penalty) || !(radius*radius>0) || !std::isfinite(radius*radius)) return false;
    auto first=contact::distance(axis,before,radius),last=contact::distance(axis,after,radius);
    auto usable=[](int status) { return status==0 || status==3; };
    if (!usable(first.status) || !usable(last.status)) return false;
    bool same=true; for (int k=0;k<9;++k) same=same && before[k]==after[k];
    if (same || inactive_box(before,after,axis,radius,multiplier,penalty)) { result=Interval(0); return true; }
    Parameters q0,q1;
    if (!parameters(axis,before,first,q0) || !parameters(axis,after,last,q1)) return false;
    return bounded_contact_change(before,after,axis,radius,multiplier,penalty,q0,q1,result);
}

inline bool edge_change(const double* before,const double* after,double rest,double stiffness,Interval& result) {
    if (!before || !after || !(rest>0) || !(stiffness>=0) || !std::isfinite(rest) || !std::isfinite(stiffness)) return false;
    for (int k=0;k<6;++k) if (!std::isfinite(before[k]) || !std::isfinite(after[k]) || std::abs(before[k])>16 || std::abs(after[k])>16) return false;
    IVec old=sub(intervals(read(before,0)),intervals(read(before,3)));
    bool same=true; for (int k=0;k<6;++k) same=same && before[k]==after[k];
    if (same && norm2(old).lo>0) { result=Interval(0); return true; }
    IVec delta=sub(sub(intervals(read(after,0)),intervals(read(before,0))),sub(intervals(read(after,3)),intervals(read(before,3))));
    IVec current=add(old,delta);
    Interval first,last;
    if (!root(norm2(old),first) || !root(norm2(current),last) || !(first.lo>0) || !(last.lo>0)) return false;
    Interval sum=first+last;
    Interval length_change=divide(dot(delta,add(old,current)),sum);
    Interval answer=Interval(stiffness)*length_change*(sum-Interval(2)*Interval(rest))*Interval(Quad(.5));
    if (!finite(answer)) return false;
    result=answer; return true;
}
inline double lower_double(Interval value) {
    if (value.lo==0) return 0;
    return std::nextafter(static_cast<double>(value.lo),-std::numeric_limits<double>::infinity());
}
inline double upper_double(Interval value) {
    if (value.hi==0) return 0;
    return std::nextafter(static_cast<double>(value.hi),std::numeric_limits<double>::infinity());
}
} // namespace membrane::merit
