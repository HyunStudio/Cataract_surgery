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

- [ ] Add isolated probe endpoint and failing tests for runtime interval enclosure and exact caller control restoration.
- [ ] Implement small private RAII header, apply before arithmetic at native numerical entry points; prove pinned compiler respects the boundary.
- [ ] Ensure build provenance and cache dependencies include header; rebuild affected independent artifacts.

## Task2: cross-environment qualification and actual engine

- [ ] Requalify old distance/guard/merit/coupled tests plus new FEM/grasp/curved cases under both significand and rounding contexts.
- [ ] Actual frozen Godot curved11stage and focused script regressions; read-only review.
- [ ] Record exact supported platform and limits, then continue jaw/controller/anatomy/partial-tip work. No whole-surgery/release claim from this boundary alone.

## Evidence

Confirmed original engine curved failure also reproduces underx87CW0x37f; intermediate AL policy fixed separately with final gates unchanged. Read-only reviewer supplies distinct pre-existing interval counterexample: callerPC53 yields1 for1+2^-54, then one80bit ULP expansion reaches only1+2^-63. This plan addresses the remaining interval contract rather than changing engine precision to make tests green. Current GodotPC64 test results are scoped to that actual environment.
