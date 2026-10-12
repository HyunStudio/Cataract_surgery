# Windows GPU validation — experimental ModernGL atlas

Status: **Windows hardware gate still open**. Python CI validates geometry and input, while a separate Linux Mesa llvmpipe software-OpenGL workflow **has actually compiled shaders and rendered two framebuffers**. Do not confuse a software OpenGL context with Windows physical GPU validation.

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
| GL01 | Open a Pygame OpenGL 3.3 core window and ModernGL context | Starts without exception | UNVERIFIED |
| GL02 | Compile both scene/HUD shader programs | No GLSL compilation errors | UNVERIFIED |
| GL03 | Iris, cloudy lens and corneal shell visibility | No missing layer or full occlusion | UNVERIFIED |
| GL04 | Space changes scene from cataract to IOL | Visible synthetic optical state change | UNVERIFIED |
| GL05 | Orbit, zoom, extreme camera angles | No clipping/black screen/crashes | UNVERIFIED |
| GL06 | Window resize / DPI / repeated scale changes | Correct aspect and HUD alignment | UNVERIFIED |
| GL07 | 5-minute run, repeated scene changes | No memory growth or context loss | UNVERIFIED |
| GL08 | 1920×1080 frame time | Target ~60fps; document measured mean/P95 | UNVERIFIED |
| GL09 | Real Pygame 2.5D game remains working | No cross-mode regression | CI ONLY |
| GL10 | Synthetic 3D mode is labeled non-clinical | Warnings visible | CODE REVIEW ONLY |

Collect operating system, GPU, driver version, OpenGL version, display scaling, Python/pygame/moderngl versions, average/P95 FPS and screenshots. Report failure if GL context creation is not possible. Never treat CPU offline checks or SDL dummy tests as hardware validation.

## Technical next steps

- Confirm shader compilation, culling orientation, depth interactions and HUD texture y-direction on target driver.
- Profile full-screen HUD RGBA texture upload each frame; optimize with a small static atlas or subregion upload if it dominates.
- Add depth-picking and a synchronized object-space tool model before enabling any 3D surgery interactions.
- Replace the closed globe background shortcut with a modeled anterior scleral cutaway; validate layer visibility with real screenshots.
- Keep a fully playable 2.5D fallback until these tests pass.

## Additional completed Linux software-OpenGL gate (2026-10-13)

[GitHub Actions run 38319493162](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38319493162) passed on Mesa llvmpipe OpenGL 4.5. It verified context creation, shader compilation, transparent/opaque draw calls, read-only ray hit on iris, synthetic IOL/opaque-lens state changes, two nonblank PNG readbacks. [Screenshot artifact](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38319493162/artifacts/11779035082). These findings are for a Linux software rasterizer only; GL01–GL10 Windows statuses in the table above intentionally remain unchanged. Short 20-frame timing (2.97 ms mean) does not meet any sustained performance gate.
