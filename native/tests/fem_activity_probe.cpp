// Count exact private helper calls only in this isolated qualification DLL.
static int query_calls=0,merit_calls=0;
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
