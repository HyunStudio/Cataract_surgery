// Isolated late-line observer. Not linked into the application.
#include <fstream>
#include <iomanip>
#include <vector>
static int first_trace=245;
static bool append_trace=false;
static void trace_contact_line(const std::vector<double>& x,const std::vector<double>& y,const std::vector<double>& dual,
                               double rho,int iteration,double fraction,double slope,double change,double work,bool valid) {
    if(iteration<first_trace) return;
    std::ofstream out(".tools/native/fem-contact-trace.json",append_trace ? std::ios::app : std::ios::out);out<<std::setprecision(17);
    out<<"{\"iteration\":"<<iteration<<",\"rho\":"<<rho<<",\"fraction\":"<<fraction<<",\"slope\":"<<slope<<",\"change\":"<<change<<",\"work\":"<<work<<",\"valid\":"<<(valid?"true":"false");
    auto array=[&](const char* key,const std::vector<double>& v) {out<<",\""<<key<<"\":[";for(size_t i=0;i<v.size();++i) {if(i) out<<',';out<<v[i];}out<<']';};
    array("x",x);array("y",y);array("dual",dual);out<<'}';if(append_trace) out<<'\n';
}
#define FEM_CONTACT_TRACE
#include "../membrane_fem.cpp"
FEM_EXPORT int fem_trace_configure(int first,int append) {
    if(first<0 || first>1000 || (append!=0 && append!=1)) return -1;
    first_trace=first;append_trace=append!=0;
    std::ofstream clear(".tools/native/fem-contact-trace.json");return clear?0:2;
}
