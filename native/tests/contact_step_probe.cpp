// Test-only interface for the bounded local unilateral model, not a product ABI.
#include "../contact_step_model.h"
static int run(
    int n,int pairs,const double* h,const double* j,const double* force,
    const double* gap,const double* dual,double rho,const int* regular,int budget,
    double* output,double* stats,bool proposal) {
    using namespace membrane::step_model;
    if (n<1 || n>16 || pairs<0 || pairs>64) return -1;
    std::vector<Triplet> ht,jt;
    for (int a=0;a<n;++a) for (int b=0;b<n;++b) if (h[n*a+b]) ht.emplace_back(a,b,h[n*a+b]);
    for (int a=0;a<pairs;++a) for (int b=0;b<n;++b) if (j[n*a+b]) jt.emplace_back(a,b,j[n*a+b]);
    Matrix hl(n,n),rows(pairs,n); hl.setFromTriplets(ht.begin(),ht.end()); rows.setFromTriplets(jt.begin(),jt.end());
    auto result=solve(hl,rows,Eigen::Map<const Vector>(force,n),Eigen::Map<const Vector>(gap,pairs),
        Eigen::Map<const Vector>(dual,pairs),rho,std::vector<int>(regular,regular+pairs),budget,proposal);
    stats[0]=result.factors; stats[1]=result.residual; stats[2]=result.change_upper; stats[3]=result.restarts;
    if (!result.status || result.status==descent_proposal || result.status==unmodelled_proposal || result.status==raw_seed_proposal)
        std::copy(result.direction.data(),result.direction.data()+n,output);
    return result.status;
}
extern "C" __declspec(dllexport) int contact_step_probe(
    int n,int pairs,const double* h,const double* j,const double* force,
    const double* gap,const double* dual,double rho,const int* regular,int budget,
    double* output,double* stats) {
    return run(n,pairs,h,j,force,gap,dual,rho,regular,budget,output,stats,false);
}
extern "C" __declspec(dllexport) int contact_step_proposal(
    int n,int pairs,const double* h,const double* j,const double* force,
    const double* gap,const double* dual,double rho,const int* regular,int budget,
    double* output,double* stats) {
    return run(n,pairs,h,j,force,gap,dual,rho,regular,budget,output,stats,true);
}
