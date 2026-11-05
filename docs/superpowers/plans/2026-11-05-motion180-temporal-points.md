# Next owned180 failure: temporal distributed material normals

Full frozen blade session21538 is TERMINAL exit0 capture/route_passedfalse
(actual engine return1). Do not poll/restart it. Source snapshotd665ac5:
.tools/fem-extension-fdy5l63n. Previous cut299 capacity failure is passed,
but no complete frame beyond179 is qualified.

Captured operative-motion180-state.bin owns staged state:179steps,301cut
events,4486fine vertices,4817faces,346controls,limit8192. Events301 belong to
intermediate cut processing before the rejected physics frame, not accepted
whole-frame publication. Whole simulator transaction correctly rolls back.

Native request0 material_points budget250 succeeds22Newton, force3.2243e-11;
request1 material_points budget228 succeeds24Newton, force1.6662e-10.
Full geometry guard then finds a middle-path collision at t=.5, face22/body0,
gap-4.18177e-5. Cold original-fine-face trajectory gets remaining204Newton and
fails withforce.37807666. Total work250 is preserved; do not raise it or relax
force1e-8/gap1e-9/COMP1e-11. Central flap remains attached.

Raw little-endian exporter/decode retains exact request and response doubles,
including the entire guard history. Use owned requests instead of replaying
another long successful prefix. Endpoint success is not motion clearance.

Next implementation after bulk-query foundation:
- Native private FineContacts already supports material_points with layer-major
  time(), local interpolated controls, force t, Hessian t² and point merit
  change(previous,before,after,shape,time). Verify these paths with RED tests;
  add a separate recorded-trajectory material-point API, preserve all old calls.
- Godot point generator must inspect actual original geometry at every sampled
  body pose/time and add penetrating material-point rows across layers.
- Independent point reactions must validate provenance, dual shape, t-scaled
  force and original stress/inertia. Never reuse point duals as fine-face
  temporal multipliers; separate candidate model/seed contracts remain.
- Full physical motion guard remains mandatory and can insert another witness
  time within existing16layer/shared250work limits. Publish only after all
  independent force/gap/COMP/whole-motion gates; otherwise roll back everything.
- Test analytic moving/rotating interior contact, time scaling, endpoint-only
  parity, invalid model/negative work/ownership, callerFP and owned180 exact
  whole-step acceptance before another full route. Bulk witnesses may reduce
  repeated query cost but are not a contact-model or real-time qualification.

Native optional bulk ABI5tests and actual bridge6stages pass. It is not yet used
by runtime; full native270test qualification is still running before commit.

Implemented and owned180 core PASS in frozen .tools/owned-temporal-anwstl6u.
Native cold/point-only seeded trajectory APIs keep ordinary APIs unchanged.
Nine native tests pass (analytic mid-arc KKT, t/t² derivatives, old endpoint
and zero-body bits, invalid/seed atomicity, cold+seeded64FP contexts). GD force,
point-seed source/row/time mapping and backend budget/model tests pass. Budget
mutation in a separate copy provably produces3failed assertions; production
source remains unchanged. Read-only review found no substantive issues.

Cold temporal retries exhausted250work at5layers. Separate point-only warm
seeds now preserve canonical original-control rows/source epoch/xyz/body packet,
zero new row/layer reactions, and never enter ordinary fine-face seed APIs.
Owned180 passes with154totalNewton/250, force7.51869677628747e-11, nine times
[.00390625,.0078125,.015625,.03125,.0625,.125,.25,.5,1]. Complete fine physical
motion guard returns0 and failed budget0 cannot mutate accepted state/history.
Fine vertices4486/faces4817/controls346. Runtime153946ms is FAR from real-time.
This is Embedded core only; app anatomy/full route/actual input remain unproven.

Resource accounting: only the explicitly supported sparse-point candidate can
exceed the old finefaces*bodies*layers storage count. Actual native constraints
remain rows*bodies*layers<=65536, rows<=8192,layers<=16. Every full fine surface
is inspected separately per layer (eachfaces*bodies<=65536), and each complete
motion guard retains its original pair/work caps. Ordinary fallback still checks
its original dense cap. No tolerance or250work limit was raised.
Exact150 regression now checks actual sparse packet dimensions/provenance when
using this model, retaining the old layer-retirement assertion for dense mode.

Full Native279tests/28patterns,59focused suites and33actual engine stages are
currently running on frozen sources before commit. Do not restart a full blade
prefix until these checks qualify the new source. Capture proxies now forward
both point-time APIs and preserve raw response ownership; replay tool names
match separate C candidate models. Numerical-query bulk API remains unused in
runtime and still carries no performance claim.


Regression investigation (2026-11-05, before qualification):
- Native279/28 and59focused suites passed on the first temporal implementation,
  but actual engine qualification FAILED exact150. This is not a passing33-stage
  result. No full route was started from this failed component report.
- Exact150 endpoint point solves used26+22+22=70Newton; the full motion guard
  inserted t=.125. A622-row seeded trajectory inherited penalty1e6 and exhausted
  the remaining180Newton, force43.56724160813015. Accepted state stayed unchanged.
- Owned raw request SHA fba792dfbc31e61884f657efd276350e63856c317aec5743b735d63a5c108614
  (serialized failure packet). The identical native request cold passed27Newton;
  preserving initial positions and mapped reactions but restarting penalty1
  passed22Newton, independent native residual1.091639511684747e-11.
- Hypothesis confirmed: numerical endpoint penalty is unsuitable for newly added
  contact constraints. warm_start now restarts only this numerical penalty when
  rows or time layers expand. Same constraint set preserves it. Mapped reactions,
  physical source, force/gap/COMP gates and shared250 budget remain unchanged.
- RED: row-only, time-only and combined expansion assertions failed3times.
  GREEN: all pass after the change; unchanged set and ownership remain checked.
  Actual full-engine and59-suite regression requalification are running in new
  immutable snapshots; owned180 must also continue to pass before adoption.

Review commit provenance located at C:/tmpcs/kind: HEAD39481ff. It and79c5c8d
are already ancestors of this development branch through27f9eb8/c1f760b.
Do not cherry-pick duplicate review fixes. Windows packaging at27f9eb8 is an
older desktop preview, not qualification of the optional native surgery model.


Follow-up: resetting every expansion was NOT sufficient. Full actual engine
still rejected150 after246pointNewton and4ordinaryNewton; no source qualified.
Trace rows grew321→622→623→1070→1662→2399 because every retry seeded all
feasible near faces at every layer. The final sparse pair capacity also became
unavailable. This was investigated separately from the numerical penalty.

Two isolated copies narrowed the scheduling policy:
1. Keep all full original-surface/body/layer inspections, but initially acquire
   only actually violating witnesses, plus all owned prior rows. All post-solve
   complete checks and final full-motion guard remain. No physical pair is
   skipped during inspection. Rows150 stayed321→326→327→329→330→331; runtime
   dropped223s→73s for these failed diagnostics, but work still exhausted250.
2. Exact same captured request4 with its previous temporal penalty1000 uses
   9Newton versus35when reset1. Final policy resets numerical conditioning only
   on endpoint→time-model transition; within temporal continuation, preserve it.
   This is a numerical heuristic, not a convergence guarantee or physical gate.

Combined copy: owned150 actual result VALID,155Newton/250, original force
1.604e-11,8times down to.001953125,334rows, complete motion status0 and atomic
zero-budget rollback. Its throwaway diagnostic inherited owned180's requirement
that.5appear, so exits1 on that irrelevant assertion; it is NOT a qualified test.
The production exact150 test remains the authority in the fresh full validator.

Read-only review identified zero-row acquisition: native zero-contact solve has
stats[15]=0, so it cannot make a contact penalty seed. Temporal exchange now
acquires those new rows cold, retaining shared work and immutable predictor.
RED6assertions across protocol/seed tests; GREEN after implementation. Coverage
includes empty→violating acquisition with a seeded API present, near-feasible
faces, row/time continuation, endpoint transition and input ownership. No source
model lineage/fixture-number strategy was adopted. Final59+33 frozen validation
is running again before any qualification, commit or continuous route.


FINAL component qualification, frozen .tools/fem-extension-e83q8l5s:
- Native279/28 PASS; report inputs and all build source hashes unchanged.
- Focused59 suites PASS, frozen .tools/embedded-regressions-0f3sqp9n.
- Actual optional engine33 stages PASS, current source/frozen file hashes match.
- Original exact144/146/150/156/167 all PASS. Exact150155Newton, force
  1.60448321295803e-11, elapsed66237ms. No fixture-specific strategy adopted.
- Exact180177Newton, force2.891069605936991e-10, elapsed123125ms, nine times,
  unchanged source history/clock once; full guard0 and zero-budget rollback PASS.
  Work remains<=250, full force/gap/COMP gates unchanged. NOT real-time.
- Raw reports/metrics archived under docs/assets/temporal-contact-final-*.
  Earlier running/failed statements above are history, not current qualification.
- Latest remote2e616eb native/Python CI succeeded, legacy Godot failed domain
  step and skipped render. New source CI, full route/anatomy/all phases/actual
  OS input/GPU/native Windows release remain unqualified. Goal stays active.

Next: commit component milestone, run unchanged frozen continuous blade route,
collect owned failures, profile costs before optimization. Do not mark whole
simulation complete or merge a release based only on this component result.
