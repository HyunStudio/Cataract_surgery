# Numerical seeds with an immutable physical predictor

Continue the full surgical simulator objective fromf72acdf. The real closed-blade
route accepts149 ticks, then needs a seventh dense layer(69356>65536 pairs).
All but one old nonendpoint layer have exactly zero multipliers. Late exchange
fits memory but cold re-solving exhausts the original250 Newton iterations.
This is not a cleared route or real-time simulator.

1. Add a separate seeded original-FEM trajectory API. Keep `xyz` as the immutable
   inertial predictor/output; add const numerical initial coordinates and const
   nonnegative normalized multiplier seeds. Preserve old APIs bitwise. Validate
   pins, finite domain, typed bridge sizes and failed-candidate atomicity.
2. Start Newton/AL from those seeds while original energy/inertia still uses the
   original predictor. Preserve exact holds, force1e-8/gap1e-9/COMP1e-11, SPD,
   original-system linear residual and full geometry evaluation contracts.
3. RED independent KKT against the original predictor from different guesses,
   zero-budget reuse of an already equilibrated seed, bad seeds/pins/atomicity
   and caller FP restoration. Replay exact150 with the original remaining budget.
4. Bind seeded requests in Godot. Reuse only candidates which passed independent
   physical checks and were rejected by the complete motion guard. Never use a
   failed native solve's unpublished iterate or change physical history/dt.
5. Exchange whole exact-zero multiplier layers when needed; retain every positive
   layer and endpoint1, remap normalized multipliers by time/face/body, add the
   new verified witness. The complete guard can rediscover retired constraints.
   Keep16 attempts,65536 pairs and250 total Newton iterations; reject bad work.
6. Qualify actual144/146/150 engine states, focused regressions, source-bound
   numerical/bridge suites and read-only review. Repeat the identical full blade
   route and save the next genuine failure. No default promotion or completion
   claim until the full input/anatomy/model/throughput/GPU/Windows objective passes.


## Implemented and verified

The old30-argument trajectory export is unchanged. A separate33-argument
`membrane_fem_solve_trajectory_seeded` accepts const initial coordinates,
normalized multiplier guesses and an algorithmic penalty seed. The original
`xyz` still supplies the physical inertial predictor; q0, dt, material parameters,
fixed coordinates and exact hold targets are unchanged. Failed output/reaction/
dual buffers remain unpublished. Old cold bitwise and caller FP regressions pass.

Warm coordinates/duals with a reset penalty1 did NOT qualify the saved150 case:
the next solve needed51 steps and the continuation exhausted the original250.
Carrying the previous finite validated algorithmic penalty as well resolved that
numerical restart. This is an AL solver parameter, not material stiffness or
an applied physical force. The failed reset experiment is retained locally in
`godot/reports/seeded-motion150-extension.json`; it is not green evidence.

Godot retries use a candidate only after independent original material/grasp/
contact force checks pass and the complete interval guard rejects its motion.
A failed native solve never supplies an iterate. Private retry coordinates are
erased before every public result. On memory/time-layer overflow only, the helper
retires whole exactly-zero nonendpoint multiplier layers. Every positive value
(including1e-300) and endpoint1 are retained. New guard witnesses can rediscover
retired constraints. The original16 attempts,65536 pairs and250 total Newton
iterations remain, as do force1e-8/gap1e-9/COMP1e-11, SPD, original linear-system
residual and final complete motion checks. Physical state publishes once only.

### Current source-bound evidence

- [224 numerical tests /18 suites](../../assets/seeded-trajectory-numerical-2026-11-05.json), nine DLL variants.
- [43 focused engine suites plus fresh import](../../assets/seeded-trajectory-regressions-2026-11-05.json).
- [16 real native bridge/engine stages](../../assets/seeded-trajectory-bridge-2026-11-05.json).
- Read-only native/bridge/engine review found no substantive defect. Reviewer did
  not edit code or run the validations above; those are direct validator results.

| Saved core tick | Total Newton steps | Retired layers | Independent force infinity norm | Wall time |
|---|---:|---:|---:|---:|
|144|47|0|2.4223623107388903e-11|23.437s|
|146|36|0|3.513866975168867e-11|12.482s|
|150|91|4|2.784905639430235e-10|79.781s|

Each saved core state clears the complete interval guard and publishes exactly
one physical clock/history step. These are NOT outer operative anatomy/full-route,
actual OS mouse/keyboard, real-time, clinical or Windows release qualification.
The full identical operative route is being repeated separately; do not substitute
these core checks for its outcome.

## Remaining qualification and next work

The current default Godot CI at f72acdf still fails `test_volumetric_encounter.gd`
(the log explicitly reports no real detached anterior flap). Native and Python CI
at that commit pass. The new backend remains optional and is not promoted.

The closed-blade route currently accepts any nonempty detached component list.
Small chips appear before the intended circle closes, so this assertion alone
cannot prove a central flap. Strengthen it using the original central material
vertex/component, after observing the frozen repeat, rather than an invented
clinical size threshold. The engineering knife-circle route itself is not CCC
qualification; finite-jaw acquisition/tearing is still pending.

Throughput is still far from real-time. The previous source-instrumented profile
points to repeated outward hull/inactive certificates and interval merit work,
not sparse factorization. A next bounded optimization can cache the same original
control/time/candidate hull across bodies and merit comparisons while preserving
every full geometry query and every final gate. It must retain source-bound
bitwise/FP/physical regressions and be measured on these exact saved states.
