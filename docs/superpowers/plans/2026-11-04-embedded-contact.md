# Retained material contact implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Couple actual retained fine-face contact to the optional embedded membrane, then qualify real instrument acquisition and motion.

**Architecture:** Query only retained fine triangles reconstructed from their original material control map. Pull distance derivatives back through that fixed affine map. Use exact smooth-feature distance Hessians from minimizer elimination; reject undefined/ambiguous curvature. Subsequent coupled solves must include grasp and unilateral reactions together and certify continuous motion.

**Tech Stack:** Pinned Zig C++17, existing capsule/triangle query, Python/NumPy independent tests, Godot4.7.2.

**Spec:** docs/superpowers/plans/2026-11-04-embedded-grasp.md, Required contact boundary.

## Global constraints

- Retain force1e-8, gap1e-9 and complementarity1e-11; do not change geometry to pass.
- No coarse collider over removed material, no contact-safe claim from float publication tolerance.
- Default simulator and previous failures remain visible until full input qualification.

## Review focus

- Retained subtriangle excludes empty material of its parent cell.
- Capsule axis reversal and triangle/control permutations preserve physical results.
- Feature ties/zero distance/degeneracy never publish a fabricated Hessian.
- Malformed maps, nonfinite inputs, singular feature systems fail atomically.
- Small fine faces retain correct original control force, not a nearest-node approximation.

## Task 1: independent fine contact derivative primitive

- [x] Add failing native tests for missing embedded distance ABI, analytic face/edge/vertex branches, affine chain rule, finite-difference Hessian, exclusions and atomicity.
- [x] Implement native/embedded_contact.h, exported via contact_distance.cpp, with original fine witness preserved and squared-distance gradient/Hessian in three control coordinates.
- [x] Track header in build provenance, run old and new distance suites, read-only review and commit.

## Task 2: precise contact state and bridge

- [ ] Preserve double material weights across cut transfers or certify remap trajectory.
- [ ] Add typed engine contact bridge and fine support export; independently check physical force and actual retained geometry.

## Task 3: coupled motion and actual acquisition

- [ ] Implement same-objective grasp+unilateral contact solve and continuous tool/anatomy guard.
- [ ] Add continuous jaw/face material attachment, tool roll throughout physical/render paths, partial-tip enrichment as needed.
- [ ] Qualify actual knife-to-forceps case, then full preparation-to-review mouse input, GPU and Windows delivery.

## Ledger

The previously qualified grasp core is an optional primitive, not the default application. Whole simulator is unfinished. Task1 starts with a missing ABI test, not a release claim.

Task1: initial missing local DLL was built to establish the intended missing-ABI RED (4f52f2). Implemented minimizer Schur Hessian, including mixed r*dw terms, and B-transpose pullback. Build4aa6ea terminal0, qualification968c03 terminal0:17 old+10 new tests pass. Includes exact feature switches, ties, tiny retained face, deformed controls, map/input/null-output atomicity, axis/control/fine permutations and absent parent material. Read-only core reviewer independently reran27tests, no actionable findings. Source-bound report: docs/assets/embedded-contact-core-validation-2026-11-04.json. This is a static primitive; no coupled contact, continuous clearance, engine integration or app completion claim.
