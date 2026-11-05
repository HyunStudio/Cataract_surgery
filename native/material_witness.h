#pragma once
#include "contact_distance.h"
#include <vector>

// Read-only static proposal on the same normalized, rounded fine geometry as
// embedded_contact. An intersection/tie is useful geometry, not a C2 derivative,
// force equilibrium, unique grasp, unrounded-field certificate or motion proof.
namespace membrane::material_witness {
struct Result {
    int status=-1;
    // squared, gap, axis[3], surface[3], barycentric[3], axis parameter, feature.
    std::array<double,13> values{};
};
inline Result query(const double* segment,const double* controls,const double* shape,double radius) {
    numeric::Scope environment;
    Result out;
    if(!segment || !controls || !shape || !std::isfinite(radius) || radius<=0. || radius>.3) return out;
    for(int i=0;i<6;++i) if(!std::isfinite(segment[i]) || std::abs(segment[i])>16.) return out;
    for(int i=0;i<9;++i) if(!std::isfinite(controls[i]) || std::abs(controls[i])>16. ||
                            !std::isfinite(shape[i]) || shape[i]<0. || shape[i]>1.) return out;
    double triangle[9];
    using contact::Real;
    for(int i=0;i<3;++i) {
        const Real sum=Real(shape[3*i])+shape[3*i+1]+shape[3*i+2];
        if(std::abs(sum-1)>64*std::numeric_limits<double>::epsilon()) return out;
        const Real b=Real(shape[3*i+1])/sum,c=Real(shape[3*i+2])/sum;
        for(int a=0;a<3;++a) triangle[3*i+a]=static_cast<double>(Real(controls[a])+
            b*(Real(controls[3+a])-controls[a])+c*(Real(controls[6+a])-controls[a]));
    }
    const auto fine=contact::distance(segment,triangle,radius);
    out.status=fine.status;
    if(fine.status==0 || fine.status==1 || fine.status==3) {
        std::copy(fine.values.begin(),fine.values.begin()+11,out.values.begin());
        out.values[11]=fine.values[20];out.values[12]=fine.values[21];
    }
    return out;
}
// All scalar proposals in face-major/body-major order. Failure is global and
// publishes no partial packet; no distance query or numerical gate is skipped.
struct Batch {
    int status=-1;
    std::vector<Result> pairs;
};
inline Batch query_batch(int faces,const double* controls,const double* shapes,
                         int bodies,const double* capsules) {
    numeric::Scope environment;
    if(faces<1 || faces>8192 || bodies<1 || bodies>64 || faces*bodies>65536 ||
       !controls || !shapes || !capsules) return {};
    for(int i=0;i<faces*9;++i)
        if(!std::isfinite(controls[i]) || std::abs(controls[i])>16. ||
           !std::isfinite(shapes[i]) || shapes[i]<0. || shapes[i]>1.) return {};
    for(int face=0;face<faces;++face) for(int row=0;row<3;++row) {
        const int off=face*9+row*3;
        const contact::Real sum=contact::Real(shapes[off])+shapes[off+1]+shapes[off+2];
        if(std::abs(sum-1)>64*std::numeric_limits<double>::epsilon()) return {};
    }
    for(int body=0;body<bodies;++body) {
        for(int i=0;i<6;++i) if(!std::isfinite(capsules[body*7+i]) || std::abs(capsules[body*7+i])>16.) return {};
        const double radius=capsules[body*7+6];
        if(!std::isfinite(radius) || radius<=0. || radius>.3) return {};
    }
    try {
        Batch batch;batch.pairs.reserve(static_cast<std::size_t>(faces*bodies));
        for(int face=0;face<faces;++face) for(int body=0;body<bodies;++body) {
            const auto result=query(capsules+body*7,controls+face*9,shapes+face*9,capsules[body*7+6]);
            if(result.status!=0 && result.status!=1 && result.status!=3) return {result.status,{}};
            batch.pairs.push_back(result);
        }
        batch.status=0;return batch;
    } catch(...) {return {};}
}
} // namespace membrane::material_witness
