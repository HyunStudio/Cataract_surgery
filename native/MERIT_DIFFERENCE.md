# Stable contact merit changes

The optional coupled solver keeps the same objective, physical force/gap/complementarity gates, final curvature screen, work limits and atomic publication. When a valid trial fails ordinary double-precision Armijo subtraction, `Problem::stable_descent` may instead certify the *change* in that objective. No acceptance epsilon is added. Failed or inconclusive bounds retain the original line-search behavior.

The captured265 full trial increases material energy by about1.22675295e-16 and decreases contact merit by about1.22677367e-16. Independent80-digit Decimal active-set quadratic geometry gives total change-2.07209772e-21; rounded absolute subtraction had rejected it. The canonical snapshot and independently recomputed full objective are regression tests.

Inertia changes use `m*dx*(new+old-2*predictor)/2`. Spring changes use the factored squared-length difference divided by the sum of lengths, then the factored energy difference. These identities avoid subtracting nearly equal energies.

For contact, let `D` be minimum squared distance over the triangle simplex and segment interval, and `F(q)` the squared distance at a feasible witness. A convex first-order support gap bounds the witness's suboptimality: `0 <= F(q)-D <= e`. This is a specialized conditional-gradient dual-gap certificate; see [Jaggi2013](https://proceedings.mlr.press/v28/jaggi13.html). With new and old witnesses, respectively:

```
F_new(q_new)-F_old(q_new)-e_new <= D_new-D_old
D_new-D_old <= F_new(q_old)-F_old(q_old)+e_old
```

Fixed-witness changes use `2*old_separation*delta_separation + delta_separation²`. Nested convex parameters guarantee witness feasibility even if separately rounded barycentric weights would not sum to one. Parameters are refined from the existing closest feature, but their optimality is not assumed: the support gap accounts for error or a wrong feature choice. Old distance/gap is bounded as well. Monotonicity of the convex unilateral PHR increment determines which old-gap endpoint to use for each change bound. Inactivity is skipped only with independent AABB certificates at both states, or certified distance lower bounds at both states.

Arithmetic uses outward binary128 intervals with the pinned Zig/Clang Windows toolchain. Adjacent values bound elementary operations. Newton proposes square roots; outward squared comparisons must certify both brackets within bounded work. There is no libquadmath call or runtime Python calculation. This implementation targets the pinned binary128 compiler, not arbitrary platforms. Selected-time queries use the actual represented double triangle coordinates, including interpolation rounding.

`tools/build_contact_merit_probe.py` builds a separate test-only ABI. Tests compare against an independent80-digit active-set QP reference, including no-op motion, active transitions, finite edges/vertices, translated scenes, a deliberately suboptimal witness, selected-time rounding and the complete captured trial. The product ABI/stats12 layout is unchanged. Bound arithmetic adds work and does not establish realtime or clinical calibration.

The corrected merit comparison alone does not make the original265 input pass. Its float32 jaw tips overlap despite nominal.01 radii. The original request remains unchanged and rejects atomically; physical tool coordinates are corrected separately. See `tests/fixtures/joint_physical265.md`.
