# Execution and dirty-test report — first playable 2.5D vertical slice

Updated 2026-10-12. **This report applies only to the initial build**, not completion of the 32-WP specification.

## Implemented
- Executable Pygame 2.5D vector-art eye renderer, synthetic vital monitor, nine phases with manual interactions, safe abort, synthetic log export.
- Strict headless state machine with phase guards, fixed-step time, deterministic scenario seeds, assessment branches, bounded events and coordinate validation.
- Four synthetic scenarios: normal, motion, vitals and capsule integrity. One scenario intentionally ends with safe abort.

## Unit/integration/adversarial coverage
- Normal start-to-recovery route; skipped phase rejection; invalid scenario/seed/coordinates/dt; pausing; alert locking; safe abort; deterministic log replay; bounded event data; 5,000 randomized malformed input calls plus two immediate state-entry hazard-bypass tests.
- Run `python -m pytest -q` (requires pytest, no Pygame for engine-only tests).
- Run `python -m compileall -q ophthosim main.py` for syntax.

## Environment and limitations
- The local execution environment has Python 3.13, numpy and pytest, **but lacks pygame**; network package installation is unavailable. GitHub Actions has successfully executed Pygame GUI smoke tests via an SDL dummy display. Actual Windows desktop input, GPU/driver compatibility, FPS, 1080p/4K visual quality and real 3D **remain unvalidated**.
- UI implementation contains procedural 2.5D styling only; no real 3D mesh, ModernGL context, shader pipeline, medically accurate anatomy/tissue dynamics, anesthesia pharmacology or validated score model.
- Next action: run Pygame smoke tests on a desktop with `pip install -r requirements.txt`; review source inspection and collect screenshot/trace. Implement WP04 true-3D technical spike before claiming 3D support.

## Observed results
- Local Python 3.13: **39 tests passed** (pytest, 2026-10-12) and compileall succeeded.
- GitHub Actions (run 38252781503): **success on Python 3.12 and Python 3.13**, with pygame installed and SDL dummy-driver UI tests; 39 headless engine cases plus 7 GUI smoke cases in the test suite. GUI tests cover phase displays, alerts, keyboard navigation, coordinate scaling, real simulated end-to-end recovery screenshot and malformed mouse input.
- An initial dirty-test failure (extremely large integer coordinate OverflowError) was fixed by range checking before floating-point finiteness checking.
- A second logic improvement triggers hazards on phase entry instead of waiting for next frame to prevent burst inputs bypassing alerts.

## Clinical claims
Everything is a non-clinical game abstraction; scores and data are synthetic. No clinical skill validation or real-world safety claims.
## Visual review correction
- Reviewed generated CI screenshots. Fixed adjacent title/subtitle spacing and zero-based score initialization.
- The recovery screenshot test now performs a complete synthetic case before capturing, rather than merely forcing the phase variable; source screenshot artifacts are available from GitHub Actions.

## Follow-up testing — deterministic replay increment
- Automated checks: round-trip command replay after completing the synthetic surgical flow; preserved patient-motion/vital/capsule warnings; saved GUI replay reload; journal tamper/rejection checks; range/NaN/overflow fuzz inputs.
- Replay format contains a cryptographic digest of canonical command records and hashes of result events/snapshot. This is integrity checking, **not identity authentication**.
- Deterministic replay does not equate to a validated training simulator. Rejected out-of-region actions with synthetic stress effects are captured; rejected invalid coordinates are not (they have no state effects).
- A giant integer `dt` previously risked float overflow; it is now explicitly converted under an exception guard and raises `ValueError`. Finite large dt values continue to clamp as documented. Seed values beyond signed 63-bit magnitude are rejected.
- As before, GitHub Actions SDL dummy tests are not real Windows GPU rendering, and no interactive true 3D graphics test has run.

## 2026-10-12 additive test evidence
- GitHub Actions [run 38260708128](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38260708128): **97 automated tests passed** (Python 3.12 and 3.13 matrix).
- Verified categories: headless state machine, Pygame SDL dummy GUI, complete synthetic procedure, hazard/safe-abort, command replay/journal integrity, standalone verifier, fuzz/dirty input, normalized 3D mesh generation and ray geometry.
- `python -m compileall -q ophthosim main.py` also ran successfully in CI.
- **Not tested:** real Windows monitor/keyboard/4K, rendering on the user's GPU, ModernGL/OpenGL shader output, high-fidelity anatomy, eye biomechanics, actual clinician assessment or IRB human-subject studies.

## 2026-10-13 KST incremental 3D-preview verification

- Verified latest [GitHub Actions run 38272300713](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38272300713): success for Python 3.12 and 3.13; Python 3.12 completed **116 tests**.
- Added `tests/test_preview3d.py` to exercise triangle rendering inputs, cached deterministic meshes, rotated camera, synthetic lens/IOL distinction, malformed numerical values, adversarial invalid camera settings and 100 random valid angles.
- Added GUI smoke tests for G/J/L/I/K, camera-angle bounds, visual rendering of all procedure states, blocking surgery clicks during 3D preview, and returning to interactive 2.5D mode.
- First new test run had **2 failures / 114 passes** due to a typo in GUI yaw update; corrected in commit `4c7014637792dd874ef9b34c94065da576cf7d45` and rerun green.
- **Boundaries:** 3D scene is CPU-projected triangles, not OpenGL 3D rendering. SDL dummy-screen success does not validate performance, mouse accuracy, or visual quality on a Windows GPU/monitor.

## 2026-10-13 additive CI coverage — ModernGL prototype + shared monitor

- Latest verified [GitHub Actions run 38318581035](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38318581035): Python 3.12 **167 passed in 1.72s**, Python 3.13 workflow succeeded.
- New offline GL tests check binary vertex/normal packing, mesh indices, source shader uniforms, camera bounds under 10,000 events, malformed floats and lens/IOL swaps. GLSL source inspected only, not GPU compiled.
- New synthetic monitor tests validate deterministic ECG/pleth generated from changing in-game heart rate, zero-rate flat trace, NaN/Inf/huge-int rejection, extreme sample counts, and rendered GUI pixel changes via SDL dummy driver.
- **No evidence yet for physical Windows GPU performance, OpenGL context/shader success, IOL/cornea visual realism, clinical accuracy, or interactive 3D surgical tool precision.**

## 2026-10-13 depth picking + executable GLSL test

- [Actions tests run 38319316882](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38319316882): Python 3.12 and 3.13 success; **202 tests passed on 3.12**. Covers 3D camera inversion, lens/IOL/iris picking, mathematical roundtrip, clipping/outside viewport, extreme input rejection and seeded fuzz.
- [Mesa/Xvfb OpenGL smoke run 38319493162](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38319493162): **success**, framebuffer bytes captured for both states; PNG artifacts attached. GL renderer `llvmpipe (LLVM 20.1.2, 256 bits)`, OpenGL `4.5`. Captured two different images; 20-frame mean ~2.97 ms is a short software diagnostic sample **not** a meaningful frame-rate benchmark.
- Verified that 3D click inspection is **read-only** and does not mutate the synthetic surgery score/state. This inspection uses analytic spherical/ellipsoidal approximations and does not yet perform triangle-level precision hit testing.
- Still untested: Windows AMD graphics context/driver, 1080p/4K real monitor legibility and sustained performance, real surgical interaction, expert clinical plausibility.

## 2026-10-13 interactive ModernGL surgery integration and dirty testing

- [Tests CI run 38334178228](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38334178228): **245 tests passed on Python 3.12**, Python 3.13 matrix also successful. New tests for 3D input mapping, camera zoom/orbit calibration, stage-dependent z gating, wrong-depth ignore behavior, full end-to-end completion and replay checksum matching, alert lock, safe stop, malformed inputs, 2,000 randomized pointer inputs and IOL fresh-press requirement.
- [3D Mesa OpenGL run 38334142433](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38334142433): successful GLSL context, GPU code execution on **software OpenGL**, real framebuffer readbacks across **eight distinct surgical/complication frames**, plus full educational surgery and alert-safe-stop paths with exact replay reconstruction.
- The progress-aware 3D lens tint and IOL translation are **visual approximations** only; rendering different images is not clinical validation, nor do the current 3D rays establish tissue collision truth.
- **Still not tested:** real Windows GPU/monitor, 4K scaling, sustained 60 fps, 3D instrument pressure/deformation, external ophthalmologist appraisal.


## 2026-10-13 synthetic 3D stylus visibility tests

- Unit/GUI regression: [run 38335940393](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38335940393), Python 3.12 **274 passed in 2.27s**, Python 3.13 job success.
- `stylus_mesh()` validates packed mesh bounds/indices, normal vectors and single-entry caching.
- `visible_stylus()` displays only a world pose accepted by the existing phase-gated simulation, hides during patient alarms, pause, abort, stale depth, invalid semantic coordinates and rejected huge/nonfinite inputs.
- Renderer rejects invalid 3D uniform vectors before touching an OpenGL context.
- Mesa run [38335940404](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38335940404) confirmed a true screenshot pixel change between otherwise identical frames with/without an actual tool mesh; nine screenshot artifacts were captured, normal outcome and motion safe-stop replay matched.
- Initial screenshot-visibility test **failed** at [run 38335798484](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38335798484). After visible overlay treatment, both workflows passed. Synthetic 3D instrument overlay is deliberately not physically occluded, and **neither test validates clinical force response or hardware GPU behavior**.


## 2026-10-13 IOL mesh and scene-depth regression verification

- [Python Actions run 38337153815](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38337153815): both 3.12 and 3.13 green, **289 automated tests** each; additional IOL bounded geometry, cache, stage timing, pause and dirty numerical input coverage.
- [Mesa OpenGL run 38337153811](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38337153811) green, with distinct `iol-placement`/`iol-unfolding`/`iol-deployed` frames. The test compares a **200×200 center-eye crop, excluding HUD text**. The actual generated images were inspected; iris and synthetic IOL are visible after the scleral backdrop depth fix. [Screenshots](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38337153811/artifacts/11785108404).
- A temporary failing strict crop test [38336952604](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38336952604) was useful: it proved earlier differences were confined to HUD and that the closed sclera visually masked the IOL. Production code was repaired (not weakened test), then rerun passed.
- **No clinical validation or Windows hardware acceptance:** GPU rasterization and frame screenshots verified only on Linux Mesa llvmpipe. Actual IOL haptic design, insertion technique and force profiles are not claimed to be realistic.


## 2026-10-13 — capsule damage renderer regression and dirty tests

- [GitHub Actions Python 38338000372](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38338000372): **335 passed** on Python 3.12 and **335 passed** on 3.13.
- [Mesa OpenGL 38338000377](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38338000377): passed shader/context/frame output and synthetic surgery smoke. Two capsule render passes with **identical HUD and viewport** but different 3D ring meshes produced *distinct 200×200 center-eye image hashes*, proving the scene itself changes. Captured full normal, motion and irreversible capsule event scenarios, with replay reconstructed after safe abort.
- Unit tests exercise ring mesh bounds, cached VAOs' source meshes, topology opening, synthetic damage threshold, invalid flags, NaN/Inf/big-int states, invalid segments/gaps, game snapshot immutability and retained damage after abort. Only synthetic state values are checked.
- Nonclinical visual mapping: intact = cool green/teal; damaged = red discontinuous ring visible in pupil. Neither placement nor damage geometry represents human capsule anatomy or an actual complication. **No real clinical outcome and no physical Windows GPU/4K benchmark verified.**
