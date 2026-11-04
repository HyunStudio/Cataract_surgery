# Certified zero physical reactions

Continue full simulator objective frombf4c1d7. The full22-stage attempt is now
terminal:21 pass, final blade path fails after at least160 accepted ticks with
endpoint force/gap/COMP above the strict limits. Its exact failure is being
captured on the old frozen source/DLL via capture_frozen_operative.py. That
capture verifies its own inputs; root improvements must not modify its probe.

1. Make future full runs use transparent capture by default, inheriting both
   incision and contact failure observers. Keep identical operator/physics logic.
2. RED far physical-dual-zero refinement count while checking full geometry
   queries, positive far physical reactions, penetrating zero reactions, tiny
   positive reactions, degenerate input and normalized-gap overflow.
3. Reuse the outward inactive certificate for physical dual==0 only. A PHR update
   of zero is insufficient: a positive physical multiplier must remain active.
   Certify regularity of the unrounded fine field before skipping its refinement;
   uncertain/degenerate material geometry must fall back/reject, not be hidden.
4. Keep all full distance queries and original force/penetration/COMP/SPD/work/
   whole-interval gates. Compare actual original/native outputs, independently
   verify KKT/guards and run native/engine regressions. Measure identical inputs.
5. Diagnose the newly captured real route failure from its original predictor and
   accepted history; do not loosen feasible-retry or acceptance gates blindly.
   The whole surgery, finite-jaw acquisition, material crack opening, actual input,
   real-time, GPU and Windows release requirements remain active and unqualified.


## Implemented and verified

The old far physical-zero case performed one unnecessary unrounded gap refinement
(REDcount[query,field]=[1,1] instead of[1,0]). The new predicate uses the actual
physical multiplier==0, not its possibly-zero PHR update. Before reuse it also
requires a positive lower bound on the squared normal of the unrounded mapped
fine face, plus the existing strict outward coarse-hull separation. Full distance
queries and normalized-gap overflow checks still happen first. Positive physical
reactions and uncertain/penetrating fields retain full refinement. The old
outward COMPzero bound (one binary64 subnormal) and signed zero are preserved.

Ten new tests are GREEN, including exact collinear material mapping and a coarse
control collapse at the actual sample time. Read-only review found no substantive
certificate, FP or state issue. Manual capture smoke also confirms that the new
TraceState inheritance records an invalid incision's exact typed prior state
without mutating material. Future full validation now runs the transparent
capture subclass, covering both incision and contact failures without another
long prefix solely for data collection.

- [239 numerical tests /21 suites](../../assets/zero-reaction-numerical-2026-11-05.json)
- [16 real native/core stages](../../assets/zero-reaction-engine-bridge-2026-11-05.json), including actual144/146/150/156 cores.
- [44 focused suites plus fresh import](../../assets/zero-reaction-regressions-2026-11-05.json).
- [Serialized actual156 candidate comparison](../../assets/zero-reaction-comparison-2026-11-05.json): status, xyz, reactions, duals and all stats are bitwise identical; both pass independent original KKT and full interval guard. Baseline21.866s versus17.735s (~18.9% elapsed reduction) on this one candidate. No real-time or whole-surgery claim.

The former full run is terminal21/22 and its transparent repeat also reproduces
the failure. Exact new barrier is motion167 AFTER166 accepted ticks and249 staged
incisions, with346 controls and3407 fine faces. The owned typed snapshot roundtrips
exactly and its canonical original B reproduces old fine geometry bitwise.
[Original167 request/motion/q0](../../assets/operative-motion167-native-case-2026-11-05.json),
[capture provenance](../../assets/post-reaction-next-capture-2026-11-05.json),
and `godot/tests/fixtures/operative-motion167-state.bin` preserve it.

Its static failure has force1.235052110692969e-6, gap3.6986404357918054e-8 and
COMP8.919789087559183e-8 after24 Newton steps. No candidate or clock is published.
An offline accurate cold path resolve with the ORIGINAL remaining226/250 budget
is in progress. No eligibility/acceptance criteria have been changed for this
new infeasible endpoint. Scope remains full professional simulator; complete
input cases, native real-time, finite-jaw and material-tip opening, anatomy
qualification, GPU and Windows delivery are still outstanding.


## Captured167 resolution and dispatch selection

The offline167 resolve is terminal success: first [.5,1] candidate passes original
KKT but the guard finds witness.49609375. The next three-layer seeded candidate
passes KKT and the complete guard. Finalforce6.152375806267765e-9,60/250 total
Newton steps (including24 original failed static steps). Neither physical dt,
q0, original predictor nor any physical acceptance bound changed.
[Source-bound native167 resolution](../../assets/zero-reaction-motion167-native-2026-11-05.json).

A new dispatch transaction test is REDbefore removing only the unpublished failed
endpoint penetration/COMP eligibility caps, GREENafter. Finite/nonnegative failed
stats, status2, unchanged output predictor, valid spent work, original shared
budget and exact hold feasibility remain. No failed iterate becomes a seed.
Final successful candidate force/gap/COMP, independent force and complete path
gates are unchanged. Extra invalid temporal-force/penetration/COMP cases prove
rollback and no guard/publication when those final gates fail. Read-only review
found no selection loophole.

The21 operative component stages now can be run with --operative-components.
--operative-blade still requests the full22. After short component verification,
commit the concrete source, then observe the same frozen full route with
capture_frozen_operative.py; this lets further source work proceed while the long
immutable run remains auditable. Its route_passed flag requires exit0, the closed
blade success marker, no engine errors and unchanged frozen inputs; qualified
remains false for the whole-surgery scope. This is not a skipped full-route gate.
Current21-stage real cores include167; new focused44-suite run is in progress.


## Real engine167 verification

The21 component stages are terminal success, as are44 focused suites plus fresh
import. Actual captured167 now advances one physical/history tick in Godot,
independent engine force6.151327003323104e-9,60/250 Newton work and complete guard
clear. Observed20.972s still fails real-time requirements. Earlier144/146/150/156
saved states also pass. Read-only review found no dispatch or scope loophole.

- [21 component stages](../../assets/zero-reaction-operative-components-2026-11-05.json)
- [Five owned engine-state metrics](../../assets/zero-reaction-core-metrics-2026-11-05.json)
- [Latest44 focused suites](../../assets/zero-reaction-regressions-2026-11-05.json)

These do NOT establish that a fresh complete route passes. Commit this tested
source, then run the same frozen route with capture_frozen_operative.py. Both
incision and contact failures now retain the next exact owned inputs immediately.
No default-backend promotion, main merge, clinical or delivery completion claim.
