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
