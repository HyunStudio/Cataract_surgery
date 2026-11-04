// Test-only ABI. The product extension does not export these diagnostics.
#include "../contact_merit_difference.h"
#include "../fem_trajectory_merit.h"

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

extern "C" __declspec(dllexport) int merit_point_contact_change(
    const double* before,const double* after,const double* triangle,
    double radius,double multiplier,double penalty,double* result) {
    membrane::merit::Interval change;
    if (!membrane::merit::point_contact_change(before,after,triangle,radius,multiplier,penalty,change)) return 1;
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

// Test-only comparison against the unchanged original literal certificate.
extern "C" __declspec(dllexport) int merit_temporal_hull_compare(
    const double* previous,const double* before,const double* after,double time,
    const double* axis,double radius,double dual,double rho,double* output) {
    membrane::numeric::Scope environment;
    namespace field=membrane::fem_trajectory_merit;
    const auto a=field::hull(previous,before,time),b=field::hull(previous,after,time);
    for(int j=0;j<3;++j) {output[j*2]=static_cast<double>(a[j].lo);output[j*2+1]=static_cast<double>(a[j].hi);output[6+j*2]=static_cast<double>(b[j].lo);output[7+j*2]=static_cast<double>(b[j].hi);}
    const bool original=field::inactive(previous,before,after,time,axis,radius,dual,rho);
    const bool cached=field::inactive_hulls(a,b,axis,radius,dual,rho);
    return int(original)+2*int(cached);
}
