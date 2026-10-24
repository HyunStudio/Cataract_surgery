# 32 work packages — delivery roadmap

Each work package (WP) ends with a runnable application, a test or reproducible screenshot, an updated CHANGELOG, and a small scoped commit. **These are planned tasks, not completed features.**

| WP | Scope | Acceptance checkpoint |
|---|---|---|
| 01 | Pygame bootstrap & settings | Window, input, reproducible scene |
| 02 | FSM and event bus | Transition/abort unit tests |
| 03 | UI shell 1080p/4K scaling | Resize/layout test |
| 04 | Pygame–ModernGL feasibility spike | Renderer decision with benchmark |
| 05 | Eye anatomy logical model | Typed state & invariants |
| 06 | Layered 2.5D eye renderer | Consistent anatomical layers |
| 07 | Microscope camera, lighting, focus | Zoom/pan/focus controls |
| 08 | Optional 3D eye mesh, pick/depth | 3D fallback parity test |
| 09 | Patient/anesthesia abstract state | Seeded state replay |
| 10 | Synthetic ECG/BP/SpO2 UI | Monitor/model synchronization |
| 11 | Patient cooperation, motion, alarms | Safe pause & alert flow |
| 12 | Tool tray & input normalization | Coordinate tests |
| 13 | Microsurgical interaction/hit testing | Collision boundaries |
| 14 | Preparation & entry task | Stage scoring/logs |
| 15 | Capsular path challenge | Curve quality metric |
| 16 | Lens state & fragmentation visuals | Visual/model consistency |
| 17 | Phaco abstract controls | No clinical numeric settings |
| 18 | Fragment cleanup actions | Removal state coherent |
| 19 | Capsular stress/integrity model | Damage escalation tests |
| 20 | Cortex cleanup & completion gates | No hidden residual acceptance |
| 21 | Folded IOL animation | Fold→unfold transition |
| 22 | IOL centering and positioning | Deterministic scoring |
| 23 | IOL safety/complication checks | Incorrect placements flagged |
| 24 | Wound and final inspection | Ending gated on stability |
| 25 | Recovery/handoff UI | Safe stop and handoff path |
| 26 | Patient movement, pupil, haze events | Reproducible seeds |
| 27 | Capsule/visual loss complications | Recognition response branching |
| 28 | Vital alert and emergency abort | No forced risky continuation |
| 29 | Scoring, endings, feedback | Explainable scoring report |
| 30 | JSONL/CSV logging & experiment configs | Pseudonymous replay |
| 31 | Visual/audio polish and accessibility | High contrast/reduced-motion tests |
| 32 | Full regression, performance, release docs | End-to-end demonstration |

## Stage gates
- **G1 (WP01–04):** technical feasibility; renderer selection.
- **G2 (WP05–11):** credible anatomy and synchronized monitors.
- **G3 (WP12–20):** interactive lens-removal vertical slice.
- **G4 (WP21–28):** complete surgery and complication branches.
- **G5 (WP29–32):** explainable assessment, research logs, polished release.

## Management
Track blockers, models licensed/provenance, unresolved clinical assumptions and graphics benchmarks explicitly. Prefer quality gate over strict line-count targets. No real-world surgical validity is claimed before subject matter review and external validation.

## v1.1 milestone review — scope and delivery criteria

**Release strategy:** R0 playable graybox at WP15; R1 cataract-removal vertical slice at WP20; R2 complete core encounter at WP25; R3 safety branches at WP28; R4 research-ready release at WP32. An optional production 3D renderer is conditional on WP04 measurement; it may continue as a parallel improvement without blocking playable releases.

**Exit evidence per WP:** one short CHANGELOG entry, explicit acceptance checklist, at least one automated test where logic changes, screenshot/video for visual changes, and a known-limitations note. Mark TODO/IN PROGRESS/TESTED, never label unimplemented tasks complete.

**Critical path:** WP01 → WP02 → WP03 → WP04 → WP05 → WP06 → WP07 → WP12 → WP13 → WP14 → WP15 → WP16–20 → WP21–25 → WP26–29 → WP30–32. WP08 (optional 3D) must not stall later game-state work.

**Minimum end-to-end demo:** one normal full session and two deterministic exception sessions (patient motion and capsule/vital alert), with alternative safe-stop outcomes. Baseline 1080p, 4K scaling screenshot, simulation log replay, and results traceability must all be demonstrated.

**Risk register (owners assigned when implementation starts):**
- Pygame/OpenGL rendering interoperability → WP04 early spike; keep 2.5D fallback
- Lens/cornea transparent depth composition → isolated shader prototype; transparent picking separate from display
- UI latency/4K scaling → logical pixel coordinate conversion and frame-time logging
- Animation/medical credibility → ophthalmology reviewer checklist and explicit model assumptions
- Research confounding → freeze scenario seeds/UI conditions and pre-specify endpoints
- Asset license conflicts → provenance manifest before adding any third-party files

No fixed estimate in lines of code is a commitment. The 32 WP scope is a planning decomposition, not a validated time estimate.

## Increment tracking (not WP completion)
- **Replay & integrity milestone — implemented/tested:** bounded semantic accepted/rejected command capture, synchronized simulation tick compression, JSONL verification and CLI, GUI export, hazard replay.
- **Geometry prototype — implemented/tested:** procedural normalized cornea, iris, sclera, lens and IOL mesh surfaces; ray–sphere intersection and dirty-parameter tests.
- **WP04 / WP08 still OPEN:** Pygame↔OpenGL rendering integration, actual 3D on-screen appearance, camera depth/ray-picking against scene, Windows GPU benchmarks, visually credible textured anatomy and validated tissue interaction remain unimplemented.

## Latest progress marker — 2026-10-13 KST

- **WP08 partial prototype:** working CPU-projected, keyboard-rotatable 3D mesh *anatomy preview* in the Pygame display, with 3D math and dirty/GUI tests.
- **WP04 NOT complete:** ModernGL/OpenGL integration, physical GPU benchmarking and production-grade 3D picking/lighting still need validation on target hardware.
- 3D preview is read-only and never replaces the main surgical state interaction. Remaining gates and planned work-package status are otherwise unchanged.

## WP04 incremental status — 2026-10-13

Experimental ModernGL GPU atlas code and offline geometry/shader-interface tests have been added. **WP04 is still OPEN** pending genuine Windows OpenGL execution, actual shader compilation, frame-time measurement, window resizing and visual screenshots. The surgical 2.5D mode is still the playable fallback. Synchronized synthetic vital waveform rendering has been integrated and CI tested. Refer to `GPU_VALIDATION_CHECKLIST.md`.

## 2026-10-13 follow-up WP04/WP08

- **WP04 partial:** modern OpenGL 3.3 shaders/UI composition now actually execute on GitHub-hosted Linux Mesa llvmpipe with nonblank framebuffer screenshots, separate from earlier CPU-only shader inspections. **Windows GPU gate remains OPEN**.
- **WP08 partial:** read-only lens/IOL/iris depth picking added to a rotatable 3D atlas with camera transform inverse and safe hit boundaries. The picker does not yet drive actual surgical instrument coordinates or state actions; no production 3D surgery release claim.
- Next: bring the GPU scene and synthetic tool pose under one stateful controller; translate guarded 3D hit events into *educational* procedural actions only after phase-specific tests, and preserve 2.5D fallback.

## 2026-10-13 — integrated interactive 3D vertical slice

- **WP04 partial, Windows gate OPEN:** actual GLSL scene/HUD execution passed on Linux software OpenGL; still need physical GPU benchmarking and desktop input validation.
- **WP08 partial:** real 3D scene plus read-only surface picking, now also a separate synthetic **3D task-plane input** pipeline. Object mesh precise picking/tissue interaction remains outstanding.
- **WP12–15 partial:** combined ray-to-task mapping with existing synthetic entry and circular task; 3D view exposes stage targets. Not medically accurate procedural simulation.
- **WP16–23 partial:** existing lens clearing and IOL alignment states drive visible GPU appearance changes; no phaco biomechanical solver, lens fragmentation mesh physics or folded-IOL animation.
- **WP29–30 partial:** synthetic score/endings/replay persisted unchanged under 3D mode, with safety-hold tests.
- Regression evidence: [245 Python tests](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38334178228) and [Mesa full-session frames](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38334142433). **The 32-work-package plan remains incomplete.**


## 2026-10-13 — world-space stylus milestone (partial WP12/WP13)

- Procedural 3D synthetic tool mesh is now positioned using guarded existing task inputs and depth; the renderer cannot change surgical state or bypass alert/safe-abort gates.
- Verified under headless Python 3.12/3.13 and Mesa software OpenGL with actual before/after frame comparison.
- **WP12/WP13 remain partial** until 3D instrument selection, actual 3D collision/picking and full surgical feedback are developed; this geometry is an educational overlay rather than a force-controlled instrument.
- Next recommended implementation: state-consistent capsule geometry transitions and IOL insertion/unfold animation, plus real Windows AMD GPU profiling and 4K accessibility tests.


## 2026-10-13 — IOL fold/unfold partial milestone (WP21–23)

- A stylized *visual-only* optic with curved supports and shader folding has been integrated into the synthetic 3D game. Stage IOL shows a folded IOL and successful placement triggers a deterministic visual unfolding in CLOSE, freezing on pause.
- Automated 3D crops distinguish the unfolding **geometry**, not merely HUD text. Existing globe-depth occlusion was fixed when tests revealed the anatomy was invisible.
- **WP21 remains PARTIAL**: simulation has no validated IOL geometry, material, mechanical unfolding, capsular support/force modeling or ophthalmology reviewer acceptance. WP22/WP23 still rely on abstract normalized placement and existing safety gates.
- Next milestone: tissue/capsule integrity visual feedback and a credible but explicitly non-clinical visual complication presentation; Windows AMD real GPU and accessibility tests.


## 2026-10-13 — capsule-integrity visualization (WP19/WP27 partial)

- Synthetic capsule integrity affects a distinct 3D cosmetic ring, with an opening/red color in the damaged case. Existing Game hazard, safe hold, pause, assessment and safe abort remain authoritative.
- Verified three deterministic integration scenarios and central-eye-only geometry difference under Linux Mesa software OpenGL; Python 3.12/3.13 335 tests passed.
- WP19/WP27 are **partial**, not complete: deformable tissue and believable 3D rupture/visibility loss are not implemented; clinical review and real GPU performance are pending.
- Next target: safer motion/haze scene cues with accessibility/flicker alternatives, richer phase-specific tool visual interactions and Windows GPU hardware gate.


## 2026-10-13 — non-flashing motion/haze/accessibility increment

- **WP11/WP26 partial:** existing synthetic patient movement value now drives bounded camera-plane eye displacement in the 3D surgical viewport; paused/alerted motion freezes, and tool interaction remains locked during unsafe states.
- **WP06/WP31 partial:** a simple frosted cosmetic veil tracks synthetic opacity/cortex, **M** disables eye displacement and **H** adds a static high-contrast outline. This is not medical visual-field or physical optical simulation.
- Integrated Mesa software GL tests check **center-eye** scene differences, reduced-motion hazards and state immutability. Python 3.12/3.13 CI each passed 395 tests.
- **Open:** actual 4K UI legibility and high-contrast audit, Windows real GPU profiling, visually credible eye motion/focus system, clinical review, full WP32 release criteria.


## 2026-10-13 — 3D interaction precision increment (WP12/WP13 partial)

- The GPU 3D surgical prototype now supports a persistent world-space, color-and-text contact indicator and read-only hover classification at the active synthetic educational depth.
- Strict engine-based IOL fresh-click, safety alert and tool-depth guards are preserved. Paused tool poses are never automatically reinstated; operator must reacquire cursor position after resuming.
- Python CI and Mesa GL center-eye pixel delta pass, but **WP12/WP13 remain partial** until anatomical 3D mesh collision, geometry-driven tool deformation, failure mode coverage, clinical review and real hardware verification.
- Next: investigate triangle mesh picking with bounded CPU acceleration; preserve engine authority and conservative rejection, add depth-aware target feedback and improve 4K display adaptation. Avoid introducing real medical procedures, actual doses or procedural guidance.


## 2026-10-13 — bounded triangle-level static mesh inspection (WP12 partial)

- Standalone OpenGL atlas now uses actual visual triangle faces with prebuilt bounded BVH and nearest-hit inspection, reporting face index and synthetic ray distance. The previous analytic projection check is retained as a separate comparison/testing utility.
- **WP12 still partial:** no validated end-to-end 3D *surgical action* based on triangle intersection and no tool-tissue force simulation. In particular, GPU shader-deformed IOL, depth/cosmetic offsets and patient-eye motion must be represented in any future interaction model before it can be considered geometry-consistent.
- All existing stage/alert/score/replay safety authority stays with the 2.5D/3D `ReplayGame` state machine. Do not substitute triangle hits for procedural safety decisions.
- Next: design phase-consistent GPU/CPU deformation representation and a pure read-only instrument-to-mesh proximity indicator; independently verify static and animated coordinate parity, then improve Windows/4K UX.


## 2026-10-13 — unfolded/deforming optic picking consistency (WP12 partial)

- **Implemented in standalone 3D atlas:** IOL fold-geometry CPU/BVH replica using the same synthetic vertex-position deformation as the GPU shader; supports alignment offset and inverse camera-plane shift. F cycles static visual fold poses, and triangle selection now tracks that displayed geometry. Face counts stay bounded and cached.
- **QA:** Python 3.12/3.13 each 480 passed, Mesa software OpenGL eye-region screenshot comparisons and unfolded-vs-folded contact decision succeeded, dirty cache-value aliasing corrected.
- **Still partial:** this is visual read-only inspection, not an action-authoritative 3D surgery collision model. Cornea optics, animated capsule tear/tissue, tool interaction with physical resistance, real target hardware tests and expert anatomical review are not completed.
- Next: define an explicit nonclinical mesh/tooltip hover contract in the interactive 3D surgery display, then add geometric proximity *without* overriding ReplayGame's phase/safety decisions; profile Windows AMD GPU and 4K usability separately.


## 2026-10-13 — read-only triangle surface proximity (WP12/WP13 still PARTIAL)

- Interactive 3D game now has a point-to-actual-triangle nearest-distance display, BVH pruning, scene-motion correction, display marker on the nearest rendered synthetic surface and unitless CLOSE/NEAR/FAR text.
- The visual query is strictly gated to active/safe phases and valid 3D tool poses. The existing `ReplayGame` remains authoritative; no geometry-based injury, force feedback, surgical action validation or actual tissue collision has been enabled.
- Python 3.12/3.13 510 tests passed and Mesa software OpenGL eye-region visual comparison passed. This confirms implementation against synthetic meshes and regression tests, **not** clinical physical fidelity or real target GPU.
- Next: evaluate optimized single-pass proximity calculation and actual 3D tool/tissue pose consistency; add accessible distinction beyond color and 4K visual readability checks, then Windows Radeon hardware gate and specialist anatomy assessment.


## 2026-10-13 — renderer/HUD surface query reuse (WP12/WP31 partial)

- Interactive 3D render now computes the unitless nearest-triangle `SurfaceProbe` **once** per visual frame, passes the same immutable result to GPU overlay and HUD, and invalidates old HUD observations on changed phase, pose, camera orientation or safety state. This eliminates duplicate CPU BVH queries in one frame without allowing a visual result to authorize Game actions.
- Automated spy/counter tests, stale/hostile-input checks and Mesa software OpenGL integration pass: 522 Python tests on 3.12 and 3.13.
- **WP12/WP31 remain PARTIAL**: need measured 4K Windows GPU frame latency, adaptive 4K HUD layout/legibility, accessible status typography, validated phase-consistent visual pose and deformed *synthetic* geometry, specialist review and full release acceptance.

## 2026-10-24 — WP04 measurement tooling

- `python -m ophthosim.gl_benchmark` produces the GL08 evidence (mean/P95 at ≥1920×1080 for ≥60 s, renderer strings) needed for the WP04 renderer decision. It refuses to call software GL evidence and leaves the final pass to a human reviewer.
- Software-GL profiling shows render/HUD upload dominating over the proximity query; partial-region or cached HUD upload is the next candidate optimization once hardware numbers exist.
- **WP04 remains IN PROGRESS** until a physical Windows Radeon report is attached.

## Implementation status (2026-10-24)

DONE = implemented with automated tests. SW-DONE = done in software, but an
acceptance step needs a person or the target hardware. OPEN = needs work that
cannot be done from this repository alone.

| WP | Scope | Status | Evidence / remaining |
|---|---|---|---|
| 01 | Pygame bootstrap & settings | DONE | `main.py`, CLI case/difficulty/lang/seed/scale/resume |
| 02 | FSM and event bus | DONE | `engine.py` strict phase machine, events, `test_engine*.py` |
| 03 | UI shell 1080p/4K scaling | SW-DONE | resizable 2.5D canvas; 3D HUD integer magnification; physical 4K legibility check open |
| 04 | Pygame–ModernGL spike | SW-DONE | 3D game + Mesa CI + `gl_benchmark`; **Windows GPU GL01–GL10 open** |
| 05 | Eye anatomy logical model | DONE | typed `Eye`/`Patient` state incl. pupil and cornea clarity |
| 06 | Layered 2.5D renderer | DONE | `app.render_eye` layers, haze veil, decentred optic |
| 07 | Microscope camera, lighting, focus | DONE | zoom (input-mapped), focus blur, illumination; 3D orbit/zoom |
| 08 | Optional 3D eye mesh, pick/depth | DONE | ModernGL atlas/game, BVH picking, CPU/GPU parity tests |
| 09 | Patient/anesthesia abstract state | DONE | synthetic patient model, anesthesia confirmation |
| 10 | Synthetic ECG/BP/SpO2 UI | DONE | state-driven waveforms (both apps) |
| 11 | Patient cooperation, motion, alarms | DONE | motion/vitals hazards, timed safety hold |
| 12 | Tool tray & input normalization | DONE | instrument tray (manual in hard), normalized/zoomed input mapping |
| 13 | Microsurgical interaction/hit testing | DONE | difficulty tolerances, 3D ray/plane + depth gates, read-only proximity |
| 14 | Preparation & entry task | DONE | pre-op checklist gate, entry targets |
| 15 | Capsular path challenge | DONE | bin coverage per difficulty, action-path metric |
| 16 | Lens state & fragmentation visuals | DONE | opacity visuals 2.5D/3D, cross-section |
| 17 | Phaco abstract controls | DONE | no numeric device settings by design |
| 18 | Fragment cleanup actions | DONE | cortex stage |
| 19 | Capsular stress/integrity model | DONE | near-miss stress → capsule alert → safe stop |
| 20 | Cortex cleanup & completion gates | DONE | residue must reach zero; no hidden acceptance |
| 21 | Folded IOL animation | DONE | 3D shader fold → unfold on simulation time |
| 22 | IOL centering and positioning | DONE | alignment thresholds per difficulty |
| 23 | IOL safety/complication checks | DONE | decentration blocks the alignment check until re-centred |
| 24 | Wound and final inspection | DONE | wound-leak hold re-requires the wound check |
| 25 | Recovery/handoff UI | DONE | explained results screens (2.5D/3D) |
| 26 | Patient movement, pupil, haze events | DONE | motion, pupil, haze, seeded random case |
| 27 | Capsule/visual loss complications | DONE | capsule event, corneal haze; vitreous event out of v1.x scope |
| 28 | Vital alert and emergency abort | DONE | vitals hazard, safe abort, safety veto on inaction |
| 29 | Scoring, endings, feedback | DONE | 4 endings, 20/25/20/20/15 breakdown with reasons |
| 30 | JSONL/CSV logging & experiment configs | DONE | report/CSV export, `experiments.py`, replay schema v2 |
| 31 | Visual/audio polish and accessibility | SW-DONE | KO/EN, contrast, colour-safe, reduced motion, tones; human audit open |
| 32 | Full regression, performance, release docs | SW-DONE | 707 tests, Mesa smoke/benchmarks, docs; Windows performance open |

**Open items needing the owner:** run the GL01–GL10 checklist and the benchmarks
on the Windows Radeon PC; check legibility on a physical 4K monitor; and get
subject-matter-expert review of content plausibility. Before any study with
participants, an ethics/IRB determination is required.
