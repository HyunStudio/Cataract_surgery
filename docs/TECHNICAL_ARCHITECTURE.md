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
