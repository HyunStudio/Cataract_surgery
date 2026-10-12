# Cataract Surgery Simulator — OphthoSim-AI

**Status:** Initial playable 2.5D research prototype (2026-10-12). Full 32-WP design and true 3D are **not complete**.

An open-source, educational **2.5D-to-3D cataract microsurgery simulator** built around Python, Pygame for UI/input, and an optional hardware-accelerated 3D renderer. The project models a complete *abstracted* cataract surgery encounter: patient preparation, topical anesthesia and monitoring, microscope navigation, corneal entry, capsular task, cataract removal, residual material cleanup, intraocular lens (IOL) placement, wound assessment, recovery, and result scoring.

## Documentation
- [Product and gameplay specification (Korean)](docs/PRODUCT_SPEC_KO.md)
- [Visual and interaction design (Korean)](docs/VISUAL_DESIGN_KO.md)
- [3D rendering and technical architecture](docs/TECHNICAL_ARCHITECTURE.md)
- [32-work-package roadmap](docs/ROADMAP.md)
- [Research and evaluation plan](docs/RESEARCH_PLAN.md)
- [Safety, realism and limitations](docs/SAFETY.md)

## Quick start (Windows / Python 3.12+)

```powershell
python -m pip install -r requirements.txt
python main.py
# optional: python main.py --case motion --seed 42 --scale 1.5
```

Keys: **1–4** select a synthetic case on the first screen; **Space** confirms pre-op/anesthesia screens; **left-click** marked approach targets; **left-drag** the guide ring for capsular task; **hold left mouse** in the lens field for removal/cleanup; **left-click** central marker for IOL alignment; **left-click** final safety checks. **A** assesses a monitor alert, **X** safe-aborts, **Esc** pauses, **R** restarts, and **E** exports synthetic JSONL data after an ending.

The game contains a procedural illustrated 2.5D eye and synthetic HR/BP/SpO2 displays. **It is not yet a real 3D surgical trainer**. For test commands and caveats see [test report](docs/TEST_REPORT.md) and [implementation progress](docs/PROGRESS.md).

## Visual direction
A **microscope-first** interface with a visually realistic iris/cornea/lens, coupled to a synchronized cross-sectional depth view. Patient vital signs and a small anesthesia status panel occupy the periphery, not the operative field. A 2.5D vertical slice comes first; optional 3D meshes, camera orbit and shader-based effects are introduced behind a stable renderer interface. See the visual design document for layout, typography, accessibility and feedback specifications.

## Intended gameplay sequence
1. Preoperative verification and scenario selection
2. Anesthesia and patient preparation (abstracted)
3. Microscope alignment and surgical entry
4. Capsular access and circular precision challenge
5. Simulated lens fragmentation and removal
6. Residual lens material cleanup
7. Foldable IOL insertion, unfolding and alignment
8. Wound integrity checks and handoff
9. Recovery and performance report

Events may include patient motion/anxiety, unstable view, capsular damage, posterior capsule rupture, corneal haze, IOL decentration, wound leak and vital sign alerts. **Recognizing and safely stopping** may be the successful response; the game will not reward proceeding through unsafe situations.

## Technology (proposed, not yet implemented)
- Python 3.12; Pygame (application/UI, desktop inputs)
- NumPy for deterministic geometry and synthetic signals
- Renderer adapter: Pygame 2.5D prototype, optional ModernGL/OpenGL-backed mesh renderer
- Blender-authored original assets or appropriately licensed models
- pytest, typed models, deterministic scenario seeds, CSV/JSONL logs
- Windows target, 1080p native UI with scalable 4K support

## Research goals
Investigate simulated interaction metrics and accessibility adaptation: track cursor/tool path efficiency, near-miss events, task time, visibility interventions and complication recognition time. Evaluate against simple baseline strategies and distinguish internal synthetic results from validated clinical claims. See [research plan](docs/RESEARCH_PLAN.md).

> **Educational and research prototype only.** No clinical procedural instructions, drug dosing, tool power settings or real-patient treatment recommendations. Not a medical device, surgical training certification tool or validated physiologic model. All numbers in the simulation are synthetic until independently validated.

## Review v1.2 — development guardrails
The reviewed specifications now define a 2.5D playable MVP before 3D polish, explicit stage guards and safe-abort branches, seeded exceptions, deterministic session replay, acceptance tests, input/camera collision handling, and predeclared research metrics. **True 3D remains conditional on a Windows ModernGL interoperability/performance spike (WP04), not an implemented or guaranteed capability.**

## Deterministic test replay (implemented, educational only)

When an interactive case ends, press `E`. The game saves two synthetic JSONL files in `session_logs/`: `case_<scenario>_seed_<seed>.jsonl` (state/event trace) and `case_<scenario>_seed_<seed>.replay.jsonl` (accepted and state-changing rejected semantic input commands with run-length-compressed simulation ticks). Replay is an analysis tool, not an animated playback UI.

A replay can be independently checked using:

```python
from pathlib import Path
from ophthosim.replay import ReplayGame

raw = Path("session_logs/case_normal_seed_7.replay.jsonl").read_text(encoding="utf-8")
session = ReplayGame.replay_jsonl(raw)
print(session.phase.value, session.score(), session.ending)
```

Integrity includes command-journal and resulting event/snapshot SHA-256 digests. These catch accidental or unsanctioned edits **but do not authenticate authorship** without digital signatures. Raw mouse trajectories, clinician assessments and real patient data are not captured. Unrepresentable replay captures fail closed rather than silently export incomplete traces.

## Next milestone
**WP04:** GPU/Pygame interoperability and graphical smoke test on an actual Windows desktop, then measured selection of a production 3D rendering approach. The current graphical interface has not been launched or GPU-benchmarked in the headless coding environment.

## License
See repository [LICENSE](LICENSE); external assets must have their own documented provenance and compatible redistribution permissions.

## 3D geometry prototype (not yet rendered)
The dependency-free `ophthosim/geometry.py` now generates bounded procedural **sclera, iris, crystalline lens, IOL and cornea** meshes with vertex normals and triangle indices. It also implements ray/sphere intersection for future depth-aware tool picking. This is normalized graphical geometry — **not** validated ocular anatomy, a surgical instrument simulator, or real-time 3D rendering. See the technical architecture and test suite for the GPU renderer gate.

## Standalone replay verification
After exporting a session, check it without launching Pygame:

```bash
python -m ophthosim.verify_replay session_logs/case_normal_seed_7.replay.jsonl
```

A verified replay reports its synthetic ending, score and simulation step count. Invalid, tampered or missing files return a nonzero status.
