// Implicit compliant-distance energy. No engine, contact or fracture dependency.
#include <algorithm>
#include <cmath>
#include <limits>
#include <vector>
#include "membrane_sparse.h"
#include "fp_environment.h"

namespace {
using Vec = std::vector<double>;
double dot(const Vec& a, const Vec& b) {
    double value = 0.;
    for (size_t i = 0; i < a.size(); ++i) value += a[i] * b[i];
    return value;
}
double infinity_norm(const Vec& a) {
    double value = 0.;
    for (double x : a) value = std::max(value, std::abs(x));
    return value;
}

struct Problem {
    int n, edges;
    const int *a, *b;
    const double* rest;
    double stiffness;
    Vec predicted, mass;

    bool evaluate(const Vec& x, double& energy, Vec& gradient, Vec& normals, Vec& diagonal) const {
        energy = 0.;
        std::fill(gradient.begin(), gradient.end(), 0.);
        for (int i = 0; i < n; ++i) {
            for (int axis = 0; axis < 3; ++axis) {
                int k = 3*i + axis;
                double d = x[k] - predicted[k];
                energy += .5 * mass[i] * d*d;
                gradient[k] = mass[i] * d;
                diagonal[k] = mass[i] > 0. ? mass[i] : 1.;
            }
        }
        for (int e = 0; e < edges; ++e) {
            int ia = 3*a[e], ib = 3*b[e];
            double dx = x[ia]-x[ib], dy = x[ia+1]-x[ib+1], dz = x[ia+2]-x[ib+2];
            double length = std::hypot(dx, dy, dz);
            if (!(length > 0.) || !std::isfinite(length)) return false;
            double c = length-rest[e];
            energy += .5*stiffness*c*c;
            normals[4*e+3] = c/length;
            if (!std::isfinite(normals[4*e+3]) ||
                !std::isfinite(stiffness*normals[4*e+3]) ||
                !std::isfinite(stiffness*(1.-normals[4*e+3]))) return false;
            for (int axis = 0; axis < 3; ++axis) {
                double normal = (x[ia+axis]-x[ib+axis])/length;
                normals[4*e+axis] = normal;
                double force = stiffness*c*normal;
                if (mass[a[e]] > 0.) {
                    gradient[ia+axis] += force;
                    diagonal[ia+axis] += stiffness*normal*normal;
                }
                if (mass[b[e]] > 0.) {
                    gradient[ib+axis] -= force;
                    diagonal[ib+axis] += stiffness*normal*normal;
                }
            }
        }
        if (!std::isfinite(energy)) return false;
        for (size_t k = 0; k < gradient.size(); ++k)
            if (!std::isfinite(gradient[k]) || !(diagonal[k] > 0.) || !std::isfinite(diagonal[k])) return false;
        return true;
    }

    void multiply(const Vec& p, const Vec& normals, Vec& result) const {
        for (size_t k = 0; k < p.size(); ++k) result[k] = mass[k/3]*p[k];
        for (int e = 0; e < edges; ++e) {
            double projection = 0.;
            for (int axis = 0; axis < 3; ++axis)
                projection += normals[4*e+axis]*(p[3*a[e]+axis]-p[3*b[e]+axis]);
            for (int axis = 0; axis < 3; ++axis) {
                double tangent = normals[4*e+3];
                double f = stiffness*(tangent*(p[3*a[e]+axis]-p[3*b[e]+axis])+
                                      (1.-tangent)*projection*normals[4*e+axis]);
                if (mass[a[e]] > 0.) result[3*a[e]+axis] += f;
                if (mass[b[e]] > 0.) result[3*b[e]+axis] -= f;
            }
        }
    }

};

int solve(int n, double* output, const double* inverse, int edges,
          const int* a, const int* b, const double* rest, double alpha,
          int budget, double tolerance, double* stats) {
    if (!output || !inverse || !stats || n < 1 || n > 4096 || edges < 0 || edges > 16384 ||
        (edges && (!a || !b || !rest)) || budget < 0 || budget > 1000 ||
        !(alpha > 0.) || !std::isfinite(alpha) || !std::isfinite(1./alpha) ||
        !(tolerance > 0.) || !std::isfinite(tolerance)) return -1;
    Problem problem{n, edges, a, b, rest, 1./alpha, Vec(output, output+3*n), Vec(n)};
    for (int i = 0; i < n; ++i) {
        double w = inverse[i];
        if (!std::isfinite(w) || w < 0. || w > 1e12) return -1;
        problem.mass[i] = w > 0. ? 1./w : 0.;
        if (!std::isfinite(problem.mass[i])) return -1;
        for (int axis = 0; axis < 3; ++axis)
            if (!std::isfinite(output[3*i+axis])) return -1;
    }
    for (int e = 0; e < edges; ++e)
        if (a[e] < 0 || a[e] >= n || b[e] < 0 || b[e] >= n || a[e] == b[e] ||
            !(rest[e] > 0.) || !std::isfinite(rest[e])) return -1;
    Vec x = problem.predicted, gradient(3*n), normals(4*edges), diagonal(3*n);
    Vec direction(3*n), hp(3*n);
    Vec trial(3*n), trial_g(3*n), trial_normals(4*edges), trial_diag(3*n);
    double energy = 0.;
    int evaluations = 1, completed = 0, status = 1;
    double damping = 1e-3; // Levenberg regularization affects directions, never the objective.
    int factorizations = 0;
    double relative_residual = 0., minimum_step = 1.;
    if (!problem.evaluate(x, energy, gradient, normals, diagonal)) return 2;
    membrane::SparseSystem system(n,edges,a,b,problem.mass);
    for (;;) {
        if (infinity_norm(gradient) <= tolerance) {
            if (!system.assemble(normals,problem.mass,problem.stiffness,0.,diagonal)) { status = 2; break; }
            ++factorizations;
            status = system.factorize();
            break;
        }
        if (completed >= budget) break;
        bool solved = false;
        // Exact compressed-spring curvature can be indefinite. Require a positive
        // damped factorization before using a direction; the objective stays unchanged.
        for (int attempt = 0; attempt < 12; ++attempt) {
            if (!system.assemble(normals,problem.mass,problem.stiffness,damping,diagonal)) break;
            ++factorizations;
            int curvature = system.factorize();
            if (curvature == 2) break;
            if (curvature == 0) {
                if (system.direction(gradient,direction,relative_residual)) { solved = true; break; }
                if (!std::isfinite(relative_residual)) break;
            }
            if (attempt == 11) break;
            damping = std::min(1e12,damping*10.);
        }
        if (!solved) { status = 2; break; }
        double slope = dot(gradient, direction);
        if (!(slope < 0.) || !std::isfinite(slope)) { status = 2; break; }
        bool accepted = false;
        double step = 1., next_energy = energy;
        for (int line = 0; line < 32; ++line, step *= .5) {
            for (int k = 0; k < 3*n; ++k)
                trial[k] = problem.mass[k/3] > 0. ? x[k]+step*direction[k] : problem.predicted[k];
            ++evaluations;
            if (problem.evaluate(trial, next_energy, trial_g, trial_normals, trial_diag) &&
                next_energy <= energy+1e-4*step*slope) { accepted = true; break; }
        }
        if (!accepted) { status = 2; break; }
        minimum_step = std::min(minimum_step, step);
        problem.multiply(direction, normals, hp);
        double predicted_reduction = -step*slope-.5*step*step*dot(direction,hp);
        double gain = predicted_reduction > 0. ? (energy-next_energy)/predicted_reduction : 0.;
        if (gain > .75 && step >= .5) damping = std::max(1e-12,damping*.25);
        else if (gain < .25 || step < .5) damping = std::min(1e12,damping*4.);
        x.swap(trial); gradient.swap(trial_g); normals.swap(trial_normals); diagonal.swap(trial_diag);
        energy = next_energy;
        ++completed;
    }
    std::copy(x.begin(), x.end(), output);
    stats[0] = energy; stats[1] = infinity_norm(gradient);
    stats[2] = completed; stats[3] = evaluations;
    stats[4] = factorizations; stats[5] = relative_residual;
    stats[6] = minimum_step; stats[7] = damping;
    return status;
}
} // namespace

extern "C" __declspec(dllexport) int membrane_solve(
    int n, double* x, const double* inverse, int edges,
    const int* a, const int* b, const double* rest, double alpha,
    int budget, double tolerance, double* stats) {
    membrane::numeric::Scope environment;
    // Keep C++ allocation exceptions behind the C ABI. No mutation until a finite iterate exists.
    if (stats) {
        std::fill(stats,stats+8,0.);
        stats[0] = stats[1] = std::numeric_limits<double>::infinity();
    }
    try { return solve(n, x, inverse, edges, a, b, rest, alpha, budget, tolerance, stats); }
    catch (...) { return 2; }
}
