# Implementation progress — 2026-10-12

## Delivered in repository
- Headless Python simulation engine: nine coherent educational phases, safe abort, synthetic vitals, 4 seeded scenarios, strict guards, scoring, bounded JSONL event output.
- Pygame UI source: custom vector 2.5D eye, synthetic monitor, interactive cursor tasks, phase progress, status overlays, JSONL export and screen scaling.
- Tests and CI: Python 3.12/3.13 GitHub Actions, deterministic flow, input fuzzing, safety event tests.
- The original 32-work-package roadmap is still the product target, **not** a completion checklist for these proof-of-concept implementations.

## Verification status
- Headless engine and static Python compilation: executed and passed locally.
- CI initial runs: green; check the latest Actions run before reporting latest-commit pass.
- Pygame window launch and input interaction: **NOT EXECUTED** (pygame unavailable in runner, external package installation blocked).
- Actual 3D viewport, ray picking, rendering performance or clinical fidelity: **NOT IMPLEMENTED/VALIDATED**.

## Remaining for completion
1. Verify Pygame GUI on Windows using actual hardware; record startup, mouse path and screenshot.
2. Create a functional 3D proof-of-concept with ModernGL or an alternate renderer using a measured feasibility gate.
3. Replace placeholder eye and instruments with properly licensed 3D assets and validated camera/depth transforms.
4. Improve motion, transparency, procedure interactions, simulated monitor behavior, scenario richness, feedback and accessibility.
5. Implement full input journal and replay reconstruction (current seeded repeated scripting is deterministic; exported JSONL is an event trace, **not** a full replay file).
6. Verify QA: GUI smoke tests, graphics regressions, 1080p/4K performance, OS-level dirty tests and clinical plausibility review.
7. Keep test claims limited to actually executed coverage. No validated clinical instruction or surgical outcome inference.

## Quality gate
Never call this a 'completed 3D simulator' until GUI execution, full procedure continuity, exception scenarios, performance and automated regression are verified on the intended target machine.

## Development increment — input replay and dirty-test coverage
- Added `ophthosim/replay.py` with compact deterministic semantic command journal, replay loader, strict schema checks, SHA-256 input/state/event consistency and bounded capture.
- GUI `E` export saves both synthetic trace and verifiable replay; errors are handled instead of crashing the game.
- Crucial edge case: **failed but in-range removal attempts can accumulate synthetic tissue stress** and are therefore recorded for exact hazard reproduction.
- Extra tests cover normal end-to-end reproduction, motion/vital/capsule alerts, paused ticks, rejected tool actions, tampered records, oversized/malformed inputs, replay overflow, 2,000 randomized inputs and GUI export.
- Remaining: animated viewer for reconstructed sessions, rich input telemetry, clinical and Windows/GPU visual validation, true 3D renderer.
- At the time of this edit, the latest CI must still be checked for the new extreme-input tests; results must not be inferred from previous green runs.
