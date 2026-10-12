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
- The local execution environment has Python 3.13, numpy and pytest, **but lacks pygame**; network package installation is unavailable. Thus graphical launch, mouse controls, GPU compatibility, FPS, 1080p/4K resizing and visual regression **have NOT been validated in this environment**.
- UI implementation contains procedural 2.5D styling only; no real 3D mesh, ModernGL context, shader pipeline, medically accurate anatomy/tissue dynamics, anesthesia pharmacology or validated score model.
- Next action: run Pygame smoke tests on a desktop with `pip install -r requirements.txt`; review source inspection and collect screenshot/trace. Implement WP04 true-3D technical spike before claiming 3D support.

## Observed results
- Local Python 3.13: **38 tests passed** (pytest, 2026-10-12) and compileall succeeded.
- GitHub Actions: Python 3.12/3.13 initial workflow run passed before the final two adversarial tests were added. Confirm the latest commit workflow result separately.
- An initial dirty-test failure (extremely large integer coordinate OverflowError) was fixed by range checking before floating-point finiteness checking.
- A second logic improvement triggers hazards on phase entry instead of waiting for next frame to prevent burst inputs bypassing alerts.

## Clinical claims
Everything is a non-clinical game abstraction; scores and data are synthetic. No clinical skill validation or real-world safety claims.