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


## 2026-10-13 — synthetic eye-motion and vision-accessibility validation

- [GitHub Tests CI 38340531317](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38340531317): **395 passed on Python 3.12** and **395 passed on Python 3.13**.
- [GitHub Mesa OpenGL CI 38340531344](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38340531344): successful full synthetic surgery rendering, with nonblank PNG frames; central eye-only crop hashes distinguish identical-scene **synthetic motion**, **haze**, and patient-motion **reduced-motion** mode without relying on changed HUD text. [Screenshot artifact](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38340531344/artifacts/11785993260).
- New boundary/dirty coverage: malformed and nonfinite patient motion, opacity, cortex, simulation time, accessibility booleans and shader inputs; 2,000 seeded valid random states; 1,000 timed samples proving bounded camera-plane offsets.
- The motion cue freezes while patient safety is on hold; low-motion removes displacement but does not cancel the existing alert, safety pause, warning, replay or score. Visual rendering queries cannot mutate `Game.snapshot()`.
- Limits: **Linux Mesa software GL only**, not Radeon/Windows/4K, real microscope optics, screen-reader certification, WCAG audit or clinically validated motion perception.


## 2026-10-13 — world-space contact guide/hover safety testing

- [GitHub Actions CI 38343565234](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38343565234): **422 tests passed on Python 3.12**; **422 tests passed on 3.13**.
- Unit/integration coverage: read-only hovering never changes `Game.snapshot()` or replay journal; phase-specific target, visited, near/outside classification; unsafe alerts and aborts suppress marker; wrong depth clears stale pose; test coverage includes camera rotation/zoom, malformed vectors and huge/nonfinite numeric input plus seeded fuzz hover.
- The pause/resume marker handling now requires a fresh validated mouse position, preventing restoration of stale tool geometry. The old expectation was replaced by explicit no-stale-display and hover-reacquisition assertions.
- [Mesa llvmpipe OpenGL 38343565188](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38343565188) passed full synthetic 3D scenario smoke and a visual **center-eye crop** comparison of otherwise identical frames with the GPU ring off/on, avoiding HUD-only false positives. [Frame captures](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38343565188/artifacts/11788405053).
- **Not tested:** real triangle-level anatomy picking, true tool-tissue contact pressure, mechanical surgical response, human factors/accessibility audit on 4K Windows or physical Radeon device. This is a non-clinical guide only.


## 2026-10-13 — BVH triangle-picking verification

- [Python Actions 38345423438](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38345423438): **452 passed** on each Python 3.12 and 3.13.
- `mesh_raycast` tests include known-plane exact barycentric coordinates, near/far exclusion, double-sided hits, collinear triangles (no spurious contact), nearest hit across overlapping faces, indexed iris pupil opening, IOL center and iris ring, camera rotation/zoom, cache/index reuse and 400 deterministic random ray queries.
- Dirty input checks include malformed vectors, booleans, NaN/infinity, integers exceeding floating range, zero-length rays, invalid mesh face budgets, missing or malformed phase/scene mapping and offscreen pointers.
- [Mesa OpenGL 38345423347](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38345423347) passed both real iris and optic face IDs: iris face 127, cataract optic face 12 and IOL optic face 12 in the fixed test camera view. [Rendered screenshots](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38345423347/artifacts/11788119181).
- **Failure history:** initial IOL result reported lowercase source name `iol` (fixed display label); strict exact `0<=barycentric<=1` comparison failed at a triangle vertex due to floating-point epsilon, corrected to tolerance consistent with the collision test. No procedural-state or safety gate was disabled.
- **Limitations:** independent static atlas mesh inspection only. GPU shader-deformed IOL, cosmetic offsets, patient movement and interactive surgical instrument contact do not yet use these face hits. Not a clinical or Windows GPU acceptance test.


## 2026-10-13 — folded-IOL CPU/GPU picking parity and cache dirtiness

- [Python CI 38351299492](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38351299492): **480 tests passed on Python 3.12** and **480 tests passed on Python 3.13**.
- New regression tests cover shader-equivalent IOL x/z deformation, synthetic alignment offset, immutable source geometry and face topology, BVH caching only when parameters change, proper loss of a selected unfolded-optic face after folding, unchanged cataract selection, inverse eye-motion translation with rotated perspective, 300 seeded parameter combinations and malformed inputs.
- **Bug discovered and fixed:** decorating a public function directly with `@lru_cache` allowed `True`/`False` to hit numeric cache keys and unhashable `[]`/`{}` to raise the wrong exception before input validation. A strict public validation wrapper now calls a private finite-float cache. Earlier [test run 38351188204](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38351188204) failed these four adversarial cases; final suite passes without weakening tests.
- [Mesa OpenGL 38351299510](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38351299510) passed actual shader output and screenshots for CATARACT/IOL, non-HUD center-eye differences for unfolded/folded/halfway synthetic IOL and actual triangle selection at the unfolded optic that correctly misses folded geometry. Existing 3-case interactive synthetic surgery smoke remains green.
- **Limits:** synthetic visual mesh, not actual implant material behavior; no real-force contact, clinical validation, Windows GPU acceptance, 4K or accessibility sign-off.


## 2026-10-13 — nearest 3D triangle proximity, safety and dirty-input coverage

- [Python 3.12/3.13 run 38355094995](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38355094995): **510 passed in each version**.
- New `surface_distance3d` regression covers closest face barycentric weights and points (interior, outside, edge, vertex), degenerate faces handled as bounded segments, two parallel faces with nearest tie/clipping behavior, distance threshold and BVH traversal.
- Read-only `surface_probe3d` verified stage-safe visual gating, no stale tool after pause/resume, no feedback during synthetic patient motion safety hold or abort, synthetic camera shift, finite distances and cached indexes. Seeded fuzz exercises 500 arbitrary bounded geometry points and dirty tests reject malformed numbers, booleans, NaN/Inf, enormous integers, invalid return objects and invalid GPU render inputs before opening a GL context.
- [Linux Mesa/Xvfb OpenGL run 38355095000](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38355095000) verified full 3-case synthetic surgery path and actual difference in a **center-eye-only framebuffer crop** with the new surface marker shown/hidden. Existing safety alert, reduced-motion and replay verification passed. [PNG artifact](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38355095000/artifacts/11792706594).
- The initial floating-point exact-zero assertion failed for a valid point on a synthetic triangle (calculated distance approximately `3.93e-17`); corrected only the assertion's strict absolute tolerance to `1e-12` and reran Python+GL successfully. It was not a mesh penetration/physics failure.
- The gap is **unitless** and cannot trigger Game actions, score changes, injury or surgical collision. No real Windows GPU/4K, force feedback, real clinical or surgical validity has been tested.


## 2026-10-13 — per-frame proximity deduplication and stale-HUD safety

- [Tests CI 38355978889](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38355978889): **522 tests passed on Python 3.12 and 522 on 3.13**.
- Instrumented query regression `test_hud_draw_reuses_prepared_surface_probe_and_never_reruns_bvh`: an active synthetic iris+lens probe performs its normal two nearest-triangle mesh lookups; five repeated HUD repaint calls add **zero additional geometry searches**. A deliberate call to the old HUD recomputation path raises an exception, proving the overlay does not use it.
- Staleness checks hide a prepared observation after moving the tool in the same phase, changing camera orientation, switching phase, pausing and resuming without a new safe hover, or restarting. Invalid `SurfaceProbe` types/status/gaps fail closed; reading the HUD does not mutate `Game.snapshot()` or the replay journal.
- [Mesa Linux software GL run 38355978911](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38355978911) succeeded, with three synthetic scenario/replay flows and the previously established *eye-only* nearest-triangle marker framebuffer difference. [Image artifact](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38355978911/artifacts/11792578657).
- **Not claimed:** wall-clock frame-rate improvement, reduced GPU draw cost, 4K performance on Windows AMD/Radeon, real tissue collision/forces or professional clinical validity. Quantitative target-device profiling remains a separate acceptance gate.


## 2026-10-24 — frame-time statistics and benchmark workload

- Local run: **557 tests passed** (Python 3.13, SDL dummy driver); 35 new tests in `tests/test_frametime.py`.
- Percentiles match `statistics.quantiles(method="inclusive")` across 200 seeded sample sets; known-sample summary, infinite FPS for zero mean, and rejection of booleans, `None`, strings, NaN/Inf, negative, >10 s and huge-integer samples.
- Profiler memory stays bounded (oldest samples drop), unknown section names and bad capacities are rejected.
- GL08 assessment: software, small-window, short, NaN-duration and empty runs are always `INSUFFICIENT_EVIDENCE`; a hardware run with acceptable mean but P95 over budget is `CANDIDATE_BELOW_60FPS`.
- Workload: camera path stays inside `View` limits for 20 000 frames; at 960×640, 1920×1080 and 3840×2160 every one of 400 frames yields a visible stylus and a nearest-triangle probe, exactly one `probe_surface` call per frame, with `Game.snapshot()` and the replay journal unchanged.
- F3 HUD label renders three distinct states (hidden / measuring / measured) without Game mutation.
- Local Xvfb + Mesa llvmpipe: `gl_smoke`, `gl_surgery_smoke` and `gl_benchmark` (120 frames at 960×640; 5 s at 1920×1080) succeeded with `game_state_unchanged: true` and `gl08.status: INSUFFICIENT_EVIDENCE`. The Software OpenGL workflow now runs a 300-frame 1080p benchmark and uploads the JSON report.
- **Not claimed:** Windows GPU frame time, 4K performance, GPU execution time or any clinical property.


## 2026-10-24 — zero-copy HUD upload

- CI for the benchmark increment: [run 40065486713](https://github.com/HyunStudio/Cataract_surgery/actions/runs/40065486713) **557 passed on Python 3.12 and 3.13**; [Mesa run 40065486734](https://github.com/HyunStudio/Cataract_surgery/actions/runs/40065486734) uploaded the 1080p frame-time JSON (`INSUFFICIENT_EVIDENCE`, software renderer).
- Local: **560 passed**. New `hud_swizzle` tests cover little/big-endian ARGB and ABGR layouts; rejection of 24-bit, padded-row, zero-width, missing/duplicate/partial-byte masks and unknown byte order; and a real pygame `SRCALPHA` surface whose swizzled raw buffer reproduces `tobytes(..., "RGBA")` exactly.
- `gl_surgery_smoke` now renders the same HUD frame through the zero-copy path and a forced copy fallback and requires identical framebuffer bytes, plus HUD surface reuse across frames. Local llvmpipe reports swizzle `BGRA`.
- Manual A/B before commit: seven captured frames byte-identical to the previous implementation for both paths; 1080p llvmpipe mean frame 14.2 → 10.0 ms (two runs each).
- **Not claimed:** any Windows GPU or 4K speedup.


## 2026-10-24 — 4K HUD magnification

- CI for the zero-copy upload commit: [Python 40065756237](https://github.com/HyunStudio/Cataract_surgery/actions/runs/40065756237) and [Mesa GL 40065756219](https://github.com/HyunStudio/Cataract_surgery/actions/runs/40065756219) succeeded.
- Local: **585 passed**. New `tests/test_hud_scale.py`: 13 window sizes including 2559/2560 boundaries, 16:10 and ultrawide; invalid sizes (zero, negative, float, bool, string, None); 1440p/4K map to the 1280×720 logical layout; `set_ui_scale` bounds; the cursor ring drawn at window (2400, 1500) lands at logical (800, 500) at 3× with the Game unchanged; every phase title wraps between words in ≤2 lines of ≤21 characters; benchmark report `hud_scale`.
- Manual GL checks under Xvfb/llvmpipe: seven 720p frames byte-identical to before; 1440p and 4K HUD textures 1280×720 with NEAREST filtering; title strip byte-identical to 720p after 1/2 and 1/3 sampling; screenshot inspection showed projected entry-target rings aligned with the 3D scene at 4K. Both GL smokes passed.
- **Not claimed:** physical 4K monitor readability, Windows DPI scaling behaviour, GPU performance.


## 2026-10-24 — GL07 memory measurement

- Local: **594 passed**. New tests: memory trend slope/late slope/extremes and validation; Linux RSS parser on good/corrupt/missing files; GL07 triage (software/short/unmeasurable → insufficient; warm-up plateau → no growth; late rise → growth); scene-switch argument validation and report label; IOL display scene stays read-only; profiler records 240 000 samples with < 4 KiB traced allocation; ring-buffer wraparound statistics.
- Manual: `tracemalloc` over 400 scene switches showed no Python-heap accumulation; RSS traces plateaued (2000 switches; 20 000 rendered frames with a switch every 10).
- 300 s llvmpipe runs: see PROGRESS (1.92 MiB / 5.82 MiB growth, late slopes 0.0 / 0.54 MiB/min).
- **Not claimed:** dedicated GPU memory behaviour or any Windows hardware result.


## 2026-10-24 — v2 regression

**Local run: 707 passed.** The new test files are:

| File | Covers |
|---|---|
| `test_engine_v2.py` | pre-op gate; difficulty tolerances, thresholds and timeouts; every case reaching an ending at every difficulty; endings and veto (pausing cannot freeze the hold); response credit vs latency; pupil, haze, decentration, leak and random-case behaviour; metrics; instrument rules; replay v2 round-trips, including timed-out failure; rejection of v1 headers and edited difficulty |
| `test_report.py` | KO/EN key parity and fallbacks; report/engine score agreement; explanations; chronological timeline; events/metrics CSV; session files; refusal of overflowed replays; agent endings; deterministic experiments with verified replays; config validation; CLI |
| `test_gui_v2.py` | all nine cases and the difficulty cycle; clickable pre-op checklist; zoomed clicks mapping to eye coordinates; zoom lock while dragging; focus blur (visual only); every hazard screen in EN/KO; decentration re-centring; all four ending screens with KO/EN export; language, palette and reduced-motion pixel changes; cross-section synchronization; help and sound; instrument tray; illumination; autosave/resume, including tamper rejection |
| `test_gl_surgery_v2.py` | checklist advance; 3D re-centring with a fresh click (held drag rejected); CLOSE without decentration has no tool; HUD for every alert and ending in EN/KO; report export; CLI; instrument cycling in hard; autosave restore |

Updated `gl_surgery_smoke.py` adds a fourth Mesa scenario (decentration hold, visible 3D re-centring, managed-complication result) to the existing zero-copy HUD and capsule/vision checks.

**Not claimed:** Windows GPU, physical 4K legibility, human usability or clinical validity.
- **CI for v2:**
  - Python 3.12/3.13: [Tests 40068709047](https://github.com/HyunStudio/Cataract_surgery/actions/runs/40068709047), 707 passed on 3.12; the 3.13 job succeeded. [GUI screenshots](https://github.com/HyunStudio/Cataract_surgery/actions/runs/40068709047/artifacts/12549384895).
  - Mesa OpenGL: [40068709064](https://github.com/HyunStudio/Cataract_surgery/actions/runs/40068709064), success with the four-scenario 3D smoke and benchmarks.
  - Earlier v2 commits were also green: [40068403280](https://github.com/HyunStudio/Cataract_surgery/actions/runs/40068403280)/[40068403263](https://github.com/HyunStudio/Cataract_surgery/actions/runs/40068403263) and [40068152868](https://github.com/HyunStudio/Cataract_surgery/actions/runs/40068152868)/[40068152833](https://github.com/HyunStudio/Cataract_surgery/actions/runs/40068152833).


## 2026-10-24 — engine v3 / design-completion regression

**Local run: 762 passed, 1 skipped (Windows-only).** The new test files are:

| File | Covers |
|---|---|
| `test_engine_v3.py` | 10 cases; vitreous escalation and irreversible flags; rim alert per difficulty (fires once); stress ×1.5; help always available and free; snapshot contract; deterministic session/scenario ids; seeded patient card that does not disturb hazard draws; normalized endpoint error; near-miss coordinates; replay v3 with help and rejection of v2 |
| `test_gui_v3.py` | keyboard-only entry task; depth gating and per-stage reset; Shift+wheel vs wheel; middle-drag pan with mapped clicks; F2 scale mapping; help by key, F1 and click; card, drape and progress rendering; bounded particles (off in reduced motion); near-miss mark and stress warning; tutorial-only guides; results heatmap; confirm-abort window; damping; enlarged cross-section; low-visibility condition logged in the report; break reminder; replay viewer (play, step, speed, final-state match, no commands); playback unit/speed/finish; CLI validation |
| `test_gl_surgery_v2.py` | adds 3D help and patient card, and checks that the scleral cutaway is open at the limbus |
| `test_research_data.py` | v1/v2 → v3 migration without content change; pass-through and invalid events; migrate CLI; practice/evaluation splits with leakage and shape validation; data dictionary covering every metrics column and event kind |

Mesa `gl_smoke` and `gl_surgery_smoke` pass with the cutaway sclera.
