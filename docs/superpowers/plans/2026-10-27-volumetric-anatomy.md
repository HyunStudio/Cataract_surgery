# Volumetric anterior segment implementation plan

> **For agentic workers:** Execute inline with superpowers:executing-plans. User opted out of design questions and authorized completing the simulator.

**Goal:** Default playable app uses a common dimensioned, volumetric lens/bag/chamber rather than the flat legacy specimen, with working tool routes and rich recording.
**Architecture:** `anterior_segment.gd` owns mm scale and generated corneal shell/iris/bag profiles. Numerical solvers accept optional geometry before reset; their no-geometry defaults remain legacy kernel fixtures. App default creates shared geometry and binds numerical/rest states, surfaces, entry ports, tool working planes, IOL target and rendering to it. Existing fixed-coordinate app regressions opt explicitly into legacy geometry; new default app regressions must prove geometry and continuous healthy/adverse operation.
**Tech Stack:** Godot 4.7.2 / GDScript.

Reference findings: 2026-10-27-anatomy-clearance-findings.md. The chosen representative geometry is not patient-specific or biomechanically validated. Physical length scale does not turn normalized fluid/exposure/device parameters into real units.

Pre-flight interfaces: config → solver rest shape → render/collision; one config is binding for all. Recordings keep actual numerical positions and anatomical surfaces. Legacy fixtures must be explicit, never the default app or the new full encounter.

## Task 1: common geometry and numerical volume
- [x] RED geometry tests: known mm diameter/thickness, positive chamber clearance, both corneal surfaces/closed rim, bag enclosure and finite indexed surfaces; default app must exhibit actual new dimensions.
- [x] Implement common geometry, optional solver rest-shape initialization, material classification scaling and bounds. Preserve mass and numerical finiteness; adapt lens surface topology cache for same-size reinitialization.
- [x] Bind default app anatomy, entry paths/working planes, IOL and rendering to geometry; explicit legacy tests.

## Task 2: playable integration
- [x] New default full encounter uses normal tool actions only, follows collision-resolved routes, removes material, delivers/alines IOL, withdraws/inspects/completes and reviews without changing live state.
- [x] New default adverse case proves actual posterior injury/flow and healthy reset; old suites continue to pass in explicit legacy mode.
- [x] Display geometry follows solver surfaces; instrument handles outside operative field. Whole-shaft constraint remains a separately tracked next milestone, not claimed by tip tests.

## Task 3: verification and delivery
- [x] Independent review, full local runner, GPU normal/adverse capture and active workload, native release and archive CRC.
- [x] Update scope/performance evidence and commit. Keep full objective active until whole-tool interactions, complications, assets/pointer workflow and sustained performance requirements are met.

Review focus: display-only scaling masquerading as numerical geometry; inconsistent bounds/anchors/rest lengths; lens outside bag; stale same-count topology caches; legacy mode hiding default app failure; malformed geometry acceptance; cap/iris collision exemptions; capture/reset identity and normal routes.

Task 2 finding: accepted-flow-only point adhesion release reached only .679 after 225 model seconds in the enlarged specimen. The old reduced model lacks a route for fluid action to spread beneath the capsule. Add a bounded, connected cortical surface exposure field driven only by admitted flow, with conservative neighbor exchange and relaxation; retain explicit legacy local-dose fixtures. This is a reduced dissection field, not CFD or calibrated pressure. Verify local onset, finite propagation, absent-source no-op, bounds/reset and full app continuity.

Review fix evidence: actual-facet enclosure, legacy revision-zero replay and superficial corneal damage regressions observed RED, then GREEN after meridional sampling, presence-aware cache and two-boundary passage measurement. Wound passage regression also observed RED, then GREEN when a full-radius footprint was evaluated in the dimensioned tunnel cross-section instead of adding radius twice to a sloped surface projection. Existing legacy aperture tests remain unchanged.

Task 2 route ruling: withdrawal must align to the opened tunnel. The one-button current-axis request is collision-limited; the normal integration route moves through the actual opening and clears the corneal inner wall before retracting. Do not bypass the wall to make completion pass. This is an automated pose/action path, not completed pointer usability verification.

Fresh evidence: 33/33 local suites; NVIDIA GPU default normal/adverse/shape tests; accepted moving depth/power workload 46.95fps mean, 27.428ms P95, 8.108% removed mass and finite state. Stable 60fps remains unmet. Editor import/export and 120-frame native OpenGL launch exited 0; refreshed archive CRC passed. Overall goal remains active.
