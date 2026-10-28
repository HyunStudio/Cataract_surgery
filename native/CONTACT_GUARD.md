# Continuous motion guard

The optional joint capsule path uses `MembraneContactKernel.guard_motion(request)` after the static constrained solve and before committing tissue positions. It receives authoritative packed64 previous/current tissue, triangle indices and physical body trajectories. It never projects positions or changes forces. Anatomy remains a separate rejection guard.

Status0 certifies complete-interval clearance within the supplied gap tolerance using conservative convex-hull separation. Status1 reports sampled penetration,2 reports inconclusive/exhausted work, and-1 reports invalid input. The bounded physical solver may resolve a sampled collision and recheck; unresolved nonzero results roll back the outer physical step. This floating-point certificate is not exact-predicate CCD, an exact impact time, calibrated tissue mechanics or clinical validation.

The separate `membrane_guard_motion_witness` ABI adds an output pointer for the actual status1 sample time while preserving the legacy eight-value stats buffer. Godot exposes it as `witness_t`. Invalid input leaves the witness untouched; valid nonpenetration results use-1. The optional physical solver can add a time-weighted constraint and recheck the entire interval as described in `TRAJECTORY_CONTACT.md`.

Each body packet has41 doubles: previous axes A/B(6), current axes A/B(6), radius(1), original tip0/tip1(6), quaternion0/quaternion1 XYZW(8), original local a0/b0/a1/b1(12), global interval t0/t1(2). Kind0 interpolates recorded axes linearly. Kind1 follows the original shortest spherical quaternion path with linear tip/local motion, plus an affine correction that exactly retains recorded substep endpoints. The correction adds no chord curvature error. Pose paths use physical radius; paths lacking original pose data conservatively retain any caller-supplied enclosure radius.

Tissue moves linearly within each accepted substep. A subinterval capsule is enclosed by its endpoint chord hull plus a bound on rotation/local-shape curvature. Separation projects every hull vertex on each candidate axis. A complete separating projection certifies that interval; an overlapping hull alone never proves collision. Ambiguous geometry, budget exhaustion and depth exhaustion remain uncertain. Limits are4096 vertices,16384 faces,64 bodies,65536 pairs,128 nearest queries per potentially intersecting pair and subdivision depth32.

For a moving triangle the guard also retains time correlation through a plane certificate. Its affine edges produce a quadratic Bernstein normal `n(t)`; each capsule chord endpoint has a cubic signed plane numerator `d(t)`. Both endpoints must retain the same strict sign. Every degree-six Bernstein coefficient of `d(t)^2 - R^2 dot(n(t),n(t))` must have a strictly positive lower bound, where `R` includes physical radius minus gap tolerance plus the existing curvature and numerical enclosure. Products, degree elevation, sums and differences use outward-rounded long-double intervals. The positivity test cannot pass through a zero normal; finite-feature hull separation remains the fallback. The build uses no fast-math flags.

Moving finite-feature planes now supplement that face-plane test. Candidate normals are the endpoint chord relative to a triangle vertex (linear), `e cross (relative-endpoint cross e)` for a triangle edge (cubic), and triangle-edge cross body-axis direction (quadratic). The plane passes through the selected vertex/edge. Nonexempt triangle vertices must remain on the opposite side from both body endpoints. Edge endpoints are algebraically coplanar, so no rounded zero test is needed for them. Shared sign and strictly positive clearance coefficients are checked with outward arithmetic through degree8; strict positivity excludes a zero normal. An ordinary midpoint filter only discards impossible candidates and never certifies one. Existing curved-motion/radius margins, hull fallback and all work limits remain unchanged.

Build and test on the pinned Windows toolchain:

```
python tools/build_contact_guard.py
python -m unittest native.tests.test_contact_guard -v
python tools/build_membrane_extension.py
python tools/validate_native_extension.py
python tools/validate_native_extension.py --coupled-capsule
python tools/validate_native_extension.py --coupled-extraction
```

The standalone27 tests include clear-endpoint translation/rotation crossings, off-midpoint collision/collapse, opposite-side segment endpoints, rigid co-motion, tolerance-scale contact, winding and segment reversal, absolute pose subintervals, explicit uncertainty, witness ABI compatibility and captured actual joint motion261/262/263. Independent affine rotating/scaling examples cover edge, vertex and interior body-axis contact under all triangle permutations; their true midtime penetrations remain rejected. Eight additional deterministic crossing cases have independent interior point-plane/barycentric witnesses. Full extraction is a separate gate; the default application backend and released Windows archive are not promoted by these component tests.

Complete separation certificates now run before point queries, and a129-slot breadth-first ring prevents early near-contact intervals starving later collisions. Two endpoint queries leave at most126 query-funded splits/127 pending nodes; query128/depth32 limits remain unchanged. Valid complete certificates need no extra point sample. Later collisions still supply actual witness times, never inferred impact times.

Moving finite-feature separation resolves the captured263outer step in frozen `u1dmbzmg`. Latest full replay `rnu0rx5o` accepts263 outer ticks, then rejects264on nonlinear force stationarity despite primal feasibility. See `native/tests/fixtures/joint_trajectory264_second.md`. The full application and complete extraction remain unqualified; whole-outer rollback preserves original material.
