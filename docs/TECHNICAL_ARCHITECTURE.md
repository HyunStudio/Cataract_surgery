# Technical architecture — 2.5D to optional 3D

**Design status:** proposed, not implemented.

## Decision
Use **Pygame as application shell** (window, UI, input, event dispatch, text, sound). It is not a full 3D engine. Implement renderer abstraction with two backends:
- `PygameLayeredRenderer`: 2.5D prototype using textured sprites, layer transforms, perspective cues, and simplified depth.
- `ModernGLRenderer`: optional true 3D via OpenGL context, GLSL shaders, meshes and camera projection. Integration/driver compatibility spike is an explicit early milestone before committing to full 3D.

Avoid writing custom volumetric physics until the gameplay loop is validated. Mesh deformation, tissue collision and optics are distinct complexity multipliers.

## Architecture & state ownership
`Application` (loop) → `ScenarioStateMachine` → `PatientState`/`EyeModel`/`ToolState`/`ComplicationState` → `SimulationSystem` → immutable `FrameSnapshot` → `Renderer` + `MonitorUI` + `Logger`.

- Game updates are deterministic with fixed timestep (e.g. 1/120 s internal, decoupled from display FPS).
- The model stores normalized, dimensionless educational values, not clinically valid simulation parameters.
- `SimulationSystem` is headless-testable; `Renderer` does **not** mutate simulation state.
- An event bus serializes tool actions, scenario transitions, alerts and abort decisions.
- All state changes trace to time-stamped, seed-reproducible actions.

## Coordinate and unit contracts
`ScreenPoint` in physical pixels; `UIPoint` in logical scaled units; `EyePoint` normalized local (x,y,z); `CameraRay` for 3D picking. A single transform service handles screen↔eye conversions. Never implicitly mix pixels, mm or normalized distance.

## Systems
1. Patient/anesthesia: synthetic ECG/HR, BP, SpO2, cooperation/motion; monitors reflect a single shared PatientState.
2. Anatomy: cornea, anterior chamber, iris/pupil, lens, capsule, IOL as separate logical objects.
3. Instruments: input adapter, tip pose, proximity contacts, cursor damping and per-task actions.
4. Procedure: nine-phase finite-state machine with guards, retry/abort/help paths.
5. Complications: seeded conditional scenarios, risk accumulation and reversible/terminal branches.
6. Assessment: transparent scoring, safety vetoes, action trace, task metrics.
7. Presentation: visual renderer and monitor/UI independently consume snapshots.

## 3D MVP performance budgets (targets, not benchmarks)
1920×1080 @60fps for current midrange Windows GPU; fixed update, minimal shader passes, LOD, instancing where useful, deferred advanced translucency. Profiling must measure average, P95 frame time, draw calls, VRAM and memory usage; provide fallback 2.5D quality mode. True corneal optics and biomechanical deformation remain optional research extensions.

## Test plan
- FSM: stages never advance without gates; abort allowed in all critical states
- Unit: invariant ranges; no NaN/negative state; deterministic seed replay
- Interaction: camera transforms round-trip tolerance and tool-tip collision guards
- Integration: 2.5D and 3D backends produce compatible visibility IDs/picking
- UI: monitors always read current patient snapshot; paused simulation doesn't advance
- Stress: repeated scene transitions and session exports without leaks
- Accessibility: keyboard-equivalent paths, contrast, font scaling, reduced-motion coverage

## Suggested directory tree
```
src/ophthosim/
  app/          # game loop, scene switching, config
  domain/       # patient, eye, tool state typed models
  simulation/   # deterministic state progression
  procedures/   # cataract phase machine
  rendering/    # backend protocol, 2.5d/, gl3d/
  ui/           # HUD, monitor, menus
  events/       # events and complication rules
  research/     # logger, synthetic scenario export, assessment
tests/
assets/concepts/ assets/models/ assets/textures/ assets/audio/
docs/
```

## Critical early decision gate
After WP04 run the Pygame+OpenGL feasibility spike on target Windows device. If frame/context interoperability is fragile, use a dedicated 3D engine for the surgical viewport or remain in polished 2.5D without coupling business logic to rendering.

## v1.1 design review — decisions and risk gates

### Renderer choice is a measured decision, not an assumption
**Path A:** Pygame surfaces for 2.5D and independent UI. **Path B:** Pygame OpenGL window with a ModernGL context and UI drawn via GPU-uploaded texture(s). Do not assume Pygame software surfaces can be directly blitted onto an OpenGL display. Prototype texture upload, text rendering, resize, fullscreen toggle, input and context restoration under Windows; document benchmarks and compatibility. Do not launch separate blocking render loops. If Path B fails, ship Path A or re-evaluate a dedicated 3D engine rather than force dual context hacks.

### Gate WP04 (pass/fail)
On target Windows machine: render rotating simplified eye mesh, eye-camera pan/zoom, two overlay panels, mock ECG; handle resize and DPI changes; perform screen→ray→hit test and reset. Log GPU/driver/library versions and 5-minute fps/P95 frame time/memory. **Pass** only if input mapping remains aligned after zoom/resize and UI overlay stays legible without crashes. 60fps at 1080p is an aspirational target; 30fps fallback is allowed as a documented degraded mode. All performance numbers measured, never fabricated.

### Physics scope
No surgical force prediction, no physiologically accurate lens removal. Use simple capsule region geometry, sprite/mesh blend states and particle pool with bounded size. Put collision layer in simulation domain, never in shaders. 3D deformation is optical approximation and MUST NOT drive clinical scoring.

### Data schema & replay
Every event has `schema_version`, `session_id` (random synthetic ID), `scenario_id`, `seed`, `step_index`, `sim_time_ms`, `event_type`, `payload`. Do not rely on wall-clock timestamps for deterministic replay. JSONL stores authoritative event stream; CSV is analysis export. No personal identifiers, no external telemetry by default. Include versioned event migration and dataset dictionary.

### Explicit application loop
Handle input → map to semantic commands → advance fixed simulation steps (bounded catch-up) → snapshot → render surgical viewport → compose UI → log resulting events. Pause blocks simulation time advancement while rendering menus. Resume with no accumulated time jump. Replay reads commands and seed in recorded order.

### Quality gates & dependencies
WP01–04 before 3D scope approval. Eye model and coordinate transforms before tool collision. Event schema before assessment and complications. Scoring requires explainable raw event references. Rendering backend never directly changes synthetic patient values. Automated CI can run headless simulation tests even when OpenGL is unavailable.

## 2026-10-12 3D geometry increment — not a completed renderer
Implemented in `ophthosim/geometry.py`: immutable mesh vertices/normals/face indices for schematic cornea dome, iris annulus, sclera and two elliptical optical elements (original lens/IOL). +Z points towards the microscope, units are **normalized**, and a bounded ray/sphere hit test provides a future picking primitive. Triangle winding and input-resolution limits have automated tests. Meshes do not deform tissue and are not surgically accurate.

**Next integration gate:** upload meshes to an OpenGL vertex/index buffer; check orientation/culling, transparent-corneal depth sorting, view/projection matrices, DPI scaling, texture overlay for UI and resizing/context loss on Windows. Capture GPU environment and measured frame times. Only then can we label it live 3D. The CPU geometry tests are deliberately independent of ModernGL and do not satisfy WP04.

## Implemented optional GL experiment (2026-10-13)

`ophthosim/gl_preview.py` creates a single Pygame-owned OPENGL window and requests a ModernGL 3.3 context, packs authored procedural geometry into GPU-compatible vertex and index buffers, uses per-frame yaw/pitch/zoom uniforms, and draws a GPU-textured overlay. External `moderngl` is **optional** so default `python main.py` remains 2.5D and dependency-light.

The GL atlas has its own input loop and no surgical input/state mutations. Scene/HUD shaders and mesh buffers are tested **without a GPU**, but OpenGL execution and shader compilation are not validated in CI. The closed sclera renders as non-depth-writing background pending a future anatomical cutaway; do not mistake this for physical optics. See `docs/GPU_VALIDATION_CHECKLIST.md` for exact hardware gates and failure reporting.

## 2026-10-13: separate interactive GPU viewport proof

`gl_surgery.py` orchestrates the same authoritative `ReplayGame` state machine as the 2.5D UI. The `input3d.py` adapter reverses the GLSL camera mapping into a ray and intersects a **dimensionless educational task plane**. Guarded task actions are forwarded through semantic Game commands; all alerts, phase locks, safe aborts, score and journaling remain inside the engine. Visual progress is conveyed by immutable `AnatomyAppearance` values (synthetic opacity, residual matter, IOL centering) supplied to the renderer; the renderer does not change physics/game state.

The implemented surgery mode is *not yet a true 3D collision simulator*: no mesh pressure/contact, capsule cutting mesh, fluid simulation or procedural surgical physics. Task-plane input and true mesh inspection are different intentionally labeled features. CI reproduces state through `gl_surgery_smoke.py` on Mesa llvmpipe and validates exact JSONL replay. Physical Windows OpenGL driver/device acceptance remains a required separate gate.


## Non-physical stylus renderer contract (2026-10-13)

`tool3d.stylus_mesh()` generates one cached small 3D render mesh. `tool3d.visible_stylus(controller)` checks the strict controller's last accepted pose, active depth and safety/ending states; the renderer only receives an optional validated three-component world-space offset. `GPUEyePreview` retains the stylus VAO/VBO/IBO independently from regenerated eye meshes, translates through the existing GLSL `u_offset` and releases resources in `close()`.

The shader's **visual-overlay draw pass** intentionally ignores depth occlusion and face culling for legibility: it does **not** simulate tool tissue penetration, contact physics or clinical depth. Scene state remains authoritative in `ReplayGame`; no render call is allowed to issue a semantic game action. Source/dirty tests and Mesa framebuffer-delta integration are mandatory for changes in the visual tool pipeline.


## Read-only 3D contact guide contract (2026-10-13)

`contact3d.py` evaluates pre-existing **abstract normalized phase targets**, the selected educational tool depth and the immutable `ToolPose` snapshot. It exposes only `ContactGuide(status, location)`. It cannot call `Game.action`, alter case hazards or serialize new semantic events. Its bounded statuses also distinguish previous entry/capsule points from currently active targets.

`Surgery3DController.inspect` computes new hover feedback separately from `pointer` (which alone may invoke `Game.action`). Unsafe phases and wrong depth clear previously cached render poses, including on pause/resume. `GPUEyePreview` keeps one reusable ring geometry on the GPU and renders it at an optional world-space offset with status text and color; this visual ring is not physical tissue collision. Mesa smoke checks a center-eye pixel difference with the HUD unchanged. The whole pipeline remains synthetic educational design, not validated surgical training.


## Shared immutable 3D visual-frame proximity (2026-10-13)

`gl_surgery.run()` now calls `visual_feedback(Game)` and `probe_surface(controller, feedback)` once per frame and hands the same read-only probe to `GPUEyePreview.render(surface_probe=...)` and `SurgeryHUD.set_frame_proximity()`. HUD painting never traverses the triangle BVH; it reads the prepared probe and validates active phase, live stylus position, camera yaw/pitch and safety status before displaying unitless model gap. This avoids the former second HUD-time proximity lookup and prevents stale marker text after game transitions.

Regression spies prove two expected triangle-mesh lookups at probe preparation and zero further lookups during five HUD repaints. The visual result cannot drive procedural actions, replay, simulated complications or clinical interpretation. GPU marker draw remains a separate purely visual pass. This is an architectural optimization, **not measured wall-clock FPS or hardware 4K readiness**.
