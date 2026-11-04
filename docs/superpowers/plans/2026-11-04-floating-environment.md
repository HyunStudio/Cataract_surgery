# Numerical calling-environment boundary plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline. No implementer delegation.

**Goal:** Make native long-double interval and solver contracts independent of caller precision/rounding controls while restoring caller state exactly.

**Architecture:** Scoped x86-64 numerical entry boundary establishes64bit x87 significand and nearest rounding (including SSE rounding/subnormal controls as needed), saves/restores exact caller controls on every return/exception and supports nesting. Entry guards cover distance/embedded geometry, continuous guard, merit public helpers and original FEM/legacy coupled exports. No global persistent host-state change, no lower-precision workaround. Audit compiler ordering under pinned Zig/Clang and test actual runtime operands.

**Tech Stack:** Pinned Windows x86-64 Zig0.17.0, C++17/Eigen, Python ctypes, actual Godot4.7.2.

**Spec:** Coupled FEM contact plan's confirmed callerPC53 interval issue; full simulator objective remains intact.

## Constraints and review focus

- `Bound(1)+Bound(2^-54)` under callerPC53 must enclose exact value after the callee scope.
- Restore exact x87 control and SSE control state for valid, invalid, budget and exceptional paths; nested scopes must not leak changes.
- Preserve final force1e-8/gap1e-9/comp1e-11, geometry and original objective.
- Original zero-body/grasp behavior must agree under the same established numerical contract.
- Guard/merit conservatism needs bothPC53/PC64 and directed-rounding caller regression, not status-only tests.
- Product dependency/source manifests AND object cache keys must include the new boundary header transitively.

## Task1: scoped contract and a real enclosure counterexample

- [x] Add isolated probe endpoint and failing tests for runtime interval enclosure and exact caller control restoration.
- [x] Implement small private RAII header, apply before arithmetic at native numerical entry points; prove pinned compiler respects the boundary.
- [x] Ensure build provenance and cache dependencies include header; rebuild affected independent artifacts.

## Task2: cross-environment qualification and actual engine

- [x] Requalify old distance/guard/merit/coupled tests plus new FEM/grasp/curved cases under both significand and rounding contexts.
- [x] Actual frozen Godot curved11stage and focused script regressions; read-only review.
- [x] Record exact supported platform and limits, then continue jaw/controller/anatomy/partial-tip work. No whole-surgery/release claim from this boundary alone.

## Evidence

Confirmed original engine curved failure also reproduces underx87CW0x37f; intermediate AL policy fixed separately with final gates unchanged. Read-only reviewer supplies distinct pre-existing interval counterexample: callerPC53 yields1 for1+2^-54, then one80bit ULP expansion reaches only1+2^-63. This plan addresses the remaining interval contract rather than changing engine precision to make tests green. Current GodotPC64 test results are scoped to that actual environment.

## Execution ledger

Previous goal turn was progress f23fa4c: actual curved coupling and inexact-AL policy fix. This boundary is the next actual release prerequisite, not an external blocker.

Probe contract4tests76192 RED4, then Scope implementation1b669d GREEN4. Runtime raw unscoped counterexample is retained as a diagnostic: enclosurefalse underPC53 andtrue underPC64. New RAII keeps caller x87CW/SSEMXCSR, establishes PC64/RN and SSE RN/gradual-underflow/DAZoff, restores exact saved values on normal, early, exceptional and nested exits. No global persistent host-state setting. Applied to actual geometry/guard/merit/model/old and new solver boundaries before arithmetic. Native final force1e-8/gap1e-9/comp1e-11 and geometry unchanged.

Ruling: quoted local header dependencies must be captured transitively rather than independently remembered in10build scripts, because new Scope is shared by every numerical artifact. Added native_build_provenance source traversal for existing workspace-local quoted C/C++ includes, with cycle/root checks. Native provenance31919 RED2 (missing headers/outside root), then37500 GREEN2. Third-party angle headers remain protected by existing compiler/dependency pins. Extension object-cache key explicitly includes Scope header. All8affected standalone artifacts and66unit extension rebuilt terminal0.

Mode grid expanded to64caller contexts: 2x87precisions x4x87rounding x4independentSSErounding x2FTZ/DAZ settings. Four wrapper paths(normal/early/exception/nested) preserve full controls;8real API cases(distance/invalid, guardclear/crossing, FEMsuccess/budget/invalid, conservative contact merit) preserve controls and produce bitwise-identical outputs. Independent80digit Decimal merit bounds included. Raw counterexample demonstrates why the scope is needed. Test-only setters/probes are never linked into product.

Pinned O3 assembly audit65177 terminal0 (Zig -S injects an unused-c warning, suppressed only for this assembly-only diagnostic): Scope constructor atline349 before runtime fadd435, destructor paths634/701/711/764. Runtime data tests confirm current pinned binary behavior. Read-only reviewer finds no actionable defect; flags include -fno-rounding-math, so memory barriers do NOT establish compiler-independent ordering. Qualification is explicitly the pinned toolchain and tested APIs; future toolchain changes must requalify. No broader compiler portability claim.

Full source-bound qualification66372 terminal0:189tests across15native suites, including old distance/guard/merit/model/coupled/trajectory/anatomy and new FEM/grasp/curved, FP and provenance. Fresh actual11stage10232 terminal0 in fem-extension-p9yvveua, no errors/leaks/source changes; all curved cases still pass. Focused32script rerun started separately to finish the planned gate. No default app/main integration/push/release. Real-time contact cost, true jaw/controller/anatomy/partial-tip and full input/GPU/Windows case remain required.

Focused script regression80241 completed terminal0:32 suites. Archived native, actual engine and focused regression reports under docs/assets/fp-boundary-*-validation-2026-11-04.json. This closes the scoped boundary milestone only; full simulator work continues.
