// Isolated late-line observer. Not linked into the application.
#include <fstream>
#include <iomanip>
#include <vector>
static void trace_contact_line(const std::vector<double>& x,const std::vector<double>& y,const std::vector<double>& dual,
                               double rho,int iteration,double fraction,double slope,double change,double work,bool valid) {
    if(iteration<245) return;
    std::ofstream out(".tools/native/fem-contact-trace.json");out<<std::setprecision(17);
    out<<"{\"iteration\":"<<iteration<<",\"rho\":"<<rho<<",\"fraction\":"<<fraction<<",\"slope\":"<<slope<<",\"change\":"<<change<<",\"work\":"<<work<<",\"valid\":"<<(valid?"true":"false");
    auto array=[&](const char* key,const std::vector<double>& v) {out<<",\""<<key<<"\":[";for(size_t i=0;i<v.size();++i) {if(i) out<<',';out<<v[i];}out<<']';};
    array("x",x);array("y",y);array("dual",dual);out<<'}';
}
#define FEM_CONTACT_TRACE
#include "../membrane_fem.cpp"
