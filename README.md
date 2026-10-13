# Cataract Surgery Simulator — OphthoSim-AI

**Status:** Playable 2.5D prototype + experimental *interactive* ModernGL 3D synthetic surgery mode (2026-10-13). The full 32-work-package product, medical realism and Windows GPU QA are **not complete**.

An open-source, educational **2.5D-to-3D cataract microsurgery simulator** built around Python, Pygame for UI/input, and an optional hardware-accelerated 3D renderer. The project models a complete *abstracted* cataract surgery encounter: patient preparation, topical anesthesia and monitoring, microscope navigation, corneal entry, capsular task, cataract removal, residual material cleanup, intraocular lens (IOL) placement, wound assessment, recovery, and result scoring.

## Documentation
- [Product and gameplay specification (Korean)](docs/PRODUCT_SPEC_KO.md)
- [Visual and interaction design (Korean)](docs/VISUAL_DESIGN_KO.md)
- [3D rendering and technical architecture](docs/TECHNICAL_ARCHITECTURE.md)
- [32-work-package roadmap](docs/ROADMAP.md)
- [Research and evaluation plan](docs/RESEARCH_PLAN.md)
- [Safety, realism and limitations](docs/SAFETY.md)
- [Windows ModernGL GPU validation checklist](docs/GPU_VALIDATION_CHECKLIST.md)
- [Interactive 3D surgical prototype setup and controls (Korean)](docs/INTERACTIVE_3D_USAGE_KO.md)

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

## Implemented stack and proposed extensions
- Python 3.12; Pygame (application/UI, desktop inputs)
- NumPy for deterministic geometry and synthetic signals
- Pygame 2.5D interactive surgery and CPU 3D anatomy preview (implemented)
- Separate **experimental** ModernGL GPU atlas demo (code implemented, real Windows GPU execution **unverified**)
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
**WP04:** Execute the now-playable experimental 3D synthetic surgery viewport on an actual Windows desktop, check shader compilation and HUD/depth accuracy, and benchmark rendering before treating the 3D backend as production-ready. CI validates source/CPU geometry and SDL dummy rendering but does not GPU-benchmark it.

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

## Interactive 3D anatomy preview (implemented, CPU-rendered)

Press **G** during gameplay to switch between the interactive 2.5D surgical scene and a **non-interactive 3D mesh anatomy preview**. In preview mode press **J/L** to yaw left/right and **I/K** to tilt; press **G** again to resume 2.5D interaction. Preview mode deliberately blocks surgical mouse actions to avoid mapping 3D projection pixels into the 2D task coordinates.

This uses cached normalized 3D iris, lens/IOL and corneal dome meshes, real 3D rotation and perspective projection, back-face selection and painter sorting. **Triangles are rasterized by Pygame on the CPU. It is not a ModernGL/GPU renderer, does not provide 3D tool picking, and must not be described as completed 3D surgery.** Model state drives which synthetic lens is visible. Run `python -m pytest -q` to validate projection and mode isolation.

CI evidence for the increment: [GitHub Actions run 38272300713](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38272300713) — Python 3.12/3.13 jobs green; 116 tests on Python 3.12. Hardware GPU/Windows validation still outstanding.

## Experimental hardware-accelerated atlas (new, not a 3D surgical game)

An opt-in ModernGL shader renderer is now available as a separate feasibility demo:

```powershell
python -m pip install -r requirements-3d.txt
python -m ophthosim.gl_preview --check   # CPU mesh validation, **not** a GPU check
python -m ophthosim.gl_preview           # attempts real OpenGL 3.3 context
```

Orbit with arrow keys, zoom with +/- and switch between cloudy lens / simulated IOL with Space. The Pygame 2.5D surgical game remains under `python main.py`. The GPU atlas cannot perform surgery, tool picking, tissue deformation, or provide clinically valid optical realism. Follow the [GPU validation checklist](docs/GPU_VALIDATION_CHECKLIST.md) on a real Windows machine before claiming hardware rendering support.

## Shared synthetic ECG and pulse monitor (new)

The game's synthetic ECG and pulse waveform shapes now change with the same in-game heart-rate state displayed in the monitor. No vital signs are measured and the schematic curves have **no diagnostic or clinical physiological interpretation**. Automated GUI tests check that two simulated heart rates produce different rendered waveforms.

[Latest tested CI run](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38318581035): Python 3.12/3.13 jobs success; **167 tests** passed on 3.12. GitHub CI runs without a physical monitor, GPU, or clinical evaluation.

## Linux software OpenGL smoke: verified (2026-10-13)

An isolated GitHub Actions workflow [Software OpenGL Smoke, run 38319493162](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38319493162) successfully created an OpenGL context using **Mesa llvmpipe**, compiled the ModernGL scene/HUD shaders, performed read-only 3D iris ray picking, rendered synthetic cataract and IOL states, read back the framebuffer and generated distinct PNG screenshots. Reported software renderer: `llvmpipe (LLVM 20.1.2, 256 bits)`, OpenGL version 4.5. Two [PNG screenshots](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38319493162/artifacts/11779035082) are attached to the run.

**What it does not prove:** performance on the author's Windows AMD GPU, clinical fidelity, a finished 3D surgery game, GPU-based tissue simulation or actual operating-room training value.

In the standalone 3D atlas `python -m ophthosim.gl_preview`, left-click the iris or lens/IOL to inspect its synthetic surface label and ray depth; arrow keys orbit, +/- zoom, Space switches lens/IOL. This is read-only; normal surgical tasks remain in `python main.py`. The 3D depth picking coordinates are tested against the same projection/rotation mathematics used in GLSL.

## Experimental interactive 3D surgery (implemented, still non-clinical)

The **separate** ModernGL game now shares the proven 2.5D surgery state machine, deterministic replay, synthetic patient monitor and safety gates. It uses camera-correct 3D ray/plane mapping, stage-specific synthetic tool depth, visual guide targets, educational cataract lens color changes and IOL offset feedback. **This is an interactive 3D educational prototype, NOT accurate tissue collision, physical optics or a validated surgery trainer.**

```powershell
python -m pip install -r requirements-3d.txt
python -m ophthosim.gl_surgery --case normal --seed 7
```

Controls: **Space** next preop/anesthesia stage, **mouse** entry/capsular tracing/lens clearing, **a fresh click** for IOL placement, **1–3** final safety checks, **arrows** orbit, **+/-** zoom, **Q/E** tool depth, **A** acknowledge synthetic patient warning, **X** safe abort, **Esc** pause, **R** restart, **S** export results/replay after the end. The standard 2.5D game is still launched with `python main.py`. See [complete Korean guide](docs/INTERACTIVE_3D_USAGE_KO.md).

**Verified in CI:** [Python tests run 38334178228](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38334178228), **245 tests passed on Python 3.12 and successful Python 3.13 matrix**. [Mesa OpenGL run 38334142433](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38334142433) exercised two synthetic cases, a complete end-to-end surgical game replay, safe abort and eight distinct rendered frames including mid-phaco visual change. [Screenshot artifact](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38334142433/artifacts/11783937737). Windows physical GPU/4K performance is still unverified.


## 3D synthetic instrument visualization (2026-10-13)

The interactive GPU 3D surgery prototype now draws a **cached tapered synthetic stylus mesh** in the world coordinates of the most recent validated procedure input. The 3D mesh follows the controller's normalized tool position and educational depth plane; it is **not** a real surgical instrument model, physical collision object, or source of state changes. The tool is hidden when there is no valid pose, during safety hold/pause, after an ending, or when the pose no longer matches the active depth.

The stylus is drawn as a clear **visual overlay** to avoid misleadingly disappearing behind transparent display anatomy; its occlusion therefore does not model optical or tissue physics. The existing strict ReplayGame drives tasks and records replay deterministically.

[Verified 274-test CI](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38335940393) (Python 3.12/3.13 jobs succeeded); [Mesa OpenGL integration run](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38335940404) confirms real framebuffer pixel change when the 3D stylus appears, nine synthetic screenshots, normal completion, motion-alert safe stop and replay consistency. This is Linux software rasterization only. Windows GPU/4K and clinical assessments are **not** validated.


## Synthetic foldable IOL visual sequence (2026-10-13)

The **interactive 3D synthetic cataract game** now uses `ophthosim/iol3d.py` to construct a cached optic with two stylized curved haptics. A vertex-shader-only deformation compresses the model during the IOL stage; after a successful simulated placement, it smoothly unfolds over **1.5 seconds of simulation time**, not wall-clock time. Pausing the game freezes the animation; finishing Recovery displays the final deployment. Scoring, safety holds, patient state and the deterministic replay format are unaffected.

**Visual accuracy warning:** The model and unfolding timeline are artistic educational abstractions, not validated IOL mechanical/material behavior or clinical insertion guidance. The ophthalmic eye geometry is not a medical model.

A stricter Linux Mesa software-OpenGL test now hashes a **center-of-eye crop excluding the HUD** so changing deployment text alone cannot pass for visible unfolding. This revealed an existing bug: an opaque closed scleral globe was covering the iris and lens. The sclera now renders as a **depth-test-free background**, while iris and lens use normal scene depth testing. The repaired renders visibly show iris, pupil and simulated IOL; they are not physiologically accurate corneal optics.

[Verified Python 3.12/3.13 CI (289 tests each)](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38337153815) and [Mesa OpenGL screenshots](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38337153811/artifacts/11785108404). **Actual Windows Radeon GPU performance, detailed mesh realism, force interaction and clinical validation remain open.**


## Synthetic capsule integrity visualization (2026-10-13)

The interactive 3D game now displays a stylized pupil-centered **intact green/teal ring** or a **discontinuous red damaged ring**, driven exclusively by the existing `Game.eye.capsule_integrity` and appropriate stage visibility. The meshes are cached per OpenGL context; the display cannot affect progression, replay or complication decisions. In the deterministic `capsule` case, the capsule integrity event pauses surgery; assessing the warning causes a safe abort, with the damage indicator retained.

**Educational illustration only:** this is not a clinically accurate capsule location, rupture geometry, mechanical tear simulation, surgical rescue guidance or medical-device validation. The indicator is deliberately positioned for visibility in the simplified pupil view.

[Python 3.12/3.13 CI: 335 tests each](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38338000372), including malformed numerical state, cache/mesh integrity and 3 scenario safety checks. [Mesa llvmpipe OpenGL CI](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38338000377) validates different *central-eye* pixels (HUD excluded) for intact and injured capsule, and completes full normal, motion and capsule-injury scenarios. [Synthetic screenshots](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38338000377/artifacts/11785910265). Physical Windows GPU/4K validation and medical specialist review remain open.


## Synthetic movement and haze feedback / accessibility (2026-10-13)

The *separate interactive 3D prototype* now reads existing synthetic patient motion, game phase, opacity and cortex state through `ophthosim/vision3d.py`. Its camera-plane eye translation and frosted-view HUD veil are **visual metaphors only**; they are not physical eye tracking, simulated clinical optics, predictive physiology, or an input to the surgical collision/score engine. Motion is bounded and deterministic from **simulation time**, freezes during a safety hold, and never adds flashing or strobe animations.

- Press **M** in the 3D prototype to disable eye-motion displacement (reduced motion); warning text, pausing and safety locks remain fully active.
- Press **H** for an additional bright static high-contrast microscope outline. Both settings are purely local display choices.
- Synthetic opacity/cortex clearing reduces the veil in active procedural phases. The view remains clinically unvalidated and the 2.5D fallback is unchanged.

**Verified:** [Python 3.12 and 3.13, 395 tests each](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38340531317); [Mesa Linux software OpenGL full integration](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38340531344), showing distinct **center-eye** pixels for scene motion and haze and visual differences with reduced motion under the same patient-motion safety hold. [Captured screenshots](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38340531344/artifacts/11785993260). Windows Radeon hardware GPU, 4K monitor testing, contrast accessibility audit and clinical review remain **unverified**.


## Stage-aware 3D educational contact guide (2026-10-13)

Interactive 3D mode now includes a **read-only hover/contact guide** with a retained GPU world-space indicator ring. It evaluates the existing normalized stage targets, controller tool depth and patient safety state. Green = active target, blue = already visited, amber = near target. The exact state also appears as text in the HUD for non-color-only feedback. Wrong depth, offscreen misses, inactive phases, alerts and paused/ended sessions suppress the 3D ring.

Moving the mouse without pressing a button **never invokes Game.action**, changes the synthetic score, or adds replay events. A real click still passes through the original strict phase engine (including its existing safety assessment and IOL explicit fresh-click gate). Previously cached instrument poses are deliberately **not restored automatically after pause**; fresh hover reacquires the display position.

**Important limitation:** this is proximity feedback against **synthetic normalized task targets and a selected educational depth plane**, not a precise anatomical triangle mesh collision or force-feedback measurement. It must not be interpreted as a real surgery guidance system. Color/shape accessibility, real Windows GPU/4K, clinical review, and detailed tissue interaction remain to be tested.

[CI tests Python 3.12/3.13: 422 each](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38343565234). [Mesa OpenGL integration passed](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38343565188), proving the GPU contact ring changes center-eye pixels with otherwise identical state and HUD. [Screenshot artifact](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38343565188/artifacts/11788405053).
