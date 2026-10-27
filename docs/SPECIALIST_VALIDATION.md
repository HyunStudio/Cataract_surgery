# Integrated specialist simulator validation — 2026-10-27

This report applies to the new default `simulator.tscn`, not the earlier procedural `main.tscn`.

## Verified locally

- Windows, Python 3.12.10, Godot 4.7.2 stable official `ed1daf0bf`, Compatibility OpenGL 3.3, NVIDIA driver 566.14, RTX 3070 Laptop GPU.
- Python regressions: **522 passed in 30.57 seconds**.
- All **18 Godot headless suites** passed through `tools/run-godot.ps1 -Test`: session, world, input, integration, playthrough, capsule solver, lens/fluid solver, instrument rig, simulator, case director, case recording, incision, IOL, lens surface, operating app, simulation UI, surgical display, full encounter.
- Full new-mode encounter: three preparation checks; continuous blade entry; membrane cutting changes connectivity; adaptive local phaco/aspiration removes 100% material in 321 solver steps; user-held IOL delivery and independent elastic unfolding; tool withdrawal; three measured inspections; completed ending; immutable visual review. Test drives constrained instrument poses and user action methods, with no tissue/mass/completion mutation. It is an automated integration route, not a human usability or clinical evaluation.
- The same full encounter passed with a real NVIDIA GPU context. `test_simulator_render.gd` passed actual contact, traction rupture and local aspiration (5.4% removed, remaining >50%) and captured four states.
- Additional operating tests cover a seeded patient-motion event, release/fresh-press pedal rearming, paused observation until assessment, persistent two-hand grasp, source-injector binding during partial IOL delivery, depth reset, help-modal release/freeze, review keyboard isolation and sound callback.
- Minimum-width UI layout tested at 1152×800; 1600×1000 microscope and result captures visually inspected. New-mode GPU images: `godot/reports/professional-microscope.png`, `professional-results.png`, `physics_01_intact.png`–`physics_04_local_aspiration.png`.
- Independent code review found partial IOL delivery following the selected hand and stale aiming depth after new case. Both were fixed and regression tested. Additional inspection fixed path-length accounting for direct pitch/insertion changes and review keyboard shortcuts.
- Windows release export and a 120-frame native OpenGL launch completed with exit 0 and no script/shader errors. Source/editor import completed without errors. No remote GitHub CI success is claimed.

## New-mode GPU measurement

`godot/tests/benchmark_simulator.gd` runs the integrated microscope, live capsule/lens physics, persistent dual instruments and monitor/UI for 30 seconds at 1920×1080. First 2 seconds are discarded. It does not benchmark powered tissue removal or all scenarios.

| Metric | Observed |
|---|---|
| Frames after warmup | 1,628 |
| Mean frame time / FPS | 17.202 ms / 58.13 fps |
| P95 frame time | 21.149 ms |
| GPU | NVIDIA GeForce RTX 3070 Laptop GPU |

This is a short shared-desktop observation, not a 60fps guarantee, endurance test or cross-hardware acceptance. The earlier game's 300-second 59.97fps result does not apply to this mode.

## Model scope and remaining fidelity work

The playable integrated path is verified. It is an initial specialist simulation game, not the completion of the entire historical 32-work-package roadmap. The models are uncalibrated: 217-node XPBD membrane, 111-particle connected lens, single fluid compartment, elastic point implant and traced incision gap. Mesh surface interpolation follows physical positions/connectivity. Mechanical tip contact and local energy/aspiration are implemented; full shaft/cornea/posterior-capsule contact, anatomical layer hydrodissection, separate cortical material, physiological feedback, real device calibration, photorealistic assets and clinical/haptic validation are not.

Record review uses sampled immutable visual states (2-second interval, 900 frames, 32MB export limit); it is not deterministic physical input replay. The director checks simulation evidence and provides no clinical skill grade. See [Korean controls and scope](SPECIALIST_SIMULATOR_KO.md).

## Reproduce

```powershell
powershell -ExecutionPolicy Bypass -File tools/run-godot.ps1 -Test
python -m pytest -q
.tools/godot/Godot_v4.7.2-stable_win64_console.exe --path godot --resolution 1600x1000 --script res://tests/test_simulator_render.gd
.tools/godot/Godot_v4.7.2-stable_win64_console.exe --path godot --resolution 1600x1000 --script res://tests/test_full_encounter.gd
.tools/godot/Godot_v4.7.2-stable_win64_console.exe --path godot --script res://tests/benchmark_simulator.gd
```
