# OphthoSim-AI — Cataract Surgery Simulator

An open-source, **educational and research** cataract microsurgery game written in
Python. You play a complete *abstracted* encounter from pre-operative verification to
the explained results screen, in a 2.5D microscope view or an experimental
hardware-accelerated 3D view, with a synthetic patient monitor, ten deterministic
scenarios, three difficulty levels, Korean/English UI and replayable research logs.

> **Not a medical device and not surgical training.** Every value, waveform,
> complication and score is synthetic game feedback. There are no clinical
> instructions, drug doses or device settings. See [Safety](docs/SAFETY.md).

Screenshots of every screen are produced by CI (`build/screenshots/` artifacts of the
*Tests* and *Software OpenGL Smoke* workflows).

## Quick start (Windows, Python 3.12+)

```powershell
python -m pip install -r requirements.txt
python main.py                                   # 2.5D game
python main.py --case motion --difficulty hard --lang ko
python main.py --resume                          # continue the autosaved case

python -m pip install -r requirements-3d.txt
python -m ophthosim.gl_surgery --case decenter   # experimental 3D game (OpenGL 3.3)
```

Korean step-by-step guide: [사용자 가이드](docs/USER_GUIDE_KO.md).

## The encounter

1. **Pre-op review** — tick patient identity, operative site and planned IOL; the case
   cannot start until all three are verified.
2. **Anesthesia & preparation** — confirm readiness (no medication actions).
3. **Entry** — select the three approach targets.
4. **Capsular task** — trace the circular guide.
5. **Lens removal** and 6. **cortex cleanup** — clear opacity inside the working field.
7. **IOL** — place the synthetic lens near the optical centre (3D: folded → unfolding).
8. **Final checks** — alignment, wound stability, handoff.
9. **Results** — explained score, ending and event timeline.

Each task stage needs its instrument (entry blade, capsule forceps, phaco handpiece,
I/A aspirator, IOL injector). It is selected automatically in tutorial/standard; in
hard you pick it from the tray (`T`), and using the wrong one is rejected and logged.

### Scenarios (keys 1–9 and 0 on the pre-op screen)

| # | Case | What happens (synthetic) | Expected response |
|---|---|---|---|
| 1 | normal | no complication | complete safely |
| 2 | motion | patient motion on capsular entry | stop, assess (A) |
| 3 | vitals | monitor alarm during lens removal | hold, assess |
| 4 | capsule | capsule integrity event | assessment ends in a **safe stop** |
| 5 | pupil | pupil constriction | assess; working field shrinks |
| 6 | haze | corneal haze | assess; view clears partially |
| 7 | decenter | IOL decentration in final checks | assess, re-centre, then check |
| 8 | leak | wound-leak risk holds the ending | assess, re-check the wound |
| 9 | vitreous | vitreous event during cleanup | assessment escalates to a **safe stop** |
| 0 | random | one of the above, drawn from the seed and logged | — |

Repeatedly tracing off the capsule guide raises a one-time **capsule rim
irregular** alert in any case. After it, later stages accrue capsule stress
1.5× faster. Help (`?`) is always available and never costs points. The pre-op
screen shows a synthetic patient card: ID, operative eye, opacity grade, pupil
and IOL plan.

### Difficulty (`D` on the pre-op screen)

| | tutorial | standard | hard |
|---|---|---|---|
| Target tolerances | wide | baseline | narrow |
| Ghost guides (tolerance rings, IOL crosshair) | yes | no | no |
| Instrument | automatic | automatic | choose (`T`) |
| IOL acceptance | ≥ 55 % | ≥ 65 % | ≥ 75 % |
| Unattended alert limit | none | 30 s | 15 s |

### Endings and score

Four endings: **Simulation complete**, **Complication recognised and managed**,
**Safely aborted** (a positive outcome, not a failure) and **Critical failure**. The
last one is a *safety veto*: it happens only when a safety hold is left unattended past
the difficulty's limit. Pausing cannot freeze that timer, while assessing (`A`) or a
safe abort (`X`) always stops it.

The 100-point score is explained on the results screen. Each category is earned only
once that part has been evaluated:

| Category | Max | Basis |
|---|---|---|
| Stage completion | 20 | stages completed of 7 |
| Tissue protection | 25 | capsule integrity minus near-miss penalty |
| IOL position | 20 | final alignment |
| Complication response | 20 | recognition latency per alert (full credit ≤ 3 s) |
| Patient safety | 15 | no safety veto |

The weights are game-design hypotheses, not a validated skill measure.

## Controls

| 2.5D (`python main.py`) | |
|---|---|
| Mouse, or arrows + Enter | task / checklists / instrument tray (fully keyboard-playable) |
| Space | next pre-op item → start → prepare |
| 1–9, 0, D | case, difficulty (pre-op only) |
| T, Q/E or Shift+wheel | cycle instrument, tool depth (must match the stage's depth band) |
| A / X / Esc / ? | assess (call anesthesia team) / safe abort / pause / help request |
| Wheel or + −, middle drag, [ ], , . | microscope zoom, pan (both locked while operating), focus, illumination |
| L, H, C, M, S, K | language, high contrast, colour-safe palette, reduced motion, sound, tremor damping |
| F1, F2, V | help, UI scale 100–200 %, enlarged depth cross-section |
| G | CPU 3D mesh preview (read-only) |
| E, R | export logs, restart |

Options: `--confirm-abort` (X twice), `--condition low_visibility` (logged research view),
`--replay FILE` (step-by-step replay viewer: Space, →, +/−, End, Esc).

The 3D game (`python -m ophthosim.gl_surgery`) uses the same engine and keys for the
procedure, plus arrows to orbit, Q/E or Shift+wheel for tool depth, ? for help,
F3 for frame time, F11 for fullscreen and S to export. Its eye uses an anterior
scleral cutaway mesh.

## Research and data

Every session is deterministic for a given case, seed and difficulty. **E** (2.5D) or
**S** (3D) writes these files to `session_logs/`:

- `*.jsonl` — the event trace
- `*.replay.jsonl` — the command journal with SHA-256 integrity
- `*.events.csv` and `*.metrics.csv`
- `*.report.json` — the explained score and timeline in the chosen language

```bash
python -m ophthosim.verify_replay session_logs/case_normal_standard_seed_7.replay.jsonl
python main.py --replay session_logs/case_normal_standard_seed_7.replay.jsonl   # watch it
python -m ophthosim.experiments examples/experiment_demo.json --out build/experiments/demo
python -m ophthosim.experiments examples/experiment_split.json                  # practice/evaluation
python -m ophthosim.migrate old_trace.jsonl new_trace.jsonl                     # v1/v2 -> v3 events
```

Field-by-field documentation: [data dictionary](docs/DATA_DICTIONARY.md). The primary
research metric is endpoint error normalized to each task's target radius. Exports
record the UI condition: language, palettes, motion, zoom/focus/light, scale, window
and research condition.

The experiment runner plays scripted synthetic agents (ideal, careless, slow,
unresponsive) over case × difficulty × seed grids. It writes a metrics CSV, a JSONL
file of runs and a summary, and verifies every replay. The demo config runs 192
sessions in about a second. The metrics are:

- phase times
- near misses
- rejected inputs and wrong-tool uses
- action path length
- IOL attempts and pauses
- alert-recognition latency

Agents validate the instrument only; they say nothing about human performance. See the
[research plan](docs/RESEARCH_PLAN.md).

Autosave: both apps keep `session_logs/autosave.replay.jsonl` up to date on every
phase change and on quit, and `--resume` rebuilds the exact state from the verified
journal. Tampered autosaves are rejected.

## Accessibility

- Korean and English UI. On Windows the Korean UI uses Malgun Gothic.
- High-contrast and Okabe-Ito colour-safe palettes. No state is conveyed by colour
  alone.
- Reduced motion freezes animations without hiding alerts.
- Alerts are non-flashing, with an optional gentle tone and a text equivalent.
- Microscope zoom.
- The 3D HUD scales by an integer factor at 1440p and 4K.
- Alert timers are disabled in tutorial mode.

## Performance tools (3D)

```powershell
python -m ophthosim.gl_benchmark --seconds 60 --size 1920x1080             # GL08 frame time
python -m ophthosim.gl_benchmark --seconds 300 --scene-switch-every 120    # GL07 memory
```

Reports record mean, P50, P95 and P99 frame times, the cost of the proximity query
and of the render call, and the host-memory trend with a late-half slope. They also
record the OpenGL renderer strings. Software renderers are never counted as hardware
evidence. The HUD texture is uploaded zero-copy. See the
[GPU validation checklist](docs/GPU_VALIDATION_CHECKLIST.md).

## Status

| Area | State |
|---|---|
| Full 2.5D game: 10 scenarios, 3 difficulties, 4 endings, explained score, KO/EN, accessibility, keyboard play, autosave, replay viewer | **Implemented and tested** (762 tests pass + 1 Windows-only, Python 3.12/3.13 CI) |
| Experimental 3D game with the same engine | Implemented; Mesa software OpenGL in CI and a **Windows RTX 3070 run**: GL01–GL06 automated pass, 1080p mean 5.56 ms / P95 7.26 ms, GL07 no growth ([evidence](docs/GPU_VALIDATION_CHECKLIST.md#windows-hardware-run-2026-10-24)) |
| AMD Radeon target, non-100 % display scaling, human sign-off of GL01–GL10 | **Open** — needs the owner |
| Clinical plausibility and educational value | **Open** — needs subject-matter-expert review |
| Design-document coverage | Requirement-by-requirement tables in each design doc |
| Deformable tissue physics, physical optics | Out of scope by spec (explicit non-scope) |

See the [32-work-package status](docs/ROADMAP.md#implementation-status-2026-10-24) and the
[development log](docs/CHANGELOG.md).

## Project layout

```
ophthosim/
  engine.py           phase machine, rules, hazards, endings, score breakdown, metrics
  replay.py           deterministic command journal + integrity-checked replay (schema v2)
  report.py           explained report, timeline, CSV/JSON export
  experiments.py      scripted synthetic agents, batch runs, practice/evaluation splits
  playback.py         step-by-step viewer over a verified replay
  migrate.py          event-trace schema migration (v1/v2 -> v3)
  autosave.py         verified recovery points
  i18n.py             Korean/English strings
  app.py              2.5D Pygame game
  gl_surgery.py       experimental ModernGL 3D game (+ input3d, contact3d, tool3d,
                      iol3d, capsule3d, vision3d, surface_probe3d, mesh_raycast …)
  gl_preview.py       3D anatomy atlas and renderer
  gl_benchmark.py     frame-time / memory benchmark; frametime.py statistics
tests/                763 headless, SDL-dummy and GUI tests (1 Windows-only)
docs/                 specs (KO), architecture, roadmap, safety, research, GPU checklist
```

## Documentation

- [사용자 가이드 (한국어)](docs/USER_GUIDE_KO.md)
- [3D 실행·조작 안내](docs/INTERACTIVE_3D_USAGE_KO.md)
- [Product spec (KO)](docs/PRODUCT_SPEC_KO.md)
- [Visual design (KO)](docs/VISUAL_DESIGN_KO.md)
- [Technical architecture](docs/TECHNICAL_ARCHITECTURE.md)
- [Roadmap & WP status](docs/ROADMAP.md)
- [Test report](docs/TEST_REPORT.md)
- [Progress](docs/PROGRESS.md)
- [Safety](docs/SAFETY.md)
- [Research plan](docs/RESEARCH_PLAN.md)
- [Data dictionary](docs/DATA_DICTIONARY.md)
- [GPU validation checklist](docs/GPU_VALIDATION_CHECKLIST.md)
- [Development log](docs/CHANGELOG.md)

## License

See [LICENSE](LICENSE). External assets must document their provenance and
redistribution rights.
