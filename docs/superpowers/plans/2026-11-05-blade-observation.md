# Accepted blade-action feedback

> Execute inline with superpowers:executing-plans, test-driven-development and verification-before-completion. User authorized continued implementation without design questions.

**Goal:** Let the operator distinguish an accepted new incision from motion that produced no new incision, without inferring contact from the tip target or automatically changing depth.

**Design:** The existing finite sharp-edge sweep/cutter returns `changed`. Keep a tick-local action (`new_cut`, `no_new_cut`, `stationary`) and publish it in cached capsule observations only after the entire physics tick succeeds. Existing transaction restoration already owns this cache. UI shows the selected active knife's latest accepted observation; pause, focus loss, hand/tool change and release suppress stale text. `no_new_cut` does not mean no contact: an already-open bank may correctly produce no new cut.

**Files:** simulator.gd (derive/publish observation and pass active state), simulation_ui.gd (Korean telemetry), tests/test_blade_observation.gd (real queued roll and complete tick, controlled cutter/solver response), tools/validate_embedded_regressions.py (register suite).

Review ruling: presentation follows the existing10Hz HUD cadence. Physical
disarming is immediate; stale action text is suppressed at the next UI refresh,
without waiting for another physics tick. No per-input whole-UI rebuild. The
first focused test's "immediately" message refers to its explicit presentation
refresh; it is not a zero-latency repaint contract. Additional actual input-event
suite covers mouse release, focus loss, pointer exit, hand and instrument change.

- [x] RED: accepted changed/no-op/motionless observations, rejected later solve rolls back cut and feedback, release suppresses stale display.
- [x] Implement minimal observation; no numerical, cutter, geometry, force/CCD/work gate or target changes.
- [x] GREEN: focused test and existing transaction/input/UI/integration suites; update applicable frozen validation without claiming whole-route success.
- [x] Read-only review; no remaining findings after HUD cadence clarification and additional actual event coverage. Original closed-route failure remains unresolved; full simulator goal stays active.

Final verification:62frozen focused suites PASS,36actual extension stages PASS;
every recorded source hash matches current files. Separate real default-model
initial knife operation GPU observation onRTX3070, requested1280x800/1600x1000
windows with1600logical viewport, visible Korean action fits; screenshot inspected.
This is an initial legacy/default-model visual smoke, NOT optional Native GPU
qualification, full procedure, FPS or Windows deployment acceptance.

Corrected attempted-patch observer separately passes a two-real-patch binary
history/state ownership smoke. A fresh unchanged whole route using qualified
snapshot xh43p6_0 is LIVE in terminal-route-ud_lqkbf, session30165; source hashes
of tools/capture_operative_terminal.py/.gd/_smoke.gd must remain unchanged until
terminal. No repeated prefix starts while this process is live.
