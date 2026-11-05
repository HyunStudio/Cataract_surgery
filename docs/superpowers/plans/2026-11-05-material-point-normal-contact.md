# Material point normal contact implementation plan

> Use executing-plans inline in the existing linked worktree; no new worktree.

Goal: resolve finite-axis contact with multiple physical reaction locations,
then qualify owned179 and the full surgical route. Full simulator scope remains.

Architecture: add a separate native candidate ABI for fixed barycentric material
points against finite capsule axes. Multiple nonnegative normal multipliers can
represent distributed line contact. The caller generates/retains necessary
material witnesses and must independently check every original fine face and
the entire physical motion before publication. Sampling is never full clearance.

Alternatives: five capsule/triangle feature constraints express the same gap
set but need new edge Hessians and still have parallel edge/axis degeneracies.
Single closest-witness smooth Newton has the verified179 switching stall.
Material-point constraint generation uses a convex point/segment distance with
an explicit normal Jacobian and supplies several actual reaction locations.
This is an engineering choice under the user's instruction to proceed, not a
claim of clinical calibration or finite-area jaw friction completion.

Constraints: unchanged original force1e-8, gap1e-9, COMP1e-11, SPD and linear
checks, shared250Newton budget; legacy ABIs unchanged. No positive mass deletion,
target adjustment, full geometry/guard bypass or false point-sampling clearance.
For the point ABI, all three shape rows must be exactly identical; their ordered
control weights define one material point. Failed candidates publish nothing.

- [x] RED/GREEN analytic parallel line-contact case: centered symmetric triangle
  at y=.009, capsule axis[-.2,0,0] to[.2,0,0], radius.01; equal masses with dt.1.
  Uniform final y=.01 and two endpoint reactions balance all three vertices.
  Also test zero budget, malformed point shape and legacy result invariance.
- [x] Add isolated material_point_contact.h for point/axis geometry, pullback
  normal Hessian and original-field interval merit increments; derivative and
  independent Decimal increment tests, rigid poses and FP ownership.
- [x] Add separate membrane_fem_solve_material_points ABI, reuse existing original
  FEM/AL engine with explicit point mode; retain original gates and old defaults.
- [x] Solve owned179 with material witness generation and independent distributed
  force/whole fine geometry/CCD checks. Include all spent iterations in250budget.
- [ ] Only after qualification connect typed Godot candidate and actual state
  transactions; regressions, read-only review, full route and runtime evidence.

This normal contact model is not a bilateral point grasp and not a friction law.
Pressure/friction/slip, actual jaw acquisition, remaining surgical phases,
real-time/GPU and Windows delivery are still required by the active goal.

## Current evidence

New candidate ABI was RED absent; analytic parallel equilibrium and atomic
invalid/zero-budget calls are GREEN. Primitive5tests cover independent finite
derivative/Hessian, rigid poses and endpoint generalized Hessian,80-digit
original-field merit enclosure, invalid atomicity and64caller FP contexts.
Full new API FP and no-contact legacy parity tests are included in the broader
source-bound run; the first run revealed a test import syntax error, so it is
not qualified and must be corrected and rerun after that handle terminates.

Owned179 offline constrained generation passes strict mode:30then32material
points,15+22=37Newton within original250. Independent original stress plus
distributed normal force3.6875358599974817e-9, COMP5.656382241318607e-13.
All4410original fine faces against4bodies have minimum gap-6.822890504427925e-11
and no invalid query. Original complete motion guard returns0. Archived under
operative-motion179-material-points-2026-11-05.json. This is owned native
qualification, not a full operation, engine transaction or real-time claim.

Engine fallback is implemented only after atomic endpoint status2failure. It
shares the remaining budget, independently checks original source-face point
provenance and force, then retains the unchanged original full-interval gate.
Point duals cannot become ordinary temporal seeds. Source event/step identity
is retained with accepted contact metadata. Typed actual kernel RED absent;
current extension28stage validation60217 is still LIVE in l5ozgfsx.

Read-only review found a model-selection bypass: an ordinary backend could
inject normal_rows. Added RED forged-response/empty-dual and row-provenance
tests, then corrected selection to a local owned flag/list; unsolicited model
fields reject, and weights/nodes/barycentrics are checked against the source
face before indexing. Malformed protocols abort atomically. Targeted tests
GREEN and follow-up read-only review confirmed the fix. Focused50suite run34551
and native33327 are live; do not mutate their source inputs before termination.

## Superseding validation progress

Focused34551 is TERMINAL:50suites plus fresh import PASS. Owned179 actual
Godot stage passes: steps178to179, original history/clock exactly once,
independent force3.6863186114732827e-9;38old endpoint+37point iterations=75
of250. Actual elapsed52,263ms includes the old endpoint attempt and engine
checks, so this is emphatically not real-time. The point-only native solves
total about0.35s in a separate run; that number is not gameplay/frame latency.

Initial broad native33327 is TERMINAL false solely because a global text
replacement corrupted an import in the newly expanded test module. All other
24suites passed. Corrected after termination; the exact current four tests
(valid/failed64FP caller contexts, analytic normal equilibrium, failure atomicity
and no-contact legacy bitwise parity) PASS. Full current source-bound25suite
rerun65296 is LIVE. No input was modified under the old running qualification.

Actual extension60217 remains LIVE after the passing179stage. Do not poll
terminal33327/34551/58382/72758 or restart the new native run on observation
timeout. Full closed blade route has not yet been rerun on this new fallback.

Actual extension60217 is TERMINAL:28stages PASS. Full identical frozen route
43249 is now LIVE in `.tools/fem-extension-l5ozgfsx`, log
`distributed-normal-full-route.log`, metadata
`godot/reports/distributed-normal-full-route.json`. It uses its own frozen
bytes; root edits do not authorize changing that probe. Never restart it on
observation timeout. Offline/engine/regression reports are archived. Current
native25suite rerun65296 remains LIVE after exact current four new tests passed.

## Current terminal checkpoint

65296 is TERMINAL:25native suites,261tests PASS, including the exact corrected
new test module. First import failure was corrected, not waived. Source and
artifact manifests rechecked before this checkpoint. Final current evidence:
material-normal-numerical-2026-11-05.json, material-normal-operative-components-
2026-11-05.json (28stages), material-normal-regressions-2026-11-05.json
(50suites+fresh import), operative-motion179-{material-points,engine}-2026-11-05.
Read-only review confirms the corrected force-model ownership and provenance.

Full route43249 remains LIVE; last observed148accepted physical steps and
194cut events. No full-route, full-operation, real-time or release claim.
Do not poll terminal34551/60217/65296; continue the exact43249handle and frozen
log before any rerun. Next goal work follows the full route result, then true
finite-jaw contact/pressure/friction/slip and every other surgical phase.
