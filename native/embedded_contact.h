// Static retained fine-face distance, pulled back to its three material controls.
// Smooth active-feature Hessian only; not contact equilibrium or a CCD certificate.
#pragma once
#include "contact_distance.h"

namespace membrane::embedded_contact {
using contact::Real;
using contact::V;
using contact::sub;
using contact::dot;
struct Result {
    // Existing distance statuses; 4 means no unique well-conditioned C2 branch.
    int status=-1;
    std::array<double,22> values{};
    std::array<double,9> gradient{};
    std::array<double,81> hessian{};
};

inline Result distance(const double* segment,const double* controls,const double* shape,double radius) {
    numeric::Scope environment;
    Result out;
    if(!segment || !controls || !shape) return out;
    for(int i=0;i<9;++i) if(!std::isfinite(controls[i]) || std::abs(controls[i])>16 ||
                             !std::isfinite(shape[i]) || shape[i]<0 || shape[i]>1) return out;
    Real b[3][3];double triangle[9];
    for(int i=0;i<3;++i) {
        Real sum=Real(shape[3*i])+shape[3*i+1]+shape[3*i+2];
        if(std::abs(sum-1)>64*std::numeric_limits<double>::epsilon()) return out;
        b[i][1]=Real(shape[3*i+1])/sum;b[i][2]=Real(shape[3*i+2])/sum;
        b[i][0]=1-b[i][1]-b[i][2];
        for(int a=0;a<3;++a) triangle[3*i+a]=static_cast<double>(Real(controls[a])+
            b[i][1]*(Real(controls[3+a])-controls[a])+b[i][2]*(Real(controls[6+a])-controls[a]));
    }
    auto fine=contact::distance(segment,triangle,radius);
    out.status=fine.status;
    if(fine.status!=0) return out;
    std::array<V,3> x;
    for(int i=0;i<3;++i) x[i]={triangle[3*i],triangle[3*i+1],triangle[3*i+2]};
    V axis{fine.values[2],fine.values[3],fine.values[4]};
    V surface{fine.values[5],fine.values[6],fine.values[7]};
    V r=sub(surface,axis),u{Real(segment[3])-segment[0],Real(segment[4])-segment[1],Real(segment[5])-segment[2]};
    Real w[3]={fine.values[8],fine.values[9],fine.values[10]};
    int active[3],count=0;
    for(int i=0;i<3;++i) if(w[i]>0) active[count++]=i;
    if(!count) {out.status=4;return out;}
    // Local minimizer variables: active triangle barycentrics and, if interior,
    // the finite axis parameter. Eliminate them from the squared-distance Hessian.
    V direction[3];Real dw[3][3]{};int size=0;
    for(int j=1;j<count;++j) {
        direction[size]=sub(x[active[j]],x[active[0]]);
        dw[active[j]][size]=1;dw[active[0]][size]=-1;++size;
    }
    if(fine.values[20]>0 && fine.values[20]<1) {
        direction[size]=contact::mul(u,-1);++size;
    }
    // A zero inactive multiplier is a feature switch: the gradient exists but
    // the ordinary Hessian need not. Do not invent one by freezing that side.
    auto near_zero=[](Real value,Real scale) {
        return std::abs(value)<=256*std::numeric_limits<double>::epsilon()*scale;
    };
    for(int i=0;i<3;++i) if(w[i]==0) {
        V edge=sub(x[i],x[active[0]]);
        Real scale=std::sqrt(dot(r,r)*dot(edge,edge));
        if(near_zero(dot(r,edge),scale)) {out.status=4;return out;}
    }
    if(dot(u,u)>0 && (fine.values[20]==0 || fine.values[20]==1) &&
       near_zero(dot(r,u),std::sqrt(dot(r,r)*dot(u,u)))) {out.status=4;return out;}

    Real l[3][3]{},scale=0;
    for(int i=0;i<size;++i) scale=std::max(scale,dot(direction[i],direction[i]));
    for(int i=0;i<size;++i) for(int j=0;j<=i;++j) {
        Real value=dot(direction[i],direction[j]);
        for(int k=0;k<j;++k) value-=l[i][k]*l[j][k];
        if(i==j) {
            if(!(value>256*std::numeric_limits<Real>::epsilon()*scale)) {out.status=4;return out;}
            l[i][j]=std::sqrt(value);
        } else l[i][j]=value/l[j][j];
    }
    Real mixed[9][3]{},solved[9][3]{};
    for(int i=0;i<9;++i) {
        for(int j=0;j<size;++j) mixed[i][j]=w[i/3]*direction[j][i%3]+r[i%3]*dw[i/3][j];
        for(int j=0;j<size;++j) {
            Real value=mixed[i][j];
            for(int k=0;k<j;++k) value-=l[j][k]*solved[i][k];
            solved[i][j]=value/l[j][j];
        }
    }
    Real gx[9]{},hx[9][9]{};
    for(int i=0;i<9;++i) {
        gx[i]=2*w[i/3]*r[i%3];
        for(int j=0;j<9;++j) {
            Real value=i%3==j%3?w[i/3]*w[j/3]:0;
            for(int k=0;k<size;++k) value-=solved[i][k]*solved[j][k];
            hx[i][j]=2*value;
        }
    }
    for(int i=0;i<9;++i) {
        Real value=0;
        for(int v=0;v<3;++v) value+=b[v][i/3]*gx[3*v+i%3];
        out.gradient[i]=static_cast<double>(value);
        for(int j=0;j<9;++j) {
            Real h=0;
            for(int v=0;v<3;++v) for(int z=0;z<3;++z)
                h+=b[v][i/3]*hx[3*v+i%3][3*z+j%3]*b[z][j/3];
            out.hessian[9*i+j]=static_cast<double>(h);
        }
    }
    for(double value:out.gradient) if(!std::isfinite(value)) {out.status=4;return out;}
    for(double value:out.hessian) if(!std::isfinite(value)) {out.status=4;return out;}
    out.values=fine.values;
    return out;
}
} // namespace membrane::embedded_contact
