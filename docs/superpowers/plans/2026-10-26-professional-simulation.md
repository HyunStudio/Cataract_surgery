# Professional cataract simulation integration plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement task by task, with independently owned numerical/visual subsystems delegated under dispatching-parallel-agents.

**Goal:** Integrate the numerical workbench and existing theatre into a coherent specialist simulation game, with cases, preparation, instruments, equipment, physical tissue response, IOL, and debrief.

**Architecture:** Keep pure numerical solvers separate from presentation. A case director observes actions and physical outcomes; it does not erase tissue or manufacture completion. The simulator is the primary app, the former procedural game remains an explicit comparison scene.

**Tech Stack:** Pinned Godot 4.7.2, GDScript, Windows x64, mouse/keyboard, Compatibility renderer.

**Spec:** User approved the professional Euro Truck/Flight Simulator direction and asked to proceed through completion. Prior numerical model limitations remain applicable; simulation-game polish does not imply clinical validation.

## Constraints
- Continuous tissue state across the encounter. No old eight-region timed removal in the new mode.
- Expert controls plus optional navigation/teaching assistance. All settings and assessment are simulator values.
- Two persistent tool poses, latched grasp and pedal release safety.
- New visuals must follow actual solver positions/connectivity rather than replacing physics with canned transitions.
- Real data calibration, clinical certification and hardware haptics remain explicit boundaries.

## Review focus
- Latched left grasp survives right-hand operation without duplicate integration.
- Equipment pedal has independent irrigation/aspiration/energy states and never remains armed after focus or camera change.
- Case endings derive from residual material, IOL deployment/alignment and final inspection, not UI button alone.
- IOL injection remains paused when input stops; unfolded state follows a bounded dynamics model.
- Dense numerical updates must preserve solver invariants and keep UI responsive; benchmark the new mode, do not reuse game FPS.

### Task 1: Numerical responsiveness and bimanual tissue
Files: capsule_solver.gd, tests/test_capsule_solver.gd; numerical optimization helpers if needed.
API: retain step()/release(), add step_tools(dt:float, tools:Array[Dictionary]) where tools contain hand:int,tip:Vector3,radius:float,grip:bool,cut:bool. release_hand(hand:int). Each tool may grasp one distinct vertex. One integration per time step. Existing public positions, triangles, edges and pressure_load remain.
- [x] Add failing tests two independent grippers, releasing one preserves other, contact/cut and pressure correctness.
- [x] Implement and optimize hot numerical loops without reducing mesh resolution or changing accepted material behavior silently.
- [x] Run full capsule suite; record representative step costs before/after.

### Task 2: Foldable IOL dynamics and case director
Files: iol_dynamics.gd, case_director.gd, corresponding tests.
IOL API: reset(); positions:PackedVector3Array; optic_count:int; step(dt,nozzle:Vector3,injecting:bool,tip:Vector3,manipulating:bool); metrics()->{delivered:float,deployed:bool,alignment:float,finite:bool}. Elastic rest constraints recover folded optic/haptics after user-controlled release from cartridge. No stage timer initiates injection. Finite bounded model, synthetic coefficients.
Director API: reset(case_id:String,seed:int); prepare(check_id:String); ready()->bool; observe(dt:float,observation:Dictionary); inspect(check_id:String)->bool; finish()->bool; abort(reason:String); snapshot()->Dictionary. Observation contains capsule/lens/iol metrics, tool/energy/movement/wound data. Cases standard/dense/small_pupil/motion. Result includes actionable simulation metrics, chronology, completion/safe-stop, no clinical skill claim. Entry wound observations are actual blade path/pivot evidence from app, not buttons.
- [x] Write and observe failing tests for bounded IOL user-triggered delivery, independent rest recovery, manipulation and malformed input.
- [x] Implement director with state-derived briefing/operating/debrief and final checks; no forced procedural minigame sequence.
- [x] Run tests including incomplete finish rejection and seeded hazard determinism.

### Task 3: Tissue surface and microscope presentation
Files: lens_surface.gd, microscope.gdshader, tests/test_lens_surface.gd. Do not modify simulator or solvers.
Surface API: update_from_solver(solver)->ArrayMesh; display membrane and nucleus as continuous surfaces tied to solver particles/bonds; detached fragments remain visible. Cache initial topology; no per-frame convex hull/voxel rebuild. Optical postprocess via canvas shader with focus/illumination/vignette settings.
- [x] Test actual particles/bond rupture alter mesh and inactive particles cannot leave phantom faces.
- [x] Implement smooth original lens shading, geometry and usable microscope optical feedback.
- [x] Render frame evidence with unchanged numerical state; document visual approximation.

### Task 4: Integrated operating experience
Files: simulator.gd refactor into focused supporting scripts; simulator.tscn; tests/test_simulator.gd + integrated surgical encounter tests.
- [x] Add case briefing/preparation, theatre-to-microscope view, simulation-first tool controls and optional navigation assistance.
- [x] Add per-hand latched forceps, axial depth, focus, independent pedal states, device presets and synthetic patient monitor.
- [x] Couple incision interaction, membrane and lens dynamics, IOL model, case director and final inspection. User can make mistakes or stop safely; instructor assistance explains, not erases state.
- [x] Add contextual objectives, equipment telemetry, tool sound, accessibility, pause/settings, result timeline and session export.
- [x] Run a full application-controlled encounter and adverse case; verify UI-safe input, focus/resize, replay/export limits and scene visuals.

### Task 5: Verification and delivery
- [x] Fresh independent code review, fix important findings with regression tests.
- [x] Full Python/Godot suites, actual GPU captures and 1080p measured runtime of the new integrated mode.
- [x] Windows release/native graphics smoke, standalone ZIP, controls/limitations/validation docs, clean local feature-branch commit.

## Execution rulings
User's instruction to finish follows the agreed product direction; proceed without another design approval round. Build on the dedicated clone/feature branch already in use. Preserve baseline artifacts. Deliver a playable specialist simulation game; do not call it an actual validated surgical trainer.

Execution completed 2026-10-27. See docs/SPECIALIST_VALIDATION.md for exact verification and model boundaries. Integration completion does not close historical clinical fidelity roadmap items.
