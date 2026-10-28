// Test-only ABI. The product extension does not export these diagnostics.
#include "../contact_merit_difference.h"

extern "C" __declspec(dllexport) void merit_interpolate(
    const double* previous,const double* current,double time,double* result) {
    for (int k=0;k<9;++k) result[k]=membrane::merit::represented_coordinate(previous[k],current[k],time);
}

extern "C" __declspec(dllexport) int merit_contact_change(
    const double* before,const double* after,const double* axis,
    double radius,double multiplier,double penalty,double* result) {
    membrane::merit::Interval change;
    if (!membrane::merit::contact_change(before,after,axis,radius,multiplier,penalty,change)) return 1;
    result[0]=membrane::merit::lower_double(change);
    result[1]=membrane::merit::upper_double(change);
    return 0;
}

extern "C" __declspec(dllexport) int merit_edge_change(
    const double* before,const double* after,double rest,double stiffness,double* result) {
    membrane::merit::Interval change;
    if (!membrane::merit::edge_change(before,after,rest,stiffness,change)) return 1;
    result[0]=membrane::merit::lower_double(change);
    result[1]=membrane::merit::upper_double(change);
    return 0;
}

extern "C" __declspec(dllexport) int merit_contact_witness_change(
    const double* before,const double* after,const double* axis,const double* old_parameters,const double* new_parameters,
    double radius,double multiplier,double penalty,double* result) {
    membrane::merit::Parameters first{old_parameters[0],old_parameters[1],old_parameters[2]};
    membrane::merit::Parameters last{new_parameters[0],new_parameters[1],new_parameters[2]};
    membrane::merit::Interval change;
    if (!membrane::merit::bounded_contact_change(before,after,axis,radius,multiplier,penalty,first,last,change)) return 1;
    result[0]=membrane::merit::lower_double(change);
    result[1]=membrane::merit::upper_double(change);
    return 0;
}
