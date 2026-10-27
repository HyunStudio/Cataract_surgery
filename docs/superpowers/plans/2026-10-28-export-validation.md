# Repeatable Windows export validation

> **For agentic workers:** Use superpowers:executing-plans inline. Existing user authorization is to continue implementation without design confirmation.

**Goal:** Re-run outcome assertions against frozen, compiled production resources under the byte-identical release engine, preserving evidence and candidate files.

**Architecture:** A Python standard-library CLI creates a fresh ignored QA project. A Node bootstrap mounts a frozen production PCK before loading an adapted allowlisted SceneTree fixture; its QA executable is copied from the actual candidate. Exit status, outcome marker, errors, hashes and paths are recorded separately from default launcher qualification.

**Tech Stack:** Python 3.12, Godot 4.7.2, Windows release template.

**Spec:** Existing release qualification requirements in `docs/REALISM_COMPLETION_KO.md`; this is an engineering verification tool, not a product feature or clinical qualification.

## Constraints and review focus

- Never modify or overwrite the candidate or the previous verified ZIP.
- Allow only normal, adverse and control fixtures; reject fixture structure drift instead of silently weakening assertions.
- Only a completed zero exit with the expected zero-failure marker, no engine errors and matching before/after hashes qualifies.
- Live jobs have no automatic timeout termination. Do not run concurrent headed fixtures: focus loss intentionally disarms production controls.
- This gate does not qualify original main-scene startup, human event choreography, sustained performance or clinical accuracy.

## Task 1: Freeze and qualify exported resources

Files: create `tools/validate_export.py`, `tests/test_export_validation.py`.

- [x] Write failing tests for fixture adaptation, rejected unsupported structure/scenario, frozen artifact identity, missing/changed PCK, error/nonzero/missing-marker rejection.
- [x] Run `python -m pytest tests/test_export_validation.py -q`; verify missing implementation failure.
- [x] Implement helpers and CLI. Freeze candidate exe/PCK in a unique `.tools/export-validation` directory, generate bootstrap/QA pack, execute frozen release binary, and persist a JSON result with hashes/logs/return codes. Keep staging on failure.
- [x] Run focused tests, full Python suite, real compiled release control fixture. Existing full normal native run remains separate evidence; no duplicate full run during that job.
- [x] Review and commit the tool and controlled-input fixture changes.

## Ledger

- Initial state: production HEAD `be14d7f`; source full normal passed. Standard 52-suite, controlled GPU normal and compiled native normal jobs already running. GPU fixture input isolation has separate actual event-dispatch coverage and read-only reviewer approval.
- Ruling: use existing feature checkout rather than a new checkout, so live validation continues against the same frozen source/candidate. Only test/tool changes in this task.
- RED→GREEN: missing adapter module; actual normal fixture's five early failure exits; ANSI-prefixed engine errors; actual PCK collision replacing trusted fixture. Current19 focused tests pass, full Python541pass. Optional collision test skips explicitly when pinned local Godot is absent.
- Scoped independent review closed early-exit, colored-error and pack-overlay issues; no new substantive issue. Reports bind source snapshot, adapted QA inputs, adapter/editor and compiled QA pack. Official API references: https://docs.godotengine.org/en/stable/classes/class_pckpacker.html and https://docs.godotengine.org/en/stable/classes/class_projectsettings.html#class-projectsettings-method-load-resource-pack .
- Standard52suite exit0; source NVIDIA normal and adverse exit0; original candidate startup120frames exit0; compiled production full normal exit0. Screenshots inspected. No sustained performance or actual full human-input claim.
- Final hardened CLI control run `.tools/export-validation/20261027T203454Z-fd63602b/result.json` status passed, all phases exit0, frozen/candidate identities unchanged. Original source control-context suite also exits0 after actual-dispatch assertions were added. Full normal native provenance remains the separate recorded run, not a claimed run of this new CLI.
