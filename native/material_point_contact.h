#pragma once
#include "embedded_contact.h"
#include "fem_trajectory_merit.h"

// Fixed material point against a finite capsule axis. Multiple such constraints
// may carry distributed normal reactions. This is not full triangle clearance,
// a bilateral grasp, pressure-area calibration or friction. Caller must check
// the complete original surface and the entire motion before publication.
namespace membrane::material_point_contact {
using contact::Real;
using contact::V;
inline contact::Result geometry(const double* segment,const double* point,double radius) {
    numeric::Scope environment;
    contact::Result out;
    if(!segment || !point || !std::isfinite(radius) || radius<=0. || radius>.3) return out;
    for(int k=0;k<6;++k) if(!std::isfinite(segment[k]) || std::abs(segment[k])>16.) return out;
    for(int k=0;k<3;++k) if(!std::isfinite(point[k]) || std::abs(point[k])>16.) return out;
    const V a{segment[0],segment[1],segment[2]},b{segment[3],segment[4],segment[5]},p{point[0],point[1],point[2]};
    const auto u=contact::sub(b,a);const Real length=contact::dot(u,u);
    const Real t=length>0 ? contact::clamp(contact::dot(contact::sub(p,a),u)/length) : 0;
    const auto axis=contact::interpolate(a,b,t),r=contact::sub(p,axis);
    const Real squared=contact::dot(r,r);
    out.status=squared>0 ? 0 : 1;out.values[0]=static_cast<double>(squared);
    out.values[1]=static_cast<double>(std::sqrt(squared)-radius);
    for(int k=0;k<3;++k) {out.values[2+k]=static_cast<double>(axis[k]);out.values[5+k]=point[k];}
    out.values[8]=1.;out.values[20]=static_cast<double>(t);out.values[21]=2.;
    for(double v:out.values) if(!std::isfinite(v)) out.status=-1;
    return out;
}
inline embedded_contact::Result distance(const double* segment,const double* controls,const double* shape,double radius) {
    numeric::Scope environment;
    embedded_contact::Result out;
    if(!controls || !shape) return out;
    Real sum=0;
    for(int j=0;j<3;++j) {
        if(!std::isfinite(shape[j]) || shape[j]<0 || shape[j]>1) return out;
        if(shape[j]!=shape[j+3] || shape[j]!=shape[j+6]) return out;
        sum+=shape[j];
    }
    if(std::abs(sum-1)>64*std::numeric_limits<double>::epsilon()) return out;
    for(int k=0;k<9;++k) if(!std::isfinite(controls[k]) || std::abs(controls[k])>16.) return out;
    V p;double rounded[3];
    for(int a=0;a<3;++a) {
        p[a]=Real(controls[a])+(shape[1]*(Real(controls[3+a])-controls[a])+shape[2]*(Real(controls[6+a])-controls[a]))/sum;
        rounded[a]=static_cast<double>(p[a]);
    }
    const auto query=geometry(segment,rounded,radius);out.status=query.status;out.values=query.values;
    if(query.status!=0) return out;
    const V a{segment[0],segment[1],segment[2]},b{segment[3],segment[4],segment[5]};
    const auto u=contact::sub(b,a);const Real length=contact::dot(u,u);
    const Real t=length>0 ? contact::clamp(contact::dot(contact::sub(p,a),u)/length) : 0;
    const auto r=contact::sub(p,contact::interpolate(a,b,t));
    // The gradient is continuous at a clamped endpoint. Select its endpoint
    // generalized Hessian there; the original merit test still gates the step.
    const bool interior=length>0 && t>0 && t<1;
    for(int i=0;i<9;++i) {
        const Real wi=Real(shape[i/3])/sum;
        out.gradient[i]=static_cast<double>(2*wi*r[i%3]);
        for(int j=0;j<9;++j) {
            const Real projector=Real(i%3==j%3 ? 1 : 0)-(interior ? u[i%3]*u[j%3]/length : 0);
            out.hessian[9*i+j]=static_cast<double>(2*wi*(Real(shape[j/3])/sum)*projector);
        }
    }
    for(double v:out.gradient) if(!std::isfinite(v)) out.status=4;
    for(double v:out.hessian) if(!std::isfinite(v)) out.status=4;
    return out;
}
inline bool change(const double* previous,const double* before,const double* after,const double* shape,double time,
                   const double* axis,double radius,double dual,double rho,merit::Interval& result) {
    namespace f=fem_trajectory_merit;namespace m=merit;
    numeric::Scope environment;
    const auto first=f::posed(previous,before,shape,time),last=f::posed(previous,after,shape,time);
    double rounded0[3],rounded1[3];bool same=true;
    for(int a=0;a<3;++a) {
        rounded0[a]=static_cast<double>((first[0][a].lo+first[0][a].hi)/2);
        rounded1[a]=static_cast<double>((last[0][a].lo+last[0][a].hi)/2);
    }
    for(int k=0;k<9;++k) same=same && before[k]==after[k];
    const auto query0=geometry(axis,rounded0,radius),query1=geometry(axis,rounded1,radius);
    if(query0.status!=0 || query1.status!=0) return false;
    if(same) {result=m::Interval(0);return true;}
    m::Parameters q0,q1;
    if(!f::parameters(axis,first,query0,q0) || !f::parameters(axis,last,query1,q1)) return false;
    const auto old0=f::witness(axis,first,q0),new1=f::witness(axis,last,q1),old1=f::witness(axis,first,q1);
    const m::Interval r2(radius*radius),oldg=m::divide(m::squared_bounds(old0),r2)-m::Interval(1),newg=m::divide(m::squared_bounds(new1),r2)-m::Interval(1);
    const auto threshold=m::divide(m::Interval(dual),m::Interval(rho));
    if(oldg.lo>=threshold.hi && newg.lo>=threshold.hi) {result=m::Interval(0);return true;}
    f::Face delta_controls{};
    for(int j=0;j<3;++j) delta_controls[j]=m::mul(m::sub(m::intervals(m::read(after,j*3)),m::intervals(m::read(before,j*3))),m::Interval(time));
    const auto delta=f::map(delta_controls,shape);
    const auto lower=m::divide(f::fixed(delta,q1,old1)-m::Interval(new1.error),r2),upper=m::divide(f::fixed(delta,q0,old0)+m::Interval(old0.error),r2);
    if(!m::finite(oldg) || !m::finite(lower) || !m::finite(upper) || lower.lo>upper.hi) return false;
    const auto high=m::phr_change(lower.lo<0?oldg.lo:oldg.hi,lower.lo,dual,rho),low=m::phr_change(upper.hi>0?oldg.lo:oldg.hi,upper.hi,dual,rho);
    const m::Interval answer(low.lo,high.hi);if(!m::finite(answer)) return false;result=answer;return true;
}
} // namespace membrane::material_point_contact
