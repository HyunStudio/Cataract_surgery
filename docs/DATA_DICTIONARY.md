# Data dictionary — synthetic session data (schema v3)

All data are **synthetic**. There are no personal identifiers and no wall-clock
timestamps. Identifiers are derived deterministically from case, difficulty and seed.
Time is simulation time. Files are written locally under `session_logs/`, and only
when the user exports (E in 2.5D, S in 3D).

## Files per exported session

| File | Content |
|---|---|
| `*.jsonl` | Authoritative event trace, one JSON event per line (below). |
| `*.replay.jsonl` | Command journal with session header, accepted/rejected commands, run-length ticks and SHA-256 integrity footer. Re-executes to the identical state. |
| `*.events.csv` | Event trace for analysis: `step, sim_time_ms, phase, kind, case, seed, data` (data = compact JSON). |
| `*.metrics.csv` | One metrics row (columns below). |
| `*.report.json` | Explained score, timeline, metrics, `ui_conditions`, `patient_card`, `session_id`, `scenario_version`. |
| `autosave.replay.jsonl` | Recovery point: replay journal of the unfinished case. |

## Event fields

| Field | Meaning |
|---|---|
| `schema_version` | Event schema version (3). Older traces are upgraded with `python -m ophthosim.migrate`. |
| `session_id` | Synthetic `SIM-xxxxxxxxxx` from case/difficulty/seed. |
| `scenario_id` | `case/difficulty`. |
| `case`, `seed` | Scenario and its 64-bit seed. |
| `step` | Simulation step index (ticks applied, including timed safety-hold ticks). |
| `sim_time_ms` | Procedure clock in milliseconds; frozen during pauses and holds. |
| `phase` | Phase when the event was recorded. |
| `kind` | Event type (below). |
| `data` | Event payload (below). |

## Event kinds (`kind` → `data`)

| Kind | Payload |
|---|---|
| `start` | `case`, `seed`, `difficulty`, `card` (synthetic patient card) |
| `scenario_draw` | Random case only. Fields: `hazard`, `source` (`seeded_rng`), `probability`. |
| `preop_check` | `item`: `identity`, `site` or `iol_plan` |
| `phase` | `from`, `to` |
| `tool` | `tool`: instrument selected |
| `rejected` | `action`, `reason`. Reasons: `preop_checks_incomplete`, `wrong_tool` (with `tool`, `required`), `iol_not_centered` (with `item`). |
| `entry_point` | `index` of the entry target reached |
| `capsule_completed` | `bins` traced |
| `removed` | `x`, `y` of an accepted removal (normalized eye coordinates) |
| `near_miss` | `x`, `y` of a removal outside the working field |
| `placed` | `alignment` (0–1), `reposition` (bool) |
| `alert` | `kind` (alert label) |
| `assessed` | `alert`, `latency_s` |
| `help_requested` | `alert` (or null) |
| `pause` | `paused` |
| `check` | `item`: `alignment`, `wound` or `handoff` |
| `veto` | `reason` (`alert_unaddressed`), `alert` |
| `ending` | `outcome` (one of the four endings), `score` (when scored) |

## Metrics CSV columns

| Column | Meaning |
|---|---|
| `policy` | Experiments only: scripted agent policy. |
| `split` | Experiments only: `practice`, `evaluation` or `all`. |
| `case` | Scenario. |
| `hazard` | The hazard actually used (differs from `case` for `random`). |
| `difficulty` | `tutorial`, `standard` or `hard`. |
| `seed` | Seed. |
| `ending` | Ending label (empty if unfinished). |
| `score` | Total 0–100 (game feedback, not a skill measure). |
| `sim_time_s` | Procedure time in seconds. |
| `near_misses` | Removals outside the working field. |
| `rejected_inputs` | Positional task commands that were not accepted. |
| `wrong_tool` | Task commands with the wrong instrument. |
| `iol_attempts` | IOL placements (including re-centring). |
| `pauses` | Pause toggles. |
| `help_requests` | Help requests (never penalized). |
| `capsule_misses` | Capsule traces outside the ring. |
| `endpoint_error_entry` | Mean entry endpoint error ÷ entry target radius (1 = target edge). |
| `endpoint_error_capsule` | Mean ‖radius − 0.28‖ ÷ half the capsule band width. |
| `endpoint_error_iol` | Mean IOL placement distance ÷ the radius that passes the difficulty threshold. |
| `alert_count` | Alerts raised. |
| `first_alert_latency_s` | Seconds from the first alert to the response. |
| `first_alert_response` | `assess`, `abort` or `timeout`. |
| `score_stages` | Stage-completion points (max 20). |
| `score_tissue` | Tissue-protection points (max 25). |
| `score_iol` | IOL-position points (max 20). |
| `score_response` | Complication-response points (max 20). |
| `score_safety` | Patient-safety points (max 15). |
| `replay_verified` | Experiments only: the replay reproduced the same snapshot. |

The primary research metric is normalized endpoint error. It is scale-free, so it is
comparable across window sizes, zoom and UI conditions.

## Snapshot fields (engine state, `Game.snapshot()`)

- `phase`, `time`, `step`, `paused`, `ending`, `score`
- `patient` (synthetic HR, SpO2, BP, cooperation, motion, alert)
- `eye` (opacity, cortex, capsule integrity, IOL alignment, wound integrity, pupil,
  cornea clarity, progress sets)
- `case`, `hazard`, `difficulty`, `seed`, `session_id`, `schema_version`,
  `patient_card`
- `phase_time`, `safety_hold`, `alert_elapsed`
- `irreversible` — permanent flags: `capsule_damage`, `capsule_rim`, `vitreous`, `veto`
- `stress`, `fragments`, `tool`, `help_requests`

## UI conditions (`report.json → ui_conditions`)

The 2.5D export records the display condition so that research comparisons can
control for it:

- `language`, `high_contrast`, `colour_safe`, `reduced_motion`
- `zoom`, `focus`, `light`
- `ui_scale`, `window`
- `cursor_damping`
- `research_condition` — `baseline` or `low_visibility`; a research condition, not an
  accessibility aid
- `input`, `frame_rate_target`

## Versioning

| Schema | Change |
|---|---|
| v1 | Original trace. |
| v2 | Adds difficulty, pre-op checks, endings and alert holds. |
| v3 | Adds `session_id`/`scenario_id`, the patient card, help, near-miss coordinates and new hazards. |

Event traces migrate forward with `ophthosim.migrate`. Replays carry their own
`schema_version` and are rejected across versions, because rules changed.
