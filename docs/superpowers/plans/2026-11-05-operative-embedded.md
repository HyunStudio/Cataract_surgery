# Operative retained-material integration

Follow-up: [finite original-material inertia](2026-11-05-finite-inertia.md)
resolves the recorded fixed mass envelope with independent numerical evidence;
the failure ledger below preserves the original integration result.

Implement inline in feat/surgery-integration. Prior goal turn was progress408096d:
cache196 native tests and actual11stage qualification; real-time and whole
surgery remain unqualified. CI41854123990 and Tests41854123865 completed
successfully at408096d; the new operative path below is not covered by those runs.

Connect the existing retained original-material state to capsule_solver's actual
interface. Activation is permitted only at a pristine rest state with the actual
FEM and interval-guard backends. Preserve native force/gap/complementarity gates,
fine cut topology and original control masses. The default cannot silently
promote until complete operative cases pass.

Store authoritative embedded state as an owned value dictionary, so existing
whole-step capture/restore covers topology, history, reactions and clocks.
Publish fine arrays/topology for existing display, fluid access and recording;
their fine inverse masses are diagnostics, not FEM degrees of freedom. Cutting
uses original-material support and no legacy independent fine-mass transfer.

Every operative tool needs its actual recorded body. Pull oriented pressure
forces back through B instead of integrating tiny fine masses. A guarded coupled
native step must pass before publication. Include current iris/posterior surface
queries for nonanchored tissue and existing wound-aware shell checks; reject any
unavailable or corrective boundary result rather than project after equilibrium.
Reject unsupported grasp input explicitly until finite-jaw acquisition is wired.
This intermediate restriction is not the final simulator scope.

RED install/cut/whole-state contract, fake-failure atomicity, then the SAME actual
blade route from test_blade_closed in a frozen real-extension application. Keep
all original area and continuous physical body checks; do not substitute a
direct curtain incision, inject tool pose or weaken existing failure gates.
Record any first new physical failure and continue from that exact evidence.

Subsequent required work: finite-jaw material attachment, cut-remap/anatomy
response, extraction, partial-tip mechanics, active throughput and full actual
input preparation-to-review Windows release. Full goal remains active.

## Execution evidence

- Missing operative backend API was RED before the adapter; its unit contract
  is GREEN. Owned embedded state participates in existing capture/restore.
  Failed native candidates and malformed or pathless instrument bodies cannot
  publish accepted material state. The contract uses test doubles, not native
  physics qualification.
- Same native operative blade path first stopped at `blade_area_not_preserved`.
  Exact fixture `operative-blade-area.bin` reproduces float32 display-edge area
  drift (~1.55e-9); normalized affine bindings preserve the material partition.
  Scalar-double display area alone remained RED. Strict material mode now
  consumes positive normalized material fractions without widening the area gate.
- Regression exposed an older thin geometric fixture with positive rounded
  display orientation but negative affine fraction (-2.164079e-8). This affine
  topology is still unresolved. Explicit `material_partition=true` is required
  by embedded mechanics and rejects it. Default geometric cutting retains its
  prior display-area contract; it emits no fractions. Both contracts have tests.
  An experiment selecting near edges by material collinearity did not solve
  both display and material triangulation and was reverted.
- Native source-frozen operative replay n62orw92 reached112 accepted ticks,
  52 staged incision events, then rejected a new tiny support. Exact staged
  `operative-embedded-mass.bin` reproduces `embedded_mass_resolution` atomically.
  Its support is finite, positive and conserves total mass (difference8.88e-16):
  minimum mass8.516809511747748e-13, inverse1.1741486041464705e12,
  246 controls, minimum control on one face with area4.13259763203493e-11.
  Existing inverse1e12 native envelope remains unchanged. No mass floor,
  tissue deletion or welding was introduced. A passing rejection regression
  does not qualify the rejected physical step.
- Independent read-only review found missing accepted contact telemetry.
  Positive-dual contact count and accepted gap residual now publish after
  boundary acceptance and clear on a later contact-free step. RED then GREEN
  operator-level publication contract; fake accepted step is explicitly not
  an independent native contact validation.
- Final frozen focused regression run rq0jp9j8:39/39 suites passed plus fresh
  import, exit0. This includes the exact rejection fixture, not its resolution.
  [Full regression evidence](../../assets/operative-embedded-regressions-2026-11-05.json).
- Final real native run erjeq8yb:13/14 stages passed; operative blade stopped at
  the same positive tiny-support mass envelope, exit1, `qualified=false`.
  Existing11 native stages and both new operative contracts passed. Same path,
  metrics and first failure reproduced after the final API and telemetry fixes.
  [Native evidence](../../assets/operative-embedded-native-validation-2026-11-05.json).
  Default backend has not been promoted.
- Independent read-only final review found no further important defect. This
  was static review, not a substitute for the failing complete operative route.

## Next numerical work

Preserve the exact112tick failure fixture. Investigate physically scaled inertia,
matrix conditioning and affine support resolution before changing the numerical
mass envelope. Any support for smaller genuine fragments needs independent
positive mass, conservation, conditioning, force/contact residual and convergence
evidence; simply raising the inverse cap is insufficient. Finite-jaw acquisition,
thin affine triangulation, anatomy response and complete real input cases remain
required alongside this work.
