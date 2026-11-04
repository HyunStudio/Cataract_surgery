# Operative axial rotation

Continue inline in the isolated engine worktree. The preceding goal turn was
progress: fd9cdfd numerical boundary and27f9eb8 Python preview. The professional
Godot goal remains active. No new design questions: user requested completion.

Add radians of axial rotation about the generic tool's local +X (tip toward
handle). Preserve zero-roll behavior. Input Z/C queues rotation for the selected
hand; simulation rate limits it and clears pending rotation on focus/context
loss. The shared Profile frame drives rendering, quaternion body packets and
blade sweeps. Rigid portal contact evaluates the same roll and bounds added
endpoint speed by abs(delta_roll)*maximum local radius. Clamp/reject motion
atomically with the rig pose; rejected FEM/cut steps restore accepted roll.

Tests first: no tip/axis displacement from pure roll; shared jaw/render/path
pose and midpoint; rotating sharp edge produces a finite sweep; a small obstacle
intercepting a rotating jaw blocks a motion whose endpoints are clear; input
burst cannot publish before a fixed tick or bypass speed/focus/pause guards.
Re-run existing path/body/blade/display/transaction tests in a frozen engine
copy. Preserve the existing actual physical thickness and contact limits.

This is necessary instrument control, not jaw acquisition or complete surgery.
Actual jaw/material acquisition, retained partial-tip opening, default FEM
integration and full input/GPU/Windows surgery remain outstanding.

## Evidence

- RED rig has no axial rotation method; input RED remained0 after a commanded
  fixed tick. Implemented shared frame, bounded queued input and physical paths.
- Initial34suite frozen run18177 stops at instrument-profile because recorded
  dictionaries omit roll. Dedicated recording test RED2 plus script errors.
  Fixed accepted pose capture and backward zero defaults; recording/operator
  focused checks now pass. Read-only reviewer confirmed this defect and found
  no further blocking speed/broadphase/transaction issue.
- Fresh frozen35suite run80478 terminal0, all source/hash/error/leak gates pass.
  This includes existing body, blade, physical path, display and transaction
  contracts. Archived instrument-roll-regressions-2026-11-04.json.
- Supplement65654 terminal0 rechecks frozen hashes, adds the exact rollback
  script and verifies actual pending roll executes before a rejected tissue
  tick restores accepted pose/clock and cancels intent. NVIDIA operator66169
  terminal0 uses the same frozen project: OpenGL3.3 NVIDIA566.14 RTX3070Laptop.
  Archived instrument-roll-supplement-2026-11-04.json. This is scripted engine
  input, not OS keyboard injection or a complete case. No FPS/release claim.
- Local merge-tree reconciliation against Python preview27f9eb8 reports only
  README conflict; actual integration is a separate next action.
