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
