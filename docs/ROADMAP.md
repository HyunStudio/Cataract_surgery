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
