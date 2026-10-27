// Exact sparse free-coordinate Hessian. Eigen is a pinned, header-only build dependency.
#pragma once
#include <Eigen/SparseCholesky>
#include <algorithm>
#include <cmath>
#include <limits>
#include <vector>

namespace membrane {
class SparseSystem {
    using Matrix = Eigen::SparseMatrix<double>;
    struct Entry { int offset, edge, row_axis, col_axis; double sign; };
    struct Pending { int row, col, edge, row_axis, col_axis; double sign; };
    std::vector<int> mapping, full_coordinates, diagonal_offsets;
    std::vector<Entry> entries;
    Matrix matrix;
    Eigen::SimplicialLDLT<Matrix> ldlt;
    Eigen::VectorXd rhs, answer;

public:
    SparseSystem(int n, int edges, const int* a, const int* b,
                 const std::vector<double>& mass) : mapping(3*n,-1) {
        for (int k = 0; k < 3*n; ++k) if (mass[k/3] > 0.) {
            mapping[k] = static_cast<int>(full_coordinates.size());
            full_coordinates.push_back(k);
        }
        int size = static_cast<int>(full_coordinates.size());
        matrix.resize(size,size); rhs.resize(size); answer.resize(size);
        if (!size) return;
        std::vector<Eigen::Triplet<double>> pattern;
        std::vector<Pending> pending;
        pattern.reserve(size+21*edges); pending.reserve(21*edges);
        for (int i = 0; i < size; ++i) pattern.emplace_back(i,i,0.);
        for (int e = 0; e < edges; ++e) {
            int ends[2] = {a[e],b[e]};
            for (int row_end = 0; row_end < 2; ++row_end)
                for (int col_end = 0; col_end < 2; ++col_end)
                    for (int r = 0; r < 3; ++r) for (int c = 0; c < 3; ++c) {
                        int row = mapping[3*ends[row_end]+r], col = mapping[3*ends[col_end]+c];
                        if (row < 0 || col < 0 || row < col) continue;
                        pattern.emplace_back(row,col,0.);
                        pending.push_back({row,col,e,r,c,row_end == col_end ? 1. : -1.});
                    }
        }
        matrix.setFromTriplets(pattern.begin(),pattern.end()); matrix.makeCompressed();
        auto offset = [&](int row, int col) {
            int begin = matrix.outerIndexPtr()[col], end = matrix.outerIndexPtr()[col+1];
            auto found = std::lower_bound(matrix.innerIndexPtr()+begin,matrix.innerIndexPtr()+end,row);
            return static_cast<int>(found-matrix.innerIndexPtr());
        };
        for (int i = 0; i < size; ++i) diagonal_offsets.push_back(offset(i,i));
        for (const auto& p : pending)
            entries.push_back({offset(p.row,p.col),p.edge,p.row_axis,p.col_axis,p.sign});
        ldlt.analyzePattern(matrix);
    }

    bool assemble(const std::vector<double>& normals, const std::vector<double>& mass,
                  double stiffness, double damping, const std::vector<double>& metric) {
        if (full_coordinates.empty()) return true;
        std::fill(matrix.valuePtr(),matrix.valuePtr()+matrix.nonZeros(),0.);
        for (size_t i = 0; i < full_coordinates.size(); ++i) {
            int k = full_coordinates[i];
            matrix.valuePtr()[diagonal_offsets[i]] = mass[k/3]+damping*metric[k];
        }
        for (const auto& entry : entries) {
            double tangent = normals[4*entry.edge+3];
            double value = stiffness*((entry.row_axis == entry.col_axis ? tangent : 0.)+
                (1.-tangent)*normals[4*entry.edge+entry.row_axis]*normals[4*entry.edge+entry.col_axis]);
            matrix.valuePtr()[entry.offset] += entry.sign*value;
        }
        for (Eigen::Index i = 0; i < matrix.nonZeros(); ++i)
            if (!std::isfinite(matrix.valuePtr()[i])) return false;
        return true;
    }

    // Numerical curvature screen:0positive finite pivots,3negative pivot,
    // 4singular/inconclusive,2nonfinite factorization. No clinical stability claim.
    int factorize() {
        if (full_coordinates.empty()) return 0;
        ldlt.factorize(matrix);
        if (ldlt.info() != Eigen::Success) return 4;
        auto pivots = ldlt.vectorD();
        bool negative = false;
        for (Eigen::Index i = 0; i < pivots.size(); ++i) {
            if (!std::isfinite(pivots[i])) return 2;
            if (pivots[i] < 0.) negative = true;
            if (pivots[i] == 0.) return 4;
        }
        return negative ? 3 : 0;
    }

    bool direction(const std::vector<double>& gradient, std::vector<double>& result,
                   double& relative_residual) {
        relative_residual = std::numeric_limits<double>::infinity();
        std::fill(result.begin(),result.end(),0.);
        if (full_coordinates.empty()) { relative_residual = 0.; return true; }
        for (size_t i = 0; i < full_coordinates.size(); ++i) rhs[i] = -gradient[full_coordinates[i]];
        double norm = rhs.stableNorm();
        if (!rhs.allFinite() || !std::isfinite(norm)) return false;
        answer = ldlt.solve(rhs);
        if (ldlt.info() != Eigen::Success || !answer.allFinite()) return false;
        Eigen::VectorXd residual = matrix.selfadjointView<Eigen::Lower>()*answer-rhs;
        double residual_norm = residual.stableNorm();
        if (!residual.allFinite() || !std::isfinite(residual_norm)) return false;
        relative_residual = norm > 0. ? residual_norm/norm : residual_norm;
        if (!std::isfinite(relative_residual) || relative_residual > 1e-5) return false;
        for (size_t i = 0; i < full_coordinates.size(); ++i) result[full_coordinates[i]] = answer[i];
        return true;
    }
};
} // namespace membrane
