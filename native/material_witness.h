#pragma once
#include "contact_distance.h"

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
} // namespace membrane::material_witness
