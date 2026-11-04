#pragma once
#include "contact_merit_difference.h"

// Enclose the continuous affine material field BEFORE publication rounding.
// Closest-feature proposals may use doubles; their support residual bounds
// certify the true interval-valued face, not a separately rounded trajectory.
namespace membrane::fem_trajectory_merit {
namespace m=membrane::merit;
using Face=std::array<m::IVec,3>;

inline Face map(const Face& controls,const double* shape) {
    Face result{};
    for(int j=0;j<3;++j) {
        m::Interval sum=m::Interval(shape[j*3])+m::Interval(shape[j*3+1])+m::Interval(shape[j*3+2]);
        const auto a=m::divide(m::Interval(shape[j*3+1]),sum),b=m::divide(m::Interval(shape[j*3+2]),sum);
        result[j]=m::add(controls[0],m::add(m::mul(m::sub(controls[1],controls[0]),a),m::mul(m::sub(controls[2],controls[0]),b)));
    }
    return result;
}
inline Face posed(const double* previous,const double* end,const double* shape,double time) {
    Face controls{};
    for(int j=0;j<3;++j) controls[j]=m::add(m::intervals(m::read(previous,j*3)),m::mul(m::sub(m::intervals(m::read(end,j*3)),m::intervals(m::read(previous,j*3))),m::Interval(time)));
    return map(controls,shape);
}
// Refine the proposed feature on the unrounded binary128 face. Using its
// rounded proxy here leaves a first-order support residual near cancellation.
// Feasibility is clamped; witness support bounds still certify optimality error.
inline bool parameters(const double* axis,const Face& face,const membrane::contact::Result& query,m::Parameters& q) {
    m::Vec vertices[3];
    for(int j=0;j<3;++j) for(int a=0;a<3;++a) vertices[j][a]=(face[j][a].lo+face[j][a].hi)/2;
    const auto a=m::read(axis,0),b=m::read(axis,3);const int feature=static_cast<int>(query.values[21]);
    m::Quad w1=0,w2=0;
    if(feature==0 || feature==1) {
        q.axis=feature;
        const auto e=m::sub(vertices[1],vertices[0]),f=m::sub(vertices[2],vertices[0]),w=m::sub(feature?b:a,vertices[0]);
        const auto ee=m::dot(e,e),ef=m::dot(e,f),ff=m::dot(f,f),we=m::dot(w,e),wf=m::dot(w,f);
        const auto determinant=ee*ff-ef*ef;if(!(determinant>0) || !m::finite(determinant)) return false;
        w1=(we*ff-wf*ef)/determinant;w2=(wf*ee-we*ef)/determinant;
    } else if(feature>=2 && feature<=4) {
        const int edge=feature-2,next=(edge+1)%3;
        const auto u=m::sub(b,a),v=m::sub(vertices[next],vertices[edge]),w=m::sub(a,vertices[edge]);
        const auto aa=m::dot(u,u),ee=m::dot(v,v),bb=m::dot(u,v),cc=m::dot(u,w),ff=m::dot(v,w);m::Quad t=0;
        if(aa==0) {q.axis=0;t=ee>0?m::clamp(ff/ee):0;}
        else if(ee==0) q.axis=m::clamp(-cc/aa);
        else {
            const auto product=m::cross(u,v);const auto determinant=m::dot(product,product);
            q.axis=determinant>0?m::clamp(m::dot(m::cross(v,w),product)/determinant):0;
            t=(bb*q.axis+ff)/ee;
            if(t<0) {t=0;q.axis=m::clamp(-cc/aa);}
            else if(t>1) {t=1;q.axis=m::clamp((bb-cc)/aa);}
        }
        m::Quad weights[3]{0,0,0};weights[edge]=1-t;weights[next]=t;w1=weights[1];w2=weights[2];
    } else return false;
    const auto sum=w1+w2;q.s=m::clamp(sum);q.u=sum>0?m::clamp(w2/sum):0;q.axis=m::clamp(q.axis);
    return m::finite(q.s) && m::finite(q.u) && m::finite(q.axis);
}
inline m::Witness witness(const double* axis,const Face& face,m::Parameters q) {
    const auto origin=m::intervals(m::read(axis,0)),axis_delta=m::sub(m::intervals(m::read(axis,3)),origin);
    Face vertices{};for(int j=0;j<3;++j) vertices[j]=m::sub(face[j],origin);
    const auto surface=m::point(vertices,q),segment=m::mul(axis_delta,m::Interval(q.axis)),normal=m::sub(surface,segment);
    m::Interval support(m::dot(normal,m::sub(vertices[0],surface)));
    for(int j=1;j<3;++j) {const auto value=m::dot(normal,m::sub(vertices[j],surface));support={std::min(support.lo,value.lo),std::min(support.hi,value.hi)};}
    const auto end0=m::dot(normal,segment),end1=m::dot(normal,m::sub(segment,axis_delta));
    support=support+m::Interval(std::min(end0.lo,end1.lo),std::min(end0.hi,end1.hi));
    return {normal,m::norm2(normal),std::max(m::Quad(0),(-m::Interval(2)*support).hi)};
}
inline m::Interval fixed(const Face& delta,m::Parameters q,const m::Witness& old) {
    const auto moved=m::point(delta,q);
    return m::Interval(2)*m::dot(old.normal,moved)+m::norm2(moved);
}
// Preserve the small normalized gap before binary64 conversion. Subtracting1
// from an already rounded squared-distance ratio injects rho-scaled force noise.
inline bool gap(const double* previous,const double* end,const double* shape,double time,
                const double* axis,double radius,const membrane::contact::Result& query,m::Interval& result,m::Interval& separation) {
    const auto face=posed(previous,end,shape,time);m::Parameters q;
    if(!parameters(axis,face,query,q)) return false;
    const auto squared=m::squared_bounds(witness(axis,face,q));
    result=m::divide(squared,m::Interval(radius*radius))-m::Interval(1);
    return m::finite(result) && m::root(squared,separation);
}
inline bool contact_change(const double* previous,const double* before,const double* after,const double* shape,double time,
                           const double* axis,double radius,double dual,double rho,m::Interval& result) {
    membrane::numeric::Scope environment;
    if(!previous || !before || !after || !shape || !axis || !std::isfinite(time) || time<=0. || time>1. ||
       !std::isfinite(dual) || dual<0. || !std::isfinite(rho) || rho<=0. || !(radius*radius>0.) || !std::isfinite(radius*radius)) return false;
    bool same=true;
    for(int k=0;k<9;++k) {
        for(const double* data:{previous,before,after}) if(!std::isfinite(data[k]) || std::abs(data[k])>16.) return false;
        if(!std::isfinite(shape[k]) || shape[k]<0. || shape[k]>1.) return false;
        same=same && before[k]==after[k];
    }
    for(int j=0;j<3;++j) if(std::abs((shape[j*3]+shape[j*3+1])+shape[j*3+2]-1.)>64.*std::numeric_limits<double>::epsilon()) return false;
    for(int k=0;k<6;++k) if(!std::isfinite(axis[k]) || std::abs(axis[k])>16.) return false;
    const Face first=posed(previous,before,shape,time),last=posed(previous,after,shape,time);
    double rounded0[9],rounded1[9];
    for(int j=0;j<3;++j) for(int k=0;k<3;++k) {
        if(!m::finite(first[j][k]) || !m::finite(last[j][k])) return false;
        rounded0[j*3+k]=static_cast<double>((first[j][k].lo+first[j][k].hi)/2);
        rounded1[j*3+k]=static_cast<double>((last[j][k].lo+last[j][k].hi)/2);
    }
    const auto query0=membrane::contact::distance(axis,rounded0,radius),query1=membrane::contact::distance(axis,rounded1,radius);
    if((query0.status!=0 && query0.status!=3) || (query1.status!=0 && query1.status!=3)) return false;
    if(same) {result=m::Interval(0);return true;}
    m::Parameters q0,q1;
    if(!parameters(axis,first,query0,q0) || !parameters(axis,last,query1,q1)) return false;
    const auto old0=witness(axis,first,q0),new1=witness(axis,last,q1),old1=witness(axis,first,q1);
    const m::Interval r2(radius*radius),oldg=m::divide(m::squared_bounds(old0),r2)-m::Interval(1),newg=m::divide(m::squared_bounds(new1),r2)-m::Interval(1);
    const auto threshold=m::divide(m::Interval(dual),m::Interval(rho));
    if(oldg.lo>=threshold.hi && newg.lo>=threshold.hi) {result=m::Interval(0);return true;}
    Face delta_controls{};
    for(int j=0;j<3;++j) delta_controls[j]=m::mul(m::sub(m::intervals(m::read(after,j*3)),m::intervals(m::read(before,j*3))),m::Interval(time));
    const Face delta=map(delta_controls,shape);
    const auto lower=m::divide(fixed(delta,q1,old1)-m::Interval(new1.error),r2),upper=m::divide(fixed(delta,q0,old0)+m::Interval(old0.error),r2);
    if(!m::finite(oldg) || !m::finite(lower) || !m::finite(upper) || lower.lo>upper.hi) return false;
    const auto high=m::phr_change(lower.lo<0?oldg.lo:oldg.hi,lower.lo,dual,rho),low=m::phr_change(upper.hi>0?oldg.lo:oldg.hi,upper.hi,dual,rho);
    const m::Interval answer(low.lo,high.hi);if(!m::finite(answer)) return false;result=answer;return true;
}

// Fine convex shape rows lie in this coarse original-control hull. This is
// only a merit cache certificate AFTER both full distance evaluations pass.
inline bool inactive(const double* previous,const double* before,const double* after,double time,const double* axis,double radius,double dual,double rho) {
    using membrane::guard::Bound;
    if(!std::isfinite(dual) || dual<0. || !std::isfinite(rho) || rho<=0.) return false;
    const long double ratio=static_cast<long double>(dual)/rho;
    const Bound threshold=Bound(radius*radius)*(Bound(1)+Bound(membrane::guard::down(ratio),membrane::guard::up(ratio)));
    for(const double* end:{before,after}) {
        Bound lower(0);
        for(int axis_index=0;axis_index<3;++axis_index) {
            long double lo=std::numeric_limits<long double>::infinity(),hi=-lo;
            for(int j=0;j<3;++j) {
                const Bound value=Bound(previous[j*3+axis_index])+Bound(time)*(Bound(end[j*3+axis_index])-Bound(previous[j*3+axis_index]));
                lo=std::min(lo,value.lo);hi=std::max(hi,value.hi);
            }
            const long double body_lo=std::min(axis[axis_index],axis[axis_index+3]),body_hi=std::max(axis[axis_index],axis[axis_index+3]);
            const Bound a=Bound(lo)-Bound(body_hi),b=Bound(body_lo)-Bound(hi);
            const long double distance=std::max({0.L,a.lo,b.lo});lower=lower+Bound(distance)*Bound(distance);
        }
        if(!(lower.lo>threshold.hi)) return false;
    }
    return true;
}
} // namespace membrane::fem_trajectory_merit
