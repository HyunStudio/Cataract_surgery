# Normal contact priority implementation plan

Use executing-plans inline in the existing worktree. User opted out of repeated
design questions; retain the full professional surgical simulator objective.

Goal: remove the unnecessary slow failed smooth-contact prefix for finite-axis
tools, without accepting sampled geometry as full collision clearance.

Evidence: owned179 succeeds in37point iterations, but current engine path first
spends38failed ordinary iterations. The measured52.263s includes that old prefix.
The same normal candidate/force/full-guard gates should be attempted first when
the backend supports material-point normals and any actual tool axis is finite.
Point-only bodies retain ordinary preference; existing point fallback remains.

No new native math/API change. Original force1e-8, gap1e-9, COMP1e-11, shared250
budget, original geometry and whole path guard remain mandatory. Each native
candidate's work is validated BEFORE addition; malformed work aborts atomically.
Known numerical failure may use the remaining budget with the ordinary candidate.

- [x] RED pure engine spies: finite-axis primary uses no ordinary call; known
  point failure decrements the ordinary request budget; malformed point response
  never falls through; negative ordinary work cannot hide behind point work.
- [x] Implement local owned point flag/rows and candidate ordering in embedded
  state only. Report normal/ordinary work separately for diagnostic evidence.
- [x] Actual owned179 engine case: no ordinary iterations, force/whole guard,
  exact clock/history once, zero-budget rollback; measure complete engine latency.
- [x] Focused regressions and actual extension components, read-only review.
- [ ] Do not restart live full route43249 on observation timeout. It retains its
  previous frozen source and remains independently authoritative for that version.

This is a step toward real-time input. It does not finish real-time throughput,
finite-jaw pressure/friction/slip, full surgery, GPU or Windows delivery.

## Terminal evidence

Pure ordering/remaining-budget/malformed-model tests were RED on the old path,
then GREEN. Removing only the per-candidate negative-work check was RED, then
byte-exact restoration GREEN. The first mutation experiment accidentally
doubledCRLF using write_text on already decodedCRLF bytes; invalid probes
021z_x41/o2nl0pbk were rejected/stopped, root restored in finally, then the
byte-safe test completed BEFORE starting current validators. Never chain
validation after an exec command until its returned session is terminal.

Final7672:51suites+fresh import PASS. Final80929:28actual extension stages PASS,
including all five previous144/146/150/156/167states and owned179. Read-only
review found no substantive defects. Original261native core test source and
artifact manifests remain unchanged and verified; no native math change here.

Owned179 is4,779ms vs52,263ms previous:37normal iterations,0ordinary, same
independent force3.6863186114732827e-9 and final elastic energy. Original full
guard and exactly one clock/history update pass. This is not real-time.
The instrumented profile has5,738,268us total:358,732point-kernel us,907,076
scalar witness us,16,043full guard us,4,456,417other(engine validation/allocation)
us;52,920witness calls =3complete sweeps of4,410faces*4bodies.
Profile wrappers add overhead; do not compare its total as an uninstrumented FPS.

Archive: normal-priority-{regressions,operative-components,owned179-engine,
cost-profile}-2026-11-05.json. Reproduce cost observation with a qualified frozen
project and absolute script tools/profile_material_normal_cost.gd. No product
UI/renderer or native global environment is modified by that observer.

Old full route43249 is still LIVE in l5ozgfsx, last172steps/269cut events. It
uses the previous037a9c7 frozen source, not this new ordering. Do not mutate or
restart it, and do not poll terminal7672/80929/16000/72022/34756.

Next bottlenecks: batch full scene witness queries while independently checking
returned source material points and retaining the full guard; then sparse
material-point temporal candidates to avoid the remaining expensive ordinary
trajectory solves. Keep all original force/gap/COMP and shared-work gates.

## Superseding full-route status

43249 is TERMINAL failed, not live. Former179physical solve passed, then a
staged cut299hit vertex_budget. All4095fine points used, current exact boundary
reducer removes0,346mechanical controls. Typed packet and complete source-bound
replay are preserved; see2026-11-05-cut299-geometry-capacity.md. No central flap
completion or full-route qualification. No current validation/full-route job
remains live. Do not duplicate the prefix before qualifying the owned cut.
