#include "contact_distance.h"

extern "C" __declspec(dllexport) int membrane_contact_distance(
    const double* segment,const double* triangle,double radius,double* output) {
    if (!output) return -1;
    auto result=membrane::contact::distance(segment,triangle,radius);
    if (result.status>=0) std::copy(result.values.begin(),result.values.end(),output);
    return result.status;
}
