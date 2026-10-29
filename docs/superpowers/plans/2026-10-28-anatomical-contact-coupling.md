# Couple anatomical surfaces into the physical tissue solve

Execute inline under the existing active professional-surgery simulator goal. User has authorized continuing implementation with mouse/keyboard and no further design questions. This is a correctness prerequisite for that goal, not its completion definition.

## Starting evidence

5a9fa68 fixes false Armijo rejection and float32 physical jaw overlap. Full replay faad2gqn accepts264 then rejects265 at anatomical correction, despite accepted endpoint/trajectory tool-contact KKT and continuous tool guard. Exact requests, full checkpoint, candidate and iris geometry are preserved; see native/tests/fixtures/joint_trajectory265_boundary.md. Frozen replay and independent Decimal geometry reproduce the next defect without the full prefix. Old height-field acceptance does not imply clearance from the actual iris normal margin, even at the prior state. No process from that full replay remains live.

## Requirements and sequence

1. Preserve the exact new failure as regression evidence and finish native verification. Keep old tool-only ABIs/caller behavior stable. Test passing tool KKT separately from rejecting actual anatomical motion; never relabel the latter as success.
2. Define bounded nonmutating actual-surface queries for detached tissue, initially iris. The existing native guard can query a static anatomical triangle mesh against a linearly moving point capsule for each tissue vertex. Chunk queries within existing limits and preserve witness face, vertex and time. Every omitted pair needs a conservative broad-phase certificate; no handpicked face252 exception. Test thin/steep finite faces, pupil edge, crossings with clear endpoints, ambiguous/degenerate geometry, limits, immutable inputs and actual265 evidence. Radius.004 remains an explicit engineering margin. Corneal wound clipping, closed-shell sidedness, limbal containment and exterior tracking must be explicit separate geometry rules, not implicit height-field clearance.
3. Add optional rigid-triangle/moving-tissue-vertex constraints to the same inertia/spring/tool-contact objective, via a new ABI rather than silently changing old call contracts. Each constraint specifies tissue vertex, finite rigid triangle, radius and selected physical time; rigid geometry has no dynamic inverse mass. Derive the point gradient from translation invariance or an independently checked finite-feature formula; selected-time Jacobian scales by time. Include active anatomy contributions in force, complementarity, Hessian model/final curvature and stable merit difference. Closest-witness errors and actual represented coordinates need conservative change bounds. Keep original physical tolerances, exact pins, bounded work and atomic outputs.
4. RED→GREEN analytical cases: point against plane/edge/vertex with independent equilibrium/reactions; rigid rotation/translation invariance; simultaneous tool/anatomy contact; prescribed penetrating point; unsupported/ambiguous geometry; intermediate-only collision; limits/exhaustion with all outputs untouched. Validate finite-feature distance/gradient/Hessian and whole objective against independent Decimal geometry and numerical derivatives. Do not replace finite geometry by unlimited supporting planes without a demonstrated valid domain. Keep the same predictor/history/material across constraint generation.
5. Integrate bounded witness-driven anatomical constraint generation into the optional actual capsule path and final nonmutating continuous check. Current old265 history already penetrates the actual-surface margin, so do not claim clearance by solving only its endpoint. Start a fresh canonical history only after initial-state consistency and integration checks pass. Geometry/outside state and whole outer time rollback remain transactional. Preserve old height-field tests as their documented approximation until the replacement is explicitly validated.
6. Rebuild/provenance, complete native and focused Godot checks, request one read-only review of this implementation boundary, then frozen bridge/actual integration. Only then replay the full canonical extraction once; keep its process handle until terminal and capture any next failure. No tolerance/budget increases, hidden projection, route changes or wound enlargement to pass. Record performance honestly.

Default incision/grasp refined-traction failure also remains: frozen kutyucft rejects small traction and trace shows an already overstretched accepted tiny edge. Do not assume moving a tear check solves it. Default promotion, actual mouse/keyboard whole case, fluid/device complications, anatomical assets/OR/microscope, realtime/GPU and Windows delivery remain required after this scoped work.

## Implementation ledger

Task1: complete as failure evidence, not anatomical acceptance. Native92 tests pass in90.204s with independent KKT for the actual265 trajectory and independent Decimal iris penetration proof. Full replay34947, failed-step replay92370, baseline62900 and all boundary diagnostics are terminal. Frozen source identities and failed-step checkpoint are documented in the fixture MD. No source mutation during those validations.

Task2: optional finite-surface query adapter implemented at godot/scripts/anatomical_contact.gd, not connected to product acceptance. It freezes copied actual triangles and creates double point-capsule motion packets, queries every selected point against every configured face, chunks within64bodies/65536pairs, and maps the first native collision back to finite face/tissue vertex/time. No projection, physical-state mutation, shell/wound classification or response solve. Query budget128/gap1e-9 unchanged. Existing native interval certificates handle pair culling; the adapter drops no pairs itself. Shapes/coordinate/selection/malformed native output are rejected before clearance can be claimed.

Focused adapter test was RED from missing module, then GREEN. Stronger malformed-status test exposed a typed conversion error; corrected by validating the returned status type before conversion and finite face/body coordinates before integer conversion. Large16384face test checks all18chunks for70points; old input/mesh/radius immutability tested. Read-only reviewer found one domain mismatch: native requires radius>gap. Added actual RED tests for radius5e-10 and1e-9 with atomic old-configuration preservation, then fixed configure radius<=GAP rejection; focused test GREEN. Reviewer found no further evidence-backed issue. The earlier aborted malformed-status diagnostic was stopped only after an explicit script error and matching process identity, not an observation timeout.

Frozen coupled engine qvrw5c5w passed actual iris adapter rejection (vertex663/face252/prior endpoint) and existing integration checks. Final post-review source validation knlvko8y/session17077 is terminal0/qualified: import/runtime stages complete, exact input hashes unchanged,0failures. Focused adapter test also passes after the review fix. All current jobs/reviews are terminal. Tasks3–6 mechanics/integration remain, as do cornea/wound/closed-shell rules beyond this iris surface query scope. No fresh full extraction until those are ready.

Task3/4 native implementation: new26argument membrane_solve_trajectory_anatomy adds rigid triangle9/radius/time constraints named by tissue vertex. Old ABIs remain unchanged. Shared Problem includes their point gradients via translation invariance, time scaling, normalized gaps, PHR reactions, three-coordinate FD contact curvature, strict final screen and atomic output. New point-contact merit-change bounds use outward binary128 intervals and feasible witness support gaps with negative point displacement. No physical tolerance, work limit, material, predictor or history change. Initial anatomy ABI test observed RED from missing export, then14analytical/physical/ABI tests GREEN. Point bound shim observed RED from missing export, then4tests GREEN against independent Decimal geometry (100random cases included). Full110native tests pass in82.429s; earlier107suite passed before three added regressions.

Godot solve_anatomy bridge added with packed types/dimensions/count checks. New method RED against the original frozen DLL ui3b183w; rebuilt65-TU extension succeeds. Read-only numerical/ABI/bridge review finds no evidence-backed defect. Fresh minimal bridge aplabvxc import terminates AV3221225477 despite complete stages; same frozen DLL/resources runtime independently exits0 with0failures. This does not qualify its failed import. The35frames/25ms workaround remains timing-dependent. Actual coupled1mixyfvi/session98988 and independent identical-input editor35frames/1000ms zv4vc8y2/session74349 both terminate0. Ruling: retain explicit35frames and completed-stage checks, increase editor-only delay to1000ms after demonstrated25ms failure/identical-input1000ms success; no retries, runtime delay or physics changes. This is a verified workaround path, not an upstream engine fix. Final canonical fresh bridge bdunpvxy/session11378 and actual capsule ptyzo_sg/session18274 both qualify with import/runtime0 and all input hashes unchanged.

New native ABI DLL SHA0623b0d9b4c46467aaa947d45afa9f55ebb2cee4b1368d315eb16acc86280e5b; extension SHAbf181d447974723b06510009806511d9defb0c23cb3f6fe3ccc50aa8c104cc39; merit header SHA1405200a32f25cfdb395fd72abe5b0726053dcbe6a7fb2852d3fc9485badfa57. All current jobs/reviews are terminal. No fresh full extraction.

Actual-scene diagnostic .tools/joint-anatomy265-probe-_3bxp4fp (session29499 terminal0 as a diagnostic) appends two finite face252 endpoint constraints to the exact saved tool trajectory request without changing predictor/history/material/pins. Native solve returns status2, force.0109791, gap2.15787e-8, complementarity4.66026e-6,11outer/256evaluations/194inner/283factors. Output positions and all reactions remain untouched; do not call this a solve pass. The input's prior states already penetrate the actual-surface margin, so it also cannot be a continuous clearance proof. Preserve the request/result hashes in the ignored probe; integrate from a consistent initial history before a new full prefix, and diagnose any remaining solver failure on exact captures. No tolerance/iteration increase or endpoint projection was adopted.

Next Task5 implementation: expose actual iris query geometry from the configured boundary; collect every detached material vertex; check old state without mutation; generate finite anatomical face/vertex/time constraints alongside tool witness times using the same fixed predictor and bounded8-solve refinement loop. Require both continuous tool and anatomical guards before publication. Backend missing anatomy support, initial penetration, repeated witness, geometry uncertainty or work exhaustion must roll back the whole outer timestep. Test analytical integration/transactionality and initial actual geometry before fresh replay. Corneal wound/closed-shell/exterior rules, full tissue-face contact beyond the vertex approximation, default incision/input, performance/assets/GPU/Windows remain unfinished requirements.

## Actual capsule integration continuation

Previous goal turn is progress: native/bridge work committed30a7e16,110native tests and frozen engine checks verified, exact difficult endpoint diagnosis retained as failure. This continuation implements Task5 in the existing feature worktree. No native code/DLL changes or tolerance/budget increases.

Configured FlapBoundary now builds a copied finite iris query at the current radius. Capsule selects every detached positive-area component's nonremoved vertices, including prescribed material points. It requires old-state clearance before the first solve; a legacy penetrating history fails before touching the physical solver. One shared8-solve loop retains all time layers and finite anatomical constraints with the original predictor/history/material; anatomical changes require a fresh tool check, and tool changes retain anatomical reactions. A result needs both continuous guards before publication. Accepted anatomy records are captured with the physical state and restored on whole outer rollback. Tool-contact metrics count only tool reactions. Existing corneal wound/outside projection-as-guard is retained and may still reject; no complete shell or tissue-face contact claim.

New joint anatomy regression observed RED from missing integration interface, then GREEN. Covers no-body anatomy response, interleaved tool/anatomy refinement, fixed inputs, missing capability, malformed outputs, initial uncertainty/penetration, duplicate and work exhaustion, and whole outer rollback after an accepted first substep. Existing joint guards/grasp and flap boundary focused tests pass. Native frozen integration also proves an actual generated plane witness resolves to y=.1/reaction.0025 and is rechecked continuously; old actual265 iris history rejects before a static solve; actual refined three-tick traction remains intact.

Read-only review found one material selection omission: an inherited area<=1e-12 cutoff excluded supported positive material. Added RED assertions for5e-13 area at density100 (inverse mass6e10) and removed/zero support handling, observed2failures, then changed only the new selector to exclude area<=0. Focused joint anatomy rerun GREEN. Review found no further evidence-backed issue. Initial frozen hf0a1v_4/session88891 and final post-fix9005gm1j/session96197 are terminal0/qualified, with completed import/runtime and unchanged hashes. All current jobs are terminal. Full replay is not started yet; next is commit then one fresh canonical prefix with the new consistent initial contact history. Preserve its handle through observation timeouts. Ignored failed-step replay adapter now forwards solve_anatomy and records every native request for exact next-failure capture.

Task5 committed3a1c95b. Fresh canonical full replay ttc652cp/session90943 is terminal1/unqualified:263ticks accepted,264rejected with native_joint_solve/status2. Original area remains with0broken/lost/accepted uncertainty and whole-step rollback. Frozen checkpoint replay c77pa78w reproduces the failure without another prefix. Exact combined request38 is preserved as joint_anatomy264.json with provenance in its sibling Markdown file. Initial iris history clears; this is a new combined mechanical failure, not legacy265 prior penetration. Explicit heavy check tools/check_anatomy_capture.py is RED/status2 with atomic rejection. Frozen line trace3f__oy1q is terminal and retains the failing direction/all32represented candidates; geometry is valid but line search cannot establish descent. Investigate the actual directional model before any numerical change; original gates and budgets remain.

Independent performance diagnosis while waiting: ignored frozen guard-bounds-cache-ld6q6z71 precomputes the unchanged per-body swept bounds/margins and per-face old/new bounds outside the pair loop. No pair is dropped beyond the same comparisons; order/counters/tolerances/work limits are retained. All28guard tests pass and88base/cached comparisons have identical statuses/eight stats. On301flap vertices against the actual1280face iris in6batches, contended isolated timings are baseline.057–.077s versus cached.00495–.00751s (5alternating runs); this is not app/realtime qualification. Proof binds original/cached source hashes, compiler, flags, baseline build manifest/DLL before/after and cached artifact. Cached header SHA3bd9f9eb7d73dfaf8b47a713672b49e08ebd326050ece920b2eb32f3021f826a. Prototype is not adopted while the full replay is live. Consider this mechanically identical culling-loop optimization after the next correctness gate; do not mix it with changing solver tolerances or accepting failed contacts.

### New264 line-search cause and bounded experiments

Trace3f__oy1q and canonical heavy gate both terminate status2; failed positions/reactions remain unpublished. At the final captured state, the iris constraint has normalized gap1.421218698e-11, dual5.257702861e-9 and rho2236.4580104, so its current PHR multiplier is zero. The Newton model therefore excludes its penalty curvature. The proposed direction immediately activates it: slope-6.395952122e-9 and model curvature6.395736858e-9, but full-step actual merit rises68.5467128, dominated by the new iris penalty. At the last original halving step4.6566e-10, actual change remains positive. Independent tool-pair comparison finds no per-pair discrepancy above1e-15 at step2^-20. Frozen model probe and root-cause.json retain direction/state provenance. The model diagnostic uses a host-target build and is causal evidence, not a production artifact qualification.

First ignored experiment anatomy264-quadratic-ej__fuju uses standard safeguarded quadratic proposals after every failed Armijo trial. It keeps all gates and32trial evaluations, removes the line-search failure but exhausts100outer iterations: force5.8793e-9/gap1.1147e-10 pass, complementarity2.5423e-11 fails. It is unadopted and not qualified.

Second ignored experiment anatomy264-final-probe-e5vtyv6k preserves the first31probes and replaces only the final blind halving with a quadratic estimate clamped to[.1step,.5step]. Existing direct/certified Armijo checks still decide acceptance; no tolerance, material, route, factor or evaluation bound changes. Read-only numerical review finds no actionable correctness issue; proposal cancellation can reduce effectiveness but cannot bypass acceptance. All110existing native regressions pass against this isolated DLL in125.163s. Its full captured solve is now terminal/status2: force.00933255, gap4.2259e-10, complementarity6.9902e-11,10outer/3083evaluations. Both experiments remain unadopted. A local final-probe heuristic does not resolve repeated activation stiffness. Next numerical design should model the unilateral PHR activation during step construction, with explicit factor/evaluation bounds, independent small active-set cases and this unchanged capture as RED. No third heuristic or tolerance/work-budget increase.

After all source-bound probes reached terminal and their source audits passed, adopted only the independently reviewed guard bounds cache from ld6q6z71 into canonical contact_guard.h. This is a mechanically identical performance change, not a solver correction: same min/max arithmetic/order, margins, pair traversal, counters and work limits. Guard, coupled DLL and isolated Godot extension rebuilds are terminal0; canonical110suite passes145.607s (contended, not a benchmark). Fresh bridge cie4a592 and actual-capsule mm1db2up both qualify with completed imports/runtimes and unchanged source/artifact hashes. Focused guard28passes. Numerical Armijo code remains unchanged. All current build/test/probe jobs are terminal. Do not rerun the full prefix merely for this culling-cache change; saved264convergence gate remains RED.

### Next numerical investigation: bounded unilateral step model

Use the saved request, not another full prefix. The current Newton matrix is the
local Hessian of the PHR merit only for the currently active contacts. Investigate
the same local model with its activation retained explicitly:
`m(d)=force·d+.5*d'*(H_L+D)*d+sum(phi(g+J*d)-phi(g))`, where
`phi(s)=(max(0,dual-rho*s)^2-dual^2)/(2*rho)` and `D` is the existing
scaled diagonal numerical damping. At zero this has exactly the current physical
gradient and active Hessian; it predicts newly active constraints without applying
any extra force to the accepted physical state.

An isolated working-set prototype may retain regular inactive geometry rows,
solve the sparse model, recompute the predicted active set, and use the same
12factorization-attempt bound. Work-set convergence alone never qualifies a step:
require a finite negative original gradient slope and the unchanged actual
32probe Armijo/interval test. Final KKT, curvature and atomic publication gates
stay unchanged. A model cycle, inconclusive gradient or exhausted work must
reject/fall back explicitly; do not invent gradients for ambiguous geometry.
The nonconvex elastic/contact Hessian and damping selection need particular
review; SPD of one working-set matrix does not prove global model convexity.

Before adoption, use independent small problems with a currently inactive plane
that activates during the step, release of an active plane, simultaneous opposing
contacts, shared/prescribed vertices, ambiguous geometry, working-set cycling and
budget exhaustion. The complete captured request must then pass independent KKT
and unchanged engine replay/continuous guards. This is a proposed investigation,
not an implemented or qualified solver. Full tissue-face anatomy, corneal wounds,
actual pointer incision/tearing, optics/assets, realtime and delivery remain.

Read-only model review adds mandatory implementation requirements:

- `force` is the material/inertial gradient State.force, not State.gradient.
  With working set A the RHS is `-force+J_A'*(dual_A-rho*g_A)`; changing A
  changes this affine RHS as well as the matrix.
- Keep all-regular inactive geometry rows in a separate matrix. Existing
  State.jacobian and final curvature must retain only the current positive
  updated_dual rows. Otherwise inactive normals could conceal an unstable
  feasible tangent direction and falsely qualify a saddle.
- Freeze H_L and the scaled damping matrix for one model. A damping change
  reconstructs the model consistently. Working-set changes, damping retries and
  any fallback share one aggregate12factorization-attempt counter.
- Require finite linear/model residuals, active-set consistency and a model
  decrease computed without cancellation. A single working-set SPD test does
  not establish global convexity. Actual Armijo and final physical gates remain.
- Add a stationary compressed saddle with strictly inactive contact normals
  spanning its unstable mode; it must still fail the unchanged final screen.

Guard-cache change is committed1ae4c31; failure provenance/gate is2afb082.
Current canonical solver/Armijo remains unchanged. No live jobs or unresolved
review messages remain. Next work is the bounded unilateral-model RED tests and
isolated prototype, followed by the existing captured request; no full-prefix
rerun or default/release promotion is justified yet.

## 2026-10-29 — unilateral model implementation and isolated qualification

Previous goal turn made authoritative progress: failure capture/convergence gate
2afb082 and reviewed guard-cache optimization1ae4c31, with canonical110native and
fresh engine checks. Current work adds a test-only bounded local PHR helper in
native/contact_step_model.h, test probe/build tool and independent model tests.
The product membrane_contact_solver.h is still unchanged. Initial RED was the
missing helper; analytical activation/release/coupled-coordinate/ambiguity/budget
tests then passed. Forty small convex problems also match an independent
exhaustive active-set oracle. An actual stationary compressed saddle surrounded
by strictly inactive anatomical normals still rejects5 in the existing DLL.

First frozen integrated prototype r9agif66 passes the unchanged joint_anatomy264
request: force6.511627379e-9, gap8.674844176e-12, complementarity2.966849672e-12,
31outer/654evaluations/468inner/610factors. Separate KKT/energy recomputation
qualifies the result (force6.511627379e-9, gap8.674843829e-12); this is one
selected-time solve, not continuous acceptance. All-regular rows are stored
separately; final curvature still uses only the original active Jacobian.

Review found two reporting/hardening issues: nearest conversion did not preserve
the reported interval upper bound, and residual norms lacked finite checks.
Observed independent80digit reported-bound test RED, then changed to
merit::upper_double and explicit finite numerator/denominator guards. Added force
norm overflow coverage. These changes do not loosen physical acceptance.

First integrated122suite had6failures on deep planes/arc and saved265, so no
adoption. A scalar released working set exposed negative H_L and repeated resets
spent two factors per damping level. A RED local case reproduced12attempt
exhaustion; retaining the working set on a failed SPD factorization fixed simple
planes/arc, but exposed deep simultaneous contact failure. That local case was
also RED. Coercive damping now selects an existing power10 coefficient only
after an SPD failure, with outward interval proof of strict positive diagonal
dominance of frozen H_L+D. This model property does not replace the physical
final screen. Matrix reconstruction retains the working set and clears cycle
history; scalar coefficient growth is bounded320 and all factorizations still
share12attempts. Read-only review found no defect in the proof or retry logic.

All15local model tests pass, including the exhaustive oracle and independent
reported interval bound. Second frozen prototype gz_ql0sq retained the264pass,
but focused regression still rejected the deep simultaneous case and saved265.
Third frozen18gxy2es includes certified model convexification; focused tests now
pass all small anatomical/arc cases. Saved265 and the264capture are still live
in sessions1956 and9857 respectively. Preserve these handles and hash-bound
canonical native/helper sources until terminal. Do not adopt from one capture
alone; require all regressions, independent KKT, fresh engine checks, then saved
failed-step replay and actual complete extraction. Full objective remains active.

### Updated isolated results and current state

The third18gxy2es experiment is terminal and unadopted: exact264exhausts100outer
(force.33968), and saved265exhausts100outer/rho1e12. Global model convexification
is too conservative in these large cases despite the small tests passing.
After explicit architecture review, separated a direction proposal from an exact
auxiliary-model solution. A released contact's hinge penalty is no larger than
its old active quadratic extension, so a certified full-model descent direction
can be useful without working-set convergence. New activation still requires the
complete modeled change to decrease. Actual Armijo, physical KKT and curvature
are always authoritative; internal6means descent proposal, not model convergence.

Unavailable inactive gradients must not be invented or treated as actual future
collision evidence. The proposal helper now filters those auxiliary rows only,
requires their current multiplier to be zero, and reports internal7for a
supported-part proposal. It does not claim complete-model descent. The full
nonlinear evaluator still inspects every actual trial contact and rejects active
ambiguity/nonfinite gradients; continuous guards and final active Jacobian stay
unchanged. Exact-mode model tests reject unavailable rows. Read-only review
confirmed these distinctions preserve the prior inactive semantics.

Frozen proposal veriwyi9 passes264force8.812482522e-9/gap8.674960750e-12/
complementarity2.966889666e-12; saved265rejected a forecast ambiguous gradient.
Supported-part prototype qgpfd9m0 retains the264pass, independently verified
force8.812482522e-9, gap8.674960056e-12 and energy2.477775732e-7. Its full135suite
passes134; saved265alone rejects2at outer11with local-model work exhaustion.
Do not adopt this integrated prototype or erase that failure.

Review exposed three real static-domain regressions in the optional model:
overflow from averaging finite equal H_L entries, an unusable inactive normalized
Jacobian, and a negative overflowing dual-rho*g that the physical evaluator
correctly clips to zero reaction. Old canonical static solver passes the added
reproducers; early frozen model versions fail them. Safe half-scaled averaging
preserves equal coefficients exactly, unavailable inactive gradients are filtered,
and provably negative overflow is marked unmodelled/inactive (positive overflow
still rejects). Independent reported interval-bound and norm hardening remain.
All24local model tests pass, including40exhaustive convex oracle cases. The
canonical full suite in session82773is live; it uses the OLD product core plus
the NEW separate test component, so passing it will not qualify integration.

Instrumented exact legacy265request replay8427nk1k captures the failing local
input as failed_model.bin:2124free coordinates,5544constraints,34398H_L entries,
18207model-J entries,3active constraints and43unavailable inactive rows.
At outer11inner1 helper uses12factors/7restarts and fails; actual gradient norm
9.4219465635. Independent SciPy reconstruction equals the captured actual
gradient exactly at this state, so gradient anchoring is not an established cause.
No full extraction prefix rerun. Local pure-model replay7swtviri/session89882
is running after a diagnostic-only namespace compile fix; it prints factor/set
progress and modeled change along the original Newton ray. Inspect that evidence
before changing the algorithm. A bounded, interval-certified ray scaling fallback
is under read-only review, not implemented. Preserve the live session.

Canonical membrane_contact_solver.h remains unchanged (SHA3358b1a2…); neither new
model nor any trial integration is installed in the product/default backend.
Before eventual adoption register contact_step_model.h in BOTH coupled build
source provenance and extension provenance/cache keys, rerun all integrated
regressions and independent capture, rebuild/fresh-import engine checks, and
replay the saved failed outer timestep with the NEW extension before a new full
prefix. Corneal shell/wounds, whole tissue-face anatomy, actual pointer incision/
tearing, appearance, realtime, GPU and Windows delivery remain in the full goal.

### 2026-10-29 continuation: preserve a checked Newton seed

Canonical old-core plus separate model suite82773 terminated0:138tests pass
in172.418s. This did not qualify experimental integration. Local replay89882
also terminated0. It locates the first valid initial-set damped Newton seed at
damping.001, slope-9.233100394e-5, norm.101257131. Its full modeled change is
positive514970.24; the represented1/256ray already has negative supported-model
change-3.1181565e-7. Subsequent working sets expand3to611to669and exhaust the
aggregate12factors. There is no evidence that a second nonlinear search or a
looser physical gate is needed.

Read-only architecture review approves retaining the first finite residual-checked
negative-slope initial-set seed, proposal mode only, only on budget exhaustion.
Internal8means raw seed, change_upper=+infinity, with that seed's linear residual.
It makes no model-decrease or convergence claim. Fatal input/current-active
geometry returns cannot reach it. Caller must recheck the actual physical slope
and run exactly one original32trial nonlinear search, retaining final KKT,
curvature, continuous guards and atomic publication. No added factor budget.

Observed RED: the new exhausted-budget proposal test returned1instead of8.
After implementation,26local tests pass, including the zero-budget/no-seed case
and the existing independent40convex cases/outward Decimal bound. Frozen
integration experiment j3lig_49/session14837 is live. It adds internal8to accepted
direction statuses, with every physical acceptance gate unchanged. Do not adopt
until exact264, saved265, all regressions and independent KKT have been checked.

Frozen j3lig_49 now terminal0. Exact264retains independent force8.81248252169605e-9,
gap8.674960055854442e-12, complementarity2.966889666422271e-12 and
energy2.477775732351442e-7. Full140regressions pass in336.902s, including legacy265.
DLL SHAefb07eea88271b8403855752bdc6059387a4f898ce555449626cb560d6e0b469.
Read-only final source review finds no actionable defect and confirms the raw
seed contract, single line search, unchanged active final curvature/publication.

Adopted the exact frozen membrane header SHA d355bd9a9f99d6cdb1c3e18c8dbc34e09a432f31ad1a78efd360cd416d8e1c70
into canonical optional core; registered contact_step_model.h in coupled/extension
provenance and extension native-object cache keys. Both builds terminate0;
extension compiles/caches65TUs. Canonical full native16429, heavy capture77630,
fresh bridge3758and actual coupled capsule37704are live; preserve their handles
and all bound sources until terminal. Default application backend/release is
unchanged. No new complete extraction prefix yet.

Fresh canonical artifacts bind the new model header: coupled DLL
ead69a737d55070554ca78a56b35fd7d2aa0a65ed2a3355921399732bd1e3402;
extension7ae81204f42cc04fedcd194302b2b2c40f821e05e37d5a66e24febe1c1e2bd01.
Source/manifest identities verified after builds. Fresh minimal bridge vu4akqs9
terminates0/qualified, both import and runtime stages pass with unchanged hashes.
Actual capsule dtepwcp6/37704, full native16429and heavy capture77630remain live.

Canonical full native16429terminates0:140tests pass in285.473s. Explicit heavy
capture77630also terminates0/qualified with the same independent264values above.
The new source-bound extension is being used by saved outer-step replay
km0ox2ou/session19386, copied from historical ttc652cp. All copied canonical
scripts must match the historical checkpoint; the script verifies current build
sources, original checkpoint inputs and frozen replay inputs before/after. It
replaces only the old DLL and returns nonzero on nonempty native_failure. Actual
capsule37704and saved outer-step19386remain live. No fresh full prefix yet.

Actual coupled capsule dtepwcp6/37704terminates0/qualified: fresh import and
runtime pass,0failures, all bound inputs unchanged. Its real incision, packed64
traction/history, physical saved requests, anatomical rejection and rollback
checks pass with the rebuilt extension. Only saved whole outer-step19386remains
live; it has reached call29and continues the original tool-time refinements.
This is scoped numerical/integration progress, not complete extraction or app
qualification. Preserve this live replay and its exact DLL/scripts.

Saved outer-step km0ox2ou/19386terminates0:52calls, native_failure empty,
integration_steps264, initial/retained rest area5.31932634674013, zero cut loss,
broken edges and accepted body uncertainty. First anatomy request38passes,
continuous scan identifies second tissue vertex670; combined constraints663/670
pass at call45and all final tool/anatomy guards46–52return0. The replayed request
differs from old capture only in initial/previous/predicted coordinates (maximum
4.216e-10), due to the newly solved preceding substep; no tolerance/material/
history replacement. Source/checkpoint/probe hash audits all pass.

Exported saved call45's packed64result with Godot, without rerunning mechanics.
Independent KKT recomputation qualifies force4.776136828607631e-9,
gap1.1201699290364076e-12, complementarity3.8342466431432986e-13,
energy2.4849586556424434e-7. qualified_step.json binds summary/log/replay proof/
independent result and checks material conservation, finite state, advancement,
zero uncertainty/fracture and final guards. replay_proof.json SHA
f51e32f70905842583caefe5c85be6f4c1b6e39d431e3d5951558bd22f5ee887.

This repairs the saved whole timestep, not the whole surgery. One justified new
complete extraction prefix is now live: uvp7et92/session76433on c70f532 sources
and extension7ae81204… . Import has completed and actual extraction runtime has
started. Preserve that handle and ALL bound native/Godot sources until terminal;
do not restart on observation timeout or launch another prefix. Default backend,
real-time behavior, appearance and Windows release remain unqualified.

Full uvp7et92/76433is now terminal1/unqualified. Fresh import passes; runtime
accepts264ticks, then265rejects native_joint_solve status1at100outer iterations.
Stats: energy1.04255175e-6, force3.29753427e-6, gap~1e-14,
complementarity~4e-14, evaluations3205, penalty223645.801040861,
inner3029/factors3193. All physical acceptance gates and work limits remain.
Outer rollback retains area5.31932634674013, zero cut loss/broken edges/accepted
uncertainty, integration_steps264. This is a new consistent-history failure,
not the historical penetrating265state. Exact checkpoint is preserved under
uvp7et92/rejected-extraction-step.bin; log SHA
66d705a743e989d6bd483728c024a7b183c63591dd9f95302e216aee05d42b1e.
All bound source/checkpoint audits passed. No process from that prefix remains
live; do not rerun it until a saved-state repair is verified. Extract the failing
anatomy request from its checkpoint with a capture-only stop before the expensive
anatomy solve, explicitly distinguished from numerical reproduction.

Capture-only bwkezn0x/39003terminates1with deliberate sentinel-98at request16;
its prior real solves/guards pass. Preserved request as joint_anatomy265.json,
SHAf3667fb46cebc4e8e084503056c58d2a86dc262f642e7a342173843067baf881,
with sibling provenance Markdown. Actual standalone instrumented h8bdirmj/1770
terminates0diagnostic, reproducing solve1/outer100force5.439475852737881e-6.
Different compile/arithmetic trajectories produce different final statistics,
so this is not a bitwise extension reproduction. Actual outputs remain atomic.
It captures the terminal local model without changing accepted mechanics.

Pure linear analysis finds active-penalty diagonal scale2.794826e10versus
H_L diagonal225.57. At initial1e-8damping, the former leaves linearized-gradient
norm2.012e-6and direction norm5.09e-8; H_L-only diagnostic scale gives direction
.00040646and linearized-gradient1.97e-10. Gradient reconstruction difference
5.26e-18rules out a large anchoring error at this terminal state. These are LU
diagnostics without SPD/nonlinear certification. No metric change is adopted.
Read-only review is considering a proposal-only physical/Lagrangian metric as
an isolated next experiment versus a structured solve for normal-equation
conditioning. All numerical/build/replay jobs are terminal; review remains.
