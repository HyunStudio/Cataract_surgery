// Bounded local PHR activation model. A successful model is only a proposal;
// actual nonlinear merit, KKT and final curvature checks remain mandatory.
#pragma once
#include "contact_merit_difference.h"
#include <Eigen/SparseCholesky>
#include <vector>

namespace membrane::step_model {
constexpr int descent_proposal=6; // certified model descent; not model convergence
constexpr int unmodelled_proposal=7; // supported-part descent; full nonlinear check required
constexpr int raw_seed_proposal=8; // negative slope only; no model-change certificate
using Vector=Eigen::VectorXd;
using Matrix=Eigen::SparseMatrix<double>;
using Triplet=Eigen::Triplet<double>;
struct Result {
    int status=1,factors=0,restarts=0;
    double residual=std::numeric_limits<double>::infinity();
    double change_upper=std::numeric_limits<double>::infinity();
    Vector direction;
};
inline bool finite(const Matrix& matrix) {
    for (int col=0;col<matrix.outerSize();++col)
        for (Matrix::InnerIterator it(matrix,col);it;++it) if (!std::isfinite(it.value())) return false;
    return true;
}
inline Matrix selected(const Matrix& rows,const std::vector<unsigned char>& active) {
    std::vector<Triplet> entries;
    entries.reserve(rows.nonZeros());
    for (int col=0;col<rows.outerSize();++col)
        for (Matrix::InnerIterator it(rows,col);it;++it)
            if (active[it.row()]) entries.emplace_back(it.row(),it.col(),it.value());
    Matrix result(rows.rows(),rows.cols()); result.setFromTriplets(entries.begin(),entries.end());
    return result;
}
// Sufficient model coercivity after an indefinite working-set factorization.
// Strict positive diagonal dominance of H_L+D makes every added rho*J'J
// positive definite too. This does not certify the physical final Hessian.
inline bool coercive_damping(const Matrix& hl,const Vector& scale,double current,double& damping) {
    using merit::Interval;
    std::vector<Interval> deficit(scale.size());
    for (int col=0;col<hl.outerSize();++col)
        for (Matrix::InnerIterator it(hl,col);it;++it) {
            if (it.row()==it.col()) deficit[it.row()]=deficit[it.row()]-Interval(it.value());
            else deficit[it.row()]=deficit[it.row()]+Interval(std::abs(it.value()));
        }
    merit::Quad required=0;
    for (int k=0;k<scale.size();++k) {
        auto ratio=merit::divide(deficit[k],Interval(scale[k]));
        if (!merit::finite(ratio)) return false;
        required=std::max(required,ratio.hi);
    }
    damping=current*10;
    // At most the finite double exponent range; no extra factorization or
    // physical merit evaluation is spent while choosing a model coefficient.
    for (int growth=0;growth<320;++growth,damping*=10) {
        if (!std::isfinite(damping)) return false;
        if (!(merit::Quad(damping)>required)) continue;
        bool strict=true;
        for (int k=0;k<scale.size();++k) {
            double diagonal=damping*scale[k];
            if (!std::isfinite(diagonal)) return false;
            if (!((Interval(diagonal)-deficit[k]).lo>0)) strict=false;
        }
        if (strict) return true;
    }
    return false;
}
// Outward interval of m(d)-m(0), using the frozen model coefficients.
inline merit::Interval change(const Matrix& hl,const Matrix& rows,const Vector& force,
        const Vector& gap,const Vector& dual,double rho,const Vector& damping,const Vector& d) {
    using merit::Interval;
    Interval value(0),half(merit::Quad(.5));
    for (int k=0;k<d.size();++k)
        value=value+Interval(force[k])*Interval(d[k])+half*Interval(damping[k])*merit::square(Interval(d[k]));
    for (int col=0;col<hl.outerSize();++col)
        for (Matrix::InnerIterator it(hl,col);it;++it)
            value=value+half*Interval(it.value())*Interval(d[it.row()])*Interval(d[it.col()]);
    std::vector<Interval> shift(gap.size());
    for (int col=0;col<rows.outerSize();++col)
        for (Matrix::InnerIterator it(rows,col);it;++it)
            shift[it.row()]=shift[it.row()]+Interval(it.value())*Interval(d[it.col()]);
    for (int i=0;i<gap.size();++i) {
        Interval before=Interval(dual[i])-Interval(rho)*Interval(gap[i]);
        Interval moved=-Interval(rho)*shift[i],after=before+moved;
        if (before.hi<=0 && after.hi<=0) continue;
        Interval difference=before.lo>0 && after.lo>0?moved*(after+before):
            merit::square(merit::positive(after))-merit::square(merit::positive(before));
        value=value+merit::divide(difference,Interval(2)*Interval(rho));
    }
    return value;
}
inline Result solve(const Matrix& input_hl,const Matrix& rows,const Vector& force,
        const Vector& gap,const Vector& dual,double rho,const std::vector<int>& regular,int budget=12,bool proposal=false) {
    Result out;
    int n=force.size(),pairs=gap.size();
    if (n<1 || n>12288 || pairs>65536 || input_hl.rows()!=n || input_hl.cols()!=n ||
        rows.cols()!=n || rows.rows()!=pairs || dual.size()!=pairs || int(regular.size())!=pairs ||
        !force.allFinite() || !gap.allFinite() || !dual.allFinite() || (dual.array()<0).any() ||
        !finite(input_hl) || !std::isfinite(rho) || !(rho>0) || budget<0 || budget>12) {
        out.status=-1; return out;
    }
    bool unmodelled=false;
    std::vector<unsigned char> available(pairs);
    Vector intercept=dual-rho*gap;
    for (int i=0;i<pairs;++i) {
        if (regular[i]!=0 && regular[i]!=1) { out.status=-1; return out; }
        available[i]=regular[i]; unmodelled=unmodelled || !regular[i];
        if (!std::isfinite(intercept[i])) {
            // Finite nonnegative dual minus an overflowed positive rho*gap
            // is provably inactive. Its missing affine coefficient belongs
            // to the unmodelled part; never turn positive overflow inactive.
            if (std::isinf(intercept[i]) && intercept[i]<0 && gap[i]>0) {
                intercept[i]=0; available[i]=0; unmodelled=true;
            } else { out.status=2; return out; }
        }
    }
    Matrix filtered;
    if (unmodelled) filtered=selected(rows,available);
    const Matrix& usable=unmodelled?filtered:rows;
    if (!finite(usable)) { out.status=-1; return out; }
    if (unmodelled && !proposal) { out.status=4; return out; }
    // Average before adding to avoid overflowing finite equal coefficients.
    // Preserve equal entries exactly, including the smallest subnormals.
    Matrix hl=input_hl*.5+Matrix(input_hl.transpose())*.5;
    for (int col=0;col<input_hl.outerSize();++col)
        for (Matrix::InnerIterator it(input_hl,col);it;++it)
            if (it.value()==input_hl.coeff(it.col(),it.row())) hl.coeffRef(it.row(),it.col())=it.value();
    std::vector<unsigned char> initial(pairs);
    for (int i=0;i<pairs;++i) {
        initial[i]=intercept[i]>0;
        if (initial[i] && !available[i]) { out.status=4; return out; }
    }
    Vector original_gradient=force-usable.transpose()*intercept.cwiseMax(0.);
    double norm=original_gradient.stableNorm();
    if (!std::isfinite(norm) || !(norm>0)) { out.status=3; return out; }
    Matrix current_rows=selected(usable,initial);
    Matrix initial_base=hl+rho*(current_rows.transpose()*current_rows);
    Vector scale(n);
    // A diagonalized normal penalty also damps unconstrained tangent modes.
    // Proposal damping follows H_L; retain the full rho*J'J in every solve.
    // Exact auxiliary-model mode keeps its original frozen metric.
    for (int k=0;k<n;++k)
        scale[k]=std::max(1.,std::abs(proposal?hl.coeff(k,k):initial_base.coeff(k,k)));
    if (!scale.allFinite()) { out.status=2; return out; }
    double damping=1e-8;
    std::vector<unsigned char> active=initial;
    std::vector<std::vector<unsigned char>> visited;
    Vector seed;
    double seed_residual=std::numeric_limits<double>::infinity();
    auto restart=[&](bool reset=true) {
        damping*=10; if (reset) active=initial; visited.clear(); ++out.restarts;
    };
    for (;out.factors<budget;) {
        Matrix j=selected(usable,active);
        Matrix matrix=hl+rho*(j.transpose()*j);
        Vector diagonal=damping*scale;
        for (int k=0;k<n;++k) matrix.coeffRef(k,k)+=diagonal[k];
        Vector affine=Vector::Zero(pairs);
        for (int i=0;i<pairs;++i) if (active[i]) affine[i]=intercept[i];
        Vector rhs=-force+j.transpose()*affine;
        Eigen::SimplicialLDLT<Matrix> factor; factor.compute(matrix); ++out.factors;
        if (factor.info()!=Eigen::Success || !factor.vectorD().allFinite() || !(factor.vectorD().array()>0).all()) {
            // Rebuild the newly damped model from the current working set.
            // Resetting to the initial set here repeats its release at every
            // level and spends two factorizations per damping increment.
            if (proposal) { restart(false); continue; }
            double next=0;
            if (!coercive_damping(hl,scale,damping,next)) { out.status=2; return out; }
            damping=next; visited.clear(); ++out.restarts; continue;
        }
        Vector d=factor.solve(rhs);
        double numerator=(matrix*d-rhs).stableNorm(),denominator=rhs.stableNorm();
        if (!std::isfinite(numerator) || !std::isfinite(denominator)) {
            out.residual=std::numeric_limits<double>::infinity(); restart(); continue;
        }
        out.residual=denominator>0?numerator/denominator:(numerator==0?0:std::numeric_limits<double>::infinity());
        if (!d.allFinite() || !std::isfinite(out.residual) || out.residual>1e-5) { restart(); continue; }
        double slope=original_gradient.dot(d);
        if (proposal && seed.size()==0 && active==initial && std::isfinite(slope) && slope<0) {
            seed=d; seed_residual=out.residual;
        }
        Vector predicted=intercept-rho*(usable*d);
        if (!predicted.allFinite()) { restart(); continue; }
        std::vector<unsigned char> next(pairs);
        for (int i=0;i<pairs;++i) {
            next[i]=predicted[i]>0;
            if (next[i] && !available[i]) { out.status=4; return out; }
        }
        Vector model_gradient=force+hl*d+diagonal.cwiseProduct(d)-usable.transpose()*predicted.cwiseMax(0.);
        double model_residual=model_gradient.stableNorm()/norm;
        auto delta=change(hl,usable,force,gap,dual,rho,diagonal,d);
        bool certified=std::isfinite(model_residual) && std::isfinite(slope) && slope<0 &&
            merit::finite(delta) && delta.hi<0;
        bool converged=next==active && model_residual<=1e-5;
        if (certified && (proposal || converged)) {
            out.status=unmodelled?unmodelled_proposal:(converged?0:descent_proposal);
            out.direction=std::move(d); out.change_upper=merit::upper_double(delta);
            return out;
        }
        if (next!=active) {
            visited.push_back(active);
            if (std::find(visited.begin(),visited.end(),next)!=visited.end()) restart();
            else active=std::move(next);
            continue;
        }
        restart();
    }
    // Budget exhaustion may retain the original Newton direction contract.
    // No model decrease is claimed. The caller must recheck its actual
    // gradient and spend only the original single nonlinear line search.
    // Fatal returns above deliberately cannot reach this fallback.
    if (proposal && seed.size()) {
        out.status=raw_seed_proposal; out.direction=std::move(seed);
        out.residual=seed_residual;
    }
    return out;
}
inline Result propose(const Matrix& hl,const Matrix& rows,const Vector& force,
        const Vector& gap,const Vector& dual,double rho,const std::vector<int>& regular,int budget=12) {
    return solve(hl,rows,force,gap,dual,rho,regular,budget,true);
}
} // namespace membrane::step_model
