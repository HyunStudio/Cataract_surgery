# Godot Surgery Game Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Ship a playable offline Windows 3D cataract game from preparation to results, with instruments, tissue feedback, hazards and replay.

**Architecture:** Pure GDScript RefCounted procedure state owns all progression. Node3D visuals read it; a Camera3D adapter creates normalized semantic inputs. Existing Python code stays independent.

**Tech Stack:** Godot 4.7.2 stable, GDScript, Compatibility renderer, Windows x64.

**Spec:** docs/superpowers/specs/2026-10-26-godot-surgery-design.md

## Global Constraints
- Windows x64, mouse/keyboard, Korean UI, offline single player.
- No patient data, no clinical power/dose settings, no external runtime downloads.
- Wrong instruments, out-of-region/depth input, pause and alert must not progress tasks.
- Existing Python suite remains green. Godot behavior is tested independently.
- Version 2 semantic replay, fixed 60Hz simulation, game-relative geometry.

## Review Focus
- Held input at a phase/tool change must require release and a new press.
- Pointer over UI or outside operative view must stop surgical input.
- Rapid tool movement must not jump across protected boundaries undetected.
- Replay malformed data must fail without partial success.
- Resize, mode/camera switching and pause must clear held input and preserve state.

### Task 1: Domain + semantic replay
**Files:** godot/scripts/procedure_session.gd, godot/tests/test_session.gd
**Interfaces:** Session.new(); phase:String; tool:String; case_id:String; paused:bool; alert:String; ending:String; progress:float; eye:Dictionary; events:Array; reset(case_id,seed); select_tool(id)->bool; confirm()->bool; begin_stroke(); end_stroke(); act(point:Vector3,dt:float)->bool; tick(dt); assess(); abort(); snapshot()->Dictionary; export_log()->String; replay_log(raw)->Dictionary.
- [x] Write tests for complete normal route, wrong tool/depth, discontinuous capsule path, phase transition held click, three hazards, restart, deterministic replay and invalid replay.
- [x] Run failing suite before implementation.
- [x] Implement pure fixed-tick domain and replay with bounded finite inputs and region-local tissue state.
- [x] Run headless suite to green.

### Task 2: 3D operating room and eye assets
**Files:** godot/scripts/surgical_world.gd, godot/tests/test_world.gd, godot/assets/manifest.json
**Interfaces:** World extends Node3D; build(); microscope:Camera3D; room_camera:Camera3D; set_room_view(bool); update_state(snapshot:Dictionary,tip:Vector3,tool_id:String,active:bool); normalized_to_world(Vector3)->Vector3; world_to_normalized(Vector3)->Vector3. Model coordinates: eye x/y 0..1; world x=(x-.5)*4, world z=(y-.5)*4; positive world y toward microscope; normalized z in [-.3,.3] maps world y=0.8+z. Microscope overhead with screen up toward world -Z. Tool tip must be model origin.
- [x] Write headless tests for separate visible anatomy/instrument nodes, eye coordinate roundtrip and tissue changes affecting geometry.
- [x] Observe failing tests, implement original procedural meshes/materials and bounded fragments, distinct seven instrument models.
- [x] Add room, lighting, drape, patient, microscope, tray, local assets manifest.
- [x] Run world tests and capture actual rendered frames during integration.

### Task 3: Application, UI and input integration
**Files:** godot/project.godot, godot/main.tscn, godot/scripts/main.gd, godot/scripts/monitor.gd, godot/tests/test_integration.gd
**Interfaces:** Uses Session and World above, no direct mutation of session internals by renderer.
- [x] Test boot and normal/hazard integration, UI bounds, release-to-rearm, room mode and pause lock.
- [x] Implement main screen, 3D viewport, Korean briefing, stage/tool panels, patient monitor, synchronized depth diagram, result/report/export, settings and procedural audio.
- [x] Add ray-to-operative-plane coordinates, depth wheel, UI-safe input and swept sample interpolation, camera/zoom/pause resets.
- [x] Run headless tests and actual GPU screenshots; fix any shader/parse/input regressions.

### Task 4: Delivery and review
**Files:** godot/export_presets.cfg, tools/run-godot.ps1, docs/GODOT_GAME_KO.md, docs/GODOT_VALIDATION.md, README.md, .github/workflows/godot.yml
- [x] Run Python suite + all Godot suites, inspect gameplay captures and final branch diff.
- [x] Export Windows executable, perform rendered runtime smoke and measured 5-minute 1080p benchmark; report actual renderer and frame times.
- [x] Fresh independent review, fix important findings and rerun relevant tests.
- [x] Update README/status/run guide/assets provenance with verified limitations and artifact paths.

## Execution rulings and ledger
- User said “완성해” after the full design: authorized implementation, no further plan approval round. Execute and verify without asking again.
- Fresh clone is already dedicated to this task; use a feature branch in place, avoid creating another worktree and asking consent.
- Parallel asset/domain implementation uses isolated file ownership under dispatching-parallel-agents; main agent owns app/integration/review.
- Baseline: 522 Python tests passed before Godot changes.

## Completion ledger
- All four tasks complete. 522 Python tests passed; five Godot suites and actual GPU playthrough passed.
- Independent reviewer reproduced and verified fixes for four input/path bugs.
- Windows x64 release exported and native GPU smoke exited 0; standalone ZIP 39,347,058 bytes.
- Final 300-second 1080p RTX 3070 sample: 59.97 mean FPS, 18.537ms P95 (idle ENTRY scene only).
- Source stays on feat/godot-surgery-game; no main merge or remote publication performed.
