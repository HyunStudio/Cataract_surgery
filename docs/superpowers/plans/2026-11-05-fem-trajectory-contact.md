# Original-material FEM with time-weighted contact

Continue the full surgery goal from material-edge insertion. Do not replace
the original energy with the legacy edge-spring model or promote the backend
before operative grasp/anatomy/full input/throughput qualification.

## Exact unresolved case

`native/tests/fixtures/operative_motion144.json` contains the real guard request
and response plus the endpoint FEM request and response. Companion
`godot/tests/fixtures/operative-motion144-state.bin` contains the original owned
state after143 accepted ticks and178 staged incision events, dt1/60,351 controls,
1902 fine vertices and2091 faces. The next outer tick is not accepted.

The endpoint equilibrium is genuine: native replay is bitwise identical, and
independent NumPy physical KKT passes. Complete guard replay identically rejects
face165/body0 at t=.5, gap-1.9805245988378448e-4. Independent80-digit Decimal
active-set distance with SciPy recorded-pose interpolation confirms gaps:
t0:+.001872049869225869; t.5:-.00019805245988378448;
t1:+.0010119761025022996. Clear endpoints do not clear this motion.

## Implementation sequence

1. Retain the endpoint-equilibrium and mandatory-path-rejection regressions.
   Use the exact request directly, not another long operative prefix, for initial
   solver experiments. Inspect existing `membrane_solve_trajectory`,
   `test_trajectory_contact.py`, motion sampling in `contact_guard.h`, and the
   retained original FEM contact implementation. These are references, not
   permission to switch the material model.
2. Add a distinct original-FEM trajectory candidate API. Inputs include old
   original control coordinates, the actual kinds/41-value recorded body packets,
   and bounded sorted unique sample times including1. Keep existing static API
   behavior unchanged. Validate finite coordinates, legal recorded poses and the
   existing total constraint budget; exhausted time/constraint work must reject.
3. At a sample t, evaluate tissue B[(1-t)q0+t*q1] against that recorded body pose.
   Contact gradients with respect to q1 carry factor t and Hessians factor t^2.
   Keep original endpoint elastic/inertial energy, exact holds, normalized physical
   duals, force1e-8, gap1e-9, COMP1e-11, original-system linear residual and SPD
   gates. Preserve interval-safe merit comparisons and validated inactive caching.
   Do not infer clearance from endpoints or a loose rigid-motion enclosure.
4. RED analytic mid-arc obstruction and exact144 case. Independently check original
   energy/KKT, derivative pullbacks, all sampled gaps/complementarity, exact pins
   and failed-candidate atomicity. A t=1-only trajectory candidate must agree with
   the static model within its original numerical contract. Complete CCD remains
   a separate mandatory final acceptance condition.
5. Engine retries a staged implicit candidate with newly discovered guard witness
   times, always from the same accepted old q/history and same physical dt/force.
   Neither failed candidates nor time sampling advance physical time or publish
   state. A t=0 violation is an inconsistent starting history, not a movable q1
   constraint. Duplicate witness/exhausted work rejects explicitly. Boundary and
   anatomy acceptance remain required after a fully guarded candidate.
6. Re-run the same actual operative blade route and capture the next genuine
   failure. Revalidate numerical suites, focused engine regression, source-frozen
   native integration and independent review before commit. Follow with finite-jaw
   acquisition/traction, anatomy response, full actual input cases, GPU throughput
   and Windows delivery; these remain original completion requirements.

## Alternative requiring separate history work

Adaptive physical substeps are possible, but must first qualify explicit velocity
or previous-dt metadata, damping/force scaling, original history timestamps,
outer-tick clocks, render history and whole-tick rollback. Simply running the
current displacement predictor twice at half dt doubles inherited velocity and
changes the physical model. Do not use that shortcut to clear this fixture.

## Native candidate implementation and remaining failure

Implemented the separate `membrane_fem_solve_trajectory` C API, with up to16
strictly increasing sample times ending at1 and layer-major contact multipliers.
It validates the same41-value recorded body poses as the complete motion guard.
Original endpoint material energy, finite inertia, exact holds, force/gap/COMP
limits, SPD and linear residual checks are unchanged. The t=1-only path preserves
the static candidate bitwise. This API is not yet wired into the Godot controller.

Each intermediate tissue field is B[q0+t(q1-q0)]; its contact derivative carries
t and its Hessian t². An initial analytic regression exposed merit cancellation
after separately rounding intermediate control coordinates. New interval merit
code bounds the unrounded affine field using binary128 support certificates.
Closest-feature refinement only proposes feasible witnesses; support residuals
still certify their error. Cache reuse requires both complete evaluations to have
passed and a strict original-control-hull separation certificate.

Nine new tests pass: independent original-material KKT for a curved mid-arc
obstruction, t/t² derivative finite differences,80-digit Decimal enclosure of the
stalled merit comparison, bitwise endpoint compatibility, malformed history and
recorded-pose rejection, exact pins/holds with multiple bodies/layers, atomic
budget exhaustion, and identical results/caller restoration across64 FP modes.
A read-only independent reviewer found no substantive native defect after the
test observer counter was corrected. No controller, anatomy or full-case
qualification follows from these component tests.

Exported exact original controls from the already frozen143-step owned state;
canonical B reconstruction is bitwise identical to all1902 captured fine
positions. `replay_fem_trajectory.py --output <report.json>` now reproduces bounded
offline witness generation with the same predictor/history/dt. It verifies source
and DLL build provenance before and after execution. Complete CCD is mandatory;
all retries share the original250-iteration budget and never publish a candidate.

The exact motion is **still unqualified**, reproduced twice:

| Contact times | Native iterations | Full interval guard |
|---|---:|---|
|1|15|Rejects t=.5, gap-1.9805e-4|
|.5,1|18|Rejects t=.375, gap-1.9092e-5|
|.375,.5,1|24|Rejects t=.25, gap-3.5516e-6|
|.25,.375,.5,1|38|Candidate status2; no state publication|

The final attempt has force residual3.572208300273161e-7 (required1e-8), gap
2.42946e-17 and COMP7.08575e-17, rho1e7. Cumulative work is95 iterations, so this
is a failed merit descent rather than exhaustion. At iteration38/fraction1,
slope=-2.106188217037991e-23 but certified merit upper=+2.642605576508075e-24;
all32 line fractions reject. Largest candidate displacement is1.05305e-13.
Rounded contact activation at high penalty is the next hypothesis to isolate
against independent high-precision force evaluation; it is not yet a proven fix.
Do not relax acceptance thresholds or claim that the smaller sampled gaps clear
the physical path. Failed final outputs preserve the original predictor.

The previous76fb8ed native Windows CI and Python CI succeeded. Its default Godot
CI41874959884 remains red at `test_volumetric_encounter`: continuous blade target
blocked and no detached anterior flap. This remains separate from the optional
original-material candidate and is not waived. No main merge, release tag or
default-backend promotion has been performed.

## Verification ledger

- Source-bound numerical validator:214 tests across17 suites/nine DLLs passed,
  exit0. A prior pass was deliberately discarded because the diagnostic replay
  helper changed during that run; the successful run used stable inputs.
  [Numerical evidence](../../assets/fem-trajectory-numerical-validation-2026-11-05.json).
- Frozen focused engine regression:40 suites plus fresh import passed, exit0,
  probeu16onsdg. [Engine evidence](../../assets/embedded-precision-regression-2026-11-05.json).
- Exact original-control reconstruction and bounded native replay: exit1,
  qualified=false, failed candidate preserves the original predictor. The API is
  not connected to operative input and no new accepted operative tick is claimed.
  [Unqualified actual-motion evidence](../../assets/fem-trajectory144-validation-2026-11-05.json).
- Extension object cache now hashes transitive local includes using the same
  helper as its manifest, replacing a handwritten header list which omitted the
  new merit header. Compiler, flags, API and pinned third-party dependencies stay
  in the cache key. Independent read-only review found no substantive issue.
- Rebuilt extension after the cache correction; frozen probeg4u5_cmo passed all11
  retained bridge/dynamics/grasp/contact/coupled/curved stages, exit0. This tests
  compatibility of existing entry points, not new operative trajectory wiring.
  [Native engine evidence](../../assets/fem-trajectory-engine-validation-2026-11-05.json).
