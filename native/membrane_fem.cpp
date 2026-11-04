// Standalone embedded membrane energy and implicit Euler candidate solve.
// No contact/CCD, bending, fracture propagation or clinical material calibration.
#include "membrane_fem.h"
#include <Eigen/SparseCholesky>
#include <algorithm>

#if defined(_WIN32)
#define FEM_EXPORT extern "C" __declspec(dllexport)
#else
#define FEM_EXPORT extern "C" __attribute__((visibility("default")))
#endif
namespace {
using membrane_fem::Cell;
using membrane_fem::Vec;
double norm(const Vec& x) {double result=0.;for(double v:x) result=std::max(result,std::abs(v));return result;}
double dot(const Vec& x,const Vec& y) {double result=0.;for(size_t i=0;i<x.size();++i) result+=x[i]*y[i];return result;}
bool material(double mu,double lambda) {return std::isfinite(mu) && mu>0. && std::isfinite(lambda) && lambda>=0.;}

class SparseCells {
    using Matrix=Eigen::SparseMatrix<double>;
    struct Entry {int offset,cell,row,col;};
    struct Pending {int row,col,cell,local_row,local_col;};
    std::vector<int> coordinates,diagonals;
    std::vector<Entry> entries;
    Matrix matrix;
    Eigen::SimplicialLDLT<Matrix> ldlt;
    Eigen::VectorXd rhs,answer;
public:
    SparseCells(int n,const std::vector<Cell>& cells,const Vec& mass) {
        std::vector<int> map(n*3,-1);
        for(int k=0;k<n*3;++k) if(mass[k/3]>0.) {map[k]=static_cast<int>(coordinates.size());coordinates.push_back(k);}
        const int size=static_cast<int>(coordinates.size());
        matrix.resize(size,size);rhs.resize(size);answer.resize(size);
        if(!size) return;
        std::vector<Eigen::Triplet<double>> pattern;
        std::vector<Pending> pending;
        for(int i=0;i<size;++i) pattern.emplace_back(i,i,0.);
        for(size_t k=0;k<cells.size();++k) for(int r=0;r<9;++r) for(int c=0;c<9;++c) {
            const int row=map[cells[k].node[r/3]*3+r%3],col=map[cells[k].node[c/3]*3+c%3];
            if(row<0 || col<0 || row<col) continue;
            pattern.emplace_back(row,col,0.);pending.push_back({row,col,static_cast<int>(k),r,c});
        }
        matrix.setFromTriplets(pattern.begin(),pattern.end());matrix.makeCompressed();
        auto offset=[&](int row,int col) {
            const int begin=matrix.outerIndexPtr()[col],end=matrix.outerIndexPtr()[col+1];
            return static_cast<int>(std::lower_bound(matrix.innerIndexPtr()+begin,matrix.innerIndexPtr()+end,row)-matrix.innerIndexPtr());
        };
        for(int i=0;i<size;++i) diagonals.push_back(offset(i,i));
        for(const auto& p:pending) entries.push_back({offset(p.row,p.col),p.cell,p.local_row,p.local_col});
        ldlt.analyzePattern(matrix);
    }
    int factor(const Vec& blocks,const Vec& mass,double damping,const Vec& metric) {
        if(coordinates.empty()) return 0;
        std::fill(matrix.valuePtr(),matrix.valuePtr()+matrix.nonZeros(),0.);
        for(size_t i=0;i<coordinates.size();++i) matrix.valuePtr()[diagonals[i]]=mass[coordinates[i]/3]+damping*metric[coordinates[i]];
        for(const auto& entry:entries) matrix.valuePtr()[entry.offset]+=blocks[entry.cell*81+entry.row*9+entry.col];
        for(Eigen::Index k=0;k<matrix.nonZeros();++k) if(!std::isfinite(matrix.valuePtr()[k])) return 2;
        ldlt.factorize(matrix);
        if(ldlt.info()!=Eigen::Success) return 4;
        bool negative=false;
        for(double pivot:ldlt.vectorD()) {
            if(!std::isfinite(pivot)) return 2;
            if(pivot==0.) return 4;
            if(pivot<0.) negative=true;
        }
        return negative ? 3 : 0;
    }
    bool direction(const Vec& gradient,Vec& output,double& residual) {
        std::fill(output.begin(),output.end(),0.);residual=0.;
        if(coordinates.empty()) return true;
        for(size_t i=0;i<coordinates.size();++i) rhs[i]=-gradient[coordinates[i]];
        answer=ldlt.solve(rhs);
        if(ldlt.info()!=Eigen::Success || !answer.allFinite()) return false;
        const Eigen::VectorXd error=matrix.selfadjointView<Eigen::Lower>()*answer-rhs;
        const double scale=rhs.stableNorm();
        residual=scale>0. ? error.stableNorm()/scale : error.stableNorm();
        if(!std::isfinite(residual) || residual>1e-5) return false;
        for(size_t i=0;i<coordinates.size();++i) output[coordinates[i]]=answer[i];
        return true;
    }
};
struct Problem {
    Vec predicted,mass;
    std::vector<Cell> cells;
    double mu,lambda;
    bool evaluate(const Vec& x,double& energy,Vec& gradient,Vec* blocks=nullptr) const {
        if(!membrane_fem::evaluate(x,cells,mu,lambda,energy,gradient,blocks)) return false;
        for(size_t k=0;k<x.size();++k) {
            const double delta=x[k]-predicted[k];energy+=.5*mass[k/3]*delta*delta;
            gradient[k]=mass[k/3]>0. ? gradient[k]+mass[k/3]*delta : 0.;
        }
        return std::isfinite(energy) && std::all_of(gradient.begin(),gradient.end(),[](double v){return std::isfinite(v);});
    }
    bool difference(const Vec& x,const Vec& y,double& change) const {
        double elastic=0.;
        if(!membrane_fem::difference(x,y,cells,mu,lambda,elastic)) return false;
        long double total=elastic;
        for(size_t k=0;k<x.size();++k) {
            const double delta=y[k]-x[k];
            total+=mass[k/3]*((x[k]-predicted[k])*delta+.5*delta*delta);
        }
        change=static_cast<double>(total);
        return std::isfinite(change);
    }
};
int solve(int n,double* output,const double* inverse,int count,const int* nodes,const double* gradients,
          const double* areas,double mu,double lambda,double dt,int budget,double tolerance,double* stats) {
    if(!output || !inverse || !stats || !material(mu,lambda) || !std::isfinite(dt) || dt<1e-6 || dt>.1 ||
       budget<0 || budget>1000 || !std::isfinite(tolerance) || tolerance<=0.) return -1;
    Problem problem;
    if(!membrane_fem::cells(n,count,nodes,gradients,areas,problem.cells)) return -1;
    problem.predicted.assign(output,output+n*3);problem.mass.resize(n);problem.mu=mu;problem.lambda=lambda;
    for(int i=0;i<n;++i) {
        if(!std::isfinite(inverse[i]) || inverse[i]<0. || inverse[i]>1e12) return -1;
        problem.mass[i]=inverse[i]>0. ? 1./(inverse[i]*dt*dt) : 0.;
        if(!std::isfinite(problem.mass[i])) return -1;
        for(int j=0;j<3;++j) if(!std::isfinite(output[i*3+j]) || std::abs(output[i*3+j])>16.) return -1;
    }
    Vec x=problem.predicted,g,blocks,direction(n*3),trial(n*3),next_g,metric(n*3);
    double energy=0.,next_energy=0.,damping=1e-3,residual=0.,min_step=1.;
    int iterations=0,evaluations=1,factors=0,status=1;
    if(!problem.evaluate(x,energy,g,&blocks)) return 2;
    SparseCells system(n,problem.cells,problem.mass);
    for(;;) {
        if(norm(g)<=tolerance) {++factors;status=system.factor(blocks,problem.mass,0.,metric);break;}
        if(iterations>=budget) break;
        for(int k=0;k<n*3;++k) metric[k]=problem.mass[k/3]>0. ? problem.mass[k/3] : 1.;
        for(size_t cell=0;cell<problem.cells.size();++cell) for(int j=0;j<9;++j)
            metric[problem.cells[cell].node[j/3]*3+j%3]+=std::abs(blocks[cell*81+j*9+j]);
        bool solved=false;
        for(int attempt=0;attempt<12;++attempt) {
            ++factors;const int curvature=system.factor(blocks,problem.mass,damping,metric);
            if(curvature==2) break;
            if(curvature==0 && system.direction(g,direction,residual)) {solved=true;break;}
            damping=std::min(1e12,damping*10.);
        }
        if(!solved) {status=2;break;}
        const double slope=dot(g,direction);
        if(!(slope<0.) || !std::isfinite(slope)) {status=2;break;}
        bool accepted=false;double step=1.;
        for(int line=0;line<32;++line,step*=.5) {
            for(int k=0;k<n*3;++k) trial[k]=problem.mass[k/3]>0. ? x[k]+step*direction[k] : problem.predicted[k];
            ++evaluations;
            double change=0.;
            if(problem.evaluate(trial,next_energy,next_g) && problem.difference(x,trial,change) &&
               change<=1e-4*step*slope) {accepted=true;break;}
        }
        if(!accepted) {status=2;break;}
        min_step=std::min(min_step,step);
        damping=step>=.5 ? std::max(1e-12,damping*.25) : std::min(1e12,damping*4.);
        x.swap(trial);energy=next_energy;++iterations;
        ++evaluations;
        if(!problem.evaluate(x,energy,g,&blocks)) {status=2;break;}
    }
    stats[0]=energy;stats[1]=norm(g);stats[2]=iterations;stats[3]=evaluations;
    stats[4]=factors;stats[5]=residual;stats[6]=min_step;stats[7]=damping;
    if(status==0) std::copy(x.begin(),x.end(),output);
    return status;
}
} // namespace

FEM_EXPORT int membrane_fem_evaluate(int n,const double* x,int count,const int* nodes,const double* gradients,
                                    const double* areas,double mu,double lambda,double* energy,double* gradient,double* hessian) {
    if(!x || !energy || !gradient || !material(mu,lambda)) return -1;
    try {
        std::vector<Cell> cells;
        if(!membrane_fem::cells(n,count,nodes,gradients,areas,cells)) return -1;
        Vec values(x,x+n*3),g,blocks;double value;
        if(!membrane_fem::evaluate(values,cells,mu,lambda,value,g,hessian ? &blocks : nullptr)) return 2;
        *energy=value;std::copy(g.begin(),g.end(),gradient);
        if(hessian) std::copy(blocks.begin(),blocks.end(),hessian);
        return 0;
    } catch(...) {return 2;}
}
FEM_EXPORT int membrane_fem_solve(int n,double* output,const double* inverse,int count,const int* nodes,const double* gradients,
                                 const double* areas,double mu,double lambda,double dt,int budget,double tolerance,double* stats) {
    if(stats) {std::fill(stats,stats+8,0.);stats[0]=stats[1]=std::numeric_limits<double>::infinity();}
    try {return solve(n,output,inverse,count,nodes,gradients,areas,mu,lambda,dt,budget,tolerance,stats);}
    catch(...) {return 2;}
}
FEM_EXPORT int membrane_fem_difference(int n,const double* x,const double* y,int count,const int* nodes,const double* gradients,
                                      const double* areas,double mu,double lambda,double* change) {
    if(!x || !y || !change || !material(mu,lambda)) return -1;
    try {
        std::vector<Cell> cells;
        if(!membrane_fem::cells(n,count,nodes,gradients,areas,cells)) return -1;
        const Vec old(x,x+n*3),next(y,y+n*3);double result=0.;
        if(!membrane_fem::difference(old,next,cells,mu,lambda,result)) return 2;
        *change=result;return 0;
    } catch(...) {return 2;}
}
