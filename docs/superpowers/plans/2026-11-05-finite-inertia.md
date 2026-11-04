# Finite original-material inertia

Continue from3bd748c, classified as progress: optional operative mechanics,
strict material area,39 focused suites and13/14 native operative stages. The
same actual blade route rejects a finite positive8.5168e-13 support mass.

The native FEM API rejects inverse mass above1e12 before assembling any matrix.
That constant is an input envelope, not a demonstrated conditioning boundary.
For dt in[1e-6,.1], finite positive inverse values can yield finite positive
physical inertia well beyond it. Determine support with explicit reciprocal and
time-scaled inertia representability, retaining zero inverse only for fixed DOFs.
Never clamp mass, delete fragments, merge crack banks or relax force/gap/COMP.

1. RED native tests above the old envelope: independently checked nonlinear
   equilibrium with common physical mass/area scaling, mixed disconnected
   macro/micro material, exact grips and active/inactive unilateral contact.
   Scale test force tolerance with specimen mass to avoid an absolute tolerance
   falsely accepting an undeformed prediction. Preserve absolute operative gates.
2. Validate native finite-positive inertia input consistently in all three FEM
   entry points. Keep SPD curvature, original-system linear residual and physical
   KKT checks. Add diagonal equilibration only if actual conditioning evidence
   requires it; do not add numerical machinery speculatively.
3. GREEN native oracle checks, including invalid/overflow input and atomicity.
   Then update engine original support policy to the proven representability
   contract; keep the legacy fine-node backend unchanged.
4. Convert the exact failure fixture into positive topology/mass/history evidence
   and test its actual implicit native step. Run same frozen actual blade path
   to the next genuine failure, never skip its prefix or inject tool pose.
5. Source-bound numerical qualification, focused engine regressions, independent
   code review and evidence ledger before commit/push. No default promotion or
   full surgery claim without full input/anatomy/extraction/throughput evidence.

## Evidence ledger

- RED against old native DLL: scaled positive micro material and disconnected
  macro/micro equilibrium rejected before solving; exact grip and active/inactive
  contact similarly rejected. No mass modification was required by the equations.
- The existing native formula is retained bit-for-bit:1/(inverse*dt*dt). A shared
  input helper requires finite nonnegative inverse and finite positive resulting
  inertia for free DOFs. Zero remains the fixed-DOF convention. Overflowing,
  nonfinite, negative or unrepresentable input still rejects atomically.
- An additional contact-plus-nodal-hold regression failed even at1e6 inverse,
  inside the old envelope:250 exhausted iterations, force14.77, gap0.01857.
  Standalone grasp increased equality-normal augmentation on failed factors;
  coupled contact increased only whole-space damping. Increasing its hold_rho
  alongside retry damping restores equality-normal stabilization. Physical force,
  penetration, complementarity, SPD and linear residual gates remain unchanged.
  Held-inertia values1,1e6,1e12,1e13 now have equivalent physical minimizers
  (maximum observed coordinate difference6.4e-17) and independent KKT checks.
- Native component suites GREEN:11 FEM,8 grasp,16 coupled contact. Common
  mass/area scales1e-12,1e-13,1e-16 preserve the nonlinear minimizer with force
  tolerance scaled equally, not a loose absolute target accepting predictions.
  Disconnected macro/micro material remains distinct. Extreme finite inertia
  is checked only in a nonelastic diagonal case; this is not a guarantee that
  every extreme elastic system is well conditioned or solvable.
- Frozen numerical qualification:203 tests across16 suites/nine native artifacts
  passed, exit0. This includes existing saddle, unstable unheld tangent, derivative,
  interval, physical KKT, provenance and caller FP-context checks.
  [Source-bound numerical evidence](../../assets/finite-inertia-numerical-validation-2026-11-05.json).
- Engine exact112tick failure fixture first remained RED with the old engine
  cap; its finite-positive reciprocal policy then accepted the actual tiny mass,
  preserving exact original control position/history and material partition.
  Real native implicit continuation took4 iterations, independently measured
  force1.1693e-10, linear residual2.0909e-13, unchanged8.5168e-13 minimum mass.
  [Exact native step](../../assets/finite-inertia-exact-step-2026-11-05.txt).
  This isolated continuation has no surgical instrument contact and is not the
  same claim as the live guarded operative route, recorded separately below.
- Independent read-only review found no important defect. It did not substitute
  for the actual native and source-frozen engine runs.
- First operative15-stage run vht89zi6 passed14 stages, including exact native
  microfragment dynamics. The live route crossed the former mass failure and
  stopped instead at113 accepted ticks/55 staged incision events with input
  `degenerate_face`, work0. Exact state is `operative-blade-degenerate.bin`:
  687 points,850 faces, two current faces under the legacy1e-12 input threshold,
  minimum display area2.42344e-14, positive material area2.50199e-14 and minimum
  physical support mass1.09736e-15.
- Root cause was inconsistent geometric contracts: the cutter accepts positive
  output slivers of this size, then rejects them merely as next-cut input, even
  before determining whether the blade intersects them. Explicit material mode
  now requires finite positive source area, keeps the original elastic basis,
  and retains every winding/affine partition/manifold/seam/resolution check.
  Legacy source threshold remains unchanged. Exact strict cutter AND embedded
  incision replay changed RED to GREEN; truly zero-area input still rejects.
  Follow-up independent read-only review found no important defect.
- Final focused frozen run vfeu_kx5:39/39 suites plus import passed, exit0.
  [Focused evidence](../../assets/finite-inertia-regressions-2026-11-05.json).
- Final actual native run u3ka37k5:14/15 stages passed; the same live blade
  route now crosses both former failures. It accepts122 physical ticks and
  reaches91 staged incision events, then rejects `subdivision_winding` on a
  newly formed near-collinear triangle. Full route remains `qualified=false`,
  exit1. Neither physical acceptance gates nor tool waypoints were changed.
  [Operative evidence](../../assets/finite-inertia-engine-validation-2026-11-05.json).
- Exact next failure is preserved as `operative-blade-winding.bin` for subsequent
  implementation, not a passing regression. Its accepted state has1017 points,
  1194 triangles and minimum support mass1.09736e-15. Diagnostic insertion witness
  identifies source face869 [1011,1009,967], new triangle[1018,1009,967]. New
  vertex1018 has nonzero binding only to1009 and967, so this candidate lies
  on a source material edge; its normalized affine fraction is~1.09e-17.
  Display-proximity insertion produced a collinear/incorrect local triangle,
  correctly rejected by the unchanged orientation gate.
  [Diagnostic witness](../../assets/operative-winding-witness-2026-11-05.json).

## Next action

Use the exact122tick fixture instead of replaying the whole prefix to diagnose
the next topology fix. Prefer an existing material source edge when inserting
an edge-bound point; do not guess between nearly coincident display edges or
accept a zero-area triangle. Preserve partial interior-point behavior, the
historical thin fixtures, both material and display contracts, all mass/history
and source-area partitions. Then repeat the same guarded operative path. This
remaining issue is not solved by changing another tolerance or deleting slivers.
