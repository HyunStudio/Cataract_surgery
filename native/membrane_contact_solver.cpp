#include "membrane_contact_solver.h"
#include "contact_guard.h"

extern "C" __declspec(dllexport) int membrane_solve_contact(
    int n,const double* predicted,double* output,const double* inverse,int edges,
    const int* a,const int* b,const double* rest,double alpha,int faces,const int* triangles,
    int bodies,const double* capsules,int budget,double force_tol,double gap_tol,double comp_tol,
    double* multipliers,double* stats) {
    membrane::numeric::Scope environment;
    if (stats) {
        std::fill(stats,stats+12,0.);
        std::fill(stats,stats+4,std::numeric_limits<double>::infinity());
        stats[9]=std::numeric_limits<double>::infinity();
    }
    try { return membrane::coupled::solve(n,predicted,output,inverse,edges,a,b,rest,alpha,faces,triangles,
                                          bodies,capsules,budget,force_tol,gap_tol,comp_tol,multipliers,stats); }
    catch (...) { return 2; }
}

// Collocation contact only. The caller must still certify the complete motion.
// Layer-major dual layout: (layer*faces+face)*bodies+body.
static int solve_trajectory_with_anatomy(
    int n,const double* predicted,double* output,const double* inverse,int edges,
    const int* a,const int* b,const double* rest,double alpha,int faces,const int* triangles,
    int bodies,const int* kinds,const double* packets,const double* previous,int layers,const double* times,
    int budget,double force_tol,double gap_tol,double comp_tol,double* multipliers,double* stats,
    int anatomy_count=0,const int* anatomy_vertices=nullptr,const double* anatomy=nullptr) {
    membrane::numeric::Scope environment;
    if (stats) {
        std::fill(stats,stats+12,0.);
        std::fill(stats,stats+4,std::numeric_limits<double>::infinity());
        stats[9]=std::numeric_limits<double>::infinity();
    }
    try {
        if (!times || layers<1 || layers>16 || faces<0 || faces>16384 || bodies<0 || bodies>64 ||
            faces*bodies*layers>65536) return -1;
        double last=0;
        for (int l=0;l<layers;++l) {
            if (!std::isfinite(times[l]) || !(times[l]>last) || times[l]>1) return -1;
            last=times[l];
        }
        if (last!=1) return -1;
        double validation[8];
        if (membrane::guard::check(n,previous,previous,0,nullptr,bodies,kinds,packets,0,gap_tol,validation)!=0) return -1;
        std::vector<double> capsules(7*bodies*layers);
        for (int b=0;b<bodies;++b) {
            membrane::guard::Motion motion; motion.init(packets+41*b,kinds[b]);
            for (int l=0;l<layers;++l) {
                int offset=7*(l*bodies+b);
                for (int end=0;end<2;++end) {
                    auto point=motion.sample(end,times[l]);
                    for (int k=0;k<3;++k) capsules[offset+3*end+k]=static_cast<double>(point[k]);
                }
                capsules[offset+6]=packets[41*b+12];
            }
        }
        return membrane::coupled::solve(n,predicted,output,inverse,edges,a,b,rest,alpha,faces,triangles,
            bodies,capsules.data(),budget,force_tol,gap_tol,comp_tol,multipliers,stats,layers,previous,times,anatomy_count,anatomy_vertices,anatomy);
    } catch (...) { return 2; }
}

extern "C" __declspec(dllexport) int membrane_solve_trajectory(
    int n,const double* predicted,double* output,const double* inverse,int edges,
    const int* a,const int* b,const double* rest,double alpha,int faces,const int* triangles,
    int bodies,const int* kinds,const double* packets,const double* previous,int layers,const double* times,
    int budget,double force_tol,double gap_tol,double comp_tol,double* multipliers,double* stats) {
    return solve_trajectory_with_anatomy(n,predicted,output,inverse,edges,a,b,rest,alpha,faces,triangles,bodies,kinds,
        packets,previous,layers,times,budget,force_tol,gap_tol,comp_tol,multipliers,stats);
}

// Old layer-major tool reactions followed by one reaction per rigid constraint.
// Each anatomy record is triangle9, radius, physical sample time in (0,1].
extern "C" __declspec(dllexport) int membrane_solve_trajectory_anatomy(
    int n,const double* predicted,double* output,const double* inverse,int edges,
    const int* a,const int* b,const double* rest,double alpha,int faces,const int* triangles,
    int bodies,const int* kinds,const double* packets,const double* previous,int layers,const double* times,
    int anatomy_count,const int* anatomy_vertices,const double* anatomy,
    int budget,double force_tol,double gap_tol,double comp_tol,double* multipliers,double* stats) {
    return solve_trajectory_with_anatomy(n,predicted,output,inverse,edges,a,b,rest,alpha,faces,triangles,bodies,kinds,
        packets,previous,layers,times,budget,force_tol,gap_tol,comp_tol,multipliers,stats,anatomy_count,anatomy_vertices,anatomy);
}
