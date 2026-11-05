# Bounded fine geometry implementation plan

Execute inline with TDD in the existing worktree. Full simulator goal remains.

Decision: retain every original fine material point, with an explicit opt-in8192
fine-point capacity negotiated with an extended geometry guard. Default legacy
4096 remains. Fine faces stay8192; mechanical controls stay4096;65536pairs,
128guard work,250Newton, force1e-8/gap1e-9/COMP1e-11 remain unchanged.
This separates resource roles instead of removing material or relaxing physics.

Alternatives: the owned state has no unused points, no exact boundary collapse,
and no unanchored single-chart interior vertex. A different remesher cannot be
assumed to preserve the existing piecewise material field. Retain that detailed
geometry with bounded dynamic buffers; qualify all consumers and performance.

- [x] RED/GREEN separate membrane_guard_fine_motion_witness ABI,8192points max.
  All points and faces validated/visited, high-index collision and invalid-data
  rejection,8193atomic rejection, legacy4096unchanged, small-input bitwise parity,
  independent caller FP contexts. Same interval algorithm and pair/work gates.
- [x] RED/GREEN opt-in fine geometry state policy. Default Support.build and
  simplifier remain4096; explicit extended argument8192, original/control4096
  bounds retained. Record capacity in owned state; no clock/position changes.
- [x] Typed guard_fine_motion bridge and safe dispatch when fine mesh>4096.
  Unsupported guard rejects before solving. Activate extended state only when
  operative native guard exposes the explicit capability; proxies delegate it.
- [x] Owned cut299 succeeds with area/mass/history and positive material rows;
  legacy still reproduces its old failure. Actual large native geometry guard
  and an actual original-FEM tick, independent force and rollback checks.
- [ ] Native/engine regressions, independent audit of material rows, read-only
  review and the same whole blade route. A successful single cut is insufficient.

For8192fine points the previous/current double coordinate arrays are at most
393216bytes combined. Index validation remains bounded and body/face pairs
remain65536. The sparse mechanical solve retains its separate4096control bound.
No real-time or GPU claim follows from these memory bounds; runtime needs its
own measurement. Full jaw mechanics, other phases and Windows delivery remain.

Review found anatomical_contact moving-point input still4096. Reproduced
with an operative.boundaries regression: high-index clear and collision both
reject before native call. Add an explicit optional moving-point limit with
legacy default4096; operative passes its authoritative state limit. Static
obstacle geometry, chunk64, pair65536, work128 and collision mapping stay.
First native/engine frozen validators predate this correction; do not call
them final qualification of the corrected source.

Native all10artifact rebuild complete. Source-bound native265tests/26patterns
pass. Exact owned cut299 audit after integrated anatomy correction:4103fine
points4432faces346controls, every Fraction determinantpositive(min3.0485e-19),
areaerror-1.5077e-19,masserror0, history/clockunchanged andevent+1.
Review anatomy correction accepted with no additional substantive findings.
Actual far-body owned tick previouslypassedforce1.59885e-9,2Newton; final
integrated30stageengine/56focused validators are running on frozen sources.

Final integrated focused56suites +freshimport PASS. Native anatomy
required-kernel and owned fine cut/tick stages PASS in final engine snapshot.
Remaining final engine stages still running; no complete-route claim.

Final integrated qualification: native265tests/26patterns PASS; focused56
suites+freshimport PASS; actual engine30stages PASS, snapshot
.tools/fem-extension-fdy5l63n. All validators terminal exit0 and sources frozen.
Independent exact material audit PASS; read-only final review clear.
Remaining: same closed-blade full route, then remaining simulator acceptance.
