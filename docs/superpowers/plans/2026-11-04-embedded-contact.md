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

- [x] Preserve double material weights across cut transfers or certify remap trajectory.
- [x] Add typed engine contact bridge and fine support export; independently check physical force and actual retained geometry.

## Task 3: coupled motion and actual acquisition

- [ ] Implement same-objective grasp+unilateral contact solve and continuous tool/anatomy guard.
- [ ] Add continuous jaw/face material attachment, tool roll throughout physical/render paths, partial-tip enrichment as needed.
- [ ] Qualify actual knife-to-forceps case, then full preparation-to-review mouse input, GPU and Windows delivery.

## Ledger

The previously qualified grasp core is an optional primitive, not the default application. Whole simulator is unfinished. Task1 starts with a missing ABI test, not a release claim.

Task1: initial missing local DLL was built to establish the intended missing-ABI RED (4f52f2). Implemented minimizer Schur Hessian, including mixed r*dw terms, and B-transpose pullback. Build4aa6ea terminal0, qualification968c03 terminal0:17 old+10 new tests pass. Includes exact feature switches, ties, tiny retained face, deformed controls, map/input/null-output atomicity, axis/control/fine permutations and absent parent material. Read-only core reviewer independently reran27tests, no actionable findings. Source-bound report: docs/assets/embedded-contact-core-validation-2026-11-04.json. This is a static primitive; no coupled contact, continuous clearance, engine integration or app completion claim.

Task2 precision: new actual finite two-cut test b5118f RED2, double physical/history interpolation errors1.916924e-8 and2.239164e-8. Compose accepted per-source-fine-face B with normalized cut bindings; validate optional precise maps in Support.build instead of refitting float rest coordinates. bcf3f4 and expanded malformed-map test57f4a9 GREEN0, requiring errors<2e-14. Existing support continuity, support mass, accepted holds and whole-patch staging remain. This map consistency alone does not certify material partition geometry or continuous clearance.

Actual native engine6stage probe62198 terminal0 (fem-extension-zcb0u3ia): old35step force/recut and17step one/two-hand/release/recut pass, mass5.319326346740127, force8.0340765354e-9/gap1.1102230246e-16. Report: docs/assets/embedded-precision-native-validation-2026-11-04.json. Fresh independent Godot FEM reference numerical payload is unchanged exactly; only Support source hash refreshed. Native qualification1b5dfb terminal0,15tests pass; docs/assets/fem-precision-core-validation-2026-11-04.json. Read-only review of map composition/validation/transaction found no actionable issue.

Focused regression helper53187 terminated1 because it expected a numeric zero-failures marker from test_surgical_display, which correctly printed SURGICAL DISPLAY: PASS and exit0. This was a harness completion-marker defect, not a product failure. Fixed exact completion alternatives for numeric and PASS tests; fresh full frozen rerun51737, no killed/restarted live process.

Rerun51737 terminal0: fresh import plus all30focused source-frozen suites pass, no engine errors/leaks or source changes. Report: docs/assets/embedded-precision-regression-2026-11-04.json. New test is in run-godot.ps1; full -Test remains RED at the separately retained default closed-blade/fine-traction cases. All started builds/checks are terminal. No default backend switch, main integration, push or Windows release. Active goal progresses to contact bridge/coupled mechanics.

Next: typed native contact bridge and retained fine support export, then original-force coupled grasp/unilateral contact and whole-interval guard. Actual jaw face acquisition, roll, partial-tip enrichment and complete input/GPU/Windows qualification remain open. Default application stays on its existing path; actual closed knife mass-resolution and legacy fine-traction failures are unchanged and still listed in run-godot.ps1.

Task2 contact: old-DLL actual bridge97960 terminal1 missing contact_fem (intended RED). Typed method and embedded_contact.h build/cache provenance added; extension build52795 terminal0. State-wrapper test283081 RED1 missing API, then4c0800 GREEN0. contact_geometry exports duplicate accepted coarse/fine histories, actual fine connectivity and per-face B; contact_face reads only its three original controls, validates native packed fields/shape/finiteness/status and independently checks numerical witness reconstruction, convex closest-point KKT signs, squared gap, B-transpose witness gradient and Hessian symmetry. CHECK1e-11 is a static consistency diagnostic, not the final force/gap/CCD certificate or a replacement for coupled equilibrium.

Real frozen8stage13909 terminal0, fem-extension-2ai50f2i: existing legacy/FEM/grasp bridges,35force ticks and17held ticks still pass; new typed contact finite differences and actual deformed curved refined contact pass.217controls404fine faces, chosen fine face38, measured gap.01999999918305446, continuous material point/virtual-work displayed errors0. Report: docs/assets/embedded-contact-engine-validation-2026-11-04.json. Query does not integrate time or create attachment. It returns continuous B-transpose-w material weights for subsequent true jaw acquisition; no nearest-vertex substitution. Read-only reviewer found no actionable math/type/bounds/aliasing/provenance defect. Focused31suite frozen regression99157 is running separately.

Next implementation boundary: the actual same-objective implicit solve must include both exact grasp equality and unilateral retained-face contact reactions. Use actual fine maps throughout; no postprojection may replace force balance. Preserve original force1e-8, physical gap1e-9 and complementarity1e-11 and certify entire tool/tissue interval before acceptance. The new static CHECK cannot qualify that boundary. Only then connect actual jaw acquisition, tool roll and partial-tip support to full operator case.

Focused frozen99157 terminal0: fresh import and all31suites pass, no source changes/errors/leaks. Report docs/assets/embedded-contact-regression-2026-11-04.json. State-contract fake backend covers wiring/rejection only; actual accuracy comes from native/real-engine tests, not fabricated Hessian. All started processes terminal. Default GS closed-blade/fine-traction failures remain; no default backend change, main integration, push or release. Previous goal turn and this turn are progress (committed precision maps, then actual bridge/export/real curved checks), not a blocker. Continue active complete-simulator goal with coupled reactions.
