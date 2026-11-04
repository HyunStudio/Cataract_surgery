# Embedded forceps attachment and contact plan

Execute inline in the existing isolated worktree. User authorizes continuous
implementation; no design/permission questions. Full original simulator goal
persists, including actual tool/input/GPU/release qualification.

## Current basis

Native/Godot implicit state integration now passes a real retained curved flap
force/recut case (35steps,129incisions, exact retained mass, independent force
gate1e-8). This uses prescribed point force, not actual instrument grasp/body
contact. Default GS still rejects a continuous blade route at mass resolution.
Partial interior cracks cannot yet open in the current support-star basis.

## Next deliverable: actual held material point

Use the canonical fine-point map `p=Bq`, with at most3 original controls per
material point. Add exact linear equalities `Bq=target` for up to2 held points
(6 scalar constraints). Keep the current unconstrained ABI and bridge working.
Do not emulate an exact hold by an enormous external explicit spring or by
discarding tissue. Actual coarse masses/inertia remain in the objective.

Files: native/membrane_fem.cpp/.h, new constrained-core tests, bridge and
embedded_membrane.gd, native engine grip tests and build/qualification manifests.

1. RED: a fine-point attachment moves the true embedded material point, including
   an interior barycentric point, to within1e-9 of its target. Native original
   force balance including attachment reactions must remain<=1e-8. Test two
   distinct grips, fixed rim, conflicting/rank-deficient targets, bad shapes,
   work exhaustion and atomic failure. Preserve the unconstrained8-test contract.
2. Solve constrained Newton directions with sparse primal factors and a small
   Schur complement. For stable factors use `H+rho*A^T*A` with the corresponding
   normal RHS correction; this does not change directions on the feasible
   tangent or the physical objective. Levenberg damping changes directions only.
   Final positive augmented curvature certifies the original Hessian on kerA;
   final KKT force and equality gap are independently recomputed. Bound all
   retries/iterations, no unverified fallback or gap/force tolerance relaxation.
3. Start from a certified feasible inertial projection onto held targets, or
   reject if undefined. Keep accepted line iterates feasible; no unchecked
   post-solve projection. Release retains existing velocity/history.
4. Store grasp identity by held material vertex AND source attachment face.
   Cutting into two equally valid banks releases that severed attachment, as
   the existing capsule transfer does. Remap unique surviving attachment and
   target histories transactionally; never pick an arbitrary new bank.
5. Real Godot case: acquire a retained curved flap point, move its target in
   bounded increments including the existing0.005small-traction scenario,
   verify exact material motion/reactions/no area deletion, then release/recut.
   Still not a whole operator case until forceps body and anatomy are coupled.

## Required contact boundary

Each fine triangle belongs to one original material basis, so its three vertex
positions are an affine map of that cell's three controls. Transform true fine
triangle distance gradients/Hessians through that map; do not substitute the
whole virtual triangle, which includes absent cut material. Preserve fine-tool
and anatomy continuous guards, gap1e-9 and complementarity1e-11.

Use transferred double material bindings, or independently certify remap motion,
before treating a cut publication as a contact-safe transition. Current float
publication tolerance is not a gap certificate. Handle actual blade bevel/shaft
and jaw contact regions consistently with rendered geometry; do not arbitrarily
widen instrument profiles to pass contact. Complete partial-tip enrichment or
controlled support refinement before claiming a real puncture can open/tear.

Final work remains the full mouse/keyboard preparation-to-review case, coupled
fluid/material/IOL/wound behavior, professional3D view, active GPU throughput and
Windows delivery. None is waived by a local constrained-core test passing.

## Execution ledger

- Previous turn progress:59613f1 connected actual native implicit histories and
 28engine suites/35real force ticks. Same complete goal active, no blocker.
- Added bounded native exact attachments via sparse primal+smallSchur system,
 actual mass projection and independent Gram KKT reactions. Missing CABI RED.
 Build55059 terminal0: original8tests pass, first6grasp tests have1failure.
- Failure is normal-roundoff work, not a force-tolerance defect: R∞3.8349e-8,
 g·delta=+1.2463e-17 vs tangentR·delta=-4.9258e-18, withAδ≈2.04e-18 andreaction
8.53. Fixed-dual Lagrangian line comparison removes normal-work roundoff while
 retaining original objective on feasible motion and unchanged final force,
 gap and constrained-curvature gates. Second build64046 terminal0;6grasp tests
 pass. Added unheld-negative-tangent case; total15native tests pass, old
 unconstrained zero-grip results/statistics bitwise unchanged.
- New typed solve_grasp_fem bridge missing-method RED, extensionbuild78424 ends0.
 Fresh bridge-only probe72683 passes4stages. Material/source-face acquisition,
 accepted target/reaction commit and cut/release/remap contract initially1RED
 then0. All additions remain optional; no default simulator backend promotion.
- Real frozen6stage probe6676 (fem-extension-5d6a8xbt) terminates0: all existing
 bridge checks, old35step dynamics, new grasp bridge and17step actual attachments.
 Uses fine point217 of free flap, weights[.5985469049067181,.40145309509328186].
 One-hand10*.005 motion, release without velocity reset, two-hand5*.005 motion,
 recut while uniquely held and continuation. Mass5.319326346740127,events129,
 force8.0332485973e-9/gap1.1102230246e-16. No actual tool-body/anatomy contact.
- Latest source-bound native qualification91c620 passes15tests.29source-frozen
 Godot suites13170 terminate0 with no changes/errors/leaks. Reports preserved
 under docs/assets: fem-grasp-core-validation-2026-11-04.json,
 embedded-grasp-validation-2026-11-04.json, embedded-grasp-regression-2026-11-04.json.
- Read-only reviewer independently reran15native tests and found no actionable
 issue in math, type/pointer bounds, staged targets/reactions or cut face identity.
 All started jobs terminal. No main integration, default change, push or release.

Next: transform exact fine-face/body distance derivatives through the actual
original-material map, then couple grasp reactions and unilateral contact in
one original-force solve with full continuous guards. Do not use the virtual
coarse triangle as a collider over absent cut material. Certify all inequalities
and retain force1e-8/gap1e-9/complementarity1e-11; do not fix contact rank issues
by widening tools or changing acceptance. Inspect actual geometry/constraints.
Preserve precise bindings or verify cut-remap motion, address partial-tip support,
connect real instrument/controller acquisition and only then qualify the full
mouse/keyboard surgical sequence, active GPU and Windows delivery.

Actual acquisition must use a certified jaw/fine-face contact point and material
barycentric identity, not just the legacy nearest-vertex sphere. The present
vertex+source-face API proves a kinematic primitive; extend it to a continuous
face point or a conservative inserted material marker before controller use.
Preserve unique bank identity through cuts and release genuinely severed holds.
Account for real jaw/blade orientation (including required tool roll) throughout
renderer, pose interpolation and collision; do not rotate only the visual mesh.
