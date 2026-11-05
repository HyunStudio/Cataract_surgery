// Count exact private helper calls only in this isolated qualification DLL.
static int query_calls=0,merit_calls=0,field_calls=0;
static void observe_temporal_field(){++field_calls;}
#define FEM_TEMPORAL_FIELD_OBSERVER
static void observe_contact_query(bool merit) {if(merit) ++merit_calls;else ++query_calls;}
#define FEM_CONTACT_OBSERVER
#include "../membrane_fem.cpp"

FEM_EXPORT int fem_activity_probe(const double* xyz,const double* next,const double* body,
                                  const double* shape,double dual_value,double rho,double* result) {
    membrane::numeric::Scope environment;
    query_calls=merit_calls=0;
    const int nodes[3]{0,1,2};
    const double gradients[6]{-1.,1.,0.,-1.,0.,1.},areas[1]{.5};
    Problem problem;problem.mu=2.;problem.lambda=3.;problem.mass={1.,1.,1.};
    problem.predicted.assign(xyz,xyz+9);
    if(!membrane_fem::cells(3,1,nodes,gradients,areas,problem.cells)) return -1;
    Vec x(xyz,xyz+9),y(next,next+9),dual{dual_value};
    FineContacts contacts{1,1,nodes,shape,body};ContactState state,candidate;
    double change=0.;const bool evaluated=contacts.evaluate(problem,x,dual,rho,state);
    const bool compared=evaluated && contacts.evaluate(problem,y,dual,rho,candidate) && contacts.difference(problem,x,y,dual,rho,state,candidate,change);
    result[0]=query_calls;result[1]=merit_calls;result[2]=change;
    result[3]=evaluated?state.updated[0]:-1.;result[4]=evaluated?state.penetration:-1.;
    result[5]=0.;if(evaluated) for(size_t i=81;i<state.blocks.size();++i) result[5]=std::max(result[5],std::abs(state.blocks[i]));
    return compared?0:2;
}

// Isolated chain-rule probe; never linked into the product extension.
FEM_EXPORT int fem_time_contact_probe(const double* previous,const double* xyz,const double* body,const double* shape,
                                      double time,double dual,double rho,double* gradient,double* hessian) {
    membrane::numeric::Scope environment;
    if(!previous || !xyz || !body || !shape || !gradient || !hessian || !std::isfinite(time) || time<=0. || time>1. ||
       !std::isfinite(dual) || dual<0. || !std::isfinite(rho) || rho<=0.) return -1;
    for(int k=0;k<9;++k) if(!std::isfinite(previous[k]) || std::abs(previous[k])>16.) return -1;
    const int nodes[3]{0,1,2};Problem problem;problem.mu=2.;problem.lambda=3.;problem.mass={1.,1.,1.};
    problem.predicted.assign(xyz,xyz+9);Vec x(xyz,xyz+9);ContactState state;
    FineContacts contacts{1,1,nodes,shape,body,1,previous,&time};
    if(!contacts.evaluate(problem,x,Vec{dual},rho,state)) return 2;
    std::copy(state.gradient.begin(),state.gradient.end(),gradient);
    std::copy(state.blocks.begin(),state.blocks.end(),hessian);return 0;
}
// Independent chain-rule observation of the material-point/time combination.
FEM_EXPORT int fem_time_point_contact_probe(const double* previous,const double* xyz,const double* body,const double* shape,
                                            double time,double dual,double rho,double* gradient,double* hessian) {
    membrane::numeric::Scope environment;
    if(!previous || !xyz || !body || !shape || !gradient || !hessian || !std::isfinite(time) || time<=0. || time>1. ||
       !std::isfinite(dual) || dual<0. || !std::isfinite(rho) || rho<=0.) return -1;
    for(int k=0;k<9;++k) if(!std::isfinite(previous[k]) || std::abs(previous[k])>16.) return -1;
    const int nodes[3]{0,1,2};Problem problem;problem.mu=2.;problem.lambda=3.;problem.mass={1.,1.,1.};
    problem.predicted.assign(xyz,xyz+9);Vec x(xyz,xyz+9);ContactState state;
    FineContacts contacts{1,1,nodes,shape,body,1,previous,&time,true,true};
    if(!contacts.evaluate(problem,x,Vec{dual},rho,state)) return 2;
    std::copy(state.gradient.begin(),state.gradient.end(),gradient);
    std::copy(state.blocks.begin(),state.blocks.end(),hessian);return 0;
}
FEM_EXPORT int fem_time_merit_probe(const double* previous,const double* before,const double* after,const double* shape,
                                   double time,const double* body,double radius,double dual,double rho,double* output) {
    membrane::numeric::Scope environment;
    if(!output) return -1;
    membrane::merit::Interval change;
    if(!membrane::fem_trajectory_merit::contact_change(previous,before,after,shape,time,body,radius,dual,rho,change)) return 1;
    output[0]=membrane::merit::lower_double(change);output[1]=membrane::merit::upper_double(change);return 0;
}

// Isolated physical reaction/geometry checks; no new product ABI.
FEM_EXPORT int fem_physical_zero_probe(double height,double dual,int physical,int bad,double radius,int* counts,double* output) {
    membrane::numeric::Scope environment;query_calls=merit_calls=field_calls=0;
    double xyz[9]{0.,0.,0.,1.,0.,0.,0.,0.,1.};
    if(bad==2)xyz[0]=std::numeric_limits<double>::quiet_NaN();
    const int nodes[3]{0,1,2};const double gradients[6]{-1.,1.,0.,-1.,0.,1.},areas[1]{.5},time=.5;
    double shape[9]{1.,0.,0.,0.,1.,0.,0.,0.,1.};
    if(bad==1) {std::fill(shape,shape+9,0.);shape[0]=shape[3]=shape[6]=1.;}
    const double body[7]{.3,height,.3,.3,height,.3,radius};
    Problem problem;problem.mu=2.;problem.lambda=3.;problem.mass={1.,1.,1.};problem.predicted.assign(xyz,xyz+9);
    if(!membrane_fem::cells(3,1,nodes,gradients,areas,problem.cells)) return -1;
    Vec x(xyz,xyz+9);FineContacts contacts{1,1,nodes,shape,body,1,xyz,&time};ContactState state;
    const bool valid=contacts.evaluate(problem,x,Vec{dual},1.,state,physical!=0);
    counts[0]=query_calls;counts[1]=field_calls;
    if(valid) {output[0]=0.;for(double v:state.gradient)output[0]=std::max(output[0],std::abs(v));output[1]=state.penetration;output[2]=state.complementarity;output[3]=state.updated[0];}
    return valid?0:2;
}

FEM_EXPORT int fem_field_regular_probe(const double* previous,const double* end,const double* shape,double time) {
    membrane::numeric::Scope environment;
    return membrane::fem_trajectory_merit::regular(previous,end,shape,time)?1:0;
}
