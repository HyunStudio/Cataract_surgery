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

## Verified increment — 2026-10-12 (latest run)
- GitHub Actions run [38260708128](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38260708128): **97 tests passed** in the checked matrix with Python 3.12 and 3.13 (SDL dummy driver for GUI tests).
- Replayer/CLI tests cover tamper detection, malformed files, seeded hazards, rejected but state-changing actions and GUI export; synthetic 3D mesh tests cover normals, bounds, face orientation, deterministic generation, ray hits and malformed geometry inputs.
- Added `ophthosim/geometry.py` and `tests/test_geometry.py`. This is a GPU-independent **mesh math prototype**, not a finished 3D rendered operating field.
- Priority remains WP04 Windows OpenGL feasibility, then live 3D viewport and richer microsurgical tool interaction. No completed clinical skill validation.

## Development increment — interactive software-projected 3D atlas (2026-10-13 KST)

- Implemented `ophthosim/preview3d.py` using cached 3D meshes, yaw/pitch transforms, bounded perspective projection, face sorting and wireframe corneal meridians.
- Added `G` toggle and `J/L/I/K` orbit keys to existing Pygame UI. The atlas is **view-only**; 2.5D surgery remains the only interactive surgery scene. Surgical clicks do not run while the 3D view is active.
- Added pure-Python dirty tests for NaN/inf/huge integers/invalid angles and centers, 100 deterministic random previews, and SDL GUI tests across phases, orbits and blocked tool actions.
- CI failure from typo `self.view_y` was diagnosed and corrected to `self.view_yaw`; final checked [run 38272300713](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38272300713) passed on Python 3.12 and 3.13. 116 tests passed on Python 3.12.
- Remaining: real GPU 3D rendering, synchronized depth-based surgical tool interaction, graphics performance on Windows hardware, licensed high-quality anatomy assets, 4K UI and clinical subject-matter review.

## Implementation increment — ModernGL GPU atlas source and synced monitors (2026-10-13 KST)

- Added `ophthosim/gl_preview.py`, an independent optional OpenGL 3.3/ModernGL **hardware renderer experiment** with separate scene and GPU-uploaded HUD textures. Real driver/GLSL execution **not yet verified**.
- Added `requirements-3d.txt`, CPU geometry packing and camera bound tests, a standalone `--check` mode that explicitly reports `gpu_tested: false`, and `docs/GPU_VALIDATION_CHECKLIST.md`.
- Improved the atlas' opaque globe rendering so its closed front surface does not hide lens/iris in depth buffer. This code correction is not yet visually verified on hardware.
- Added `ophthosim/signals.py`: deterministic synthetic ECG/pleth waveforms use the current PatientState heart rate and simulation time; integrated into Pygame monitor. These are stylized, non-clinical curves.
- Added tests for invalid/huge/nonfinite values, 10,000 repeated camera input events, lens/IOL switching, CI-only GUI render differences, patient HR coupling and deterministic output.
- Verified [Actions run 38318581035](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38318581035): success for Python 3.12 & 3.13, **167 tests passed on Python 3.12**.
- **Remaining for full completion:** actual Windows GPU shader/scene validation, production 3D surgery viewport, depth-based tools, realistic but non-clinical animation and anatomical materials, 4K desktop test, SME review.

## 2026-10-13 follow-up — depth picking and actual software-OpenGL smoke

- Added `ophthosim/picking3d.py`: reverse-projection from scaled window pixels to normalized world rays; deterministic nearest-surface synthetic lens/IOL/iris hits; offscreen/NaN/huge-int rejection. Transparent cornea is excluded to permit viewing inner synthetic anatomy. Picker is **read-only**, not authority for surgical tool/tissue collision.
- Connected iris/lens/IOL selection and crosshair to experimental ModernGL view. Camera/phase changes invalidate selection to avoid stale annotations.
- Added `tests/test_picking3d.py` covering projected-point roundtrips, rotation, near/far, simulated surfaces and 2,000 seeded fuzz selections. Both Python 3.12 and 3.13 CI jobs green: [run 38319316882](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38319316882), 202 tests on 3.12.
- Added `ophthosim/gl_smoke.py` and [Mesa/Xvfb workflow](../.github/workflows/gl-software.yml). Real Linux software OpenGL context created, GLSL compiled, both synthetic states rendered; verified framebuffer not blank and saved PNG artifacts. [Run 38319493162](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38319493162) passed with llvmpipe OpenGL 4.5. This removes the previous **complete absence of executed GL shaders**, but it does **not** meet WP04's real Windows hardware gate.
- Remaining: Windows AMD GPU/4K performance, physical input and display quality; accurate GPU scene picking vs triangle meshes, 3D surgical tool gesture integration, anatomy/capsule animations, depth visual calibration and SME assessment.

## 2026-10-13 — experimental interactive GPU 3D synthetic surgery

- New `ophthosim/input3d.py`: screen-ray intersection with a normalized game-task plane; stage-specific tool z/depth guard; only the strict `ReplayGame` controls procedure state. Independent camera pitch/yaw/zoom mapping with round-trip and invalid-pointer tests.
- Fixed transition hazard: continuous removal mouse gestures **cannot automatically place the IOL**; placement needs a new press. Regression tests confirm no bypass.
- New `ophthosim/gl_surgery.py`: separate runnable ModernGL game with overlay task targets, synthetic ECG/vitals, tool-depth cue, safe hold, endings and JSONL replay export. Default 2.5D app remains intact.
- 3D shader now responds to shared synthetic opacity/cortex/IOL-alignment values. This is appearance feedback, not physiological geometry deformation.
- New `ophthosim/gl_surgery_smoke.py` executed under Mesa llvmpipe through CI, captured eight distinct images in normal and patient-motion cases; full normal completion and safe-abort replay reconstructed exactly.
- Verified [Python 3.12/3.13 Tests CI 38334178228](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38334178228): **245 passed on Python 3.12**. [3D software OpenGL CI 38334142433](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38334142433) success. [Screenshot artifact](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38334142433/artifacts/11783937737).
- **Not completed:** realistic 3D mesh/force interactions, capsule tissue deformation, true IOL fold/unfold, ophthalmology expert verification, actual Windows AMD GPU performance, research outcomes.


## 2026-10-13 — synthetic 3D instrument mesh and visual validation

- Added `ophthosim/tool3d.py`: cached low-polygon tapered stylus mesh (visualization only), bounded normalized coordinates and fail-closed visibility gate. Patient alert, pause, ending, invalid tool pose or depth mismatch suppresses instrument rendering.
- Connected a single retained GPU VAO/VBO/IBO and world-space `u_offset` shader translation to the *interactive* 3D surgical controller in `gl_preview.py` / `gl_surgery.py`. Mesh resources release on application close; pointer motion is render-only and does not create extra game events.
- Added `tests/test_tool3d.py` including geometry/index validation, valid tool position, pause/abort/hazard hiding and malformed/NaN/Inf/giant-number cases.
- First Mesa screenshot comparison failed because the tiny tool was visually occluded; changed to an explicit world-positioned 3D visual overlay (non-physical occlusion) and reran tests. Final OpenGL integration **passed** and confirmed the instrument changes actual framebuffer pixels.
- [Python Tests CI 38335940393](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38335940393): both Python 3.12 and 3.13 jobs succeeded, **274 passed** on Python 3.12.
- [Mesa software OpenGL run 38335940404](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38335940404): passed 3D normal/safety-stop/replay flow, captured **nine distinct frames**, including `entry-stylus`. [Nine-screenshot artifact](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38335940404/artifacts/11784746740).
- **Open:** actual Windows GPU and 4K performance; realistic procedural tool designs, depth-correct physical occlusion, force/collision with tissue, capsule deformation, IOL fold animation, expert review.


## 2026-10-13 — stylized 3D IOL folding/unfolding and ocular visibility correction

- Added `ophthosim/iol3d.py`: bounded and cached optic+two-support synthetic IOL render mesh. The shader selectively compresses/curves the IOL for a folded appearance, driven by `AnatomyAppearance.iol_deployment`.
- `iol_visual_deployment()` reads the actual Game IOL→CLOSE transition event and simulation time. The 1.5-second smoothstep animation is **render-only**, pauses with simulation time, and cannot change score, stage, complications or replay.
- Replaced the previous simple synthetic IOL ellipsoid in the GPU atlas; added deployment indicator to the 3D surgical HUD and captured IOL-placement, middle and deployed frames.
- A stronger visual regression test excluded HUD regions and uncovered a previously masked renderer defect: an opaque closed globe hid both iris and lens. Fixed by disabling the depth test for the *background* globe pass; foreground iris and lens still use normal depth tests.
- `tests/test_iol3d.py` covers generated geometry and bounds, stage transition timing, simulation pause, state non-mutation, bad duration/NaN/Inf/giant integer inputs and random timed ticks. The legacy shader assertion was updated for intentional IOL deformation without losing world-space translation.
- **Verified** [Python 3.12/3.13 CI 38337153815](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38337153815): **289 passed per Python version**. [Mesa software OpenGL run 38337153811](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38337153811) passed actual 3D central-eye IOL deformation test, normal/safety-stop full sessions, and generated [frame artifacts](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38337153811/artifacts/11785108404).
- **Next:** stable patient/eye tissue damage visuals, deeper tool/tissue interaction (currently synthetic task plane only), Windows GPU 4K frame-time profiling and anatomical subject-matter review. IOL design/material behavior is not clinically validated.


## 2026-10-13 — simulated capsule injury visual feedback / safety regression

- Added `ophthosim/capsule3d.py`: cached two synthetic ring meshes (intact, discontinuous injured), strict finite/range validation, and display-state mapping from the authoritative `Game.eye.capsule_integrity`. No changes to the clinical status, phase engine, scoring, or safety logic.
- Integrated a separate retained GPU capsule VAO for each state into `GPUEyePreview`, with stage-specific appearance state and cleanup. HUD reports *CAPSULE INTACT / CAPSULE ALERT* but selection is based on game state only. The ring sits in front of the simplified iris solely for visual legibility, **not anatomical accuracy**.
- Added `tests/test_capsule3d.py` for ring topology/opening, cache, phase visibility, capsule alert, irreversible safe-abort branch, side-effect-free rendering queries and malformed/huge-number/NaN/Inf inputs.
- Expanded `ophthosim/gl_surgery_smoke.py` to compare **eye-center-only pixels with identical HUD** for intact and torn rings. Added third deterministic complication scenario and verified input lock, warning assessment, safe abort and deterministic replay. This catches UI-label-only implementations.
- Initial geometry test expected an unnecessarily large per-vertex displacement; corrected its threshold while preserving separate discontinuity/topology checks. Validated test suite afterward.
- **Verified:** [Python CI 38338000372](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38338000372) Python 3.12 and 3.13 **335 passed each**; [Mesa OpenGL CI 38338000377](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38338000377) **success**, [frame captures](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38338000377/artifacts/11785910265).
- **Remaining:** actual capsule tissue deformation and realistic optics/occlusion (not simulated), richer patient motion visualization, hardware Windows Radeon GPU/4K performance, accessibility review, subject-matter validation, and completion of 32 WP.


## 2026-10-13 — deterministic motion/veil graphics and accessibility toggles

- Added `ophthosim/vision3d.py`: read-only, bounded deterministic patient-motion offsets and synthetic opacity/cortex-based haze; rejects NaN, infinity, huge integers, invalid booleans and malformed game state.
- The OpenGL vertex shader now shifts eye anatomy in camera-plane coordinates without moving synthetic tool poses or changing normalized task picking. The HUD draws a non-flashing frosted synthetic veil and optional bright static contrast ring.
- Interactive GPU app has **M = reduced motion** (zero scene translation) and **H = high contrast** visual toggles. On safety hold the motion cue is static and the existing Game input interlock is unchanged. Visibility/physics explicitly non-clinical.
- Added `tests/test_vision3d.py` for seeded pseudo-random fuzz, 1000 time samples, invalid values, no state mutation, pause/safety invariants and accessibility type validation.
- Expanded `gl_surgery_smoke.py` to verify eye-center-only (no sidebar or HUD labels) pixel differences for haze/motion with an otherwise identical scene, plus actual before/after **M low-motion** state in a patient-motion hazard; compared snapshots for game-state immutability.
- **Verified** [Tests run 38340531317](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38340531317): Python 3.12 and 3.13 **395 passed each**; [Mesa llvmpipe 38340531344](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38340531344): success, [capture artifact](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38340531344/artifacts/11785993260).
- **Open:** actual eye/iris motion tracking, realistic optical scattering/material shaders, real hardware AMD GPU/4K profiling, accessibility contrast/vision testing on Windows, specialist clinical review and complete 32 WP acceptance.


## 2026-10-13 — stage-aware contact guide and pause-safe 3D hover

- Added `ophthosim/contact3d.py`: bounded, deterministic, non-mutating tool contact preview for ENTRY, CAPSULE, PHACO, CORTEX, IOL synthetic task regions. Statuses `TARGET`, `VISITED`, `NEAR`, `OUTSIDE`, `DEPTH`, `HOLD`, `INACTIVE`. The engine's action success remains the only procedural authority.
- Reused cached CPU-authored guide ring mesh and one persistent GPU VAO/VBO/IBO in `GPUEyePreview`. The ring is overlaid in 3D at the validated educational tool depth. Colors are paired with explicit HUD labels; never claim optical occlusion, force, physical tissue picking or clinical correctness.
- New `Surgery3DController.inspect()` is a read-only mouse hover preview; does not touch Game or ReplayGame history. Pointer actions retain all existing strict game and fresh-IOL-press checks. Incorrect depth or unsafe phase clears stale pose. Pause+resume now requires fresh cursor movement before the old stylus becomes visible; earlier pose is not resurrected.
- Added `tests/test_contact3d.py` including 1,500 seeded hover events, stage targets and visited bins, camera rotations/zoom, wrong depth, pause/alert/abort, bad vectors/NaN/Inf/huge integer rejection, snapshot/replay immutability and HUD-independent GPU input checks.
- Updated `tests/test_tool3d.py` to assert the safer no-stale-tool-on-resume contract rather than old automatic pose restoration; an initial regression failure was investigated and fixed by updating this expectation without weakening core safety.
- Linux Mesa Xvfb OpenGL smoke now compares **center-eye-only** frame pixels for guide mesh on/off with identical HUD and tool; result differs, proving GPU visualization rather than HUD-only label change. Normal, motion and capsule injury simulations still passed.
- **Verified:** [Python 3.12/3.13 tests 38343565234](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38343565234) **422 passed per version**; [Mesa OpenGL 38343565188](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38343565188) **success**, [screenshots](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38343565188/artifacts/11788405053).
- **Open:** actual eye-anatomy triangle collision/feedback; simulated instrument forces, tissue deformation, real hardware GPU/Windows/4K, expert clinical review and overall 32-work-package release acceptance.


## 2026-10-13 — static iris/optic face picking, true triangle intersection (WP12 partial)

- Added `ophthosim/mesh_raycast.py`: bounded immutable CPU BVH (per-mesh AABBs, balanced subtrees, ray/slab checks), double-sided Möller–Trumbore ray-triangle intersection, nearest triangle index, hit coordinates and barycentric weights, degeneracy rejection, finite/range input validation. Static geometry, *not* tissue physics.
- Updated the standalone GPU 3D atlas `GPUEyePreview.select()`: real triangulated iris, cataract lens, unfolded synthetic IOL face selection; source mesh indexes built on scene change. The HUD prints synthetic face number and ray distance. This supersedes only the **standalone atlas inspect/pick** path, not the educational task engine or abstract normalized surgical target planes.
- Added `tests/test_mesh_raycast.py`: exact triangle barycentric calibration, back-side hits, bounded clipping, collinear degenerates, nearest/overlapping faces, rotated camera, offscreen misses, hostile NaN/Inf/huge numbers and 400 seeded selections.
- Expanded `gl_smoke.py` under Mesa OpenGL to require valid iris and optic face IDs for both CATARACT and IOL; visible screenshots are generated and recorded. Numerical vertex-edge barycentric values are accepted within fixed 1e-9 tolerance rather than requiring impossible exact floating-zero.
- Initial CI found a lowercase `iol` mesh name not normalized for HUD; fixed and reran. A stricter Mesa face-weight check then exposed rounding epsilon at triangle boundaries; fixed the test to match the raycast algorithm's finite tolerance.
- **Verified** [GitHub Python CI 38345423438](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38345423438): **452 tests passed on Python 3.12 and 452 on 3.13**. [Mesa software GL CI 38345423347](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38345423347): success, actual face IDs, scene screenshots and preexisting three-case synthetic surgery integration.
- **Open:** deformed/camera-shifted GPU mesh parity, complete interactive 3D surgical tool/tissue collision, per-contact tissue deformation/force, Windows Radeon GPU 4K performance and ophthalmologist/clinical validation. **WP12/WP13 remain partial.**


## 2026-10-13 — shader-parity IOL deformation and bounded dynamic mesh picking

- Created `ophthosim/iol_pick3d.py`, mirroring synthetic GLSL fold transform `x' = x*(.24+.76*d)`, `z' = z+(1-d)*.30*abs(x)` and `x` alignment offset `.18*(1-a)`; the CPU mesh retains the *same* source triangle face IDs. The output remains a stylized, nonclinical IOL optical model.
- Validated `deployment`/`alignment` input **before** the private 16-entry cached mesh generator, preventing `True==1` and unhashable list/dict cache lookup bypasses. This defect was found by hostile-input tests and corrected in the implementation rather than weakening coverage.
- Added optional inverse GLSL camera-plane translation to `mesh_raycast.pick_indexed` using inverse yaw/pitch rotation. CPU ray-to-scene contact points now account for the same synthetic view-only shift drawn by the shader.
- `GPUEyePreview.select()` now accepts optional validated `AnatomyAppearance` and `VisualFeedback` state, updates the fold/alignment BVH **only on selection when either property differs**, and retains the original static cataract/iris behavior. Standalone IOL atlas supports the **F** key to cycle unfolded/folded/midpoint previews. The normal interactive surgery engine is **not** switched to mesh-based physical collision and is unaffected.
- New `tests/test_iol_pick3d.py` covers the vertex equation, mesh immutability, cache bound, changing face selection at unfolded vs folded state, alignment and rotated camera-motion parity, invalid/massive/unhashable input and seeded 300-state fuzz.
- Enhanced Mesa/Xvfb `gl_smoke.py`: screen-picks the unfolded optic at an actual triangle, verifies a miss after folding at the same projected point, compares **three distinct central-eye crops** excluding HUD changes, and captures additional folded/midpoint PNG frames. Full prior synthetic surgery safety regression continues to pass.
- **Verified:** [Python CI 38351299492](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38351299492), **480 passed each** on 3.12 and 3.13; [Linux Mesa OpenGL 38351299510](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38351299510), success. Software OpenGL is **not** physical Windows GPU validation.
- **Remaining:** visual/screen-geometry consistency for corneal refraction and dynamic tissue, end-to-end 3D tool/material interactions, true triangle collisions driving guarded *synthetic* tasks, Windows Radeon/4K benchmark, accessibility audit, SME review, and all outstanding 32 work packages.


## 2026-10-13 — synthetic nearest-triangle tool-tip proximity (WP12/WP13 partial)

- Added `ophthosim/surface_distance3d.py`: immutable closest-point / triangle-barycentric Euclidean query, with BVH bounding-box pruning, nearest face ID, bounded input validation, safe triangle edge/vertex and degenerate face handling. Reported distances are **unitless synthetic model coordinates**.
- Added `ophthosim/surface_probe3d.py`: read-only model gap classification `CLOSE/NEAR/FAR` on iris, crystalline lens or rendered synthetic IOL based on visible, phase-guarded stylus pose. Tissue indexes and eight IOL deformation states are cached; when the scene has an artificial camera-plane displacement, it is inverted for model-frame proximity.
- Updated `gl_preview.py` and `gl_surgery.py`: retain all existing procedural/safety interlocks while drawing a **separate nearest-triangle marker** on the real authored 3D mesh and a textual MESH GAP status. The marker is deliberately schematic and never acts as a collision or tissue-damage trigger.
- Added `tests/test_surface_distance3d.py`: exact interior/edge/vertex cases, multiple overlapping faces and nearest selection, degenerate line-triangle, distance budget, cache invariants, phase/pause/alert/abort suppression, malformed/NaN/Inf/huge inputs, 500 seeded finite geometric queries and no Game state mutation.
- Updated Mesa `gl_surgery_smoke.py` to compare **HUD-excluded center-eye pixels** of a frame with and without the nearest-triangle marker under otherwise identical visual and Game conditions; asserted Game snapshot remains unchanged. Normal, motion and capsule injury integration scenarios still pass.
- A test initially demanded exact mathematical zero but floating-point output was approximately `3.93e-17`; changed assertion to a strict `1e-12` absolute epsilon with the production algorithm and remaining tests unchanged.
- **Verified [Python CI 38355094995](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38355094995): 510 passed on both Python 3.12/3.13. [Mesa OpenGL 38355095000](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38355095000): success with nearest-triangle marker visibly changing central-eye pixels and 3 synthetic surgery scenario/replay paths.**
- **Open:** true physical contact with force/tissue response, anatomy realism and deformation, per-stage refined instruments, Windows Radeon GPU 4K performance and professional clinical review.


## 2026-10-13 — one surface-proximity evaluation per interactive 3D frame

- Removed a redundant geometry query: the main 3D surgery loop now computes `visual_feedback` and `probe_surface` once, passes the immutable proximity result to both `GPUEyePreview.render(surface_probe=...)` and `SurgeryHUD.set_frame_proximity()`, and avoids re-running `probe_surface()` inside `SurgeryHUD.draw()`.
- HUD display of a prepared result is fail-closed against stale phase, changed camera yaw/pitch, changed validated stylus world pose, patient alert, pause or completed case. Reacquiring a cursor pose requires a new per-frame proximity observation. Added explicit numeric **unitless** model gap alongside the CLOSE/NEAR/FAR label; no clinically meaningful force/penetration is implied.
- Updated Mesa `gl_surgery_smoke.py` frame helper to prepare one shared proximity result. The preexisting normal, patient-motion and capsule-complication sessions and read-only replay behavior remained intact.
- Added `tests/test_3d_frame_proximity.py` with an instrumented `nearest_triangle` spy to prove two necessary initial mesh queries and **zero extra BVH queries** across repeated HUD paints. Also checks visual label on/off, dirty/untrusted prepared result rejection, stage/camera/pose invalidation, abort/pause/restart safety and synthetic Game snapshot/replay immutability.
- [CI run 38355978889](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38355978889): **522 passed on both Python 3.12 and 3.13**. [Mesa OpenGL run 38355978911](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38355978911): success, previous non-HUD triangle marker and three synthetic surgery safety scenarios still verified.
- This is an observed **reduction in duplicated geometry calls**, not a demonstrated FPS increase. Real Windows/Radeon GPU and 4K sustained frame-time/legibility acceptance remain OPEN. Synthetic geometry is not clinically validated.


## 2026-10-24 — scripted frame-time benchmark for the WP04/GL08 gate

- Added `ophthosim/frametime.py`: bounded rolling `FrameProfiler` (fixed sections `frame`/`probe`/`render`), linear-interpolated percentiles, `FrameStats` (mean/P50/P95/P99/min/max, fraction over the 16.667 ms budget), software-renderer detection and a conservative `gl08_assessment` that can only return `INSUFFICIENT_EVIDENCE` or a `CANDIDATE_…` status requiring human sign-off.
- Added `ophthosim/gl_benchmark.py`: deterministic ENTRY-phase workload (bounded camera orbit, stylus hover loop past the synthetic entry targets) that exercises one nearest-triangle query, contact ring, stylus, HUD upload and buffer swap per frame. Writes a JSON report with environment and OpenGL strings; exits nonzero if the synthetic Game snapshot or replay journal changes. `--size`, `--fullscreen`, `--seconds`/`--frames`, `--warmup` are bounds-checked.
- `GPUEyePreview` accepts an optional `fullscreen` flag for full-display measurements. The interactive 3D game shows a rolling frame mean/P95 on **F3** (display only).
- Issues found while building it and fixed before commit: the measured-duration anchor was never set after warmup (reported 0 s); per-frame `stats()` sorting would have distorted the measurement at high frame rates (replaced with a running mean); an `"unknown"` renderer string was treated as hardware; the pygame banner corrupted JSON stdout.
- Local Mesa llvmpipe 1920×1080 sample: ≈13.9 ms mean frame, ≈0.23 ms proximity query, ≈13.6 ms render call. On software GL the full-window draw/HUD upload dominates, which points the next optimization at HUD texture upload rather than the BVH.
- **WP04/GL08 remain OPEN**: no physical Windows Radeon run has been made. The tool produces evidence; it does not produce a pass.
