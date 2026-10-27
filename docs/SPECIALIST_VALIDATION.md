# Integrated specialist simulator validation — 2026-10-27

This report applies to the new default `simulator.tscn`, not the earlier procedural `main.tscn`.

## Local structural injury milestone — 2026-10-27

- Fresh standard runner: **27 Godot suites passed**. Added local injury, posterior boundary flow, persistent injury case state and actual-application suites. Python implementation/tests unchanged in this milestone.
- Actual local corneal/posterior contact exposure now refines nearby triangles and removes a bounded aperture. Collision and display use the resulting shared topology, with measured missing area and persistent case evidence. Distant geometry remains, topology is capped at 8,192 vertices/faces per surface, stale revisions are ignored and malformed batches reject atomically.
- Posterior and corneal missing area drive separately reported boundary conductance. Every macrostep's averaged actual flows obey compartment volume balance, including lower/upper bounds; posterior outflow does not delete lens mass. This remains a single compartment with an unmodeled downstream reservoir, not vitreous or dropped-nucleus dynamics.
- Actual application tests verify blade puncture, powered stationary contact, energy after switching tools at a resting contact, alert/release, completion rejection after acknowledgment, reset and immutable pre/post injury review. Independent review reproduced stationary power falsely contacting an existing incision; moving and stationary contact now share the same full-radius wound exclusion. A second structural injury raises a new event after acknowledgment.
- Independent reviewer reran injury application/case, geometry contact and injury component suites with zero failures. Additional tests cover tiny refined face contact, excluded-nearer-face handling, non-energy-tool exposure rejection and area/flag consistency.
- Healthy full layered encounter and adverse application tests passed on NVIDIA RTX 3070 Laptop GPU. Captures: `godot/reports/injury-contact.png`, `injury-debrief.png`, `professional-results.png`. The healthy fixture releases the blade and follows the open chamber route before anterior cutting; an active blade swept through intact cornea causes real injury instead of being exempted.
- Fresh 30-second moving powered workload, 1920×1080, 2-second warmup: **1,198 frames; mean 42.75 fps / 23.392 ms; P95 32.419 ms; removed mass 48.65%; finite true**. No concurrent GPU test during this measured run. This fails the stable 60fps target; performance optimization remains open.
- All injury thresholds, loads, aperture radius and conductance coefficients are synthetic engineering choices. They are not tissue failure force or clinically validated limits. Anatomical barrier reference: [AAO posterior capsule rupture signs](https://eyewiki.aao.org/Intraoperative_Signs_of_Posterior_Capsular_Rupture).
- Editor import and Windows release export exited 0; the exported native OpenGL executable ran 120 frames and exited 0 without script/shader errors. The refreshed nine-file ZIP passed CRC verification. Overall goal remains active for shaft/jaw contact, vitreous/dropped material/implant support, complication handling, richer anatomy/room assets, full pointer workflow and sustained performance.

## Continuous anatomical tip contact milestone — 2026-10-27

- Fresh standard runner: **23 Godot suites passed**, including surface-contact, anatomical-coordinator and anatomical-application suites. Existing Python source/tests were unchanged in this milestone.
- The swept sphere kernel checks triangle faces, edge cylinders and vertex spheres, with two-sided contact and bounded sliding. Tests cover fast crossings, actual missing triangles, tangent withdrawal, internal coplanar seams, malformed topology and nonfinite/overflowing coordinates.
- Shared generated corneal dome, conical finite-thickness iris and posterior bowl now drive rendering and collision. The previous displayed iris height and old numeric depth guard disagreed; both were replaced. The anatomical dimensions and app tip radius `.01` are synthetic engineering choices, not calibrated anatomical/tool data.
- In the actual app, intact capsule blocks a phaco tip and interposed membrane prevents its energy from acting on lens material. Fluid aspiration in the anterior compartment remains possible. A blade-created opening permits subsequent local phaco entry. Grasp reach and physical contact radius are separate.
- Full layered encounter passed both headless and on the NVIDIA GPU with the new contacts: entry → membrane opening → cannula local flow release → nuclear phaco → separate cortical IA → IOL → final inspections → completed. Captured GPU report: `godot/reports/full-encounter-gpu.json`.
- GPU traction/local aspiration suite passed after its old teleporting fixtures were replaced with actual chamber routing and a blade-created local access opening. Intact/traction/rupture/local-removal images were visually inspected.
- Independent review reproduced a corneal aperture that accepted a sphere whose center fit but whose footprint overlapped intact surface. Fixed by testing projected surface distance plus the full tip radius. Reviewer independently reran edge/center crossings at radii `.01` and `.018` and the large-coordinate rejection; all passed. All three new suites are in the local runner and CI workflow (remote CI not claimed).
- Interior contact query averaged **1.737 ms before broad bounds rejection, 0.770 ms after** in the 120-query microbenchmark. Rendering/solver performance is separately measured below.

### Actual moving, powered workload

`benchmark_active.gd` prepared a real membrane opening, then continuously moved a powered phaco tip in the chamber for 30 seconds at 1920×1080. First 2 seconds discarded. This is the first new-mode measurement with local fracture/aspiration and continuous contact active rather than an idle field.

| Metric | Observed |
|---|---|
| Sampled frames | 1,295 |
| Mean FPS / frame time | 46.12 fps / 21.683 ms |
| P95 frame time | 29.294 ms |
| Removed mass at end | 48.65% of initial total mass |
| Finite model state | true |

This does **not** satisfy a stable 60fps active-operation target; profiling/optimization and longer duration acceptance remain required. It is not comparable to the earlier idle measurements as if they were the same workload.

Tip collision is a sphere approximation, not complete shaft/jaw/blade contact. Contact-limited movement is recorded per hand and summed; those metrics are not tissue force or damage. This older milestone preceded the structural injury implementation above. Full hardware/tool shapes and complete pointer-driven workflow verification remain open in [overall completion criteria](REALISM_COMPLETION_KO.md). Overall goal remains active.

## Layered material milestone — 2026-10-27

The default app now enables nuclear/cortical material identity, localized capsule-cortex adhesion and cortical aspiration peeling. Homogeneous kernel fixtures remain available as the explicit legacy solver mode.

- Fresh run of `tools/run-godot.ps1 -Test`: **20 Godot suites passed**, including new lens-material and layered-lens tests.
- Extended complete encounter passed: blade entry/membrane opening → cannula local adhesion release using actually admitted compartment inflow → nuclear phaco (169 steps, approximately 51.35% of initial total mass) → separate IA cortical removal → IOL → final checks → completed. Final nuclear and cortical mass both zero, total removed mass 1.0, 52 visual frames, 102.15 seconds of simulated time. No tissue state is edited by the test driver.
- A separate cortical IA test removed all cortical mass (48.65% of initial total mass) without ultrasound while retaining all initial nuclear mass (51.35%). Closed/full compartment with zero actual admitted inflow cannot release adhesion despite a nonzero commanded pump.
- Independent review found endpoint-order dependence in cortex-cortex peeling. The fix evaluates both eligible endpoints and uses the strongest local contribution; swap-symmetry regression passes.
- GPU local traction/rupture/aspiration test passed with the material shader, and the microscope image was visually inspected. Material colors are cached by fixed source topology; tissue movement still updates geometry.
- New measured 30-second 1080p live-physics sample, after editor/export activity had finished: **1,498 frames, mean 53.47 fps / 18.701 ms, P95 23.920 ms** on the same RTX 3070 Laptop GPU. Earlier concurrent runs ranged 48.97–51.41fps. The previous 58.13fps integration measurement below is historical, before this material milestone. Active surgery and endurance acceptance remain pending.
- Fresh native Windows release/export smoke: exit 0 with the real NVIDIA OpenGL context. Python source was unchanged; the earlier 522-pass result remains regression evidence, not a new rerun.

This is still a reduced radial-shell/point-spring model. It is not continuum hydraulic layer separation or validated clinical biomechanics. [Overall completion criteria](REALISM_COMPLETION_KO.md) remain active, especially actual anatomical surface contact, posterior/corneal injury, geometry/visual fidelity and full pointer-driven operating verification.

## Earlier integration verification

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

The playable integrated path is verified. It is an initial specialist simulation game, not the completion of the entire historical 32-work-package roadmap. The models are uncalibrated: 217-node XPBD membrane, 111-particle connected lens, single fluid compartment, elastic point implant and traced incision gap. Mesh surface interpolation follows physical positions/connectivity. Mechanical tip contact and local energy/aspiration are implemented; full shaft/jaw/blade contact, continuum layer hydraulics, vitreous/dropped-material dynamics, physiological feedback, real device calibration, photorealistic assets and clinical/haptic validation are not. Later milestones above add shared corneal/posterior tip contact, separate cortical material and local structural injury.

Record review uses sampled immutable visual states (2-second interval, 900 frames, 32MB export limit); it is not deterministic physical input replay. The director checks simulation evidence and provides no clinical skill grade. See [Korean controls and scope](SPECIALIST_SIMULATOR_KO.md).

## Reproduce

```powershell
powershell -ExecutionPolicy Bypass -File tools/run-godot.ps1 -Test
python -m pytest -q
.tools/godot/Godot_v4.7.2-stable_win64_console.exe --path godot --resolution 1600x1000 --script res://tests/test_simulator_render.gd
.tools/godot/Godot_v4.7.2-stable_win64_console.exe --path godot --resolution 1600x1000 --script res://tests/test_full_encounter.gd
.tools/godot/Godot_v4.7.2-stable_win64_console.exe --path godot --script res://tests/benchmark_simulator.gd
```
