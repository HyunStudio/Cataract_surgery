# Recorded-path contact in the Godot state transaction

Continue the full surgery objective fromeb48f5f. The exact captured144 native
candidate and whole-interval guard were green, but the actual controller still
called only the static endpoint solver. This change connects the candidate to
the same accepted original-material state; it does not promote the optional
backend or qualify a complete surgical case.

## Implementation and invariants

1. A typed `solve_trajectory_fem` GDExtension request passes old original controls,
   recorded kinds/Packet41 bodies, sorted sample times and layer-major multipliers
   to the existing native API. Shared static validation preserves typed arrays,
   COW request ownership and the total face/body/layer constraint budget before
   allocation. Failed solves return original positions and no reactions/duals.
2. `recorded_body_pose.gd` samples packets using scalar binary64 arithmetic only,
   normalized shortest-arc quaternions and recorded endpoint affine correction.
   No Vector3/Quaternion Float32 conversion enters the independent force check.
   Endpoints are copied bitwise. Malformed packets and times reject.
3. The engine independently checks contact geometry on B[q0+t(q1-q0)] and
   accumulates reaction forces with factor t. Force, gap and complementarity
   thresholds remain1e-8/1e-9/1e-11. The whole physical body path is still checked
   separately by the original interval guard.
4. The endpoint candidate remains the first attempt. A genuine intermediate
   witness adds a sample and retries from the SAME accepted state, predictor,
   holds, load, damping and dt. All retries share the original Newton budget,
   validate its reported integer work and are bounded to16 attempts/65536 pairs.
   Invalid, t0, duplicate, exhausted or unavailable work rejects atomically.
5. Accepted positions, old history, grasp reactions, sampled multipliers and
   physical clock publish once, after independent force and complete-path checks.
   The outer operative adapter's anatomy, wound and boundary transaction remains
   required. There are no fake substeps, history scaling or tool-target changes.

## RED and independent tests

- The real bridge test first rejected the missing original-material trajectory
  method. After binding it, typed malformed/budget failures are atomic, t=1 is
  bitwise identical to static contact, and independent GDScript material/contact
  force is1.23e-12. A typo in the new test's C01 formula was corrected after its
  NaN diagnostic; production material formulas were unchanged.
- Pose tests first failed because the sampler was missing. Their independent
  SciPy fixture covers linear sub-Float32 coordinates, an analytic half-circle,
  sign-flipped/nonunit quaternions, subinterval endpoint correction, changing
  local segments, and all four actual captured bodies.32 sampling requests match
  within1e-13 and endpoints exactly. The original ambiguous180degree sign-flip
  fixture was replaced by a unique shortest arc for the SciPy comparison, while
  retaining the separate analytic half-circle. A diagnostic string formatter
  issue was fixed; the final tests contain no runtime errors.
- `build_recorded_pose_fixture.py` reproduces the stored fixture byte-for-byte
  using the existing independent SciPy pose reference.
- The staged transaction test was RED against the old endpoint-only rejection.
  It now verifies immutable predictor/history/dt, decreasing shared budget,
  single clock publication, duplicate/t0/NaN/exhausted witnesses, invalid work
  and fabricated retry-force rejection with unchanged owned state.
- Two prior native collision tests expected only the old immediate rejection
  reason. They now verify the real guard records collision, a real trajectory
  attempt follows, and exact-zero-distance unresolved contact still rolls back.
  No geometric acceptance assertion was removed.

## Verified state and limits

- Frozenwaff3nx7 passes15/15 actual native bridge/state/grasp/contact/curved/
  trajectory stages. Captured144 now passes the actual engine independent force
  at9.955700597252815e-9 with92 cumulative iterations and one clock commit.
  Captured-core execution took70.513s in that run (67.114s in the earlier isolated
  probe). This is explicitly not real-time qualification or an outer-anatomy
  clearance.
- Frozena8b_j_9o passes42 focused engine suites plus fresh import, exit0. A prior
  frozen run also passed42 suites before the native collision assertion update;
  the final run includes that exact updated source.
- An independent read-only review found no substantive defect in bridge shape
  validation, packet sampling, layer indexing, t weighting, retry budget or
  atomic clock/history publication.
- The first complete operative closed-blade probe, frozenm623njos, passed19/20
  stages, then stopped after145 accepted physical ticks. The next146th candidate
  failed its static endpoint force solve at7.765697285222473e-7 despite contact
  gap3.37893e-13 and COMP4.70710e-13. It did not reach the full interval guard.
  This route includes unchanged pristine setup, targets and outer anatomy;
  component qualification does not replace it.
- Previouseb48f5f Python CI41884588948 and Windows native CI41884588946 succeeded.
  The native workflow now includes the trajectory bridge, poses, transaction and
  captured-core tests. The default app's prior volumetric-blade CI failure, finite
  jaw acquisition/traction, full actual input cases, throughput/GPU and Windows
  delivery remain unresolved completion requirements.

## Exact146 numerical recovery

Transparent proxies on that SAME frozen project reproduced the final failure
and retained the original source hashes. Saved native request/response, old
original controls, body packets and owned pre-solve state in
`operative_motion146.json` / `operative-motion146-state.bin`. The owned state
has145 accepted ticks and186 staged incision events; failed state is unpublished.

An offline accurate temporal candidate at[.5,1] from this exact original predictor,
old controls and dt passes independent material KKT and full interval guard.
It uses17 additional Newton iterations after the failed static19, within250.
Final force3.5110053749534965e-11, sampled gap1.27172e-13, COMP1.77159e-13.

The engine now permits that single numerical recovery for a first static status2
failure only when its failed positions still equal the original predictor, all16
stats are finite, work is a valid integer within budget, holds/contact/COMP are
already feasible, and force is within the existing inexact inner1e-6 range.
This range selects a retry; final acceptance remains1e-8. The same flags cannot
retry a failed temporal solve. Invalid residuals, geometry or exhausted work
remain rejected. A new RED mock test passed after implementation; an independent
read-only review found no substantive eligibility or atomicity defect.

Final frozenz0gu0z_9 passes15/15 native engine stages including BOTH actual144
and146 core states. GDScript force146=3.513866975168867e-11, total work36,
one physical clock update,12.059s. Captured144 uses92 iterations,70.034s.
Frozenbzo2gcse passes42 focused suites plus import, and the expanded source-bound
numerical validator passes216/216 tests with the new retained failure fixture.
The repeated closed-blade route in frozenr33yxrys also passed19/20 stages. It
passed the former146 failure and logged148 accepted physical ticks, then rejected
`embedded_contact_motion_budget`. This is a real computational limit, not a
cleared route. A transparent diagnostic is collecting its exact final state on
the same immutable frozen inputs. Do not increase the constraint budget or relax
force/clearance criteria to hide it.

## Throughput diagnosis

An isolated instrumented source copy reproduced the exact144 candidate's native
stats, passed independent material KKT and its full motion guard. The single
four-layer solve took44.213s while other local CPU work also ran:

| Work | Seconds | Calls |
|---|---:|---:|
| Full evaluation, inclusive |25.403|67|
| Temporal gap field/inactive certificate, inside evaluation |20.586|2241552|
| Full distance queries, inside evaluation |3.968|2241552|
| Merit differences, inclusive |18.025|50|
| Embedded derivatives |.00161|258|
| Sparse factorization |.20247|36|
| Sparse linear solve |.00294|35|

Do not add inclusive rows together. The dominant cost is repeated field/certificate
and merit work, not the sparse solve. Next qualify reuse of the SAME outward
coarse material hull per face/time/candidate across bodies and merit comparisons.
Both complete geometry evaluations and all physical gates must remain intact.
Do not replace the guard with a broad-phase assumption or claim real-time FPS.
`profile_temporal_contact.py` preserves this instrumented-copy workflow without
editing or promoting the live kernel.

## Evidence

- [Current15-stage native/trajectory qualification](../../assets/trajectory-engine-connection-native-2026-11-05.json)
- [Current42-suite engine qualification](../../assets/trajectory-engine-connection-regressions-2026-11-05.json)
- [Current216-test numerical qualification](../../assets/trajectory-engine-connection-numerical-2026-11-05.json)
- [Initial full-route failure at146](../../assets/trajectory-engine-full-route-2026-11-05.json), [log](../../assets/trajectory-engine-full-route-2026-11-05.txt)
- [Transparent146 capture provenance](../../assets/trajectory-engine-next-capture-2026-11-05.json)
- [Independent146 temporal recovery](../../assets/trajectory-motion146-midpoint-probe-2026-11-05.json)
- [Repeated full-route budget rejection](../../assets/trajectory-engine-final-route-2026-11-05.json), [log](../../assets/trajectory-engine-final-route-2026-11-05.txt)
- [Instrumented throughput diagnosis](../../assets/trajectory-contact-profile-2026-11-05.json)

## Next exact barrier: motion150

The transparent repeat is terminal and confirms149 accepted physical ticks,
201 staged incision events,352 original controls,2477 fine faces and4 bodies.
The owned checkpoint round-trips exactly in`operative-motion150-state.bin`;
canonical B reconstruction of its accepted fine positions is bitwise identical.
All frozen product input hashes remain unchanged.

Six native candidates satisfy their sampled KKT but still fail the complete path:
the times advance from1 to.125,.0625,.03125,.015625,.0078125. The final guard
finds face399/body0 at t=.00390625, gap-1.3760004378970958e-8. It is a real
collision, not a false guard alarm. Adding that seventh layer would require
69356 dense constraints, exceeding65536. Only175 of250 Newton iterations were
spent. The last candidate has exactly one positive multiplier at t=.0078125;
all four older nonendpoint layers are exactly inactive.

[Exact compact native case](../../assets/operative-motion150-budget-case-2026-11-05.json)
and [capture provenance](../../assets/trajectory-engine-budget-capture-2026-11-05.json)
retain the evidence. Failed candidates and clocks remain unpublished.

An offline active-time exchange retained the positive layer and endpoint, retired
only exact-zero layers, and added the new guard witness. It passes independent
KKT but still collides at t=.001953125, gap-3.47575e-9. Another cold solve exhausts
the ORIGINAL250 iterations before its sampled gap/COMP converge. Thus late layer
retirement alone is NOT qualified and has not been added to the live controller.
[Unqualified exchange experiment](../../assets/trajectory-motion150-exchange-probe-2026-11-05.json).

Next qualify constraint exchange together with an explicitly separate numerical
initial guess/multiplier seed, or a better initial-contact witness formulation.
Keep the original inertial predictor, q0/history/dt and physical energy immutable.
Do not warm-start by overwriting`request.xyz`: the existing API interprets it as
the physical predictor. Active layers must never be dropped; retired constraints
remain subject to the complete guard and can be rediscovered. Preserve the
original iteration/pair limits and all final force/gap/COMP/SPD gates. The cached
coarse-hull optimization above addresses the independently measured throughput
cost; neither direction constitutes complete surgery qualification by itself.
