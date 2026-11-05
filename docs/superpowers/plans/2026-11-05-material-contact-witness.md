# Read-only material contact witnesses for jaw acquisition

> **For agentic workers:** Use superpowers:executing-plans inline in current linked worktree.

**Goal:** Enable actual jaw acquisition to inspect material surface contact including exact zero distance, without pretending a distance witness is a smooth force derivative, CCD or grasp law.

**Architecture:** Separate inline `material_witness.h`, standalone `membrane_material_witness` C export and typed `material_witness_fem` Godot method. Keep old derivative APIs unchanged. Normalize fine B with same stable extended arithmetic as existing embedded contact; use existing bounded convex capsule-triangle distance. Return13geometry fields only (squared distance, gap, axis/surface point, fine barycentrics, axis parameter and feature). Return existing status0regular/1intersection/3tie as explicit geometry data; status2unproven/degenerate and invalid input publish nothing. Do not use these statuses to accept physical motion or pretend uniqueness at ties. The existing full force/KKT/path acceptance remains mandatory.

- [x] RED/GREEN separate C API: point on actual fine face, crossing, regular closest, nonidentity B and rigid pose, independent closest/KKT/ownership, invalid/degenerate atomicity, caller FP contexts. No legacy distance/derivative output changes.
- [x] Typed Godot bridge preserving statuses and compact geometry only. Independent witness reconstruction against actual fine material controls; no gradient/Hessian claims.
- [x] Native/engine regression qualification, provenance and read-only review. Bind surface selection helper only after native witness contract passes.
- [ ] Follow-up actual finite jaw capture must verify both jaw surfaces/pose/closing history and unique material identity, then use material-point constraint with full simultaneous body/contact acceptance. Finite pressure/friction/slip, finite-area model, actual input and whole surgical path remain required; this read-only API alone is not completion.

Existing unrounded-material full route94265is LIVE in `.tools/fem-extension-ci701ipa`, own frozen bytes only, last observed136accepted steps. Root source edits are safe, never mutate/restart that probe on an observation timeout. No full prefix duplicate is needed for the new read-only API. Goal remains full professional surgery, real-time/GPU and Windows delivery.


## Current evidence and pending clarification

RED separate C export was absent. New8native tests pass, covering regular and
exact point contact, finite crossing, explicit nonunique status3, nonidentity B,
24independent rigid poses/closest-point KKT, ownership, invalid/degenerate output
atomicity and64caller FP contexts. Full23native suites now252tests PASS under
terminal61036. Existing derivative/equilibrium interfaces are unchanged.

RED typed method absent on an actual registered old kernel; new bridge/state
contracts pass in current frozen validation. Initial disposable minimal editor
import exited0xc0000005after layout, but a direct runtime on that registered
old kernel gave the intended missing-method failure. Full source-bound import
with normal35frame-delay setup succeeds; no cause assigned to the disposable
editor teardown failure. No stale process was restarted on observation timeout.

Surface helper RED API absent; added independent reconstruction/gap/KKT/source
checks and readonly output snapshots. A deliberately collapsed source and fake
intersection was RED, then independently rejected. Source bridge/proxies delegate
new capability; no derivative fallback. High-level actual retained refined-face
intersection matches a descriptive material point row; old derivative query still
rejects intersection as before. These tests do not approve clamp acquisition.

Read-only review found no additional substantive defect. Identified remaining
semantics issue: `.ambiguous` currently marks status3only, while finite-axis
status1may be a coplanar intersection interval. After current source-bound
validators terminate, RED a finite-axis intersection flag and conservatively mark
all such intersections ambiguous; zero-axis point contact stays not flagged.
Never infer unique grasp permission from any static geometry witness.

Current validation: focused49suites in41029 / `.tools/embedded-regressions-d_3ahy0w`,
actual27extension stages in67612 / `.tools/fem-extension-rskps22_`; do not mutate
source inputs until these handles terminate. Full route94265remains LIVE at172
last observed accepted steps, separate old frozen sources; no duplicate prefix.

## Superseding terminal evidence

The finite-axis ambiguity issue is corrected: status3 or status1 with a nonzero
axis is conservatively ambiguous. Added RED/GREEN pure finite-cross assertion
and actual native coplanar interval coverage; zero-axis point probes remain
geometry-only. Read-only follow-up review confirmed this correction.

Final current validators are terminal: native252tests/23suites (61036), focused
49suites plus fresh import (29393), actual extension27stages (30449). All PASS;
reports archived under docs/assets/material-witness-{numerical,regressions,
operative-components}-2026-11-05.json. The mixed tab/space indentation in the
new native engine test was corrected before the final check-only and validation.

The old full route94265 is TERMINAL, not live: 178accepted physical steps and
297cut events, then attempted motion179 fails native_fem_solve. Neither of its
two candidates passes the solver; no full-path guard is reached. The central
flap remains attached. Exact original state and raw-binary64 numerical requests
are retained; both replay failures match saved stats bitwise. This is failure
reproduction, not physical qualification. See operative179 nonlinear stall plan.

Finite-jaw acquisition/pressure/friction/slip, full surgery, real-time/GPU and
Windows delivery remain outstanding. No repeat full prefix is needed until the
owned motion179 failure is understood and fixed.
