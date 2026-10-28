// Experimental bounded augmented-Lagrangian coupled substep. No engine dependency.
#pragma once
#include "contact_distance.h"
#include <Eigen/SparseCholesky>
#include <vector>

namespace membrane::coupled {
using Vector=Eigen::VectorXd;
using Matrix=Eigen::SparseMatrix<double>;
using Triplet=Eigen::Triplet<double>;
struct State {
    double energy=0,merit=0,penetration=0;
    Vector gradient,force,constraints,updated_dual;
    Matrix hessian,jacobian;
};

struct Problem {
    int n,edges,faces,bodies,size=0;
    const int *a,*b,*triangles;
    const double *rest,*capsules;
    double stiffness;
    Vector predicted,mass;
    std::vector<int> mapping,coordinates;
    int evaluations=0;

    Problem(int n_,const double* pred,const double* inverse,int e,const int* ea,const int* eb,
            const double* r,double alpha,int f,const int* tri,int nb,const double* body):
        n(n_),edges(e),faces(f),bodies(nb),a(ea),b(eb),triangles(tri),rest(r),capsules(body),
        stiffness(1/alpha),predicted(Eigen::Map<const Vector>(pred,3*n)),mass(n),mapping(3*n,-1) {
        for (int i=0;i<n;++i) {
            mass[i]=inverse[i]>0?1/inverse[i]:0;
            if (inverse[i]>0) for (int k=0;k<3;++k) {
                mapping[3*i+k]=size++; coordinates.push_back(3*i+k);
            }
        }
    }

    int geometry(const Vector& x,int pair,double& g,Vector& row) const {
        int face=pair/bodies,body=pair%bodies;
        double xyz[9];
        for (int j=0;j<3;++j) for (int k=0;k<3;++k) xyz[3*j+k]=x[3*triangles[3*face+j]+k];
        auto result=contact::distance(capsules+7*body,xyz,capsules[7*body+6]);
        if (result.status<0 || result.status==1 || result.status==2) return 4;
        double r=capsules[7*body+6]; g=result.values[0]/(r*r)-1;
        row.setZero(size);
        for (int j=0;j<3;++j) for (int k=0;k<3;++k) {
            int id=mapping[3*triangles[3*face+j]+k];
            if (id>=0) row[id]+=result.values[11+3*j+k]/(r*r);
        }
        return result.status==3?6:0; // caller may ignore an inactive ambiguous gradient
    }

    int evaluate(const Vector& x,const Vector& dual,double rho,State& out) {
        ++evaluations;
        out=State{}; out.force=Vector::Zero(size); out.gradient=Vector::Zero(size);
        int pairs=faces*bodies;
        out.constraints=Vector::Zero(pairs); out.updated_dual=Vector::Zero(pairs);
        std::vector<Triplet> h,j;
        h.reserve(size+36*edges);
        for (int i=0;i<n;++i) for (int axis=0;axis<3;++axis) {
            int k=3*i+axis;
            if (!std::isfinite(x[k]) || std::abs(x[k])>16) return 2;
            double delta=x[k]-predicted[k];
            out.energy+=.5*mass[i]*delta*delta;
            if (mapping[k]>=0) { out.force[mapping[k]]=mass[i]*delta; h.emplace_back(mapping[k],mapping[k],mass[i]); }
        }
        for (int e=0;e<edges;++e) {
            Eigen::Vector3d delta=x.segment<3>(3*a[e])-x.segment<3>(3*b[e]);
            double length=delta.norm();
            if (!(length>0) || !std::isfinite(length)) return 2;
            double c=length-rest[e],t=c/length;
            Eigen::Vector3d normal=delta/length,force=stiffness*c*normal;
            Eigen::Matrix3d block=stiffness*(t*Eigen::Matrix3d::Identity()+(1-t)*normal*normal.transpose());
            out.energy+=.5*stiffness*c*c;
            if (!block.allFinite() || !force.allFinite()) return 2;
            int ends[2]={a[e],b[e]};
            for (int end=0;end<2;++end) for (int axis=0;axis<3;++axis) {
                int row=mapping[3*ends[end]+axis];
                if (row<0) continue;
                out.force[row]+=(end?-1:1)*force[axis];
                for (int other=0;other<2;++other) for (int k=0;k<3;++k) {
                    int col=mapping[3*ends[other]+k];
                    if (col>=0) h.emplace_back(row,col,(end==other?1:-1)*block(axis,k));
                }
            }
        }
        out.merit=out.energy; out.gradient=out.force;
        Vector row(size);
        for (int pair=0;pair<pairs;++pair) {
            double g=0; int status=geometry(x,pair,g,row);
            if (status!=0 && status!=6) return status;
            out.constraints[pair]=g;
            double r=capsules[7*(pair%bodies)+6];
            out.penetration=std::max(out.penetration,r*(1-std::sqrt(std::max(0.,g+1))));
            double multiplier=std::max(0.,dual[pair]-rho*g);
            out.updated_dual[pair]=multiplier;
            if (multiplier>0) {
                if (status==6) return 4;
                if (row.squaredNorm()==0 && g<0) return 3;
                out.merit+=-dual[pair]*g+.5*rho*g*g;
                out.gradient-=multiplier*row;
                for (int k=0;k<size;++k) if (row[k]!=0) j.emplace_back(pair,k,row[k]);
            } else out.merit-=.5*dual[pair]*dual[pair]/rho;
        }
        out.hessian.resize(size,size); out.hessian.setFromTriplets(h.begin(),h.end());
        out.jacobian.resize(pairs,size); out.jacobian.setFromTriplets(j.begin(),j.end());
        if (!std::isfinite(out.energy) || !std::isfinite(out.merit) || !out.gradient.allFinite() ||
            !out.constraints.allFinite() || !out.updated_dual.allFinite()) return 2;
        return 0;
    }

    // Sufficient numerical screen: positive H_L+rho*J'J is positive on the
    // active tangent space. Contact Hessians are finite-differenced, not exact.
    int curvature(const Vector& x,const State& state,const Vector& dual,double rho) const {
        if (!size) return 0;
        std::vector<Triplet> entries;
        for (int col=0;col<state.hessian.outerSize();++col)
            for (Matrix::InnerIterator it(state.hessian,col);it;++it) entries.emplace_back(it.row(),it.col(),it.value());
        for (int pair=0;pair<dual.size();++pair) if (dual[pair]>0) {
            int face=pair/bodies;
            Eigen::Matrix<double,9,9> local=Eigen::Matrix<double,9,9>::Zero();
            for (int j=0;j<3;++j) for (int axis=0;axis<3;++axis) {
                int coordinate=3*triangles[3*face+j]+axis;
                if (mapping[coordinate]<0) continue;
                double step=1e-6*std::max(1.,std::abs(x[coordinate]));
                Vector plus=x,minus=x,gp(size),gm(size); plus[coordinate]+=step; minus[coordinate]-=step;
                double ignored=0;
                if (geometry(plus,pair,ignored,gp)!=0 || geometry(minus,pair,ignored,gm)!=0) return 4;
                for (int k=0;k<3;++k) for (int b=0;b<3;++b) {
                    int row=mapping[3*triangles[3*face+k]+b];
                    if (row>=0) local(3*k+b,3*j+axis)=(gp[row]-gm[row])/(2*step);
                }
            }
            local=.5*(local+local.transpose()).eval();
            for (int i=0;i<9;++i) for (int j=0;j<9;++j) {
                int row=mapping[3*triangles[3*face+i/3]+i%3],col=mapping[3*triangles[3*face+j/3]+j%3];
                if (row>=0 && col>=0) entries.emplace_back(row,col,-dual[pair]*local(i,j));
            }
        }
        Matrix lagrangian(size,size); lagrangian.setFromTriplets(entries.begin(),entries.end());
        Matrix normal=state.jacobian.transpose()*state.jacobian;
        for (int attempt=0;attempt<8;++attempt,rho*=10) {
            Matrix matrix=lagrangian+rho*normal;
            Eigen::SimplicialLDLT<Matrix> factor; factor.compute(matrix);
            if (factor.info()==Eigen::Success && factor.vectorD().allFinite() && (factor.vectorD().array()>0).all()) return 0;
        }
        return 5;
    }
};

inline int solve(int n,const double* predicted,double* output,const double* inverse,int edges,
                 const int* a,const int* b,const double* rest,double alpha,int faces,const int* triangles,
                 int bodies,const double* capsules,int budget,double force_tol,double gap_tol,double comp_tol,
                 double* multipliers,double* stats) {
    if (!predicted || !output || !inverse || !stats || n<1 || n>4096 || edges<0 || edges>16384 ||
        faces<0 || faces>16384 || bodies<0 || bodies>64 || faces*bodies>65536 ||
        (edges && (!a || !b || !rest)) || (faces && !triangles) || (bodies && !capsules) ||
        (faces*bodies && !multipliers) || budget<0 || budget>1000 || !(alpha>0) || !std::isfinite(1/alpha) ||
        !std::isfinite(alpha) || !(force_tol>0) || !std::isfinite(force_tol) ||
        !(gap_tol>0) || !std::isfinite(gap_tol) || !(comp_tol>0) || !std::isfinite(comp_tol)) return -1;
    for (int i=0;i<n;++i) {
        if (!std::isfinite(inverse[i]) || inverse[i]<0 || inverse[i]>1e12 ||
            (inverse[i]>0 && !std::isfinite(1/inverse[i]))) return -1;
        for (int k=0;k<3;++k) if (!std::isfinite(predicted[3*i+k]) || !std::isfinite(output[3*i+k]) ||
            std::abs(predicted[3*i+k])>16 || std::abs(output[3*i+k])>16 ||
            (inverse[i]==0 && predicted[3*i+k]!=output[3*i+k])) return -1;
    }
    for (int e=0;e<edges;++e) if (a[e]<0 || b[e]<0 || a[e]>=n || b[e]>=n || a[e]==b[e] ||
        !(rest[e]>0) || !std::isfinite(rest[e])) return -1;
    for (int f=0;f<faces;++f) {
        for (int k=0;k<3;++k) if (triangles[3*f+k]<0 || triangles[3*f+k]>=n) return -1;
        if (triangles[3*f]==triangles[3*f+1] || triangles[3*f]==triangles[3*f+2] || triangles[3*f+1]==triangles[3*f+2]) return -1;
    }
    double radius=.1;
    for (int b=0;b<bodies;++b) {
        for (int k=0;k<6;++k) if (!std::isfinite(capsules[7*b+k]) || std::abs(capsules[7*b+k])>16) return -1;
        double r=capsules[7*b+6]; if (!(r>0) || r>.3 || !std::isfinite(r)) return -1;
        radius=std::min(radius,r);
    }
    Problem problem(n,predicted,inverse,edges,a,b,rest,alpha,faces,triangles,bodies,capsules);
    Vector x=Eigen::Map<Vector>(output,3*n),dual=Vector::Zero(faces*bodies);
    double rho=std::clamp((1/alpha+problem.mass.maxCoeff())*radius*radius,1e-12,1e6);
    int status=1,outer=0,inner_total=0,factors=0;
    double last_violation=std::numeric_limits<double>::infinity();
    State state;
    for (;;) {
        status=problem.evaluate(x,dual,rho,state);
        if (status) break;
        double station=state.gradient.size()?state.gradient.lpNorm<Eigen::Infinity>():0;
        double comp=state.updated_dual.size()?(state.updated_dual.array()*state.constraints.array()).abs().maxCoeff():0;
        stats[0]=state.energy; stats[1]=station; stats[2]=state.penetration; stats[3]=comp;
        stats[4]=outer; stats[5]=problem.evaluations; stats[6]=rho; stats[7]=inner_total; stats[8]=factors;
        if (station<=force_tol && state.penetration<=gap_tol && comp<=comp_tol) {
            status=problem.curvature(x,state,state.updated_dual,rho);
            if (!status) {
                std::copy(x.data(),x.data()+3*n,output);
                if (dual.size()) std::copy(state.updated_dual.data(),state.updated_dual.data()+dual.size(),multipliers);
            }
            break;
        }
        if (outer>=budget) { status=1; break; }
        for (int inner=0;inner<32;++inner) {
            ++inner_total;
            if (station<=force_tol*.25) break;
            if (!problem.size) { status=3; break; }
            Matrix base=state.hessian+rho*(state.jacobian.transpose()*state.jacobian);
            Vector direction(problem.size); bool solved=false; double damping=1e-8;
            double norm=state.gradient.stableNorm();
            if (!std::isfinite(norm) || !(norm>0)) { status=2; break; }
            for (int attempt=0;attempt<12;++attempt,damping*=10) {
                Matrix matrix=base;
                for (int i=0;i<problem.size;++i) matrix.coeffRef(i,i)+=damping*std::max(1.,std::abs(base.coeff(i,i)));
                Eigen::SimplicialLDLT<Matrix> factor; factor.compute(matrix); ++factors;
                if (factor.info()!=Eigen::Success || !factor.vectorD().allFinite() || !(factor.vectorD().array()>0).all()) continue;
                direction=factor.solve(-state.gradient);
                double numerator=(matrix*direction+state.gradient).stableNorm();
                double residual=std::isfinite(numerator)?numerator/norm:std::numeric_limits<double>::infinity();
                stats[9]=residual;
                double slope=state.gradient.dot(direction);
                if (direction.allFinite() && std::isfinite(residual) && residual<=1e-5 && std::isfinite(slope) && slope<0) { solved=true; break; }
            }
            if (!solved) { status=2; break; }
            bool accepted=false; State trial; Vector candidate;
            double slope=state.gradient.dot(direction),step=1;
            for (int line=0;line<32;++line,step*=.5) {
                candidate=x;
                for (int i=0;i<problem.size;++i) candidate[problem.coordinates[i]]+=step*direction[i];
                int code=problem.evaluate(candidate,dual,rho,trial);
                if (!code && trial.merit<=state.merit+1e-4*step*slope) { accepted=true; break; }
            }
            if (!accepted) { status=2; break; }
            x.swap(candidate); state=std::move(trial);
            station=state.gradient.lpNorm<Eigen::Infinity>();
        }
        if (status) break;
        dual=state.updated_dual;
        if (state.penetration>last_violation*.25) rho=std::min(1e12,rho*10);
        last_violation=state.penetration;
        ++outer;
    }
    stats[4]=outer; stats[5]=problem.evaluations; stats[6]=rho; stats[7]=inner_total; stats[8]=factors;
    return status;
}
} // namespace membrane::coupled
