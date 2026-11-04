#pragma once
#include <array>
#include <cmath>
#include <limits>
#include <vector>

namespace membrane_fem {
struct Cell {
    std::array<int,3> node;
    std::array<double,3> gx, gy;
    double area;
};
using Vec = std::vector<double>;

inline bool cells(int n, int count, const int* nodes, const double* gradients,
                  const double* areas, std::vector<Cell>& result) {
    if (n<1 || n>4096 || count<0 || count>8192 || (count && (!nodes || !gradients || !areas))) return false;
    result.reserve(count);
    for (int k=0;k<count;++k) {
        Cell cell{};
        cell.area=areas[k];
        if (!(cell.area>0.) || !std::isfinite(cell.area)) return false;
        double sx=0., sy=0., scale=0., g00=0., g01=0., g11=0.;
        for (int j=0;j<3;++j) {
            cell.node[j]=nodes[k*3+j];
            cell.gx[j]=gradients[k*6+j]; cell.gy[j]=gradients[k*6+3+j];
            if (cell.node[j]<0 || cell.node[j]>=n || !std::isfinite(cell.gx[j]) || !std::isfinite(cell.gy[j])) return false;
            sx+=cell.gx[j]; sy+=cell.gy[j]; scale+=std::abs(cell.gx[j])+std::abs(cell.gy[j]);
            g00+=cell.gx[j]*cell.gx[j];g01+=cell.gx[j]*cell.gy[j];g11+=cell.gy[j]*cell.gy[j];
        }
        if (cell.node[0]==cell.node[1] || cell.node[1]==cell.node[2] || cell.node[2]==cell.node[0] ||
            !std::isfinite(g00*g11-g01*g01) || !(g00*g11-g01*g01>0.) ||
            std::abs(sx)>64.*std::numeric_limits<double>::epsilon()*scale ||
            std::abs(sy)>64.*std::numeric_limits<double>::epsilon()*scale) return false;
        // Preserve partition of unity in difference-form F evaluation.
        cell.gx[0]=-cell.gx[1]-cell.gx[2]; cell.gy[0]=-cell.gy[1]-cell.gy[2];
        result.push_back(cell);
    }
    return true;
}

inline bool evaluate(const Vec& x, const std::vector<Cell>& cells, double mu, double lambda,
                     double& energy, Vec& gradient, Vec* hessian=nullptr) {
    energy=0.;gradient.assign(x.size(),0.);
    if (hessian) hessian->assign(cells.size()*81,0.);
    for (double v:x) if (!std::isfinite(v) || std::abs(v)>16.) return false;
    for (size_t k=0;k<cells.size();++k) {
        const Cell& cell=cells[k];
        double fx[3]{},fy[3]{};
        for (int axis=0;axis<3;++axis) for (int j=1;j<3;++j) {
            const double delta=x[cell.node[j]*3+axis]-x[cell.node[0]*3+axis];
            fx[axis]+=delta*cell.gx[j]; fy[axis]+=delta*cell.gy[j];
        }
        double c00=0.,c01=0.,c11=0.;
        for (int a=0;a<3;++a) {c00+=fx[a]*fx[a];c01+=fx[a]*fy[a];c11+=fy[a]*fy[a];}
        const double det=c00*c11-c01*c01;
        if (!(det>1e-20) || !std::isfinite(det)) return false;
        const double logarithm=.5*std::log(det), coefficient=lambda*logarithm-mu;
        const double a00=c11/det,a01=-c01/det,a11=c00/det;
        double hx[3],hy[3];
        energy+=cell.area*(.5*mu*(c00+c11-2.-2.*logarithm)+.5*lambda*logarithm*logarithm);
        for (int a=0;a<3;++a) {
            hx[a]=fx[a]*a00+fy[a]*a01;hy[a]=fx[a]*a01+fy[a]*a11;
            const double px=mu*fx[a]+coefficient*hx[a],py=mu*fy[a]+coefficient*hy[a];
            for (int j=0;j<3;++j) gradient[cell.node[j]*3+a]+=cell.area*(px*cell.gx[j]+py*cell.gy[j]);
        }
        if (!hessian) continue;
        for (int j=0;j<3;++j) for (int axis=0;axis<3;++axis) {
            const double dx=cell.gx[j],dy=cell.gy[j];
            const double dc00=2.*fx[axis]*dx,dc01=fy[axis]*dx+fx[axis]*dy,dc11=2.*fy[axis]*dy;
            const double dl=hx[axis]*dx+hy[axis]*dy;
            for (int a=0;a<3;++a) {
                const double dhx=(a==axis ? dx*a00+dy*a01 : 0.)-
                    (hx[a]*dc00+hy[a]*dc01)*a00-(hx[a]*dc01+hy[a]*dc11)*a01;
                const double dhy=(a==axis ? dx*a01+dy*a11 : 0.)-
                    (hx[a]*dc00+hy[a]*dc01)*a01-(hx[a]*dc01+hy[a]*dc11)*a11;
                const double dpx=(a==axis ? mu*dx : 0.)+lambda*dl*hx[a]+coefficient*dhx;
                const double dpy=(a==axis ? mu*dy : 0.)+lambda*dl*hy[a]+coefficient*dhy;
                for (int i=0;i<3;++i)
                    (*hessian)[k*81+(i*3+a)*9+j*3+axis]=cell.area*(dpx*cell.gx[i]+dpy*cell.gy[i]);
            }
        }
    }
    if (!std::isfinite(energy)) return false;
    for (double v:gradient) if (!std::isfinite(v)) return false;
    if (hessian) for (double v:*hessian) if (!std::isfinite(v)) return false;
    return true;
}

// Algebraically identical energy difference, evaluated from increments rather
// than subtracting two nearly equal absolute energies near force convergence.
inline bool difference(const Vec& x, const Vec& y, const std::vector<Cell>& cells,
                       double mu, double lambda, double& change) {
    if(x.size()!=y.size()) return false;
    for(size_t k=0;k<x.size();++k)
        if(!std::isfinite(x[k]) || !std::isfinite(y[k]) || std::abs(x[k])>16. || std::abs(y[k])>16.) return false;
    long double total=0.;
    for(const Cell& cell:cells) {
        double fx[3]{},fy[3]{},dx[3]{},dy[3]{},nx[3]{},ny[3]{};
        for(int a=0;a<3;++a) for(int j=1;j<3;++j) {
            const int i=cell.node[j]*3+a,base=cell.node[0]*3+a;
            const double old=x[i]-x[base],next=y[i]-y[base];
            const double delta=(y[i]-x[i])-(y[base]-x[base]);
            fx[a]+=old*cell.gx[j];fy[a]+=old*cell.gy[j];
            nx[a]+=next*cell.gx[j];ny[a]+=next*cell.gy[j];
            dx[a]+=delta*cell.gx[j];dy[a]+=delta*cell.gy[j];
        }
        double c00=0.,c01=0.,c11=0.,n00=0.,n01=0.,n11=0.,d00=0.,d01=0.,d11=0.;
        for(int a=0;a<3;++a) {
            c00+=fx[a]*fx[a];c01+=fx[a]*fy[a];c11+=fy[a]*fy[a];
            n00+=nx[a]*nx[a];n01+=nx[a]*ny[a];n11+=ny[a]*ny[a];
            d00+=2.*fx[a]*dx[a]+dx[a]*dx[a];
            d01+=fx[a]*dy[a]+fy[a]*dx[a]+dx[a]*dy[a];
            d11+=2.*fy[a]*dy[a]+dy[a]*dy[a];
        }
        const double det=c00*c11-c01*c01,next_det=n00*n11-n01*n01;
        if(!(det>1e-20) || !(next_det>1e-20) || !std::isfinite(det) || !std::isfinite(next_det)) return false;
        const double det_change=c11*d00+c00*d11-2.*c01*d01+d00*d11-d01*d01;
        const double ratio=det_change/det;
        const double dl=std::abs(ratio)<.5 ? .5*std::log1p(ratio) : .5*(std::log(next_det)-std::log(det));
        const double logarithm=.5*std::log(det);
        total+=cell.area*(.5*mu*(d00+d11-2.*dl)+lambda*logarithm*dl+.5*lambda*dl*dl);
    }
    change=static_cast<double>(total);
    return std::isfinite(change);
}
} // namespace membrane_fem
