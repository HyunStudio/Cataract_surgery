#include "contact_distance.h"
#include "embedded_contact.h"
#include "material_witness.h"

extern "C" __declspec(dllexport) int membrane_material_witness(
    const double* segment,const double* controls,const double* shape,double radius,double* output) {
    if(!output) return -1;
    const auto result=membrane::material_witness::query(segment,controls,shape,radius);
    if(result.status==0 || result.status==1 || result.status==3)
        std::copy(result.values.begin(),result.values.end(),output);
    return result.status;
}

extern "C" __declspec(dllexport) int membrane_material_witness_batch(
    int faces,const double* controls,const double* shapes,int bodies,const double* capsules,
    int* statuses,double* values) {
    if(!statuses || !values) return -1;
    const auto batch=membrane::material_witness::query_batch(faces,controls,shapes,bodies,capsules);
    if(batch.status!=0) return batch.status;
    for(std::size_t pair=0;pair<batch.pairs.size();++pair) {
        statuses[pair]=batch.pairs[pair].status;
        std::copy(batch.pairs[pair].values.begin(),batch.pairs[pair].values.end(),values+pair*13);
    }
    return 0;
}

extern "C" __declspec(dllexport) int membrane_contact_distance(
    const double* segment,const double* triangle,double radius,double* output) {
    if (!output) return -1;
    auto result=membrane::contact::distance(segment,triangle,radius);
    if (result.status>=0) std::copy(result.values.begin(),result.values.end(),output);
    return result.status;
}

// Shapes are 3x3 row-major fine-corner barycentrics in the three controls.
// All outputs remain untouched unless a regular smooth branch is certified.
extern "C" __declspec(dllexport) int membrane_embedded_contact_distance(
    const double* segment,const double* controls,const double* shape,double radius,
    double* output,double* gradient,double* hessian) {
    if(!output || !gradient || !hessian) return -1;
    const auto result=membrane::embedded_contact::distance(segment,controls,shape,radius);
    if(result.status==0) {
        std::copy(result.values.begin(),result.values.end(),output);
        std::copy(result.gradient.begin(),result.gradient.end(),gradient);
        std::copy(result.hessian.begin(),result.hessian.end(),hessian);
    }
    return result.status;
}
