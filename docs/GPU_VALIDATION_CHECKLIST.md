# Windows GPU validation — experimental ModernGL atlas

Status: **GL01–GL09 checked on one Windows NVIDIA GPU (2026-10-24, see below); a person still signs off, and the AMD Radeon target remains open.** Python CI validates geometry and input, while a separate Linux Mesa llvmpipe software-OpenGL workflow **has actually compiled shaders and rendered two framebuffers**. Do not confuse a software OpenGL context with Windows physical GPU validation.

## Install and run

In a Windows PowerShell session with Python 3.12 or 3.13:

```powershell
git clone https://github.com/HyunStudio/Cataract_surgery.git
cd Cataract_surgery
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-3d.txt
python -m pytest -q
python -m ophthosim.gl_preview --check
python -m ophthosim.gl_preview
```

The `--check` flag validates CPU mesh buffers only; the last command opens a real GPU rendering window.

Controls: arrow keys rotate, +/- zoom, Space changes synthetic cataract lens to IOL, Esc exits. The preview is **not an interactive surgical procedure**. Current renderer uses a closed sclera background approximation (without depth write), actual rasterized triangle meshes for iris/lens and an alpha-blended corneal dome. It does not simulate physical optics or tissue deformability.

## Pass/fail checklist

| ID | Check | Expected | Status |
|---|---|---|---|
| GL01 | Open a Pygame OpenGL 3.3 core window and ModernGL context | Starts without exception | AUTOMATED PASS (RTX 3070) |
| GL02 | Compile both scene/HUD shader programs | No GLSL compilation errors | AUTOMATED PASS (RTX 3070) |
| GL03 | Iris, cloudy lens and corneal shell visibility | No missing layer or full occlusion | AUTOMATED PASS + screenshots |
| GL04 | Space changes scene from cataract to IOL | Visible synthetic optical state change | AUTOMATED PASS (RTX 3070) |
| GL05 | Orbit, zoom, extreme camera angles | No clipping/black screen/crashes | AUTOMATED PASS (18 views) |
| GL06 | Window resize / DPI / repeated scale changes | Correct aspect and HUD alignment | AUTOMATED PASS (10 resizes); DPI ≠100% not tested |
| GL07 | 5-minute run, repeated scene changes | No memory growth or context loss (`gl_benchmark --seconds 300`, see `memory`/`gl07`) | CANDIDATE_NO_GROWTH (RTX 3070) |
| GL08 | 1920×1080 frame time | Target ~60fps; document measured mean/P95 (`python -m ophthosim.gl_benchmark`) | CANDIDATE_WITHIN_60FPS (RTX 3070) |
| GL09 | Real Pygame 2.5D game remains working | No cross-mode regression | PASS (real `windows` video driver) |
| GL10 | Synthetic 3D mode is labeled non-clinical | Warnings visible | VISIBLE in hardware screenshots |

Collect operating system, GPU, driver version, OpenGL version, display scaling, Python/pygame/moderngl versions, average/P95 FPS and screenshots. Report failure if GL context creation is not possible. Never treat CPU offline checks or SDL dummy tests as hardware validation.

## Technical next steps

- Confirm shader compilation, culling orientation, depth interactions and HUD texture y-direction on target driver.
- Profile full-screen HUD RGBA texture upload each frame; optimize with a small static atlas or subregion upload if it dominates. *(2026-10-24: software-GL profiling showed it dominating; the HUD surface is now reused and uploaded zero-copy with a texture swizzle. Re-profile on Windows hardware with `ophthosim.gl_benchmark`.)*
- Add depth-picking and a synchronized object-space tool model before enabling any 3D surgery interactions.
- Replace the closed globe background shortcut with a modeled anterior scleral cutaway; validate layer visibility with real screenshots.
- Keep a fully playable 2.5D fallback until these tests pass.

## Additional completed Linux software-OpenGL gate (2026-10-13)

[GitHub Actions run 38319493162](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38319493162) passed on Mesa llvmpipe OpenGL 4.5. It verified context creation, shader compilation, transparent/opaque draw calls, read-only ray hit on iris, synthetic IOL/opaque-lens state changes, two nonblank PNG readbacks. [Screenshot artifact](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38319493162/artifacts/11779035082). These findings are for a Linux software rasterizer only; GL01–GL10 Windows statuses in the table above intentionally remain unchanged. Short 20-frame timing (2.97 ms mean) does not meet any sustained performance gate.

## Measuring GL08 with the scripted benchmark (2026-10-24)

The GL08 row now has a repeatable measurement tool. On the target Windows machine, close other GPU-heavy applications and run:

```powershell
python -m ophthosim.gl_benchmark --seconds 60 --size 1920x1080 --out build\benchmark\gl08-1080p.json
python -m ophthosim.gl_benchmark --seconds 60 --fullscreen --out build\benchmark\gl08-fullscreen.json
```

The workload stays in the synthetic ENTRY phase, orbits the camera and hovers the stylus along a fixed path, so the per-frame nearest-triangle query, contact ring, stylus, full-window HUD texture upload and buffer swap all run every frame. Hover never calls `Game.action`; the report records `game_state_unchanged` and the command exits nonzero if the synthetic Game or replay journal changed.

The JSON report contains mean/P50/P95/P99/max milliseconds for `frame` (interval between consecutive buffer swaps), `probe` (CPU proximity query) and `render` (draw, HUD upload and swap), plus OS, Python, pygame, moderngl, `GL_RENDERER`, `GL_VENDOR` and `GL_VERSION`. Its `gl08.status` is:

| Status | Meaning |
|---|---|
| `INSUFFICIENT_EVIDENCE` | Software/unknown renderer, window below 1920×1080, or under 60 s measured. Never counts toward GL08. |
| `CANDIDATE_WITHIN_60FPS` | Hardware renderer, ≥1920×1080, ≥60 s, and both mean and P95 ≤ 16.667 ms. |
| `CANDIDATE_BELOW_60FPS` | Same evidence conditions, but mean or P95 exceeds the 60 fps budget. |

A candidate status is **not** a pass by itself: attach the JSON, display scaling, driver version and a screenshot, and have a person update the table above. Timings are CPU wall clock, not GPU execution time, and vsync is not controlled. A display locked to 60 Hz will cap measured intervals near 16.7 ms, so report the refresh rate too. In the interactive game, **F3** shows a rolling frame mean/P95 (capped at 60 fps by the game loop) for quick manual checks.

### GL07 host-memory trend (2026-10-24)

`python -m ophthosim.gl_benchmark --seconds 300 --size 1920x1080` also samples this process's resident memory (Linux `/proc/self/statm`, Windows working set via `GetProcessMemoryInfo`) every 60 measured frames and at the end. The report's `memory` block gives start/end/peak MiB, total growth and a least-squares slope in MiB/min; `gl07.status` is `INSUFFICIENT_EVIDENCE` for software GL, runs under 300 s or platforms without a reader, and otherwise `CANDIDATE_NO_GROWTH` (total growth ≤ 16 MiB and **late-half** slope ≤ 1 MiB/min, triage heuristics only) or `CANDIDATE_GROWTH`. The late-half slope fits only samples from the second half of the run, because driver/allocator warm-up rises early and then plateaus (observed under Mesa: about +2.3 MiB in the first 250 scene switches, then flat for 2000), whereas a leak keeps rising. Dedicated GPU memory is **not** included; check it with the vendor tool (e.g. AMD Adrenalin metrics or Windows Task Manager "Dedicated GPU memory") during the same run. The workload does not yet exercise repeated case restarts or atlas scene switches.

## Windows hardware run (2026-10-24)

**Environment:** Windows 11 Pro (10.0.26200), NVIDIA GeForce RTX 3070 Laptop GPU, driver 566.14 (WDDM 32.0.15.6614), OpenGL 3.3.0 core, 3840×2160 display at 60 Hz with 100 % scaling, Python 3.12.10, pygame 2.6.1, moderngl 5.13.0. This is **not** the AMD Radeon target named elsewhere; that run is still open.

| Check | Result | Evidence |
|---|---|---|
| GL01–GL06 | `python -m ophthosim.gl_hardware_check` (new): all AUTOMATED_PASS. 18 extreme views (yaw ±1.2, pitch ±0.8, zoom 2.6/5.0) render non-blank with no GL error. The same window and context were resized in place through 800×600 → 1280×720 → 1920×1080 → 1280×1024 → 2560×1440 and back; the eye stayed exactly round (aspect 1.000) and the HUD scale stepped 1 → 2 at 1440p. Hangul renders in the HUD font. | [evidence/2026-10-24-windows-rtx3070/gl01-gl06-hardware-check.json](evidence/2026-10-24-windows-rtx3070/gl01-gl06-hardware-check.json) |
| GL08 | 60 s, 1920×1080: 10,793 frames, mean 5.56 ms, P50 5.38, P95 7.26, P99 8.60 ms (≈180 fps, vsync not controlled) → `CANDIDATE_WITHIN_60FPS`. The 300 s scene-switch run: mean 6.92 ms, P95 9.04 ms. | [evidence/2026-10-24-windows-rtx3070/gl08-1080p-60s.json](evidence/2026-10-24-windows-rtx3070/gl08-1080p-60s.json) |
| GL07 | 300 s with a cataract↔IOL mesh swap every 120 frames (361 swaps): growth 9.8 MiB, late-half slope 0.10 MiB/min → `CANDIDATE_NO_GROWTH`. A separate 4,000-swap probe plateaued at ~8 MiB after 200 swaps. | [evidence/2026-10-24-windows-rtx3070/gl07-300s-scene-switch.json](evidence/2026-10-24-windows-rtx3070/gl07-300s-scene-switch.json) |
| GL09 | The 2.5D game ran 240 frames in a real window (`windows` SDL driver) through the pre-op checklist into ENTRY, Korean UI. | screenshot reviewed |
| GL10 | Header "SYNTHETIC EDUCATIONAL SURGERY - NOT CLINICAL TRAINING" visible in hardware frames. | screenshot reviewed |

**Problems found by this run and fixed in the same commit:**
- The Windows working-set reader raised `OverflowError` (64-bit pseudo-handle passed as a 32-bit int), so GL07 had never measured on Windows. It also built a ctypes Structure and WinDLL on every sample; that probe self-growth made the first GL07 run report `CANDIDATE_GROWTH` (+20.1 MiB, late slope 1.57 MiB/min, kept as [evidence/2026-10-24-windows-rtx3070/gl07-300s-scene-switch-BEFORE-probe-fix.json](evidence/2026-10-24-windows-rtx3070/gl07-300s-scene-switch-BEFORE-probe-fix.json)).
- The 3D HUD font (Segoe UI) has no Hangul: every Korean label rendered as identical empty boxes. It now uses the same Malgun Gothic fallback list as the 2D app.
- After a window resize, captures read the framebuffer at its creation size.
- moderngl's default-framebuffer *readback* sets `GL_INVALID_OPERATION` on this driver although the pixels are valid; normal frames (no readback) are error free. The hardware check reports the two separately.

**Still for a person:** sign off the statuses above, check non-100 % display scaling (GL06) and dedicated GPU memory in Task Manager during GL07, and repeat on the AMD Radeon target.
