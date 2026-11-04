# Embedded membrane support implementation plan

Use executing-plans inline; no new design questions (user opted into autonomous
completion). Reuse isolated feat/geometric-blade worktree, HEADd20fb1d.

Previous turn is progress: real blade geometry, finite incision transactions,
14 focused suites and GPU puncture evidence committed. Full goal stays active.
No live job remains. Continuous closed route remains RED, not a release gate pass.

## Evidence and decision

Repeated cuts create tiny attached triangles, not isolated debris. A node's
lumped rest area1.084e-13 violates the existing inverse-mass cap1e12. A frozen
16-float32-roundoff vertex snap trial still rejects mass_resolution; not adopted.
Do not delete material, clamp mass, raise the cap or alter tear/force tolerances.

Separate exact fine cut topology from a well-shaped original material basis.
Each original vertex gets one virtual copy per connected part of its incident
material star. Fine faces interpolate their three coarse virtual controls in
their original rest triangle. Fine-edge identity determines connectivity;
coincident crack banks must never reconnect by spatial proximity. Integrate
real material area against the original linear basis for mass and future strain
energy. This is an engineering implementation motivated by the virtual-node
literature; it is not clinical tissue calibration or a claim to reproduce an
entire paper. Partial cuts below a support star's scale may need local refinement
or enrichment; qualify that explicitly before default use.

Primary references:
- https://graphics.cs.wisc.edu/Papers/2007/SDF07/ (arbitrary embedded cuts)
- https://physbam.stanford.edu/~fedkiw/papers/stanford2004-01.pdf (virtual nodes)
- https://pmc.ncbi.nlm.nih.gov/articles/PMC8133368/ (progressive-cut limitations)

## Tasks
1. New membrane_support.gd + test_membrane_support.gd: RED missing module; map
   fine material faces to original affine bases; partition support stars across
   actual fine-edge topology. Positive mass integration, no mass clamp. Verify
   uncropped patch, actual cut, coincident banks, rigid/affine motion, area/mass/
   first moments, malformed input and output budgets. This module alone does
   not replace the accepted physical backend.
2. capsule_solver.gd: retain immutable original material rest mesh and face
   ancestors through refinement/removal/rollback/reset. Export a support build
   for current fine topology; tests prove lineage and transaction preservation.
3. Freeze actual mass-resolution failure with lineage. Compare fine vs virtual
   support distributions and embedding reconstruction; characterize partial
   crack continuity instead of assuming the method solves all cut behavior.
4. Implement objective membrane energy and consistent operator/contact mapping
   in the coarse basis; meaningful derivative/objectivity and real cut/traction
   tests. Native strict convergence/continuous guards remain unchanged.
5. Qualify closed incision, forceps tear/grasp/extraction, full operator case,
   active GPU throughput and Windows delivery. Do not promote an unqualified
   optional/support-only implementation to default or call the goal complete.

## Execution ledger

- Task1 module existence RED->GREEN; actual capsule lineage API1RED->GREEN.
  Original face ancestry is retained in _face_material/_material_ids and the
  immutable _material_rest/_material_indices. Reset/refinement/whole checkpoint
  restoration are tested. Existing physical time integration remains unchanged.
- prepare() extracts the previous material geometry/history/area transfer.
  transfer() still enforces the same1e12 fine-node inverse-mass cap. No new
  discretization is automatically used when the old mechanical state rejects.
- Rounded shared coarse-edge fixture reproduced2failures: off-edge shape weights
  can disagree between neighboring original cells. Original feature ancestry
  intersection now determines exact edge/vertex interpolation; canonical
  per-point mappings are verified across every adjacent fine face. RED->0.
- Actual failure frozen in tests/fixtures/blade-material-resolution.bin,
  with lineage and no object handles. Actual unmodified closed route rejects
  mass_resolution in job32408. The separate support fixture passes:301 fine
  vertices/482faces,221 virtual controls, fine minimum mass1.0840033148863092e-13,
  virtual minimum mass3.632163119339842e-8, total5.319326346740126 unchanged.
  This is evidence for the representation, not an accepted physical time step.
- Added explicit partial-slit characterization: a slit wholly inside one coarse
  triangle still has3 shared controls. Enrichment or controlled support refinement
  remains REQUIRED before crack-opening qualification; do not ignore this limit.
- Added optional membrane_energy.gd with double scalar Neo-Hookean surface
  energy and analytic3x2-F gradient, integrated over retained real material area.
  Tests cover zero rest stress, coordinate finite differences, rigid-motion
  objectivity, force covariance, independently moving fully severed banks,
  material parameter validation and collapsed-cell barrier rejection. Missing
  module RED->GREEN. This is a new continuum law with unit test parameters,
  not an assertion of equivalence to the legacy edge-spring constitutive model.
  No time integrator, contact coupling, bending or clinical calibration is claimed.
- Frozen source-hashed23-suite job79275 terminates0, no source changed and no
  script error/leak, preserved in docs/assets/embedded-validation-2026-11-04.json.
  The known small-traction test_capsule_incision separately terminates1 with the
  same assertion atline83. test_blade_closed remains RED2. Full -Test is not green.
  Legacy extraction regression passes but explicitly reports coarse deletion
  cut loss1.7984; it cannot prove material-conserving complete operator surgery.
- Two read-only reviews found no additional high/medium correctness defect in
  lineage, material transfer, support continuity or elastic derivative. Both
  emphasized partial-slit and integration/contact limits. No integration to main.

## Next implementation boundary

Implement an explicit experimental embedded physical backend starting from its
own reset state. Do not silently project an accepted legacy deformed state into
this lower-dimensional basis. New cut-control copies must inherit matching old
original-control positions/velocities; test total mass/momentum and no cut impulse.
Use canonical point maps for geometry publication and the transpose map for tool
forces/contact Jacobians. Fine collision geometry and coarse DOFs must remain
consistent, including kinematic rim, grasp and partial-crack enrichment/refinement.
The strict native stopping/continuous-collision contracts remain unchanged.
GDScript energy is the independently testable reference; an efficient native
implementation with derivative comparison is needed before interactive claims.
Avoid another full-prefix expensive solve until each new candidate passes its
saved local fixture. Continue full original goal, not support-only completion.
