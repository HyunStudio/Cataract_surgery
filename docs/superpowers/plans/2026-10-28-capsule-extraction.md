# Capsule flap extraction implementation plan

> **For agentic workers:** Execute inline with superpowers:executing-plans; uninterrupted implementation authorized by user.

**Goal:** Actual disconnected anterior membrane pieces can be grasped, folded against entry boundaries and extracted; normal default completion requires removal rather than leaving a floating central disc.
**Architecture:** A spatial height-field adapter indexes actual corneal/iris triangle projections and provides bounded thin-membrane vertex contact. The capsule tracks supported connectivity, detached components, per-vertex exterior passage and extracted rest area. Only a held, unanchored component whose complete vertex set passed the opened corneal channel is retired from actual triangles/constraints. Root shares anatomy/wounds and director records extraction evidence; rich recording remains geometry-based.
**Tech Stack:** Godot 4.7.2, GDScript.

Pre-flight: actual mesh → boundary projection → XPBD flap → director/recording. All share model coordinates; no timer, target-radius tissue deletion, hidden completion or clinical skill grade.

## Task 1: actual tissue boundary
- [x] RED height-field/boundary tests: actual face heights, intact shell blocks membrane points, opened passage permits crossing, exterior history/reset, iris contact, invalid geometry.
- [x] Implement cached projected triangle bins and bounded segment sampling/bisection. Contact is a thin-membrane vertex approximation, not continuum tissue/face collision.

## Task 2: supported flap topology and extraction
- [x] RED capsule tests: intact rim cannot extract, real blade trace detaches a retained component, held inside does not vanish, release does not vanish, all vertices must pass the entry, measured extracted area/triangles, reset and immutable capture.
- [x] Remove unsupported phantom constraints in dimensioned mode, cache connected components, couple boundary contact to detached vertices, retire only held fully exterior components.

## Task 3: playable sequence
- [x] Bind default app, exclude only own held detached flap from gripper tip contact, surface extraction objective and persistent director evidence/finish gate.
- [x] Update default full encounter to remove flap before hydro/phaco and demonstrate actual subsequent entry. Legacy fixtures remain explicit.

## Task 4: verify and deliver
- [x] Independent review, affected/full suites, GPU extraction/normal/adverse capture and measured active workload, native export/smoke and archive CRC.
- [x] Update documentation and commit. Full objective remains active for adaptive cut fidelity, whole-tool collision, dynamic particle/bag contacts, tool exchange, complications, pointer workflow, visual assets and sustained performance.

Review focus: phantom edges retaining disconnected faces; deleting attached/unheld/partly exterior material; area accounting; contact through closed walls; grasp self-collision; stale component/replay/reset identities; legacy tests replacing default verification. Coarse cut discretization and vertex-only contact are explicit fidelity limits, not completion of clinical capsulorhexis mechanics.

## Verification notes

The default full encounter initially failed extraction even though the isolated cloth path passed. Diagnostics showed infeasible intermediate pivot poses and lower-rim radial escape; neither was bypassed with tissue deletion or weaker tear thresholds. A reachable tunnel/pivot route, corrected near-zero aiming, and actual-rim-derived reduced lateral guard now pass the default encounter. Pressure exclusion for both-wetted free flaps and orphan-grasp cleanup each have observed failing regressions followed by passes. Independent review rechecked these paths and found no remaining blocker in the reduced scope.

37 headless suites and actual NVIDIA normal/adverse routes passed. GPU extraction and result captures were inspected. Build/performance evidence is recorded in SPECIALIST_VALIDATION.md after measurement. Full completion goal remains active; adaptive cut geometry and membrane-face mechanics are explicitly unfinished.

Windows editor/import, release export and native 120-frame smoke exited 0. Nine-file archive CRC passed. Fresh powered workload with retained flap measured 22.92fps, showing a boundary-contact cost; next implementation should profile and reduce this cost before adding more scene complexity. This milestone is complete; the full actual-surgery-like simulator objective remains active.
