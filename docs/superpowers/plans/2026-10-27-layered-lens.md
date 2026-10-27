# Layered lens and hydrodissection implementation plan

> **For agentic workers:** Use superpowers:executing-plans task by task. User explicitly instructed continued implementation toward actual-surgery-like completion, without another design approval gate.

**Goal:** Replace homogeneous lens behavior in the integrated app with measured nuclear/cortical mass and localized capsule-cortex adhesion release.

**Architecture:** A pure lens-material component owns rest classification and adhesion state. Existing lens solver remains numerical authority for particle motion/mass. Layered behavior is enabled in the default app; legacy kernel fixtures retain homogeneous mode explicitly. Cannula flow acts locally on cortical adhesions; connected cortical contact can peel under aspiration, while nuclear bonds need mechanical/energy fracture. No state timer erases material.

**Tech Stack:** Godot 4.7.2, GDScript, existing feature branch.

**Spec:** Existing professional-simulation plan plus user's 2026-10-27 actual-surgery-like goal. Anatomical distinction grounded in AAO PPP and Columbia hydrodissection reference; coefficients and discretization are engineering choices, uncalibrated.

## Constraints / review focus
- Total mass and nuclear/cortical subtotals conserve initial mass.
- No flow, distant flow and ordinary phaco irrigation cannot cause hydrodissection.
- Local release must not weaken the opposite side instantly.
- IA may peel cortex; it must not act as ultrasound on the nucleus.
- Rendering/review must tolerate extra readonly material fields; exports preserve layer metrics.

### Task 1: Local material state
- [x] Write failing `test_lens_material.gd` for classification, local adhesion release, no-op/distant/invalid input, finite bounded adhesion and recovery reset.
- [x] Implement `lens_material.gd`: reset(positions), step(dt,tip,flow,positions,active), is_cortex(i), adhesion_acceleration(i,position), metrics(active,masses). Classification uses initial radial ring; outermost shell is cortex, inner particles nucleus. Adhesion tracks individual outer shell anchors, local exposure releases only nearby anchors.
- [x] Verify unit tests pass.

### Task 2: Physical coupling and app
- [x] Add failing `test_layered_lens.gd`: localized hydro changes adhesion without mass deletion, aspiration-only peeling differs from nuclear fracture, per-layer conservation and full removal feasible.
- [x] Add opt-in layered solver mode and hydro_flow, material spring/peel coupling; app enables layered mode and supplies hydro only for active cannula irrigation. Existing energy mode remains unchanged for baseline suites.
- [x] Expose nucleus/cortex/adhesion metrics in UI, objectives and session recording.
- [x] Run material, layered and baseline solver tests plus whole-app encounter and adverse-case tests.

### Task 3: Review and delivery
- [x] Independent code review; fix substantive findings.
- [x] Update model/validation docs, run GPU path, export Windows release and refresh ZIP.
- [x] Commit milestone; keep overall realism goal active until remaining anatomical contact/visual criteria are fulfilled.

Milestone verified: 20 suites pass; local GPU render, 1080p runtime and native release verified. Overall realism goal remains active.
