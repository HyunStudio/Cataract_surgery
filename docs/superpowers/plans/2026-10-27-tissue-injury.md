# Local structural tissue injury and fluid consequences

> **For agentic workers:** Execute inline with superpowers:executing-plans; user authorized continuing the full realism objective.

**Goal:** Local corneal/posterior injury changes the shared mesh, fluid boundary flow, recorded geometry and case outcome.

**Architecture:** A pure injury component owns copied shared corneal/posterior meshes, per-face normalized exposure and bounded adaptive local carving. Contact records carry original surface/triangle/revision/point/attempted normal travel; two-hand batches validate before mutation. Coordinator uses damaged meshes. Display and recorded options use the same revised data. Lens solver reports wound and posterior rupture flows separately while conserving compartment volume. Case director retains injury evidence and cannot normal-complete it after acknowledgment.

**Spec:** Active user goal + docs/REALISM_COMPLETION_KO.md. AAO anatomical role of posterior capsule/barrier reference: https://eyewiki.aao.org/Intraoperative_Signs_of_Posterior_Capsular_Rupture . Every exposure coefficient, aperture size and conductance is an uncalibrated engineering choice, not clinical injury tolerance.

## Review focus
- No load/energy and distant or stale contact must not damage tissue; malformed second record must reject batch atomically.
- Local carving must open collision geometry with bounded vertex/triangle counts and measured area; no global disappearance.
- Intended corneal entry and anterior capsulotomy use their existing models, not accidental injury triggers.
- New-case reset restores all meshes, exposure, topology revisions and outcome flags.
- Replay displays the recorded damaged mesh without mutating live state; pre-injury replay restores original geometry.
- Rupture outflow cannot delete lens mass and obeys reported volume balance even at bounds.
- Acknowledgment clears the modal alert, not persistent structural injury evidence or failed completion conditions.

### Task 1: Local mesh injury
- [x] RED test `test_tissue_injury.gd`: no-op, local blade puncture, actual sphere passage, area conservation/locality, bounded refinement, bad/stale records, reset.
- [x] Implement `tissue_injury.gd`: reset(); surfaces; step(dt,records); metrics(). Exposure from attempted travel and local energy; blade crossing cuts. Adaptively subdivide only intersecting faces around a .04 synthetic radius before removing local leaves; preserve distant mesh, cap topology.
- [x] Contact coordinator returns detailed immutable local records and accepts revised surfaces.

### Task 2: Fluid, case, presentation
- [x] RED tests for posterior flow reporting/balance and no particle mass loss; persistent injury alert and normal-completion rejection.
- [x] Couple root contact records/injury/surfaces; preserve energy contact while tool remains at the same contact pose; drive rupture conductance from measured missing area.
- [x] Display/replay render actual revised corneal/posterior geometry; UI exposes integrity/flow and injury timeline.
- [x] Add actual application puncture/reset/recording regression and verify healthy full encounter remains possible.

### Task 3: Verify/deliver
- [x] Independent review and affected/full Godot suites; actual GPU healthy/adverse captures and native release.
- [x] Profile actual powered workload and preserve measured performance evidence; further optimization may be a subsequent milestone.
- [x] Update docs/ZIP, commit; keep overall goal active (shaft geometry, dropped material/vitreous/IOL support, complication recovery and refined visuals still required).

Verified: 27 local Godot suites, independent focused review, healthy/adverse NVIDIA GPU application tests, 30-second active workload (42.75fps; target remains unmet), editor import, native export and 120-frame launch. Overall completion goal remains active.
