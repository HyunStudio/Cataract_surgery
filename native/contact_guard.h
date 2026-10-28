// Bounded, nonmutating continuous clearance. Not an exact-predicate CCD proof.
#pragma once
#include "contact_distance.h"

namespace membrane::guard {
using contact::Real; using contact::V;
using Q=std::array<Real,4>;
inline V read(const double* p,int off) { return {p[off],p[off+1],p[off+2]}; }
inline Q unit(Q q) {
    Real n=0; for (Real v:q) n+=v*v;
    n=std::sqrt(n); for (Real& v:q) v/=n; return q;
}
inline V rotate(Q q,V v) {
    V axis{q[0],q[1],q[2]};
    V twice=contact::mul(contact::cross(axis,v),2);
    return contact::add(v,contact::add(contact::mul(twice,q[3]),contact::cross(axis,twice)));
}

// Packet41: recorded axes0(6),axes1(6),radius; original tip0/tip1(6),
// quaternion0/quaternion1 XYZW(8),local a0/b0/a1/b1(12),global t0/t1(2).
// Kind0 is linear recorded endpoints. Kind1 is shortest spherical pose motion,
// with an affine correction that exactly honors the recorded substep endpoints.
struct Motion {
    const double* data=nullptr;
    bool pose=false;
    Q q0{},q1{};
    Real theta=0,reach=0,change=0,numeric=0;
    std::array<V,2> correction0{},correction1{};
    void init(const double* p,int kind) {
        data=p; pose=kind==1;
        Real scale=1; for (int i=0;i<41;++i) scale=std::max(scale,std::abs(Real(p[i])));
        numeric=64*std::numeric_limits<double>::epsilon()*scale;
        if (!pose) return;
        q0=unit({p[19],p[20],p[21],p[22]});
        q1=unit({p[23],p[24],p[25],p[26]});
        Real dot=0; for (int i=0;i<4;++i) dot+=q0[i]*q1[i];
        if (dot<0) { for (Real& v:q1) v=-v; dot=-dot; }
        theta=std::acos(std::clamp(dot,Real(0),Real(1)));
        for (int off:{27,30,33,36}) reach=std::max(reach,std::sqrt(contact::dot(read(p,off),read(p,off))));
        for (int end=0;end<2;++end) {
            V delta=contact::sub(read(p,33+3*end),read(p,27+3*end));
            change=std::max(change,std::sqrt(contact::dot(delta,delta)));
            correction0[end]=contact::sub(read(p,3*end),ideal(end,p[39]));
            correction1[end]=contact::sub(read(p,6+3*end),ideal(end,p[40]));
        }
        numeric+=64*std::numeric_limits<double>::epsilon()*(reach+change);
    }
    Q orientation(Real t) const {
        Q q{};
        if (theta<1e-9L) for (int i=0;i<4;++i) q[i]=q0[i]+t*(q1[i]-q0[i]);
        else {
            Real denominator=std::sin(theta);
            Real a=std::sin((1-t)*theta)/denominator,b=std::sin(t*theta)/denominator;
            for (int i=0;i<4;++i) q[i]=a*q0[i]+b*q1[i];
        }
        return unit(q);
    }
    V ideal(int end,Real t) const {
        V tip=contact::interpolate(read(data,13),read(data,16),t);
        V local=contact::interpolate(read(data,27+3*end),read(data,33+3*end),t);
        return contact::add(tip,rotate(orientation(t),local));
    }
    V sample(int end,Real t) const {
        if (t==0) return read(data,3*end);
        if (t==1) return read(data,6+3*end);
        if (!pose) return contact::interpolate(read(data,3*end),read(data,6+3*end),t);
        Real global=Real(data[39])+t*(Real(data[40])-data[39]);
        return contact::add(ideal(end,global),contact::interpolate(correction0[end],correction1[end],t));
    }
    Real padding(Real lo,Real hi) const {
        if (!pose) return 0;
        Real width=(Real(data[40])-data[39])*(hi-lo),half_angle=theta*width;
        // Affine endpoint corrections have zero deviation from their chord.
        return reach*(1-std::cos(half_angle))+change*width*std::sin(half_angle);
    }
};

inline bool axis_separates(const std::array<V,3>& body,const std::array<V,6>& face,V n,Real radius,Real error) {
    Real squared=contact::dot(n,n);
    if (!(squared>0) || !std::isfinite(squared)) return false;
    n=contact::mul(n,1/std::sqrt(squared));
    Real blo=contact::dot(body[0],n),bhi=blo,flo=contact::dot(face[0],n),fhi=flo;
    for (V v:body) { Real d=contact::dot(v,n); blo=std::min(blo,d); bhi=std::max(bhi,d); }
    for (V v:face) { Real d=contact::dot(v,n); flo=std::min(flo,d); fhi=std::max(fhi,d); }
    return std::max(flo-bhi,blo-fhi)>radius+error;
}

// Outward-rounded Bernstein coefficients retain the shared time parameter.
// A fixed swept hull can overlap even when a rotating plane stays clear.
struct Bound {
    Real lo=0,hi=0;
    Bound()=default;
    Bound(Real x):lo(x),hi(x) {}
    Bound(Real l,Real h):lo(l),hi(h) {}
};
inline Real down(Real x) { return std::nextafter(x,-std::numeric_limits<Real>::infinity()); }
inline Real up(Real x) { return std::nextafter(x,std::numeric_limits<Real>::infinity()); }
inline Bound operator+(Bound a,Bound b) { return {down(a.lo+b.lo),up(a.hi+b.hi)}; }
inline Bound operator-(Bound a,Bound b) { return {down(a.lo-b.hi),up(a.hi-b.lo)}; }
inline Bound operator*(Bound a,Bound b) {
    std::array<Real,4> p{a.lo*b.lo,a.lo*b.hi,a.hi*b.lo,a.hi*b.hi};
    return {down(*std::min_element(p.begin(),p.end())),up(*std::max_element(p.begin(),p.end()))};
}
inline Bound operator/(Bound a,int b) { return {down(a.lo/b),up(a.hi/b)}; } // positive integer only
using BV=std::array<Bound,3>;
inline BV bv(V v) { return {Bound(v[0]),Bound(v[1]),Bound(v[2])}; }
inline BV bsub(const BV& a,const BV& b) { return {a[0]-b[0],a[1]-b[1],a[2]-b[2]}; }
inline BV badd(const BV& a,const BV& b) { return {a[0]+b[0],a[1]+b[1],a[2]+b[2]}; }
inline BV bhalf(const BV& a) { return {a[0]/2,a[1]/2,a[2]/2}; }
inline BV bcross(const BV& a,const BV& b) {
    return {a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]};
}
inline Bound bdot(const BV& a,const BV& b) { return a[0]*b[0]+a[1]*b[1]+a[2]*b[2]; }
inline BV binterpolate(V a,V b,Real t) {
    BV result{};
    for (int k=0;k<3;++k) result[k]=Bound(a[k])*(Bound(1)-Bound(t))+Bound(b[k])*Bound(t);
    return result;
}
inline bool moving_plane_separates(const Motion& motion,const std::array<V,3>& old,
                                  const std::array<V,3>& current,Real lo,Real hi,Real gap) {
    std::array<BV,3> first{},last{};
    Real scale=1;
    for (int j=0;j<3;++j) {
        first[j]=binterpolate(old[j],current[j],lo); last[j]=binterpolate(old[j],current[j],hi);
        for (Real v:old[j]) scale=std::max(scale,std::abs(v));
        for (Real v:current[j]) scale=std::max(scale,std::abs(v));
    }
    BV e0=bsub(first[1],first[0]),e1=bsub(last[1],last[0]);
    BV f0=bsub(first[2],first[0]),f1=bsub(last[2],last[0]);
    // Quadratic Bernstein normal of an affine triangle.
    std::array<BV,3> normal{bcross(e0,f0),bhalf(badd(bcross(e0,f1),bcross(e1,f0))),bcross(e1,f1)};
    constexpr int choose[7][7]={{1},{1,1},{1,2,1},{1,3,3,1},{1,4,6,4,1},{1,5,10,10,5,1},{1,6,15,20,15,6,1}};
    std::array<Bound,5> norm4{};
    for (int i=0;i<3;++i) for (int j=0;j<3;++j)
        norm4[i+j]=norm4[i+j]+bdot(normal[i],normal[j])*(Bound(choose[2][i]*choose[2][j])/choose[4][i+j]);
    std::array<Bound,7> norm6{};
    for (int i=0;i<5;++i) for (int j=0;j<3;++j)
        norm6[i+j]=norm6[i+j]+norm4[i]*(Bound(choose[4][i]*choose[2][j])/choose[6][i+j]);
    Bound radius=Bound(motion.data[12])-Bound(gap)+Bound(motion.padding(lo,hi))+Bound(motion.numeric)+
        Bound(512*std::numeric_limits<Real>::epsilon()*scale);
    Bound radius2=radius*radius;
    bool positive=true,negative=true;
    for (int end=0;end<2;++end) {
        BV r0=bsub(bv(motion.sample(end,lo)),first[0]),r1=bsub(bv(motion.sample(end,hi)),last[0]);
        // Signed plane numerator has degree3. Both endpoints must stay on
        // the same side, then squared distance clearance bounds the segment.
        std::array<Bound,4> numerator{};
        for (int i=0;i<3;++i) for (int j=0;j<2;++j)
            numerator[i+j]=numerator[i+j]+bdot(normal[i],j?r1:r0)*(Bound(choose[2][i])/choose[3][i+j]);
        for (Bound value:numerator) { positive=positive && value.lo>0; negative=negative && value.hi<0; }
        if (!positive && !negative) return false;
        std::array<Bound,7> squared{};
        for (int i=0;i<4;++i) for (int j=0;j<4;++j)
            squared[i+j]=squared[i+j]+numerator[i]*numerator[j]*(Bound(choose[3][i]*choose[3][j])/choose[6][i+j]);
        for (int k=0;k<7;++k) if (!((squared[k]-radius2*norm6[k]).lo>0)) return false;
    }
    return true;
}

inline int binomial(int n,int k) {
    int result=1; for (int i=1;i<=k;++i) result=result*(n-i+1)/i; return result;
}
template<size_t A,size_t B>
inline std::array<Bound,A+B-1> poly_dot(const std::array<BV,A>& a,const std::array<BV,B>& b) {
    std::array<Bound,A+B-1> out{};
    for (size_t i=0;i<A;++i) for (size_t j=0;j<B;++j)
        out[i+j]=out[i+j]+bdot(a[i],b[j])*(Bound(binomial(A-1,i)*binomial(B-1,j))/binomial(A+B-2,i+j));
    return out;
}
template<size_t A,size_t B>
inline std::array<BV,A+B-1> poly_cross(const std::array<BV,A>& a,const std::array<BV,B>& b) {
    std::array<BV,A+B-1> out{};
    for (size_t i=0;i<A;++i) for (size_t j=0;j<B;++j) {
        BV value=bcross(a[i],b[j]);
        Bound factor=Bound(binomial(A-1,i)*binomial(B-1,j))/binomial(A+B-2,i+j);
        for (int k=0;k<3;++k) out[i+j][k]=out[i+j][k]+value[k]*factor;
    }
    return out;
}
template<size_t A,size_t B>
inline std::array<Bound,A+B-1> poly_product(const std::array<Bound,A>& a,const std::array<Bound,B>& b) {
    std::array<Bound,A+B-1> out{};
    for (size_t i=0;i<A;++i) for (size_t j=0;j<B;++j)
        out[i+j]=out[i+j]+a[i]*b[j]*(Bound(binomial(A-1,i)*binomial(B-1,j))/binomial(A+B-2,i+j));
    return out;
}
using Linear=std::array<BV,2>;
template<size_t N,size_t M>
inline bool finite_plane_certificate(const std::array<BV,N>& normal,const std::array<Linear,2>& body,
                                     const std::array<Linear,M>& opposite,Bound radius) {
    bool positive=true,negative=true;
    for (const auto& relative:opposite) for (Bound h:poly_dot(normal,relative)) {
        positive=positive && h.hi<=0; negative=negative && h.lo>=0;
    }
    if (!positive && !negative) return false;
    // Multiplication by the constant quadratic1 elevates ||n||^2 two degrees.
    auto norm=poly_product(poly_dot(normal,normal),std::array<Bound,3>{Bound(1),Bound(1),Bound(1)});
    Bound radius2=radius*radius;
    for (const auto& endpoint:body) {
        auto d=poly_dot(normal,endpoint);
        for (Bound h:d) { positive=positive && h.lo>0; negative=negative && h.hi<0; }
        if (!positive && !negative) return false;
        auto squared=poly_product(d,d);
        for (size_t k=0;k<squared.size();++k) if (!((squared[k]-radius2*norm[k]).lo>0)) return false;
    }
    return true;
}
inline bool finite_midpoint_possible(V normal,V origin,const std::array<V,2>& body,
                                    const std::array<V,3>& face,int exempt0,int exempt1,Real radius) {
    Real length=std::sqrt(contact::dot(normal,normal));
    if (!(length>0)) return false;
    normal=contact::mul(normal,1/length);
    bool positive=true,negative=true;
    for (int j=0;j<3;++j) if (j!=exempt0 && j!=exempt1) {
        Real h=contact::dot(normal,contact::sub(face[j],origin));
        positive=positive && h<=0; negative=negative && h>=0;
    }
    for (V point:body) {
        Real h=contact::dot(normal,contact::sub(point,origin));
        positive=positive && h>radius; negative=negative && h< -radius;
    }
    return positive || negative; // candidate filter only; never a certificate
}
inline bool moving_finite_separates(const Motion& motion,const std::array<V,3>& old,
                                   const std::array<V,3>& current,Real lo,Real hi,Real gap) {
    std::array<Linear,3> face{}; std::array<Linear,2> body{};
    std::array<V,3> middle_face{}; std::array<V,2> middle_body{};
    Real scale=1;
    for (int j=0;j<3;++j) {
        face[j]={binterpolate(old[j],current[j],lo),binterpolate(old[j],current[j],hi)};
        middle_face[j]=contact::interpolate(old[j],current[j],(lo+hi)/2);
        for (Real x:old[j]) scale=std::max(scale,std::abs(x));
        for (Real x:current[j]) scale=std::max(scale,std::abs(x));
    }
    for (int end=0;end<2;++end) {
        V a=motion.sample(end,lo),b=motion.sample(end,hi);
        body[end]={bv(a),bv(b)}; middle_body[end]=contact::interpolate(a,b,Real(.5));
    }
    Bound radius=Bound(motion.data[12])-Bound(gap)+Bound(motion.padding(lo,hi))+Bound(motion.numeric)+
        Bound(512*std::numeric_limits<Real>::epsilon()*scale);
    for (int vertex=0;vertex<3;++vertex) {
        std::array<Linear,2> relative_body{};
        std::array<Linear,3> relative_face{};
        for (int end=0;end<2;++end) for (int k=0;k<2;++k) relative_body[end][k]=bsub(body[end][k],face[vertex][k]);
        for (int j=0;j<3;++j) for (int k=0;k<2;++k) relative_face[j][k]=bsub(face[j][k],face[vertex][k]);
        int next=(vertex+1)%3,third=(vertex+2)%3;
        Linear edge=relative_face[next];
        V e=contact::sub(middle_face[next],middle_face[vertex]);
        for (int seed=0;seed<2;++seed) {
            V r=contact::sub(middle_body[seed],middle_face[vertex]);
            if (finite_midpoint_possible(r,middle_face[vertex],middle_body,middle_face,vertex,-1,radius.hi)) {
                if (finite_plane_certificate(relative_body[seed],relative_body,std::array<Linear,2>{relative_face[next],relative_face[third]},radius)) return true;
            }
            V n=contact::cross(e,contact::cross(r,e));
            if (finite_midpoint_possible(n,middle_face[vertex],middle_body,middle_face,vertex,next,radius.hi)) {
                auto normal=poly_cross(edge,poly_cross(relative_body[seed],edge));
                if (finite_plane_certificate(normal,relative_body,std::array<Linear,1>{relative_face[third]},radius)) return true;
            }
        }
        V n=contact::cross(e,contact::sub(middle_body[1],middle_body[0]));
        if (finite_midpoint_possible(n,middle_face[vertex],middle_body,middle_face,vertex,next,radius.hi)) {
            Linear axis{bsub(body[1][0],body[0][0]),bsub(body[1][1],body[0][1])};
            if (finite_plane_certificate(poly_cross(edge,axis),relative_body,std::array<Linear,1>{relative_face[third]},radius)) return true;
        }
    }
    return false;
}

inline bool separated(const Motion& motion,const std::array<V,3>& old,const std::array<V,3>& current,
                      Real lo,Real hi,Real gap,V nearest,bool try_plane=true) {
    V a0=motion.sample(0,lo),a1=motion.sample(0,hi);
    std::array<V,3> body{V{},contact::sub(motion.sample(1,lo),a0),contact::sub(motion.sample(1,hi),a1)};
    std::array<V,6> face{};
    Real scale=1;
    for (int i=0;i<3;++i) {
        face[i]=contact::sub(contact::interpolate(old[i],current[i],lo),a0);
        face[i+3]=contact::sub(contact::interpolate(old[i],current[i],hi),a1);
    }
    for (V v:face) for (Real value:v) scale=std::max(scale,std::abs(value));
    for (V v:body) for (Real value:v) scale=std::max(scale,std::abs(value));
    Real radius=Real(motion.data[12])-gap+motion.padding(lo,hi);
    Real error=motion.numeric+512*std::numeric_limits<Real>::epsilon()*scale;
    auto test=[&](V n) { return axis_separates(body,face,n,radius,error); };
    if (test({1,0,0}) || test({0,1,0}) || test({0,0,1}) || test(nearest)) return true;
    if (try_plane && moving_plane_separates(motion,old,current,lo,hi,gap)) return true;
    for (int i=0;i<4;++i) for (int j=i+1;j<5;++j) for (int k=j+1;k<6;++k)
        if (test(contact::cross(contact::sub(face[j],face[i]),contact::sub(face[k],face[i])))) return true;
    if (test(contact::cross(contact::sub(body[1],body[0]),contact::sub(body[2],body[0])))) return true;
    for (int i=0;i<2;++i) for (int j=i+1;j<3;++j)
        for (int k=0;k<5;++k) for (int l=k+1;l<6;++l)
            if (test(contact::cross(contact::sub(body[j],body[i]),contact::sub(face[l],face[k])))) return true;
    return try_plane && moving_finite_separates(motion,old,current,lo,hi,gap);
}

inline int check(int n,const double* previous,const double* current,int faces,const int* triangles,
                 int bodies,const int* kinds,const double* packets,int budget,double gap,double* output,double* witness=nullptr) {
    if (!previous || !current || !output || n<1 || n>4096 || faces<0 || faces>16384 ||
        bodies<0 || bodies>64 || faces*bodies>65536 || (faces && !triangles) ||
        (bodies && (!kinds || !packets)) || budget<0 || budget>128 || !(gap>0) || !std::isfinite(gap)) return -1;
    for (int i=0;i<3*n;++i) if (!std::isfinite(previous[i]) || !std::isfinite(current[i]) ||
        std::abs(previous[i])>16 || std::abs(current[i])>16) return -1;
    for (int f=0;f<faces;++f) {
        for (int k=0;k<3;++k) if (triangles[3*f+k]<0 || triangles[3*f+k]>=n) return -1;
        if (triangles[3*f]==triangles[3*f+1] || triangles[3*f]==triangles[3*f+2] || triangles[3*f+1]==triangles[3*f+2]) return -1;
    }
    std::array<Motion,64> motions{};
    for (int b=0;b<bodies;++b) {
        const double* p=packets+41*b;
        if (kinds[b]!=0 && kinds[b]!=1) return -1;
        for (int k=0;k<41;++k) if (!std::isfinite(p[k])) return -1;
        for (int k=0;k<12;++k) if (std::abs(p[k])>16) return -1;
        if (!(p[12]>gap) || p[12]>.3) return -1;
        if (kinds[b]==1) {
            for (int k=13;k<39;++k) if (std::abs(p[k])>16) return -1;
            for (int off:{19,23}) {
                double norm=0; for (int k=0;k<4;++k) norm+=p[off+k]*p[off+k];
                if (std::abs(norm-1)>.001) return -1;
            }
            if (p[39]<0 || p[40]>1 || !(p[39]<p[40])) return -1;
        }
        motions[b].init(p,kinds[b]);
    }
    std::array<double,8> stats{0,0,-1,-1,std::numeric_limits<double>::infinity(),0,0,0};
    Real sample_time=-1;
    auto finish=[&](int status,int f,int b,int reason) {
        if (status) { stats[2]=f; stats[3]=b; stats[7]=reason; }
        if (witness) *witness=status==1?static_cast<double>(sample_time):-1.;
        std::copy(stats.begin(),stats.end(),output); return status;
    };
    struct Node { Real lo,hi; int depth; };
    std::array<std::array<Real,3>,64> body_lo{},body_hi{};
    std::array<Real,64> margins{};
    for (int b=0;b<bodies;++b) {
        const Motion& motion=motions[b];
        margins[b]=motion.data[12]+motion.padding(0,1)+motion.numeric;
        for (int axis=0;axis<3;++axis) {
            body_lo[b][axis]=body_hi[b][axis]=motion.data[axis];
            for (int off:{0,3,6,9}) {
                body_lo[b][axis]=std::min(body_lo[b][axis],Real(motion.data[off+axis]));
                body_hi[b][axis]=std::max(body_hi[b][axis],Real(motion.data[off+axis]));
            }
        }
    }
    for (int f=0;f<faces;++f) {
        std::array<V,3> old{},next{};
        for (int j=0;j<3;++j) { old[j]=read(previous,3*triangles[3*f+j]); next[j]=read(current,3*triangles[3*f+j]); }
        std::array<Real,3> face_lo{},face_hi{};
        for (int axis=0;axis<3;++axis) {
            face_lo[axis]=face_hi[axis]=old[0][axis];
            for (V v:old) { face_lo[axis]=std::min(face_lo[axis],v[axis]); face_hi[axis]=std::max(face_hi[axis],v[axis]); }
            for (V v:next) { face_lo[axis]=std::min(face_lo[axis],v[axis]); face_hi[axis]=std::max(face_hi[axis],v[axis]); }
        }
        for (int b=0;b<bodies;++b) {
            ++stats[1]; const Motion& motion=motions[b];
            Real margin=margins[b];
            bool disjoint=false;
            for (int axis=0;axis<3;++axis) {
                if (face_hi[axis]<body_lo[b][axis]-margin || face_lo[axis]>body_hi[b][axis]+margin) disjoint=true;
            }
            if (disjoint) continue;
            int queries=0;
            auto sample=[&](Real t,V& nearest) {
                sample_time=t;
                if (queries>=budget) return 2;
                ++queries; ++stats[0];
                V a=motion.sample(0,t),end=motion.sample(1,t);
                double segment[6],triangle[9];
                for (int k=0;k<3;++k) { segment[k]=static_cast<double>(a[k]); segment[3+k]=static_cast<double>(end[k]); }
                for (int j=0;j<3;++j) {
                    V v=contact::interpolate(old[j],next[j],t);
                    for (int k=0;k<3;++k) triangle[3*j+k]=static_cast<double>(v[k]);
                }
                auto result=contact::distance(segment,triangle,motion.data[12]);
                if (result.status<0 || result.status==2) return 3;
                double distance_gap=std::sqrt(std::max(0.,result.values[0]))-motion.data[12];
                stats[4]=std::min(stats[4],distance_gap);
                nearest=contact::sub(read(result.values.data(),5),read(result.values.data(),2));
                if (Real(distance_gap)<-Real(gap)-motion.numeric) return 1;
                return 0;
            };
            V nearest{};
            for (Real t:{Real(0),Real(1)}) {
                int status=sample(t,nearest);
                if (status) return finish(status==1?1:2,f,b,status==1?4:(status==2?1:2));
            }
            // Breadth-first subdivision prevents an almost touching early
            // interval from consuming all queries before later penetration.
            // Each split consumes a query; with two endpoint queries, at
            // most127 nodes can be pending under the128-query contract.
            std::array<Node,129> pending{}; int count=1,head=0,tail=1; pending[0]={0,1,0};
            while (count) {
                Node node=pending[head]; head=(head+1)%int(pending.size()); --count;
                Real t=(node.lo+node.hi)/2;
                // A complete separation certificate needs no point query.
                // Any prior witness direction is safe after full hull tests;
                // preserve bounded point queries for unresolved intervals.
                if (separated(motion,old,next,node.lo,node.hi,gap,nearest)) continue;
                int status=sample(t,nearest);
                if (status) return finish(status==1?1:2,f,b,status==1?4:(status==2?1:2));
                stats[6]=std::max(stats[6],double(node.depth));
                if (separated(motion,old,next,node.lo,node.hi,gap,nearest,false)) continue;
                if (node.depth>=32 || t<=node.lo || t>=node.hi || count+2>int(pending.size())) return finish(2,f,b,3);
                ++stats[5];
                pending[tail]={node.lo,t,node.depth+1}; tail=(tail+1)%int(pending.size());
                pending[tail]={t,node.hi,node.depth+1}; tail=(tail+1)%int(pending.size()); count+=2;
            }
        }
    }
    return finish(0,-1,-1,0);
}
} // namespace membrane::guard
