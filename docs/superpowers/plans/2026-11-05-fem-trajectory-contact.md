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
