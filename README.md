# Cataract Surgery Simulator — OphthoSim-AI

**Status:** Playable 2.5D surgeon game + experimental *interactive* ModernGL 3D mode (2026-10-13). The 3D mode passes its automated OpenGL smoke tests on a real Windows GPU; the full 32-work-package product, medical realism, 4K/sustained performance and manual desktop QA are **not complete**.

An open-source **mock cataract surgery game in which the player is the operating surgeon**. It is built around Python, Pygame for UI/input, and an optional hardware-accelerated 3D renderer. The project models a complete *abstracted* cataract surgery encounter: patient preparation, topical anesthesia and monitoring, microscope navigation, corneal entry, capsular task, cataract removal, residual material cleanup, intraocular lens (IOL) placement, wound assessment, recovery, and result scoring.

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

You are the surgeon, and the game follows the real order of a phaco cataract operation ([realism plan](docs/SURGERY_REALISM_PLAN_KO.md)):

1. **Case brief and time-out.** Keys **1–9** pick a case. Each has realistic risk factors, such as floppy-iris risk, pseudoexfoliation or a posterior polar cataract. **Space** runs the time-out and then anaesthesia/prep.
2. **Incisions.** Click the main incision and the two side ports, then press **V** to fill the chamber with viscoelastic.
3. **Capsulorhexis.** Drag round the ring. Pulling outwards tears the capsule, and much sooner without viscoelastic.
4. **Phacoemulsification.** Press **D** for hydrodissection, then hold on the nucleus (about 4 s).
5. **Cortex I/A.** Hold on the inner lens (about 3 s).
6. **IOL.** Press **V** to fill the bag, then click once at the centre.
7. **Closure checks.** IOL, wound watertight, handoff (click or **1–3**).

Complications appear at realistic stages: wrong-site alert, patient movement, vital alert, anterior capsule tear, zonular weakness, iris prolapse, posterior capsule rupture and wound leak. Instruments stop on a safety hold. Press **A** to assess what you see, then decide with **1** continue / **2** manage (stop, stabilise, call for help) / **3** stop and refer. Each case ends as **SUCCESS**, **COMPLICATION MANAGED**, **COMPLICATED**, **SAFE ABORT** or **CRITICAL FAILURE** (ignoring a major complication; score 0). **X** stops safely at any time, **Esc** pauses, **R** restarts, and **E** exports the session after the debrief. Management options are deliberately abstract: no device settings, drug doses or rescue techniques.

Keep the instrument tip inside the pupil. Off-target work builds **tissue stress**: it decays while you work centrally, shows a warning at 50 %, and at 100 % raises a capsule complication. Stopping safely after a complication is the correct call and is credited in the debrief.

**3D mode** (`python -m ophthosim.gl_surgery`): same procedure, cases and keys (V, D, 1–3), plus instrument **depth**. The tip starts above the eye and keeps its depth between steps, so bring it to each step's working depth with **Q/E** or the **mouse wheel** (the depth gauge turns green). Arrows orbit, +/- zoom, **S** saves after the debrief.

The game contains a procedural illustrated 2.5D eye and synthetic HR/BP/SpO2 displays. **It is not a validated surgical trainer**. For test commands and caveats see [test report](docs/TEST_REPORT.md) and [implementation progress](docs/PROGRESS.md).

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
- Pure-Python deterministic geometry, BVH picking and synthetic signals (no NumPy dependency)
- Pygame 2.5D interactive surgery and CPU 3D anatomy preview (implemented)
- **Experimental** ModernGL interactive 3D mode; automated GL smoke tests pass on Linux Mesa (CI) and on a Windows NVIDIA GPU (local run, 2026-10-13). Manual play-testing, AMD/Intel GPUs and 4K remain open
- Blender-authored original assets or appropriately licensed models
- pytest, typed models, deterministic scenario seeds, CSV/JSONL logs
- Windows target, 1080p native UI with scalable 4K support

## Research goals
Investigate simulated interaction metrics and accessibility adaptation: track cursor/tool path efficiency, near-miss events, task time, visibility interventions and complication recognition time. Evaluate against simple baseline strategies and distinguish internal synthetic results from validated clinical claims. See [research plan](docs/RESEARCH_PLAN.md).

> **Educational and research prototype only.** No clinical procedural instructions, drug dosing, tool power settings or real-patient treatment recommendations. Not a medical device, surgical training certification tool or validated physiologic model. All numbers in the simulation are synthetic until independently validated.

## Review v1.2 — development guardrails
The reviewed specifications now define a 2.5D playable MVP before 3D polish, explicit stage guards and safe-abort branches, seeded exceptions, deterministic session replay, acceptance tests, input/camera collision handling, and predeclared research metrics. **True 3D remains conditional on a Windows ModernGL interoperability/performance spike (WP04), not an implemented or guaranteed capability.**

## Deterministic test replay (implemented, educational only)

When an interactive case ends, press `E` (2.5D) or `S` (3D). The game saves two synthetic JSONL files in `session_logs/`: `case_<scenario>_seed_<seed>.jsonl` (state/event trace) and `case_<scenario>_seed_<seed>.replay.jsonl` (every semantic command that changed the simulation, accepted or rejected, with run-length-compressed simulation ticks). Commands that changed nothing are not journaled, so mouse-heavy sessions stay small. Earlier saves are never overwritten: later files get a `_2`, `_3`... suffix. Replay is an analysis tool, not an animated playback UI.

Held instruments act once per fixed 1/60 s simulation tick, so progress, tissue stress and the replay are identical at any frame rate or mouse polling rate.

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
**WP04:** The automated GL smoke tests now pass on a Windows NVIDIA GPU (see [GPU checklist](docs/GPU_VALIDATION_CHECKLIST.md)). Still open: manual play-testing of the 3D mode, resize/DPI behaviour, a sustained 1080p/4K frame-time benchmark and AMD/Intel GPUs. CI validates source/CPU geometry, SDL dummy rendering and Mesa software OpenGL but does not GPU-benchmark it.

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


## Read-only triangle-mesh inspection with bounded BVH (2026-10-13)

The independent **3D anatomy atlas** (`python -m ophthosim.gl_preview`) now selects the *actual rigid triangulated iris and lens/IOL visual mesh*, rather than relying on the older analytic iris-plane/ellipsoid approximation. A Möller–Trumbore double-sided ray/triangle test and bounded **bounding-volume hierarchy (BVH)** compute the nearest triangle's number, position, ray distance, and barycentric weights. Mouse selection exposes the actual face ID and measured synthetic ray distance in the HUD. Indexes are constructed on a scene-mesh change, not once per frame or hover.

**Scope boundary:** the selection uses static geometry for the standalone atlas. GPU shader deformations (folded IOL), appearance offsets, patient-eye motion, scene occlusion details and the interactive 3D surgery's tool collision/force response are **not represented in this CPU collision model**. Transparent cornea and decorative sclera are excluded. A triangle hit **does not** change procedural state, tissue damage, score, alerts or replay. These are procedural synthetic meshes and not medical anatomy.

[Python 3.12 and 3.13 tests: 452 passed each](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38345423438); [Mesa OpenGL smoke with iris and optic triangle face IDs + full surgical replay](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38345423347). [Screenshot artifact](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38345423347/artifacts/11788119181). Real Windows Radeon GPU performance/4K and clinical review are still unverified.


## Deformed-IOL triangle picking parity (2026-10-13)

The standalone ModernGL anatomy atlas now matches CPU read-only triangle
selection to its **synthetic GPU IOL unfolding geometry**, IOL alignment offset,
and bounded camera-plane visual motion. In IOL atlas view, press **F** to cycle
the **fully unfolded → folded → halfway → unfolded** depiction. Mesh-picking
indexes are rebuilt **on demand at selection time** only when deployment or
alignment changes; the source 3D render mesh is not changed. A bounded
16-entry mesh cache validates inputs **before** lookup, avoiding bool-vs-int
cache aliasing and unhashable-input errors.

The CPU deformation reproduces the explicit GPU vertex-position equations,
not a physically accurate foldable implant. Selecting a point on the extended
unfolded optic correctly yields an IOL face, while the same position misses
after folding. The renderer uses the corresponding IOL shape; the unchanged
iris remains separately pickable. Software OpenGL captures compare eye-center
pixels, not just the changing HUD percentage. This is a **read-only atlas
inspection** capability: the interactive simulated surgery still uses its
existing stage-based guide and safety-state engine rather than physical
triangle/tool force collision.

**Verified** [Python 3.12/3.13: 480 tests passed per version](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38351299492)
and [Linux Mesa OpenGL integration](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38351299510).
**Not verified:** Windows AMD/Radeon hardware or 4K performance, corneal
refraction/transparent occlusion parity, deforming tissue contact mechanics,
clinical relevance, or complete 32-WP readiness.


## Unitless nearest-triangle visual proximity in the interactive 3D game (2026-10-13)

The synthetic interactive 3D mode now computes the Euclidean nearest point from
the **validated, safely visible virtual stylus tip** to actual authored iris,
crystalline-lens or visually folded/aligned IOL **triangle faces**. A bounded
BVH branch-and-bound search uses exact point-to-triangle closest-point regions,
including triangle edges, vertices and nonfatal degenerate faces. Static mesh
indexes are cached; the synthetic IOL BVH is cached for up to eight
deployment/alignment states. Where the scene is visually moved, the same
camera-plane transformation is inverted for the read-only distance query.

This appears as a separate 3D nearest-surface marker and **MESH GAP:
CLOSE/NEAR/FAR (synthetic)** HUD label. Distances are **unitless model
coordinates**, not millimeters or clinically meaningful separation. These
thresholds are artistic feedback, NOT injury triggers. During a patient safety
hold, pause, ending, invalid/outdated tool pose or inactive procedure, the
visual tool and proximity indicator are suppressed. The procedural
`ReplayGame` retains exclusive authority over actions, phases, alerts,
scoring and event/replay records.

**Verified:** [Python 3.12 and 3.13 CI: 510 passed per version](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38355094995)
and [Mesa Linux software OpenGL integration](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38355095000)
with different *eye-only* framebuffer pixels when the nearest-triangle
marker is present. [Rendered synthetic screenshots](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38355095000/artifacts/11792706594).

**Not validated:** real tool/tissue force, contact physics, anatomical accuracy,
real-world surgical training, Windows Radeon GPU or 4K desktop frame-time
performance. The 32-work-package project is still in progress.


## Single-evaluation 3D proximity per visual frame (2026-10-13)

The interactive GPU surgery loop now computes the **synthetic nearest-triangle
surface probe once per frame** and shares that one validated result between
the GPU's nearest-surface ring and the 2D Pygame HUD. Previously the HUD
triggered a second, redundant BVH proximity query after the renderer's
own query. `SurgeryHUD.set_frame_proximity()` receives the prepared,
read-only `SurfaceProbe`; `SurgeryHUD.draw()` only reads it.

The HUD suppresses a stale prepared result after a stage transition, camera
orbit, tool tip movement, safety alert, pause/abort, or restart. It displays
`MESH GAP: CLOSE/NEAR/FAR 0.000u` where **u = unitless model space**, not
millimetres or physical collision. The anatomical marker still uses its
existing read-only GPU overlay. No procedural actions, safety gates, score,
injury assessments or replay events are derived from this display data.

[Python CI: 522 passed on each of 3.12 and 3.13](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38355978889);
[Mesa Linux OpenGL full synthetic surgery CI](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38355978911),
including the same three normal/complication scenarios and screenshot artifacts.
New regression checks instrument the BVH distance call count and ensure repeated
HUD draws add **zero** BVH distance queries. This reduces redundant work; it
does **not** establish a measured FPS speedup or 4K/Windows GPU performance.

**Remaining:** 4K readability and sustained frame-time profiling on physical
Windows AMD hardware, deforming tissue physics, medical realism validation and
completion of the full 32-work-package plan.
