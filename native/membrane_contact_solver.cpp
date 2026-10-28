#include "membrane_contact_solver.h"

extern "C" __declspec(dllexport) int membrane_solve_contact(
    int n,const double* predicted,double* output,const double* inverse,int edges,
    const int* a,const int* b,const double* rest,double alpha,int faces,const int* triangles,
    int bodies,const double* capsules,int budget,double force_tol,double gap_tol,double comp_tol,
    double* multipliers,double* stats) {
    if (stats) {
        std::fill(stats,stats+12,0.);
        std::fill(stats,stats+4,std::numeric_limits<double>::infinity());
        stats[9]=std::numeric_limits<double>::infinity();
    }
    try { return membrane::coupled::solve(n,predicted,output,inverse,edges,a,b,rest,alpha,faces,triangles,
                                          bodies,capsules,budget,force_tol,gap_tol,comp_tol,multipliers,stats); }
    catch (...) { return 2; }
}
