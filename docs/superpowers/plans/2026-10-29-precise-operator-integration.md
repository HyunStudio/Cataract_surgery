# Connect the precise tissue path to actual operator input

Continue the user's professional surgery simulator objective, inline, without
new design questions. Mouse and keyboard remain the first control devices.
This plan follows the source-bound complete extraction uvp7et92. Do not mutate
its native/Godot inputs while that process is live. A successful extraction is
a prerequisite, not the complete simulator or permission to claim clinical
accuracy.

## Evidence and required behavior

The optional precise capsule backend passes140native regressions, independent
actual iris/tool KKT, fresh engine bridge and actual incision/traction/rollback.
The saved failed264outer timestep now advances without loss of rest material,
fracture or accepted uncertainty. Default simulator.gd still never calls
set_contact_backend and supplies cut=true to the old edge-deletion path. The
precise backend deliberately rejects that legacy cutting instruction. Simply
selecting the new backend would break actual knife input.

simulator._physics_process currently updates instrument motion/injury, wounds,
lens flow and pressure before capsule.step_tools; afterwards it advances IOL,
clock, observations and recording without checking capsule.native_failure.
Capsule-only rollback therefore cannot support a correctly transactional whole
application. A rejected precise step must not leave these other subsystems or
tool history advanced, and must not be recorded as a completed physical tick.

Observed RED in test_precise_step_transaction.gd: a deterministic injected
capsule failure actually runs and preserves its reason, but the surgery clock,
lens/fluid state and recorded frame still advance (3failed assertions, exit1).
Registered this test first in the canonical runner so it cannot be silently
omitted. It is a new application-level defect distinct from the passing140native
tests and optional actual capsule checks. No simulator fix is applied while the
source-bound full extraction is live. The new untracked test was not among that
already frozen extraction's inputs; no bound source changed.

Read-only architecture review requires starting before _advance_motion, with
explicit model-owned snapshots restored into existing objects. In addition to
the lens packed arrays, snapshot nested lens.material adhesion/flow state;
duplicating a container does not copy a RefCounted. Injury owns one surface graph:
after restoring it, rebind anatomy.cornea/posterior and restore or invalidate flap
and rigid-body caches (restoring only _flap_revision can retain failed geometry).
Do not blanket-snapshot simulator properties: Nodes, services, diagnostic state
and slider_values=machine aliasing require different policies. Defer IOL if no
later physical failure is possible; otherwise snapshot it too. Keep failure
reason outside rollback and explicitly disarm stale cut/pedal commands. Extend
tests beyond metrics to nested material state, surface sharing, cache consistency,
incision rollback and a later-substep failure.

Concrete control caveat: release_controls() calls capsule.release() and
incision.cut(...,false). Calling it blindly after restoration would itself
change accepted grasp and incision history. Separate input disarming from
physical release; commit a release through the next accepted physical tick or
an explicitly tested safe-abort policy. Do not erase a held tissue attachment
merely to clear a failed command.

Extended the RED test with deterministic pre-rejection changes to nested
material adhesion, wound state and injury surface revision. All3new restoration
assertions fail too (6failures total, exit1). The behavioral surface-sharing
oracle passes now and will catch an alias-breaking fix. Its invocation trace is
kept outside the model snapshot so a correct rollback cannot erase the test's
evidence that failure ran. These extra state changes are injected test scenarios,
not a claim that every ordinary failed step changes those exact fields.

## Sequence and checks

1. Finish uvp7et92 with the same process handle. On failure, preserve its exact
   checkpoint/request and diagnose the smallest saved state before another full
   prefix. On success, independently inspect material conservation and the actual
   tool/anatomical guards; keep the default backend unchanged until the following
   work is verified.

2. Implement finite blade-sweep input using the existing conservative
   capsule.incise API. Derive the curtain from the accepted old/new physical
   blade pose, profile and depth. Test an ordinary uninterrupted mouse stroke,
   no movement, release/repress, a tool change, invalid contact geometry and a
   rotated blade. Preserve original material mass/rest/history and both cut
   banks; a failed incision must leave them untouched. Never replace cutting by
   proximity edge deletion, screen-space progress, or a prebuilt circular cut.
   Pass cut=false to the precise contact step after a committed geometric cut.

3. Define one complete simulator physics transaction. Snapshot authoritative
   instrument poses/targets and grip state, wound state, capsule material/history,
   lens/fluid state, injuries and IOL state that the current tick can change.
   Determine which presentation-only counters need a commit rather than a deep
   copy. On failure restore all physical state and histories and report a visible
   reason; retain input intent only under an explicit deterministic policy.
   Clock, observation, audio events and recording commit only with the accepted
   physical tick. Test forced failure after a successful earlier substep, after
   lens/pressure changes, and after incision. A release or restart must not replay
   a stale cut/aspiration/grip command.

4. Connect the native backend through an explicit capability/load result, not
   ClassDB assumptions. Missing or incompatible extension must give a usable
   startup diagnostic and must not silently select coarse mechanics while
   presenting the precise mode. Verify packaged Windows resource paths and
   packed64 authoritative state across reset, patient/case changes, pause,
   review, instrument changes and two-hand operation.

5. Qualify actual pointer/keyboard operation across the procedure. Include
   off-target incision, grasp/release without impulse, traction/tearing from
   physical interaction, irrigation/aspiration and phaco controls, cortical
   removal, IOL deployment/position, wound assessment and recording/replay.
   Completion must follow observed tissue/device state. Scripted input must use
   the same public control path as the operator. Keep genuine failure cases and
   interruption behavior in the checks.

6. Profile the accepted full path before choosing a performance change. Current
   captured CPU solves and whole-step timings do not meet a60Hz claim. Preserve
   physical acceptance, represented history and continuous guards when reducing
   broad-phase/contact assembly/factorization cost. Do not drop time, weaken
   material strength/tolerances, or change the clock to conceal backlog. A worker
   thread can preserve responsive UI but does not establish real-time throughput.
   Measure interaction latency as well as physics throughput on the actual GPU
   application.

7. Review microscope optics, anatomical surfaces, instruments, operative field
   and UI against the professional simulation objective using actual GPU images
   and operation. Fix visible coarse topology/deletion artifacts. Then run the
   full current Godot suite, actual complete operation and packaged Windows
   smoke test before changing the default or replacing the release.

Corneal wound/closed-shell geometry, tissue-face anatomical contact, calibrated
constitutive/fracture/fluid models and clinically reviewed behavior remain
explicit larger requirements. The current vertex/iris contact improvement does
not establish them.


Transaction integration423ffad restores explicit authoritative model/rig state
before rejected precise ticks, including nested lens material and injury/anatomy
aliases. Derived caches are invalidated. Failure disarms input without releasing
physical attachments, pauses and exposes the reason. Deferred clock, IOL,
recording, observations and audio commit only after accepted physics. Explicit
resume does not release attachments or repeat stale actions. Scoped13suite proof
.tools/transaction-validation-mkcan93_/proof.json qualifies; all input hashes
still match at integration. Read-only review found no actionable defect. This
is not the full Godot suite, default-backend promotion or clinical qualification.
