#include "contact_guard.h"
extern "C" __declspec(dllexport) int membrane_guard_motion(int n,const double* previous,const double* current,
    int faces,const int* triangles,int bodies,const int* kinds,const double* packets,int budget,double gap,double* stats) {
    return membrane::guard::check(n,previous,current,faces,triangles,bodies,kinds,packets,budget,gap,stats);
}

// Separate entry point preserves the legacy caller's eight-double buffer.
extern "C" __declspec(dllexport) int membrane_guard_motion_witness(int n,const double* previous,const double* current,
    int faces,const int* triangles,int bodies,const int* kinds,const double* packets,int budget,double gap,double* stats,double* witness) {
    if (!witness) return -1;
    return membrane::guard::check(n,previous,current,faces,triangles,bodies,kinds,packets,budget,gap,stats,witness);
}
