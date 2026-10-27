# Native membrane solver implementation plan

> Execute inline with superpowers:executing-plans. Continued implementation is authorized by the user.

**Goal:** Resolve refined-flap numerical stretch without hiding physical damage, and measure the cost before replacing runtime integration.

**Architecture:** A pure C++ double-precision implicit spring-energy solver, initially tested through a small C ABI. Minimize mass-weighted displacement plus existing compliant edge energy with a matrix-free Gauss–Newton direction, preconditioned conjugate gradient and energy backtracking. Report convergence and bounded-work exhaustion explicitly. A Godot GDExtension bridge is a subsequent gate, not an assumed working integration.

**Updated after measured RED:** Undamped GN still exhausted100outer iterations at E9.063e-7. Adaptive direction-only damping improved it to E4.0406e-8 but gradient1.877e-5 still failed. CG diagnostics showed only37iterations/outer on average, so the512CG cap was not the main cause. The exact distance Hessian's transverse geometric stiffness was then included, with bounded negative-curvature damping retries. The same objective,100outer limit and1e-8gradient test now pass at23outer/5118totalCG/28objective evaluations: E3.819273071e-8, gradient_inf5.6323e-9, maxstrain.00260886. Measured standalone cost.209–.224s remains unsuitable for realtime. No runtime connection/release yet.

**Tech stack:** Godot4.7.2 remains the product engine. Portable Zig0.17.0 C++ compiler (SHA256 b5663f69581dcf391293fbf16c06cb80d81d806545ce618b4d0bab7f0eb8c428); godot-cpp godot-4.5-stable commit e83fd0904c13356ed1d4c3d09f8bb9132bdc6b77 for later forward-compatible extension evaluation. No new runtime Python dependency.

**Spec:** REALISM_COMPLETION_KO.md and conservative-membrane-cut plan. Preserve material masses, actual crack topology, tool attachments and the retained failing traction gate. No clinical calibration claim.

## Review focus

- Invalid/nonfinite input rejects atomically, pinned positions stay exact, exhausted budgets cannot be reported as converged.
- Very small accepted rest lengths and masses must not gain artificial floors that change mechanics.
- Independent analytical and captured-scene objective/gradient checks, not only implementation-mirroring tests.
- Positive compliance only initially; incompressible/zero-compliance input must reject explicitly until supported.
- Standalone kernel success does not qualify dynamic contact, fracture, GPU, release packaging or real-time performance.

## Tasks

- [x] Write tests in native/tests/test_membrane_kernel.py: analytic two-point spring with unequal masses, pinned endpoint, invalid transaction, budget exhaustion, refined scene objective and gradient; run RED before implementing native/membrane_kernel.cpp.
- [x] Implement C ABI, bounded solve and native build helper; run correctness tests and record actual timing without a real-time claim.
- [ ] Review kernel and convergence failure cases. Then add GDExtension binding tests before connecting it to capsule_solver. Revisit repeated contact projection/velocity/fracture semantics explicitly.
- [ ] Run refined traction/extraction and unchanged regression gates, GPU and compiled-release validation before shipping anything.

## Evidence before native work

The same captured first refined-flap substep has initial max strain .004570974. Existing sequential constraint updates later produce spurious large stretch. Independent L-BFGS-B gave energy3.819356697e-8, max strain.002539, gradient infinity norm1.343e-6 (relative-energy stop; not strict gradient convergence). Sparse trust-region least squares gave energy3.819275721e-8, strain.002636, optimality1.583e-8, but exceeded1000evaluations and reported failure after280.266s. Global XPBD Newton updates overshot severely. This motivates a stabilized coupled solve, not claiming a unique or clinically calibrated solution.

Sources: [XPBD paper](https://mmacklin.com/xpbd.pdf), [official GDExtension guide](https://docs.godotengine.org/en/stable/tutorials/scripting/cpp/gdextension_cpp_example.html), [Zig manifest](https://ziglang.org/download/index.json).

## Review hardening

Scoped read-only review confirmed the exact Hessian/free-coordinate mathematics and identified a symmetric compressed saddle accepted by gradient alone, unavailable early-failure stats and possible overflow in geometric stiffness. New tests reproduced these RED. Early failure stats now explicitly expose infinite unavailable energy/gradient; nonfinite C/length rejects. Negative coordinate Hessian diagonal returns status3for an unstable stationary point. This screen does not certify positive definiteness of the full coupled Hessian; do not call status0a proof of a physical minimum. Complete second-order certification/escape and improved linear solve performance remain prerequisites for runtime qualification. Tests now10/10pass.

Final build also rejects overflow of stiffness times geometric-curvature coefficients, not only overflow of C/length. C++ compiles under `-Wall -Wextra -Wpedantic -Werror`; native10/10tests pass in.210s for the suite. Scoped reviewer found no new substantive issue in the fixes; the full Hessian stability and runtime contact limitations remain explicit. Compiler setup and all native build/test jobs have completed; no live child process is intentionally left by this task.
