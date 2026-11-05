// Test-only decomposition of an original-control endpoint merit increment.
// This diagnostic cannot accept a physical state and is not linked to Godot.
#include "../membrane_fem.h"
#include "../embedded_contact.h"
#include "../fem_trajectory_merit.h"
#define AUDIT_EXPORT extern "C" __declspec(dllexport)
AUDIT_EXPORT int audit_contact_step(const double* previous,const double* before,const double* after,
    const double* shape,const double* axis,double radius,double dual,double rho,double* output) {
    membrane::numeric::Scope environment;
    namespace field=membrane::fem_trajectory_merit;
    namespace m=membrane::merit;
    double triangle[9];
    for(int j=0;j<3;++j) {
        const long double sum=static_cast<long double>(shape[j*3])+shape[j*3+1]+shape[j*3+2];
        for(int a=0;a<3;++a) triangle[j*3+a]=static_cast<double>(static_cast<long double>(before[a])+
            (shape[j*3+1]*(static_cast<long double>(before[3+a])-before[a])+
             shape[j*3+2]*(static_cast<long double>(before[6+a])-before[a]))/sum);
    }
    const auto query=membrane::contact::distance(axis,triangle,radius);
    output[0]=query.status;output[1]=query.values[21];
    if(query.status!=0 && query.status!=3) return 1;
    const double r2=radius*radius;
    double g=query.values[0]/r2-1.,u=std::max(0.,dual-rho*g);
    const auto first=field::hull(previous,before,1.),last=field::hull(previous,after,1.);
    if(u==0. && field::inactive_hulls(first,first,axis,radius,dual,rho) &&
       field::inactive_hulls(first,last,axis,radius,dual,rho)) return 0;
    m::Interval gap,separation;
    if(!field::gap(previous,before,shape,1.,axis,radius,query,gap,separation)) return 2;
    const auto multiplier=m::positive(m::Interval(dual)-m::Interval(rho)*gap);
    u=static_cast<double>((multiplier.lo+multiplier.hi)/2);
    output[2]=u;output[3]=static_cast<double>((gap.lo+gap.hi)/2);
    if(u!=0.) {
        const auto exact=membrane::embedded_contact::distance(axis,before,shape,radius);
        output[4]=exact.status;
        if(exact.status!=0) return 3;
        for(int j=0;j<9;++j) output[5]-=u*exact.gradient[j]*(after[j]-before[j])/r2;
    }
    m::Interval change;
    if(!field::contact_change(previous,before,after,shape,1.,axis,radius,dual,rho,change)) return 4;
    output[6]=m::lower_double(change);output[7]=m::upper_double(change);
    return 0;
}
AUDIT_EXPORT int audit_cell_step(const double* before,const double* after,const double* basis,
    double area,double mu,double lambda,double* output) {
    membrane::numeric::Scope environment;
    const int nodes[3]={0,1,2};std::vector<membrane_fem::Cell> cells;
    if(!membrane_fem::cells(3,1,nodes,basis,&area,cells)) return 1;
    membrane_fem::Vec x(before,before+9),y(after,after+9),gradient;
    if(!membrane_fem::evaluate(x,cells,mu,lambda,output[0],gradient)) return 2;
    for(int j=0;j<9;++j) output[1]+=gradient[j]*(after[j]-before[j]);
    return membrane_fem::difference(x,y,cells,mu,lambda,output[2]) ? 0 : 3;
}
