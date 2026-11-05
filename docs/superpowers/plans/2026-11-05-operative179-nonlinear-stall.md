# Owned motion179 nonlinear failure investigation

Use systematic-debugging and executing-plans inline in the existing worktree.

Goal: identify and fix the actual native failure after178accepted steps and297cut
events, then qualify the owned step before spending another full-prefix replay.
This is a subproblem of the full professional surgical simulator, not a replacement
for finite-jaw mechanics, all surgical phases, real-time/GPU or Windows delivery.

- [x] Preserve original typed state in operative-motion179-state.bin and raw
  binary64 numerical requests in operative-motion179-native-case-2026-11-05.json.
- [x] Reproduce both requests with the source-bound product DLL: status2 and all
  saved stats bitwise equal; failed output atomicity retained. See archived replay.
- [x] Freeze and instrument the original solver only in a disposable build.
  Trace exact stop branch, factor/direction attempts, accepted iterations, line
  tests and feature/evaluation rejection. Confirm instrumented result matches
  original stats. Do not promote the diagnostic DLL to product.
- [ ] Form a single evidence-backed hypothesis and minimal failing regression.
- [ ] Fix root cause with original force1e-8, gap1e-9, complementarity1e-11,
  original SPD/linear gates and shared250iterations unchanged. No positive mass
  deletion, cap, false success, point-grasp shortcut or full-path guard bypass.
- [ ] Independent physical and whole-path qualification of owned179; related
  regressions/native extension checks, read-only review, then full route.

Observed facts:346controls,310free,461coarse cells,4410fine faces,4bodies.
Minimum positive cell area2.696469295056892e-14; positive inverse masses extend
to845552965899678.0. These ranges are facts, not proven failure causes.
First precise endpoint stops after38iterations (force0.3248599956113635), cold
trajectory [.5,1] after29 (force0.269367176138459). Total67/250, both AL outer0.
stats[14] is the AL outer index, not a stop reason. Damping is very large, but
whether factor rejection, direction, merit or geometry causes the stall still
requires instrumentation. No candidate reaches the independent full-path guard.

## Terminal diagnostic evidence

Source-bound frozen trace59105 completed: original status and all16stats match
bitwise, failed output unchanged. Exact stop is the32-trial line-search rejection
at38iterations. Final curvature passes SPD and linear residual1.669e-16 passes;
this instance is not a factor failure. Trace DLL is diagnostic-only, not promoted.

A separate small native probe decomposes five recorded original-coordinate
trial increments into elastic, inertial and per-contact terms. Their sums match
the original line observations within1e-13. Independent80-digit Decimal active
set minimization encloses nine relevant contact changes inside the existing
certified intervals. At iteration16 face22/body0 has selected smooth slope
-1.0231573173511713e-10 but true finite-step contact increment
+2.7432098073126598e-12. Its broad certified interval contains the increase;
the acceptance test correctly refuses the step. Do not weaken it.

This face uses identity B and ordinary coarse face[0,24,23], not a tiny cut face.
Native nearest feature changes fromedge2 toedge4, with closest capsule parameter
approximately0.081028 to0.062430. Decimal axis-dot-face-normal crosses zero on
the full trial and approaches zero through decreasing steps. This supports
near-parallel finite-axis closest-witness switching as the next hypothesis.
It does NOT yet prove an arithmetic bug, generalized stationary point or the
correct physical remedy. A finite nonlinear increment need not equal its tangent.
Characterize the one-sided limits and multiple witnesses before selecting a
solver change; no material deletion or model/collision-guard shortcuts.

Archive: operative-motion179-{stop-trace,increment-audit}-2026-11-05.json.
The latter retains raw binary64-decoded x/y trial arrays and sparse original
duals for local investigation without another full surgical prefix. Full20MB
line trace remains in the frozen local probe; reproducer script regenerates it.

## Terminal diagnostic evidence

Source-bound frozen trace59105 completed: original status and all16stats match
bitwise, failed output unchanged. Exact stop is the32-trial line-search rejection
at38iterations. Final curvature passes SPD and linear residual1.669e-16 passes;
this instance is not a factor failure. Trace DLL is diagnostic-only, not promoted.

A separate small native probe decomposes five recorded original-coordinate
trial increments into elastic, inertial and per-contact terms. Their sums match
the original line observations within1e-13. Independent80-digit Decimal active
set minimization encloses nine relevant contact changes inside the existing
certified intervals. At iteration16 face22/body0 has selected smooth slope
-1.0231573173511713e-10 but true finite-step contact increment
+2.7432098073126598e-12. Its broad certified interval contains the increase;
the acceptance test correctly refuses the step. Do not weaken it.

This face uses identity B and ordinary coarse face[0,24,23], not a tiny cut face.
Native nearest feature changes fromedge2 toedge4, with closest capsule parameter
approximately0.081028 to0.062430. Decimal axis-dot-face-normal crosses zero on
the full trial and approaches zero through decreasing steps. This supports
near-parallel finite-axis closest-witness switching as the next hypothesis.
It does NOT yet prove an arithmetic bug, generalized stationary point or the
correct physical remedy. A finite nonlinear increment need not equal its tangent.
Characterize the one-sided limits and multiple witnesses before selecting a
solver change; no material deletion or model/collision-guard shortcuts.

Read-only review confirms the diagnostics for this exact endpoint, with the
same interpretation caveat. Decimal audit explicitly requires identity B.
Archive: operative-motion179-{stop-trace,increment-audit}-2026-11-05.json.
The latter retains raw binary64-decoded x/y trial arrays and sparse original
duals for local investigation without another full surgical prefix. Full20MB
line trace remains in the frozen local probe; reproducer script regenerates it.

## Smaller represented displacements

Final audit11530 samples face22 along the same iteration16direction on both
sides at fractions +/-1,+/-0.01,+/-0.001,+/-0.0001 and+0.002. Within the old
feature the independent80-digit merit increment matches actual gradient work:
+0.0001 work-1.0257141394393116e-14 vs change-1.0257141393226543e-14;
+0.001 work-1.0229148195832151e-13 vs change-1.0229148184229887e-13.
So this evidence does not support a wrong infinitesimal derivative. After the
axis/plane parallel sign transition, the active closest feature changes and
the old smooth tangent ceases to describe the whole finite increment. At+0.002
true contact change-1.2582352038777194e-13 lies in a wider certified interval
whose upper endpoint is+5.754851254542777e-15. At+1 true change is positive.

Next: characterize the simultaneous closest witnesses and full merit around
the switching state, including whether tighter feasible-witness bounds alone
suffice or a nonsmooth/multiple-contact equilibrium model is required. Maintain
the original physical acceptance gates; do not guess a gradient or a tolerance.
