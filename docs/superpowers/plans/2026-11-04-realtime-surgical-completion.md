# Real-time surgical completion implementation plan

> **For agentic workers:** Use superpowers:executing-plans inline, task by task.

**Goal:** Complete the professional interactive surgical app with stable material
response, geometric operating tools and continuous full-case qualification.
**Architecture:** Retain Godot mouse/keyboard and the existing authoritative
model/display separation. Fix observed mechanical defects in the interactive
path with explicit regression evidence. The optional double-precision research
solver remains subject to its own unchanged acceptance gates; do not confuse its
isolated numerical qualifications with the default playable app.
**Tech Stack:** Existing pinned Godot4.7.2/GDScript, optional C++ native backend.
**Spec:** docs/PHYSICS_SIMULATOR_SCOPE_KO.md and docs/REALISM_COMPLETION_KO.md.

## Global constraints
- User requests continuation without design questions; existing approved platform
  and mouse/keyboard controls remain. Completion goal is active, unbudgeted.
- Preserve mass/rest area/history through incision and rejected state changes.
- Preserve genuine excessive-load rupture, input locks, dual-hand operation,
  final-state evaluation and recording/replay.
- Do not hide failure with larger tear thresholds, skipped tests or cut loss.
- Benchmark interactive state changes, then actual GPU and packaged operation.
  Numerical tests alone cannot qualify realism or end-to-end completion.

## Review focus
- Acquisition without a snap, and small movement on an irregular refined flap.
- Finite accepted strain and real rupture under excessive traction.
- Release, pause, reset, case changes and failure preserve valid state ownership.
- Geometric incision follows blade motion and preserves material bank/history.
- Complete operation uses actual mouse/keyboard controls and retains wall-time
  responsiveness, rather than isolated direct model calls.

### Task1: Stable refined traction
Files: godot/scripts/capsule_solver.gd, godot/tests/test_capsule_incision.gd,
related capsule/material tests, completion records.
- [ ] Reproduce existing RED on current source in reused isolated worktree.
- [ ] Instrument predicted vs accepted strain, smallest affected edges/masses and
      grasp/contact effects without changing material laws. Do not repeat the
      already disproven fracture-timing-only fix without new evidence.
- [ ] Add focused regressions for the identified cause; implement minimum valid
      correction; preserve actual rupture and material conservation.
- [ ] Run capsule/incision/refinement/contact/control/transaction checks, review,
      benchmark current interactive app, commit and integrate qualified change.

### Task2: Operative blade and grasp continuity
Follow 2026-10-29-precise-operator-integration.md after current state stability.
- [ ] Connect actual swept blade geometry to retained material topology with
      rollback and persistent material grasp state; verify actual input route.
- [ ] Qualify topology changes, instrument exchange and portal/wound passage.

### Task3: Complete surgical operation and delivery
- [ ] Confirm hydro, local nuclear/cortical removal, fluid/device reactions,
      IOL delivery/alignment and wound evaluation follow simulated state.
- [ ] Complete actual pointer/keyboard normal and complication cases and replay.
- [ ] Improve microscope/anatomy/tool/operative-field visuals from actual GPU
      captures; measure active throughput/latency and sustained operation.
- [ ] Full appropriate regressions, actual GPU acceptance, Windows export and
      packaged complete operation; update truthful user-facing completion record.


## Execution ledger
- Current baseline test_capsule_incision actually reproduces1failure (64535).
- Ruling: fracture timing alone and iteration increases are not fixes. Frozen
  no-fracture diagnostics show6/16GS iterations leave large sliver strains;
  area-weighted spring trial also fails to reduce them. No constitutive change
  or threshold increase is adopted.
- Global native elasticity preserves material in30small-motion ticks, but
  isolated headless median117.688ms/max210.557ms is not interactive qualification.
  Instrumented31ticks: kernel2165.918ms, project2886.673ms, checkpoint342.829ms,
  residual114.869ms. Shared host workload makes absolute timings variable.
- Constructor-only profiling is9.27ms of130.95ms captured kernel solve; symbolic
  cache alone cannot meet throughput. Unchanged strict solve paired107.8ms/0;
  frozen majorizer-preconditioned L-BFGS165.0ms/status1 after100steps, so reject
  that prototype. Its material/objective/gates remain unchanged; no production
  solver adoption. Primary references: https://mmacklin.com/xpbd.pdf and
  https://www.projectivedynamics.org/projectivedynamics.pdf. These methods are
  engineering references, not validated capsule material parameters.
- Ruling: progress on independent visual/modeling defects while the numerical
  problem remains open; do not serialize all product work behind one research
  solve. The user explicitly requests professional3D modeling and continuous
  completion. Ocular surface normals are currently UP despite a curved profile;
  vessel centerline heights do not follow that same surface and become occluded.

### Task4: Ocular surface and vascular geometry
Files: surgical_world.gd, new ocular_appearance.gd, test_ocular_appearance.gd,
related world/display tests and GPU captures.
- [x] Observe RED: curved normals must be perpendicular to sampled surface
      tangents; vessels must form a batched surface-following branching mesh.
- [x] Compute normals from the radial height derivative, generate deterministic
      tubular branching vessels with taper and proper normals on the same surface.
- [x] Keep anatomy collision/material states untouched, reuse scene geometry.
- [x] Run focused world/display/app regressions, actual GPU before/after capture,
      inspect, review and integrate only qualified visual/modeling change.


Task4 evidence: ocular test9RED->0 including normal/tangent, tube bounds, caps/
winding and idempotence. Ocular-validation-7uj2si7v/98758terminates0,11suites all
qualified, sources unchanged. Actual GPU before/final/paired static rendering jobs
85125/3175/86871/91715/88151all terminate0. Captures visually inspected. MSAA4X
fine-edge improvement costs about.205ms median in this static paired sample;
draw calls271->222. Do not infer active FPS or endurance. Final read-only branch
and delta review find no actionable correctness issue. All jobs terminal.
No numerical prototype was adopted. Goal stays active. Continue with unresolved
material-conserving actual tool/tear behavior and full-case input/performance;
do not spend another full-prefix numerical run until the saved failing step has
a reasoned fix. Local integration of this display milestone remains to be done.
