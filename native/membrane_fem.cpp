// Standalone embedded membrane energy and implicit Euler candidate solve.
// Static contact candidates; no CCD, bending, fracture or clinical calibration.
#include "membrane_fem.h"
#include <Eigen/SparseCholesky>
#include <Eigen/Cholesky>
#include <Eigen/QR>
#include <algorithm>
#include "embedded_contact.h"
#include "contact_merit_difference.h"
#include "contact_guard.h"
#include "fem_trajectory_merit.h"
#include "material_point_contact.h"

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
bool inertia(double inverse,double dt,double& coefficient) {
    if(!std::isfinite(inverse) || inverse<0.) return false;
    if(inverse==0.) {coefficient=0.;return true;}
    // Positive retained material is not bounded by an arbitrary inverse cap.
    // Reject unrepresentable physical inertia rather than clamp or erase it.
    coefficient=1./(inverse*dt*dt);
    return std::isfinite(coefficient) && coefficient>0.;
}

class SparseCells {
    using Matrix=Eigen::SparseMatrix<double>;
    struct Entry {int offset,cell,row,col;};
    struct Pending {int row,col,cell,local_row,local_col;};
    struct Augment {int offset;double value;};
    std::vector<int> coordinates,diagonals;
    std::vector<Entry> entries;
    std::vector<Augment> augmentation;
    Matrix matrix;
    Eigen::SimplicialLDLT<Matrix> ldlt;
    Eigen::VectorXd rhs,answer;
public:
    SparseCells(int n,const std::vector<Cell>& cells,const Vec& mass,const Eigen::MatrixXd* constraints=nullptr) {
        std::vector<int> map(n*3,-1);
        for(int k=0;k<n*3;++k) if(mass[k/3]>0.) {map[k]=static_cast<int>(coordinates.size());coordinates.push_back(k);}
        const int size=static_cast<int>(coordinates.size());
        matrix.resize(size,size);rhs.resize(size);answer.resize(size);
        if(!size) return;
        std::vector<Eigen::Triplet<double>> pattern;
        std::vector<Pending> pending;
        struct Normal {int row,col;double value;};
        std::vector<Normal> normals;
        for(int i=0;i<size;++i) pattern.emplace_back(i,i,0.);
        for(size_t k=0;k<cells.size();++k) for(int r=0;r<9;++r) for(int c=0;c<9;++c) {
            const int row=map[cells[k].node[r/3]*3+r%3],col=map[cells[k].node[c/3]*3+c%3];
            if(row<0 || col<0 || row<col) continue;
            pattern.emplace_back(row,col,0.);pending.push_back({row,col,static_cast<int>(k),r,c});
        }
        if(constraints) for(Eigen::Index r=0;r<constraints->rows();++r) {
            std::vector<std::pair<int,double>> row;
            for(int c=0;c<size;++c) if((*constraints)(r,c)!=0.) row.push_back({c,(*constraints)(r,c)});
            for(const auto& a:row) for(const auto& b:row) if(a.first>=b.first) {
                pattern.emplace_back(a.first,b.first,0.);normals.push_back({a.first,b.first,a.second*b.second});
            }
        }
        matrix.setFromTriplets(pattern.begin(),pattern.end());matrix.makeCompressed();
        auto offset=[&](int row,int col) {
            const int begin=matrix.outerIndexPtr()[col],end=matrix.outerIndexPtr()[col+1];
            return static_cast<int>(std::lower_bound(matrix.innerIndexPtr()+begin,matrix.innerIndexPtr()+end,row)-matrix.innerIndexPtr());
        };
        for(int i=0;i<size;++i) diagonals.push_back(offset(i,i));
        for(const auto& p:pending) entries.push_back({offset(p.row,p.col),p.cell,p.local_row,p.local_col});
        for(const auto& p:normals) augmentation.push_back({offset(p.row,p.col),p.value});
        ldlt.analyzePattern(matrix);
    }
    int factor(const Vec& blocks,const Vec& mass,double damping,const Vec& metric,double rho=0.) {
        if(coordinates.empty()) return 0;
        std::fill(matrix.valuePtr(),matrix.valuePtr()+matrix.nonZeros(),0.);
        for(size_t i=0;i<coordinates.size();++i) matrix.valuePtr()[diagonals[i]]=mass[coordinates[i]/3]+damping*metric[coordinates[i]];
        for(const auto& entry:entries) matrix.valuePtr()[entry.offset]+=blocks[entry.cell*81+entry.row*9+entry.col];
        for(const auto& entry:augmentation) matrix.valuePtr()[entry.offset]+=rho*entry.value;
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
    bool solve_matrix(const Eigen::MatrixXd& input,Eigen::MatrixXd& output,double& residual) {
        output=ldlt.solve(input);residual=0.;
        if(ldlt.info()!=Eigen::Success || !output.allFinite()) return false;
        const Eigen::MatrixXd error=matrix.selfadjointView<Eigen::Lower>()*output-input;
        for(Eigen::Index j=0;j<input.cols();++j) {
            const double scale=input.col(j).stableNorm();
            const double value=scale>0. ? error.col(j).stableNorm()/scale : error.col(j).stableNorm();
            if(!std::isfinite(value) || value>1e-5) return false;
            residual=std::max(residual,value);
        }
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
        if(!inertia(inverse[i],dt,problem.mass[i])) return -1;
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

bool positive(const Eigen::LDLT<Eigen::MatrixXd>& factor) {
    if(factor.info()!=Eigen::Success) return false;
    for(double value:factor.vectorD()) if(!std::isfinite(value) || !(value>0.)) return false;
    return true;
}
int solve_grasp(int n,double* output,const double* inverse,int count,const int* nodes,const double* gradients,
                const double* areas,double mu,double lambda,double dt,int budget,double tolerance,double gap_tolerance,
                int grips,const int* grip_nodes,const double* weights,const double* targets,double* reaction,double* stats) {
    if(!output || !inverse || !stats || grips<0 || grips>2 || (grips && (!grip_nodes || !weights || !targets || !reaction)) ||
       !material(mu,lambda) || !std::isfinite(dt) || dt<1e-6 || dt>.1 || budget<0 || budget>1000 ||
       !std::isfinite(tolerance) || tolerance<=0. || !std::isfinite(gap_tolerance) || gap_tolerance<=0.) return -1;
    if(!grips) {const int status=solve(n,output,inverse,count,nodes,gradients,areas,mu,lambda,dt,budget,tolerance,stats);stats[8]=0.;return status;}
    Problem problem;
    if(!membrane_fem::cells(n,count,nodes,gradients,areas,problem.cells)) return -1;
    problem.predicted.assign(output,output+n*3);problem.mass.resize(n);problem.mu=mu;problem.lambda=lambda;
    std::vector<int> free,map(n*3,-1);
    for(int i=0;i<n;++i) {
        if(!inertia(inverse[i],dt,problem.mass[i])) return -1;
        for(int j=0;j<3;++j) {
            const int k=i*3+j;
            if(!std::isfinite(output[k]) || std::abs(output[k])>16.) return -1;
            if(inverse[i]>0.) {map[k]=static_cast<int>(free.size());free.push_back(k);}
        }
    }
    const int rows=grips*3,size=static_cast<int>(free.size());
    Eigen::MatrixXd a=Eigen::MatrixXd::Zero(rows,size);
    Eigen::VectorXd target(rows);
    for(int grip=0;grip<grips;++grip) {
        double sum=0.;
        for(int j=0;j<3;++j) {
            const int id=grip_nodes[grip*3+j];const double value=weights[grip*3+j];
            if(id<0 || id>=n || !std::isfinite(value) || value<0. || value>1.) return -1;
            sum+=value;
        }
        if(!(sum>0.) || std::abs(sum-1.)>64.*std::numeric_limits<double>::epsilon()) return -1;
        for(int axis=0;axis<3;++axis) {
            const int r=grip*3+axis;
            if(!std::isfinite(targets[r]) || std::abs(targets[r])>16.) return -1;
            target[r]=targets[r];
            for(int j=0;j<3;++j) {
                const int k=grip_nodes[grip*3+j]*3+axis;const double w=weights[grip*3+j]/sum;
                if(map[k]>=0) a(r,map[k])+=w;
                else target[r]-=w*problem.predicted[k];
            }
        }
    }
    if(!size) return 4;
    const Eigen::MatrixXd gram=a*a.transpose();
    const Eigen::LDLT<Eigen::MatrixXd> gram_factor(gram);
    if(!positive(gram_factor)) return 4;
    Eigen::VectorXd q(size);
    Eigen::MatrixXd weighted=a;
    for(int j=0;j<size;++j) {q[j]=problem.predicted[free[j]];weighted.col(j)/=problem.mass[free[j]/3];}
    const Eigen::MatrixXd projection_gram=weighted*a.transpose();
    const Eigen::LDLT<Eigen::MatrixXd> projection_factor(projection_gram);
    if(!positive(projection_factor)) return 4;
    const Eigen::VectorXd initial_gap=target-a*q;
    const Eigen::VectorXd projection=weighted.transpose()*projection_factor.solve(initial_gap);
    q+=projection;
    const double projection_gap=(a*q-target).lpNorm<Eigen::Infinity>();
    if(!q.allFinite() || !std::isfinite(projection_gap) || projection_gap>gap_tolerance) return 2;
    Vec x=problem.predicted,g,blocks,metric(n*3),trial(n*3),next_g,direction(n*3);
    for(int j=0;j<size;++j) x[free[j]]=q[j];
    double energy=0.,next_energy=0.,damping=1e-3,rho=1.,linear_residual=0.,schur_residual=0.,minimum_step=1.;
    double force=std::numeric_limits<double>::infinity(),gap=projection_gap;
    int completed=0,evaluations=1,factors=0,status=1;
    if(!problem.evaluate(x,energy,g,&blocks)) return 2;
    SparseCells system(n,problem.cells,problem.mass,&a);
    Eigen::VectorXd dual=Eigen::VectorXd::Zero(rows),gf(size),rhs_gap(rows);
    for(;;) {
        for(int j=0;j<size;++j) {q[j]=x[free[j]];gf[j]=g[free[j]];}
        dual=-gram_factor.solve(a*gf);
        const Eigen::VectorXd balance=gf+a.transpose()*dual;
        rhs_gap=target-a*q;force=balance.lpNorm<Eigen::Infinity>();gap=rhs_gap.lpNorm<Eigen::Infinity>();
        if(!dual.allFinite() || !std::isfinite(force) || !std::isfinite(gap)) {status=2;break;}
        if(force<=tolerance && gap<=gap_tolerance) {
            for(int attempt=0;attempt<12;++attempt) {
                ++factors;status=system.factor(blocks,problem.mass,0.,metric,rho);
                if(status==0 || status==2) break;
                rho=std::min(1e12,rho*10.);
            }
            break;
        }
        if(completed>=budget) break;
        for(int k=0;k<n*3;++k) metric[k]=problem.mass[k/3]>0. ? problem.mass[k/3] : 1.;
        for(size_t cell=0;cell<problem.cells.size();++cell) for(int j=0;j<9;++j)
            metric[problem.cells[cell].node[j/3]*3+j%3]+=std::abs(blocks[cell*81+j*9+j]);
        bool solved=false;
        for(int attempt=0;attempt<12;++attempt) {
            ++factors;const int curvature=system.factor(blocks,problem.mass,damping,metric,rho);
            if(curvature==2) break;
            if(curvature==0) {
                Eigen::MatrixXd rhs(size,rows+1),answer;
                rhs.col(0)=-gf+rho*a.transpose()*rhs_gap;rhs.rightCols(rows)=a.transpose();
                if(system.solve_matrix(rhs,answer,linear_residual)) {
                    const Eigen::MatrixXd z=answer.rightCols(rows),schur=a*z;
                    const Eigen::LDLT<Eigen::MatrixXd> factor(schur);
                    if(positive(factor)) {
                        const Eigen::VectorXd b=a*answer.col(0)-rhs_gap;
                        const Eigen::VectorXd multipliers=factor.solve(b);
                        schur_residual=(schur*multipliers-b).stableNorm()/std::max(1.,b.stableNorm());
                        const Eigen::VectorXd delta=answer.col(0)-z*multipliers;
                        if(delta.allFinite() && std::isfinite(schur_residual) && schur_residual<=1e-8) {
                            std::fill(direction.begin(),direction.end(),0.);
                            for(int j=0;j<size;++j) direction[free[j]]=delta[j];
                            solved=true;break;
                        }
                    }
                }
            }
            rho=std::min(1e12,rho*10.);damping=std::min(1e12,damping*10.);
        }
        if(!solved) {status=2;break;}
        Eigen::VectorXd free_direction(size);
        for(int j=0;j<size;++j) free_direction[j]=direction[free[j]];
        // The fixed-dual Lagrangian equals the objective on the feasible
        // manifold. Its tangent slope removes normal reaction roundoff from
        // the comparison without changing any final force/gap/curvature gate.
        const double slope=balance.dot(free_direction);
        if(!(slope<0.) || !std::isfinite(slope)) {status=2;break;}
        bool accepted=false;double step=1.;
        for(int line=0;line<32;++line,step*=.5) {
            for(int k=0;k<n*3;++k) trial[k]=problem.mass[k/3]>0. ? x[k]+step*direction[k] : problem.predicted[k];
            for(int j=0;j<size;++j) q[j]=trial[free[j]];
            ++evaluations;double change=0.;
            Eigen::VectorXd delta(size);
            for(int j=0;j<size;++j) delta[j]=trial[free[j]]-x[free[j]];
            if((a*q-target).lpNorm<Eigen::Infinity>()<=gap_tolerance && problem.evaluate(trial,next_energy,next_g) &&
               problem.difference(x,trial,change)) {
                const double lagrangian_change=change+dual.dot(a*delta);
                if(std::isfinite(lagrangian_change) && lagrangian_change<=1e-4*step*slope) {accepted=true;break;}
            }
        }
        if(!accepted) {status=2;break;}
        minimum_step=std::min(minimum_step,step);
        damping=step>=.5 ? std::max(1e-12,damping*.25) : std::min(1e12,damping*4.);
        x.swap(trial);energy=next_energy;++completed;++evaluations;
        if(!problem.evaluate(x,energy,g,&blocks)) {status=2;break;}
    }
    stats[0]=energy;stats[1]=force;stats[2]=completed;stats[3]=evaluations;stats[4]=factors;stats[5]=linear_residual;
    stats[6]=minimum_step;stats[7]=damping;stats[8]=gap;stats[9]=rho;stats[10]=projection_gap;stats[11]=schur_residual;
    if(status==0) {std::copy(x.begin(),x.end(),output);std::copy(dual.data(),dual.data()+rows,reaction);}
    return status;
}
#include "membrane_fem_contact.inc"
} // namespace

FEM_EXPORT int membrane_fem_evaluate(int n,const double* x,int count,const int* nodes,const double* gradients,
                                    const double* areas,double mu,double lambda,double* energy,double* gradient,double* hessian) {
    membrane::numeric::Scope environment;
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
    membrane::numeric::Scope environment;
    if(stats) {std::fill(stats,stats+8,0.);stats[0]=stats[1]=std::numeric_limits<double>::infinity();}
    try {return solve(n,output,inverse,count,nodes,gradients,areas,mu,lambda,dt,budget,tolerance,stats);}
    catch(...) {return 2;}
}
FEM_EXPORT int membrane_fem_difference(int n,const double* x,const double* y,int count,const int* nodes,const double* gradients,
                                      const double* areas,double mu,double lambda,double* change) {
    membrane::numeric::Scope environment;
    if(!x || !y || !change || !material(mu,lambda)) return -1;
    try {
        std::vector<Cell> cells;
        if(!membrane_fem::cells(n,count,nodes,gradients,areas,cells)) return -1;
        const Vec old(x,x+n*3),next(y,y+n*3);double result=0.;
        if(!membrane_fem::difference(old,next,cells,mu,lambda,result)) return 2;
        *change=result;return 0;
    } catch(...) {return 2;}
}
FEM_EXPORT int membrane_fem_solve_grasp(int n,double* output,const double* inverse,int count,const int* nodes,const double* gradients,
                                       const double* areas,double mu,double lambda,double dt,int budget,double tolerance,double gap_tolerance,
                                       int grips,const int* grip_nodes,const double* weights,const double* targets,double* reaction,double* stats) {
    membrane::numeric::Scope environment;
    if(stats) {std::fill(stats,stats+12,0.);stats[0]=stats[1]=stats[8]=std::numeric_limits<double>::infinity();}
    try {return solve_grasp(n,output,inverse,count,nodes,gradients,areas,mu,lambda,dt,budget,tolerance,gap_tolerance,
                           grips,grip_nodes,weights,targets,reaction,stats);}
    catch(...) {return 2;}
}

FEM_EXPORT int membrane_fem_solve_contact(int n,double* output,const double* inverse,int count,const int* nodes,const double* gradients,
    const double* areas,double mu,double lambda,double dt,int budget,double tolerance,double gap_tolerance,double comp_tolerance,
    int grips,const int* grip_nodes,const double* weights,const double* targets,double* reaction,
    int faces,const int* face_nodes,const double* face_weights,int bodies,const double* capsules,double* dual,double* stats) {
    membrane::numeric::Scope environment;
    if(stats) {std::fill(stats,stats+16,0.);stats[0]=stats[1]=stats[8]=stats[12]=stats[13]=std::numeric_limits<double>::infinity();}
    try {return solve_contact(n,output,inverse,count,nodes,gradients,areas,mu,lambda,dt,budget,tolerance,gap_tolerance,comp_tolerance,
                             grips,grip_nodes,weights,targets,reaction,faces,face_nodes,face_weights,bodies,capsules,dual,stats);}
    catch(...) {return 2;}
}

FEM_EXPORT int membrane_fem_solve_precise_contact(int n,double* output,const double* inverse,int count,const int* nodes,const double* gradients,
    const double* areas,double mu,double lambda,double dt,int budget,double tolerance,double gap_tolerance,double comp_tolerance,
    int grips,const int* grip_nodes,const double* weights,const double* targets,double* reaction,
    int faces,const int* face_nodes,const double* face_weights,int bodies,const double* capsules,double* dual,double* stats) {
    membrane::numeric::Scope environment;
    if(stats) {std::fill(stats,stats+16,0.);stats[0]=stats[1]=stats[8]=stats[12]=stats[13]=std::numeric_limits<double>::infinity();}
    try {return solve_contact(n,output,inverse,count,nodes,gradients,areas,mu,lambda,dt,budget,tolerance,gap_tolerance,comp_tolerance,
                             grips,grip_nodes,weights,targets,reaction,faces,face_nodes,face_weights,bodies,capsules,dual,stats,1,nullptr,nullptr,nullptr,nullptr,1.,true);}
    catch(...) {return 2;}
}

// Fixed material-point normal constraints only. Complete original surface and
// full motion clearance must be independently checked before publication.
FEM_EXPORT int membrane_fem_solve_material_points(int n,double* output,const double* inverse,int count,const int* nodes,const double* gradients,
    const double* areas,double mu,double lambda,double dt,int budget,double tolerance,double gap_tolerance,double comp_tolerance,
    int grips,const int* grip_nodes,const double* weights,const double* targets,double* reaction,
    int faces,const int* face_nodes,const double* face_weights,int bodies,const double* capsules,double* dual,double* stats) {
    membrane::numeric::Scope environment;
    if(stats) {std::fill(stats,stats+16,0.);stats[0]=stats[1]=stats[8]=stats[12]=stats[13]=std::numeric_limits<double>::infinity();}
    try {return solve_contact(n,output,inverse,count,nodes,gradients,areas,mu,lambda,dt,budget,tolerance,gap_tolerance,comp_tolerance,
        grips,grip_nodes,weights,targets,reaction,faces,face_nodes,face_weights,bodies,capsules,dual,stats,1,nullptr,nullptr,nullptr,nullptr,1.,true,true);}
    catch(...) {return 2;}
}

// Layer-major collocation candidate only; complete motion clearance remains a
// separate mandatory acceptance condition in the caller.
static int solve_recorded_trajectory(int n,double* output,const double* inverse,int count,const int* nodes,const double* gradients,
    const double* areas,double mu,double lambda,double dt,int budget,double tolerance,double gap_tolerance,double comp_tolerance,
    int grips,const int* grip_nodes,const double* weights,const double* targets,double* reaction,
    int faces,const int* face_nodes,const double* face_weights,int bodies,const int* kinds,const double* packets,
    const double* previous,int layers,const double* times,double* dual,double* stats,
    const double* initial,const double* multiplier_seed,bool seeded,double initial_penalty=1.) {
    membrane::numeric::Scope environment;
    if(stats) {std::fill(stats,stats+16,0.);stats[0]=stats[1]=stats[8]=stats[12]=stats[13]=std::numeric_limits<double>::infinity();}
    try {
        if(!output || !inverse || !stats || !times || layers<1 || layers>16 || faces<0 || faces>8192 || bodies<0 || bodies>64 ||
           faces*bodies*layers>65536) return -1;
        if(seeded && (!initial || (faces*bodies && !multiplier_seed) || !std::isfinite(initial_penalty) || initial_penalty<1. || initial_penalty>1e12)) return -1;
        double last=0.;
        for(int layer=0;layer<layers;++layer) {
            if(!std::isfinite(times[layer]) || !(times[layer]>last) || times[layer]>1.) return -1;
            last=times[layer];
        }
        if(last!=1.) return -1;
        double validation[8];
        // Reuse the actual recorded-pose validation without a clearance query.
        if(membrane::guard::check(n,previous,previous,0,nullptr,bodies,kinds,packets,0,gap_tolerance,validation)!=0) return -1;
        for(int node=0;node<n;++node) if(inverse[node]==0.)
            for(int axis=0;axis<3;++axis) if(previous[node*3+axis]!=output[node*3+axis]) return -1;
        Vec capsules(size_t(bodies)*layers*7);
        for(int body=0;body<bodies;++body) {
            membrane::guard::Motion motion;motion.init(packets+body*41,kinds[body]);
            for(int layer=0;layer<layers;++layer) {
                const int off=(layer*bodies+body)*7;
                for(int end=0;end<2;++end) {
                    const auto point=motion.sample(end,times[layer]);
                    for(int axis=0;axis<3;++axis) capsules[off+end*3+axis]=static_cast<double>(point[axis]);
                }
                capsules[off+6]=packets[body*41+12];
            }
        }
        return solve_contact(n,output,inverse,count,nodes,gradients,areas,mu,lambda,dt,budget,tolerance,gap_tolerance,comp_tolerance,
            grips,grip_nodes,weights,targets,reaction,faces,face_nodes,face_weights,bodies,capsules.data(),dual,stats,layers,layers==1 ? nullptr : previous,layers==1 ? nullptr : times,initial,multiplier_seed,initial_penalty);
    } catch(...) {return 2;}
}
FEM_EXPORT int membrane_fem_solve_trajectory(int n,double* output,const double* inverse,int count,const int* nodes,const double* gradients,
    const double* areas,double mu,double lambda,double dt,int budget,double tolerance,double gap_tolerance,double comp_tolerance,
    int grips,const int* grip_nodes,const double* weights,const double* targets,double* reaction,
    int faces,const int* face_nodes,const double* face_weights,int bodies,const int* kinds,const double* packets,
    const double* previous,int layers,const double* times,double* dual,double* stats) {
    return solve_recorded_trajectory(n,output,inverse,count,nodes,gradients,areas,mu,lambda,dt,budget,tolerance,gap_tolerance,comp_tolerance,
        grips,grip_nodes,weights,targets,reaction,faces,face_nodes,face_weights,bodies,kinds,packets,previous,layers,times,dual,stats,nullptr,nullptr,false);
}
FEM_EXPORT int membrane_fem_solve_trajectory_seeded(int n,double* output,const double* inverse,int count,const int* nodes,const double* gradients,
    const double* areas,double mu,double lambda,double dt,int budget,double tolerance,double gap_tolerance,double comp_tolerance,
    int grips,const int* grip_nodes,const double* weights,const double* targets,double* reaction,
    int faces,const int* face_nodes,const double* face_weights,int bodies,const int* kinds,const double* packets,
    const double* previous,int layers,const double* times,double* dual,double* stats,const double* initial,const double* multiplier_seed,double initial_penalty) {
    return solve_recorded_trajectory(n,output,inverse,count,nodes,gradients,areas,mu,lambda,dt,budget,tolerance,gap_tolerance,comp_tolerance,
        grips,grip_nodes,weights,targets,reaction,faces,face_nodes,face_weights,bodies,kinds,packets,previous,layers,times,dual,stats,initial,multiplier_seed,true,initial_penalty);
}
