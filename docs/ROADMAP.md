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
