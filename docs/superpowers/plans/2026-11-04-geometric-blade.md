# Geometric blade operation implementation plan

> **For agentic workers:** Use superpowers:executing-plans inline.

**Goal:** Actual rendered cutting edges sweep finite incision patches and retain
both material banks, replacing sphere-based face deletion in the dimensioned
operator path. This is part of full simulator completion, not its completion.
**Architecture:** Extend the verified membrane cutter with finite triangular
patch clipping, share blade shape/edge geometry between renderer and tool path,
and apply patch batches transactionally through capsule material transfer.
Keep legacy edition and strict native numerical acceptance contracts explicit.
**Tech Stack:** Pinned Godot4.7.2, GDScript, existing cut/refinement/pose modules.
**Spec:** PHYSICS_SIMULATOR_SCOPE_KO.md; REALISM_COMPLETION_KO.md; existing precise
operator integration and realtime completion plans.

## Global constraints
- Mouse/keyboard, Godot and continuous work are already authorized; no new design
  questions. Previous turn classified progress: authoritative3D code plus11suite
  and actual GPU evidence, integrated2c9b990. Goal active, no blocker.
- Cut material retains rest area/mass/history and original face/grasp identity.
- Only the actual sharp blade region cuts; shaft and stationary contact do not
  silently erase tissue. No predefined ideal circle or global deletion target.
- Native force/gap/curvature gates and work limits are not weakened. Geometric
  float32 tool/membrane representation remains an uncalibrated engineering model.
- No whole-case, active performance or Windows release claim from local tests.

## Review focus
- Finite triangle vs bounding-rectangle overcut, rotated and disconnected sheets.
- Coplanar sliding is contact with no unique transverse incision; leave material
  unchanged there. Old rectangular API retains its existing rejection behavior.
- Repeat strokes must not weld banks; endpoint/interior cracks preserve topology.
- Batch failure must not leave an earlier partial cut or stale input command.
- Renderer, cut edges and sampled tool poses must agree in both hands/review.

### Task1: Finite triangular incision patch
Files: membrane_cut.gd, test_membrane_cut_patch.gd.
- [x] Observe missing-API RED.
- [x] Add slice_triangle(points,indices,a,b,c,max_vertices,max_triangles) using the
      same subdivision/state bindings as slice, with exact finite convex clipping
      in its local plane and explicit coplanar-contact behavior.
- [x] Verify analytical patch intersection, triangle-AABB near miss, rotation,
      area/winding/provenance, repeat/disconnected topology and invalid budgets.

### Task2: Physical blade shape and swept sharp edges
Files: instrument_profile.gd, surgical_instrument.gd, new blade_sweep.gd and tests.
- [x] Define shared generic sharp-edge geometry matching the visible blade.
      Existing renderer is a simple prism; do not falsely call it a measured
      manufacturer keratome. If replacing its shape, define mesh and cut edges
      together, retain the existing conservative collision enclosure.
- [x] Generate bounded triangle patches from previous/current poses using the
      same quaternion path as the body renderer; stationary and nonblade paths
      produce no cuts, and angular subdivision is bounded and tested.

### Task3: Transactional model and operator integration
Files: capsule_solver.gd, simulator.gd, transaction/control tests.
- [x] Extract the existing geometric material transfer into one shared operation.
- [x] Apply finite patch batches with atomic rollback; preserve native packed64
      transfer, rest/history/mass and grasp material-face bindings.
- [x] Connect normal dimensioned blade input and disarm/failure handling; do not
      accidentally re-enable coarse cut=true face deletion after geometric cuts.
- [ ] Validate normal actual operator route, weak/noncontact/off-target blades,
      retained flap creation and subsequent grasp/withdrawal. Record remaining
      refined-elastic failure explicitly if still unresolved.

### Task4: Qualification and integration
- [ ] Focused cut/refinement/tool/control/transaction/app tests, GPU blade/cut
      capture and review, then integrate qualified change into primary checkout.
- [ ] Continue material-conserving physical tear dynamics, full actual input
      operation, active throughput/GPU and Windows delivery; keep goal active.

## Execution ledger
- Initial missing APIs and wiring observed RED, then finite patch / sharp-edge
  sweep / material transaction / operator transaction suites pass. The genuine
  prepared model accepts100 bounded target-motion ticks and2 incision events:
  217->245 vertices,396->426 triangles, retained area5.319326346740127 unchanged,
  cut loss0. This is synthetic target input, not a literal mouse full-case proof.
- Whole-surface AABB rejects distant strokes cheaply. Oversized distant patches
  initially produced2 failures; validate cutter extent limits before the skip,
  now0 failures. Existing thresholds are unchanged.
- Continuous closed route is RED. The first rejection was subdivision_winding.
  Its8936-byte input is frozen in tests/fixtures/blade-midpoint-edge-snap.bin.
  A true interior midpoint was incorrectly snapped to a nearby source edge in
  a thin wedge. Material edge membership now controls midpoint sharing, giving
  2RED->0 on the fixture plus analytical area/orientation/provenance assertions.
- The same continuous route now progresses to mass_resolution. Its failing
  subdivision has7 vertices with rest lumped area below1e-12, e.g. node276:
  1.0840e-13 / inverse mass9.2250640405549e12. Existing cap1e12 is untouched.
  Diagnostic graph traversal finds301 connected vertices with total geometric
  area5.31932634746281: these are tiny attached slivers, NOT an isolated fragment.
  No artificial tissue deletion, mass clamp, tear threshold or solver tolerance
  relaxation is adopted. Need conservative quality control/remeshing or a
  reasoned stable multiscale mechanical representation before qualification.
-14 focused suites pass (8 cut/tool/display plus6 transaction/control/body/clock).
  Actual NVIDIA RTX3070 Laptop GPU initial-puncture job33348 terminates0 and
  its1440x900 image was visually inspected. No active FPS/endurance claim.
- Read-only review found no additional proven high/medium issue, but correctly
  blocks qualification on ordinary continuous blade motion aborting. Keep this
  development branch unmerged until normal continuous incision is resolved.
- Clean final closed-route diagnostic job28df66 terminates1 with2 assertions;
  no script errors or leaked objects. This RED is intentionally included in the
  normal test runner; do not omit it to present the feature as passing.
- Goal remains active. Next work: preserve actual material quantities and both
  crack banks while preventing unresolved sliver DOFs; validate closed incision,
  forceps grasp/withdrawal, existing small-traction regression and full operation.
