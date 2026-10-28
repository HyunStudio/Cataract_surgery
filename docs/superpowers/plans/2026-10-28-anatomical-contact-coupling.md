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
