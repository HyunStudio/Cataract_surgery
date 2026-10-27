# Packed visual snapshots implementation plan

> **For agentic workers:** Execute inline with superpowers:executing-plans. User authorized uninterrupted implementation of the complete simulator.

**Goal:** Reduce per-frame visual snapshot allocation while preserving exact existing capture/review data and last-applied-state isolation.
**Architecture:** Solvers expose copied packed presentation state. A small adapter reconstructs public dictionaries only on explicit rich capture. Rendering keeps a frozen packed lens snapshot; dictionary replay fixtures retain the existing path. Both lens and capsule snapshots use packed arrays while dictionary replay fixtures preserve their existing path.
**Tech Stack:** Godot 4.7.2 / GDScript.

Pre-flight: solver snapshot → display freeze → rich recording; preserve all existing particle/bond fields and old recording format. No interface conflict: compact state stays internal to display, capture_frame remains rich.

## Task 1: packed lens capture
- [x] RED `test_visual_snapshot.gd`: lens exposes packed snapshot, expand equals public mirror, mutating solver/returned snapshot cannot modify prior captures; all particle/bond fields and empty/replay fallback.
- [x] Implement lens visual_state + visual_snapshot adapter; display apply freezes packed lens, capture_frame expands only when requested.
- [x] Run new test, display/recording/application/injury suites, full runner.
- [x] Measure fresh headless snapshot microbenchmark and GPU powered workload against historical baseline; retain measured limits, no 60fps claim without evidence.

## Task 2: deliver
- [x] Independent review, GPU full encounter and native import/export/smoke.
- [x] Update docs and ZIP, CRC verify, commit. Overall realism goal remains active.

Review focus: snapshot aliasing, velocity/mass/cortex/adhesion/damage preservation, same-count topology change, replay dictionary compatibility and stale captures after live solver motion.

Task 1 scope ruling: the lens copy microbenchmark measured 2.068ms rich versus 0.061ms packed, proving per-frame dictionary allocation material. Extend the same isolated adapter to capsule edges to remove the other large row-copy while preserving all fields; no physics or recording format changes.

Task 1 complete: new method tests observed RED before implementation; 28/28 standard suites and independent focused review passed. Microbenchmark frozen values equal, total copy operations reduced by about 2.9ms on this machine. GPU active workload 56.01fps mean / 22.786ms P95; stable 60fps remains unmet.
Task 2 complete: full GPU encounter, import/export, native 120-frame smoke and refreshed ZIP CRC passed. Overall objective active; next anatomical geometry/whole-tool requirements recorded separately.
