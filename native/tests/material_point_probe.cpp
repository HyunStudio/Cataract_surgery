// Test-only ABI; not linked into the application.
#include "../material_point_contact.h"
extern "C" __declspec(dllexport) int point_query(const double* segment,const double* q,const double* b,double r,
    double* values,double* gradient,double* hessian) {
    if(!values || !gradient || !hessian) return -1;
    const auto answer=membrane::material_point_contact::distance(segment,q,b,r);
    if(answer.status==0) {
        std::copy(answer.values.begin(),answer.values.end(),values);
        std::copy(answer.gradient.begin(),answer.gradient.end(),gradient);
        std::copy(answer.hessian.begin(),answer.hessian.end(),hessian);
    }
    return answer.status;
}
extern "C" __declspec(dllexport) int point_change(const double* old,const double* before,const double* after,
    const double* b,double t,const double* axis,double r,double dual,double rho,double* result) {
    membrane::merit::Interval change;
    if(!membrane::material_point_contact::change(old,before,after,b,t,axis,r,dual,rho,change)) return 1;
    result[0]=membrane::merit::lower_double(change);result[1]=membrane::merit::upper_double(change);return 0;
}
