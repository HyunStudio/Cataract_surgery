// Implicit compliant-distance energy. No engine, contact or fracture dependency.
#include <algorithm>
#include <cmath>
#include <limits>
#include <vector>

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

    bool has_negative_coordinate_curvature(const Vec& normals) const {
        Vec curvature(3*n);
        for (int k = 0; k < 3*n; ++k) curvature[k] = mass[k/3];
        for (int e = 0; e < edges; ++e) {
            double tangent = normals[4*e+3];
            for (int axis = 0; axis < 3; ++axis) {
                double normal = normals[4*e+axis];
                double diagonal = stiffness*(tangent+(1.-tangent)*normal*normal);
                if (mass[a[e]] > 0.) curvature[3*a[e]+axis] += diagonal;
                if (mass[b[e]] > 0.) curvature[3*b[e]+axis] += diagonal;
            }
        }
        for (int k = 0; k < 3*n; ++k)
            if (mass[k/3] > 0. && curvature[k] < 0.) return true;
        return false;
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
    Vec direction(3*n), residual(3*n), z(3*n), p(3*n), hp(3*n);
    Vec trial(3*n), trial_g(3*n), trial_normals(4*edges), trial_diag(3*n);
    double energy = 0.;
    int evaluations = 1, completed = 0, status = 1;
    double damping = 1e-3; // Levenberg regularization affects directions, never the objective.
    int cg_iterations = 0;
    double relative_residual = 0., minimum_step = 1.;
    if (!problem.evaluate(x, energy, gradient, normals, diagonal)) return 2;
    for (;;) {
        if (infinity_norm(gradient) <= tolerance) {
            // A negative coordinate diagonal certifies an unstable stationary point.
            // Passing this screen is NOT a full second-order minimum certificate.
            status = problem.has_negative_coordinate_curvature(normals) ? 3 : 0;
            break;
        }
        if (completed >= budget) break;
        double initial_residual = dot(gradient, gradient);
        // Exact distance Hessian includes transverse geometric stiffness. Compression
        // can make it indefinite; retry with stronger direction regularization.
        for (int attempt = 0; attempt < 12; ++attempt) {
            std::fill(direction.begin(), direction.end(), 0.);
            for (int k = 0; k < 3*n; ++k) {
                residual[k] = -gradient[k];
                z[k] = residual[k]/((1.+damping)*diagonal[k]);
            }
            p = z;
            double rz = dot(residual, z);
            bool negative_curvature = false;
            for (int cg = 0; cg < std::min(3*n, 512); ++cg) {
                ++cg_iterations;
                problem.multiply(p, normals, hp);
                for (int k = 0; k < 3*n; ++k) hp[k] += damping*diagonal[k]*p[k];
                double curvature = dot(p, hp);
                if (!(curvature > 0.) || !std::isfinite(curvature) || !(rz > 0.)) {
                    negative_curvature = true; break;
                }
                double step = rz/curvature;
                for (int k = 0; k < 3*n; ++k) {
                    direction[k] += step*p[k];
                    residual[k] -= step*hp[k];
                }
                if (dot(residual, residual) <= 1e-6*initial_residual) break;
                for (int k = 0; k < 3*n; ++k) z[k] = residual[k]/((1.+damping)*diagonal[k]);
                double next_rz = dot(residual, z), beta = next_rz/rz;
                for (int k = 0; k < 3*n; ++k) p[k] = z[k]+beta*p[k];
                rz = next_rz;
            }
            if (!negative_curvature) break;
            if (attempt == 11) break; // Keep diagnostics equal to the matrix actually attempted.
            damping = std::min(1e12,damping*10.);
        }
        relative_residual = std::sqrt(dot(residual,residual)/initial_residual);
        double slope = dot(gradient, direction);
        if (!(slope < 0.) || !std::isfinite(slope)) {
            for (int k = 0; k < 3*n; ++k) direction[k] = -gradient[k]/diagonal[k];
            slope = dot(gradient, direction);
        }
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
    stats[4] = cg_iterations; stats[5] = relative_residual;
    stats[6] = minimum_step; stats[7] = damping;
    return status;
}
} // namespace

extern "C" __declspec(dllexport) int membrane_solve(
    int n, double* x, const double* inverse, int edges,
    const int* a, const int* b, const double* rest, double alpha,
    int budget, double tolerance, double* stats) {
    // Keep C++ allocation exceptions behind the C ABI. No mutation until a finite iterate exists.
    if (stats) {
        std::fill(stats,stats+8,0.);
        stats[0] = stats[1] = std::numeric_limits<double>::infinity();
    }
    try { return solve(n, x, inverse, edges, a, b, rest, alpha, budget, tolerance, stats); }
    catch (...) { return 2; }
}
