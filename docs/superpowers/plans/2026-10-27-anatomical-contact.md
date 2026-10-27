# Continuous anatomical contact implementation plan

> **For agentic workers:** Use superpowers:executing-plans. User authorized continued development toward the full realism goal; no additional design approval gate.

**Goal:** Replace numeric tip-height guards with continuous contact against visible tissue geometry and real capsule openings.

**Architecture:** A pure swept-sphere/triangle kernel detects face, edge and vertex contacts. Shared generated anatomical meshes drive both display and collision. A coordinator handles surface selection, limited contact sliding and actual incision windows. The capsule uses current solver positions and surviving triangle indices. Controller keeps its pivot kinematics; no phase flag grants capsule entry.

**Tech Stack:** Godot 4.7.2/GDScript, existing isolated repository branch.

**Spec:** docs/REALISM_COMPLETION_KO.md and user actual-surgery-like simulation goal. Geometry matches current synthetic scene coordinates, not clinical dimensions.

## Constraints and review focus
- Detect high-speed crossings, contacts along triangle edges/vertices and two-sided withdrawal without sticking.
- Removing triangle connectivity opens geometry; counters cannot create a passage.
- Invalid/nonfinite motion must be rejected atomically; no unsafe solver poses.
- Knife can cut capsule when actively operated, but unpowered knife obeys contact.
- Corneal passage follows actual incision paths; prepared practice explicitly supplies those paths.
- Preserve full physical layered encounter, bimanual holding, fresh pedal gates and immutable visual review.
- This milestone is tip contact only. Shaft contact, mechanical injury and flow/hazard coupling remain subsequent work, not claimed done.

### Task 1: Geometric kernel
- [x] RED tests in `test_surface_contact.gd`: both plane crossing directions, fast crossing, edge grazing, vertex grazing, real triangle hole, no false distant hit, tangent withdrawal, invalid input.
- [x] Implement `surface_contact.gd`: sweep(from,to,radius,positions,triangles)->Dictionary {hit,position,normal,time,triangle}; face-plane candidates + swept cylinders/spheres for edges/vertices; per-face bounds reject.
- [x] Verify exact contact locations and finite unit normals.

### Task 2: Shared anatomy and coordinator
- [x] RED tests `test_anatomy_contact.gd` for pupil hole vs iris, posterior bowl, corneal dome, local wound window, current capsule hole, blade activation and sliding.
- [x] Implement `anatomy_surfaces.gd` ring/dome/bowl indexed meshes and ArrayMesh conversion; `anatomy_contact.gd` resolves earliest surface contacts and slides with bounded iterations.
- [x] Use shared surfaces in `surgical_display.gd`; hide old mismatched corneal sphere.

### Task 3: Controller and verification
- [x] Replace `_advance_motion` constant y guards with coordinator, expose contact metrics/status, supply prepared practice incision paths.
- [x] Ensure full encounter enters capsule via actual opening; add application regression that intact capsule blocks phaco.
- [x] Independent code review, all affected domain/app suites, GPU captures and runtime; fix important findings.
- [x] Update docs/Windows ZIP, commit milestone, keep overall realism goal active.

Verified: 23 suites, full actual-GPU encounter, local GPU physics captures, moving powered workload benchmark and Windows native release. Active workload remains below 60fps; full tissue injury and shaft contact remain separate required work in the active overall goal.
