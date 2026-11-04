# Material source edge insertion

Continue fromc634b07, classified as progress. Finite original-material inertia
and held-contact stabilization passed203 native tests;39 focused engine suites
passed. Same actual operative path reached122 accepted ticks, then rejected an
incorrect near-collinear triangle during insertion. Full surgery remains open.

Use `operative-blade-winding.bin`, not a repeated whole operative prefix, for
the first RED/GREEN cycle. New point1018 is bound to source edge1009--967, but
display-nearest edge selection creates triangle[1018,1009,967]. Its material
area is zero up to roundoff. The unchanged winding gate correctly rejects it.

Choose a local subedge by original material edge identity and normalized scalar
parameter when the inserted point is source-edge-bound. Both candidate endpoints
must belong to that same material feature and bracket the point. Construct each
segment midpoint as a double convex combination of normalized endpoint bindings,
then insert it on their known connecting edge. All interpolation consumers must
use that same canonical coefficient field; old Vector3 bindings remain supported.
Preserve finite face-interior slit banks. No source point movement, welding,
tissue deletion, tolerance widening or orientation bypass.

1. Add failing exact fixture test requiring strict geometric partition and actual
   embedded cut, retaining total mass, original control history and topology.
2. Implement feature-based local subedge choice. Exercise original edge split,
   subdivided edge, opposite traversal and near competing display edge. Preserve
   finite interior slit and historical thin geometry/material contracts.
3. Run focused cut and original-material suites; independently review the change.
4. Source-frozen40 suites and same real native guarded16-stage operative path.
   Capture any next genuine failure exactly. No default backend promotion or
   complete operation claim unless original full goal evidence exists.

## Binding interface

Bindings still carry `ids:Vector3i` and the compatibility `weights:Vector3`.
New canonical midpoint bindings additionally carry `weights64:PackedFloat64Array`
of length3. Physical interpolation uses this field when present and normalizes
its scalar-double sum, otherwise normalizes the existing Vector3 coefficients.
`Precision.binding_weights` selects the raw canonical coefficient representation;
it does not independently refit coordinates. Consumers must not mix the rounded
compatibility midpoint weights with canonical position/history/material transfer.

## Execution ledger

- Exact122tick fixture reproduced two RED failures: cutter subdivision winding
  and rejected embedded incision. Material source-edge selection corrected that
  boundary insertion, exposing a second bad triangle from the reprojected interior
  midpoint in the same patch. This refined the next action; it was not a full fix.
- Removing the midpoint let that fixture pass, but a new isolated single-face
  slit regression was RED: both tips inside a face need an interior node to retain
  two separate geometric banks. The removal experiment was discarded. Geometry
  was not simplified at the expense of the requested incision behavior.
- Canonical midpoint `weights64` now composes normalized endpoint bindings.
  Its forced edge follows from inserting those endpoints into the same triangle
  first. Precision.transfer, Refinement.blend/flag and embedded material pullback
  consume the same coefficient field. Existing Vector3-only fixtures use their
  prior normalized fallback. No native numerical code changed this turn.
- Exact cutter and embedded incision GREEN; parent partitions and total mass
  remain complete, and original control position/history values remain exact.
  Refined source edge and reversed traversal cases GREEN. Single-face internal
  slit retains two interior geometric banks. This does NOT resolve original-cell
  partial-crack-tip enrichment or prove physical opening under traction.
- Historical thin case that previously had negative affine midpoint fractions
  is now strictly valid with positive complete material partitions. Its old
  expected rejection was replaced by that stronger valid-partition requirement.
- The independent accepted-double transfer oracle initially reported2.65e-8
  while reading only the compatibility Vector3 weights. It now explicitly reads
  canonical64 coefficients when supplied, without calling product helpers or
  loosening tolerance. Position and history errors are both0 in both cut cases.
- Independent read-only review found no important defect. Runtime/source-frozen
  results remain separate evidence, not inferred from static review.
- Remotec634b07 Tests41865775554 succeeded; Godot41865775527 failed at the known
  default volumetric continuous blade encounter before detaching a flap. This is
  not waived by the optional retained-material tests. Native41865775600 completed
  successfully atc634b07, including the Windows native numerical qualification.
- First frozen run3ltd98dk passed40/40 focused suites. Native run_lof3nsk
  passed15/16 stages: live blade crossed the122tick failure and reached135
  accepted physical ticks/144 staged cut events, then rejected material_partition.
  [First operative log](../../assets/material-edge-first-operative-2026-11-05.txt).
- Exact new fixture `operative-blade-partition.bin` exposed an interior point
  misclassified as a boundary point by display proximity. It did NOT come from
  the small-triangle skip threshold. Parent1355 had material area4.2810e-5 and
  retained fraction0.9999776157585039; point1501 had source weights
  [.9997095386,.0002680772,.00002238424], while the chosen boundary edge's
  endpoint weights were[1,0,0] and[0,1,0]. Its missing fraction exactly matches
  the nonzero third coordinate2.238424149614622e-5.
  [Partition evidence](../../assets/material-edge-partition-evidence-2026-11-05.json),
  [chosen-edge witness](../../assets/material-edge-choice-evidence-2026-11-05.json).
- A broader material-collinearity/containment candidate fixed this fixture but
  regressed the existing curved retained-circle cut2 (`subdivision_winding`).
  Frozen449f4owq andba1m_zsd correctly failed their operative/native setup stages.
  The broad candidate was discarded. Existing internal fan insertion and its
  display containment tolerance were restored; no tolerance was widened.
- Final targeted rule: an interior three-support point cannot split a source
  boundary subedge whose two endpoints share a zero barycentric coordinate.
  That is exactly the one-sided insertion that omitted the positive third-coordinate
  material region. Internal fan edges retain both incident faces and their existing
  final winding/partition checks. Source-edge points still use material feature and
  strict scalar bracketing; canonical midpoint insertion is unchanged.
- Exact135tick RED fixture is now GREEN, as are the original122tick case and the
  retained curved circle. An analytic interior point1e-7 from a display boundary
  still creates all3 faces, preserving its positive material portion. Follow-up
  independent read-only review found no important defect in the targeted predicate.

## Final qualification and next physical failure

- Frozenwvxw0kaw passed40/40 focused suites plus import, exit0.
  [Regression evidence](../../assets/material-edge-regressions-2026-11-05.json).
- Frozenbaxiyzao passed15/16 actual native stages. The live operative route now
  passes the former cut partition failure, accepts143 physical ticks, then rejects
  the next candidate because the actual recorded tool path intersects tissue at
  mid-time. `qualified=false`, exit1; this is not a full operative clearance.
  [Engine evidence](../../assets/material-edge-engine-validation-2026-11-05.json),
  [operative log](../../assets/material-edge-final-operative-2026-11-05.txt).
- A separate diagnostic subclass added transparent backend/guard wrappers to that
  SAME frozen project, with all original frozen input hashes verified unchanged.
  It reproduced the same failure and saved the exact FEM and guard requests plus
  owned pre-solve state. No native or product file was changed for this capture.
  [Capture provenance](../../assets/operative-motion144-capture-2026-11-05.json).
- `operative_motion144.json` and `operative-motion144-state.bin` retain the exact
  next problem. Native endpoint replay is bitwise identical and passes independent
  physical KKT; native whole-interval guard matches the recorded rejection exactly.
  Independent Decimal distance confirms positive endpoint gaps but negative gap
  -1.9805e-4 at t=.5. The guard is correct and remains unchanged.
  [Independent replay](../../assets/operative-motion144-replay-2026-11-05.json).
- Two numerical regressions preserve this distinction: endpoint equilibrium is
  valid, while accepting the complete motion would be invalid. Final expanded
  numerical qualification passed205/205 tests across16 suites/nine native
  artifacts, exit0. No native implementation changed in this turn.
  [Source-bound numerical evidence](../../assets/material-edge-numerical-validation-2026-11-05.json).
- Windows native CI now also runs the focused40-suite engine validator and uploads
  its report/logs. The distinct default Godot whole-case failure remains visible;
  focused qualification does not replace or waive it.
- Next implementation: [time-weighted original-material contact](2026-11-05-fem-trajectory-contact.md).
  Finite-jaw acquisition, partial-tip mechanics, anatomy response, full actual
  input cases, real-time performance and Windows release remain unfinished.
