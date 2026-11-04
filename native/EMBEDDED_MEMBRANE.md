# Experimental embedded membrane core

2026-11-05: line merit calculations now reuse fully evaluated inactive states
under the same multiplier/penalty and original interval certificate. Every
distance, rounded activation, active curvature and final gate remains intact.
The isolated counted probe includes tiny-radius overflow and rounded-touch
positive-dual regressions; it is never linked into the application. Native196
tests and fresh actual Godot11stages pass. The saved curved two-hand request is
bitwise identical to the old DLL; seven interleaved samples measured median
0.6031s versus0.4216s (1.43x). This is NOT real-time qualification. Archived
reports: docs/assets/inactive-cache-*-2026-11-05.json. Build the new probe with
`python tools/build_contact_activity_probe.py` after the existing native builds;
`python tools/validate_fp_environment.py` includes it. Windows CI now also builds
and qualifies the actual Godot extension, rather than just standalone DLLs.

This standalone DLL evaluates retained original-material cells and computes
implicit position candidates. It does not replace the product backend yet.
There is no contact/CCD, bending, crack propagation/enrichment, operator case or
clinical material calibration in this core. Test stiffnesses are numerical
parameters, not measured capsule tissue properties.

Build and qualify with the pinned Zig0.17.0 / Eigen5.0.1 dependencies:

```powershell
python tools/build_membrane_fem.py
python tools/build_fp_environment_probe.py
python tools/validate_membrane_fem.py
```

Regenerate the independent Godot reference with Godot4.7.2 before qualification
if one of its recorded source files changed:

```powershell
godot --headless --path godot --script res://tests/test_fem_reference.gd
Copy-Item godot/reports/fem-reference.json native/tests/fixtures/embedded_membrane_reference.json
```

The isolated native outputs live in `.tools/native`, with a source/ compiler/
dependency/artifact hash manifest. Validation refuses mismatched sources, DLL
or reference provenance. Existing native contact kernels are unchanged.

## ABI and numerical contract

Each cell contains3 node IDs,6 double reference shape gradients (gx0,gx1,gx2,
gy0,gy1,gy2) and retained real material area. Gradients preserve partition of
unity; the first is normalized from the others within a checked roundoff bound.
Bounds: nodes1..4096, cells0..8192, coordinates finite within±16, inverse mass
0..1e12. Inverse0 means an exactly fixed predicted control. Caller buffers must
have the lengths implied by these counts.

- `membrane_fem_evaluate`: energy, nodal gradient and optional81doubles per-cell
  Hessian, row-major9×9. The law is
  `W=mu/2*(trace(F^T F)-2-2log J)+lambda/2*(log J)^2`, `J=sqrt(det(F^T F))`.
- `membrane_fem_difference`: the same elastic energy change, using incremental
  Gram/determinant expressions and log1p near small steps, rather than subtracting
  nearly equal absolute energies. The wide-ratio branch uses ordinary log values.
- `membrane_fem_solve`: minimizes elastic energy plus
  `sum(mass_i/(2dt^2)*|x_i-predicted_i|^2)`. dt1e-6..0.1. Damping changes only
  Newton directions. Exact sparse LDLT,12damping retries,32Armijo backtracks and
  caller outer budget0..1000. Successful output requires caller force tolerance
  and positive finite pivots of the undamped final Hessian. No unconverged fallback.

Solve status0 is accepted,1 work exhaustion,2 numerical/undefined evaluation,
3 negative final curvature,4 singular/inconclusive final factorization and-1
invalid input. Every nonzero solve leaves input positions unchanged. Failed
evaluation/difference leaves caller output buffers unchanged. Eight statistics:
candidate energy, force∞, completed outer iterations, evaluations, factorizations,
relative linear residual, minimum accepted line step and current damping.

## Current evidence and limits

Eight native tests cover independent finite differences,3D energy/force
objectivity, shared/permuted cells, exact pins, invalid/budget/numeric atomicity,
a force-stationary compressed saddle rejected for negative curvature and
80-digit Decimal small-energy differences. A captured curved Godot model with
217controls/396cells checks the independent energy/gradient and implicit
candidates atmu2/lambda3 andmu10000/lambda15000. Independent NumPy force checks
remain below1e-8. Source-bound validation report is in
`docs/assets/fem-core-validation-2026-11-04.json`.

Six isolated repeated candidates each measure median4.323ms and6.652ms for those
two parameter choices on this shared host. These exclude tool/anatomy contact,
actual time histories, cutting, GPU presentation and full operation. They do
not establish application FPS or compare equivalent laws with the old solver.

## Optional real Godot dynamics

`MembraneFEMKernel` exposes typed/dimension-checked `solve_fem(request)` and
`evaluate_fem(request)` beside the unchanged older bridge classes. Build with
`python tools/build_membrane_extension.py`, then run
`python tools/validate_embedded_extension.py`. The validator freezes product
resources and the source-bound extension into a separate probe, imports it and
runs both bridge contracts plus the actual embedded model. Product configuration
does not automatically load or switch to this experimental backend.

`embedded_membrane.advance` uses actual support mass and accepted motion history
to predict a bounded step, then independently evaluates the original force
equation in GDScript. Only a successful, finite, fixed-rim-preserving candidate
with residual<=1e-8 advances position/history/time. Failure is atomic. Geometry
caches are invalidated on initialization and accepted cuts.

The real-engine test makes a retained curved flap with explicit geometric
curtains, applies a material point force for30steps, recuts moving material and
continues5steps. It preserves mass5.319326346740127 and history, accepts35steps,
129incisions,1008fine points/1188faces/289controls, and verifies real budget
exhaustion cannot publish a partial step. Maximum independent force9.1272e-9.
The center rises.0012946scene units. This is point-force model qualification,
not actual forceps/body/anatomical contact or a surgical input trajectory.

Latest30traction-step timings include native solve and independent GDScript
checking: median18.061ms/max24.655ms on this shared host, excluding rendering,
other device/fluid models and body contact. This is not60Hz application proof.
Reports: docs/assets/embedded-native-validation-2026-11-04.json and
embedded-dynamics-validation-2026-11-04.json (28focused engine suites).

Next: exact embedded grasp/reaction constraints, fine-contact Jacobian and
continuous-motion guards, partial interior-crack support and complete real
operator qualification. Retain original strict acceptance gates. Float32 cut
proxies are not proof of a precise remap: preserve transferred material bindings
in double precision, or certify remap motion before contact.

## Exact embedded attachments

The additional C ABI `membrane_fem_solve_grasp` and Godot method
`solve_grasp_fem` hold up to2 material points via their actual linear maps
`Bq=target`. Node slots, positive normalized weights and3D targets are explicit;
zero-grip calls preserve the original unconstrained result/statistics exactly.
Dependent constraints reject atomically rather than inventing a reaction split.
Control masses remain in the physical inertia, including held material.

Sparse primal factors plus a small Schur solve enforce the equalities. The
normal augmentation `rho*A^T*A` is a direction/factorization device; the final
undamped augmented Hessian must be positive, which checks original curvature
on the feasible tangent. Force balance includes actual attachment reactions.
Final force<=1e-8 and gap<=1e-9 remain unchanged. Positions and reactions publish
only on success. The first8 statistics retain their prior meanings; indices8..11
record equality gap, augmentation rho, initial projection gap and Schur residual.

Near constrained stationarity, normal reaction work from roundoff can exceed
the true tangent descent. Armijo therefore compares the fixed-dual Lagrangian
using the stable original energy difference plus `lambda*A*delta`, with tangent
slope `(gradient+A^T*lambda)*delta`. On exact feasible motion this is the same
physical objective. Independent final original KKT force/gap checks are required.

`embedded_membrane.grasp/release_hand` bind a material vertex and source fine
face. Targets are queued into `advance` and accepted together with reactions,
motion and time. Failed commands keep the previous accepted targets. Cutting
releases an attachment whose face has two valid banks, remaps a unique surviving
bank, and rejects if remapping would violate the held target gap. Release keeps
the accepted velocity. None of this is a forceps-body or anatomical-contact solve.

Run `python tools/validate_embedded_extension.py --grasp` for the6stage actual
engine check. It includes existing bridges, the35step force/recut regression and
a17step attachment case: a nonnodal free-flap point (weights.59855/.40145),10
single-hand moves of.005, release, two-hand moves, and a separate incision while
held. Material mass is5.319326346740127; force8.03325e-9/gap1.11022e-16. The
validation loop's10single-hand samples have median23.1ms/max36.459ms, including
diagnostic copies and independent GDScript checks, excluding instrument contact
and presentation. This is not application throughput qualification.

There are now15standalone native tests (8original+7grasp), including rejection
of an unheld unstable tangent even when the held region is augmented. Reports:
`docs/assets/fem-grasp-core-validation-2026-11-04.json`,
`embedded-grasp-validation-2026-11-04.json` and
`embedded-grasp-regression-2026-11-04.json` (29focused engine suites).

## Retained fine contact and precise cut maps

`embedded_contact.h` queries the actual retained fine triangle `Bq`, never its
uncut parent. `membrane_embedded_contact_distance` in the standalone distance DLL
returns the existing22value witness,9control gradient and81control Hessian entries
of squared distance. Shapes are9row-major nonnegative unit barycentric weights;
controls are9doubles. All outputs remain untouched on nonzero status. Status4
additionally rejects a feature switch or singular local minimizer system where
the ordinary smooth Hessian cannot be established. Other statuses match the old
distance query. The radius affects reported gap, not squared-distance derivatives.

The smooth branch eliminates free triangle/finite-axis minimizer parameters:
`H=2(W^T W-M(D^T D)^-1 M^T)`, including the `r*dw` mixed term. Gradient/Hessian
are pulled back through the retained affine map, with no finite-difference model
substitution. Run `python tools/validate_embedded_contact.py`:27tests include10new
chain-rule/feature/atomicity cases and17unchanged distance cases. This static
primitive is not yet a coupled contact solve, bridge, CCD or application feature.

Optional `Support.build(...,material_weights)` validates and retains supplied
double B. Embedded cuts now compose the accepted source-fine-face B with the
cutter's normalized barycentric binding, rather than refitting rounded rest
vertices. The two-cut `test_embedded_weights.gd` reproduces former physical/history
errors1.92e-8/2.24e-8 and now requires2e-14 consistency. The existing held-target
gap check remains. This local interpolation invariant does not certify continuous
clearance, partition nonintersection, or contact equilibrium after a cut.

The optional Godot `MembraneFEMKernel.contact_fem` now accepts a Dictionary of
PackedFloat64Array `controls`(9), `weights`(9), `segment`(6), plus scalar `radius`.
It validates types/lengths before pointer reads. Only status0 returns packed
`values`(22), `gradient`(9) and `hessian`(81); all nonzero statuses return empty
arrays. The new header is bound into extension source manifests and object keys.

`embedded_membrane.contact_geometry` duplicates accepted coarse/fine histories,
actual retained connectivity and per-face B. `contact_face` constructs the local
three-control request and checks witness reconstruction, convex closest-point
KKT signs, squared gap, B-transpose force and Hessian symmetry independently in
GDScript. Its CHECK1e-11 is a numerical static consistency diagnostic only, not
the coupled force/gap/complementarity acceptance or a CCD certificate. The
returned material weights are B-transpose times the fine witness barycentrics,
not a snapped nearest fine vertex. No query changes state/time/attachments.

Run `python tools/validate_embedded_extension.py --grasp --contact` for8actual
engine stages. This includes the existing35force/17grasp steps, direct bridge
finite differences and refined deformed curved face contact. The current probe
has217controls404faces; gap.01999999918305446 at an intended.02clearance, with
reported material-point/virtual-work errors0. See
`docs/assets/embedded-contact-engine-validation-2026-11-04.json`. This is still
static contact, not an instrument-controlled reaction solve or full surgery.

## Coupled static implicit candidates

New standalone C ABI `membrane_fem_solve_contact` shares the original Problem,
Neo-Hookean energy/inertia and SparseCells factors with existing solvers through
the private `membrane_fem_contact.inc`. It accepts the old material data and
up-to2exact linear held points, then retained fine faces (3control IDs+9shape
weights each), rigid capsules (7doubles each) and output nonnegative contact
multipliers in face-major/body-minor order. Bounds:4096controls8192cells/faces,
64capsules and65536pairs. Invalid/nonregular/inconclusive/budget cases leave
positions AND both reaction arrays unchanged. No body dispatches the original
grasp solve bitwise, including the first12statistics.

For each true fine triangle Bq, the constraint is `g=d²/r²-1>=0`. Bounded PHR
outer minimization uses exact smooth distance gradients/Hessians; original
elastic stable differences and conservative contact merit difference bounds
drive line acceptance. Equalities retain their actual inertia and use the old
primal/Schur projection. Early infeasible inner minimization can stop at1e-6;
this is only an intermediate optimizer tolerance. Final original force<=1e-8,
held/physical gap<=1e-9, nonnegative duals and `abs(dual*g)<=1e-11` are mandatory.
Rho progress includes both penetration and complementarity. Final curvature
factor has zero damping; the PHR and equality normal augmentations vanish on
the simultaneous active tangent. No damped objective is accepted as physics.

Statistics16: first12retain the grasp meanings (slot11currently0), then maximum
physical penetration, complementarity, zero-based outer index and contact rho.
There are at most100outer models,1000totalNewtonsteps,12factor attempts and32line
trials per step. Inactive ambiguous witnesses need no Hessian; active nonregular
geometry fails without a fabricated derivative or approximate accepted fallback.

`test_fem_contact.py` now has11tests and an independent NumPy enumeration of all
triangle simplex/finite-axis active sets. It recomputes actual original energy
gradient, inertia, held material point/reaction and contact reaction without
calling the native distance query. Cases include nodal/nonnodal holds, partially
fixed controls, one/two hands and bodies, redundant rows, finite endpoints,
empty parent material, bitwise zero-body old-grasp regression, invalid/budget/
impossible target atomicity and negative free-tangent rejection. All26native
tests pass; see fem-coupled-core-validation-2026-11-04.json. Existing actual8stage
engine checks also pass with the new linked core (separate build regression
report). A coupled Godot method/time step, whole-interval/anatomy guards and
actual instrument/controller behavior are still missing; none is implied by
these static synthetic candidate tests.

## Guarded optional engine step

`MembraneFEMKernel.solve_contact_fem` now exposes the typed coupled request. In
addition to old material/grasp data it requires packed `face_nodes`,
`face_weights`, `capsules` and scalar `complementarity_tolerance`. Counts/types
are checked before native pointers; non-success preserves request xyz and
publishes empty `reaction`/`dual` arrays, not uninitialized candidates.

`embedded_membrane.advance_contact(...,motion,...)` takes `kinds`,41value body
`packets` and the real `MembraneContactKernel` guard object. Static current axes
and radius derive from those SAME physical packets. The optional old `advance`
path remains available with no contact and the default app is unchanged.
`embedded_contact_step.gd` reconstructs each positive contact's original B^T
force and multiplier-gap product using independently checked fine witnesses.
The original GDScript elasticity+inertia+grasp+contact force gate remains1e-8.
Zero duals require no undefined ordinary derivative; complete-interval guard
checks every retained face, including inactive ones. Its original gap1e-9 and
budget128 remain. Guard status0 is mandatory before ANY position/history/time,
held target/reaction or contact diagnostic commits. Guarded failure rolls back
the whole candidate. The guard's nearest sampled gap may be +INF when a complete
separation certificate requires no samples; NaN, negative INF and nonfinite
other statistic slots reject.

Run `python tools/validate_embedded_extension.py --grasp --contact --coupled`.
The actual10stage probe adds a typed coupled candidate and six guarded1/2hand
ticks on a synthetic single triangle. Initial body pressure has positive duals
3.3785/6.8503; subsequent inertial separation has zero contact force and positive
clearance.01756..03524, rather than invented adhesion. Maximum independent
original force5.786e-9 and complementarity1.674e-14 pass. A linear full crossing
and quaternion arc have safe static endpoints but real interior collision;
both are rejected with unchanged accepted state/time. See
`docs/assets/fem-guarded-step-engine-validation-2026-11-04.json` and separate
26test core report. Reported sub-millisecond/few-millisecond synthetic step times
are not application throughput evidence.

Real nonidentity refined B, multiple faces/bodies, actual instrument/controller
pose authority, surrounding anatomy and cut-remap motion still need combined
qualification. Jaw acquisition, roll and partial-tip mechanics remain open.
This optional component has not been promoted to the default surgical app;
the old default continuous-blade/fine-traction failures remain visible.

## Retained curved coupled regression and caller precision

`--curved` adds the actual217control/404fine-face retained capsule to the real
engine probe, with nonidentity B and one/two hands/pressure bodies. Its exact
two-hand/two-body failed request is stored in
`native/tests/fixtures/curved_coupled_two_hands.json` with a standalone replay
helper. It is synthetic direct setup, not jaw/controller acquisition or a full
capsulotomy. Independent NumPy original KKT checks use every real fine face and
both face-major/body-minor multiplier columns.

The original250step engine failure reproduces bitwise under caller x87PC64,
while the exact DLL/request passes under Python's PC53. FTZ/DAZ toggles have no
effect on this fixture. The inexact AL inner switch had activated strict force
minimization at comp<=10tol even when complementarity still failedtol, preventing
outer multiplier/rho progress. It now uses ANY remaining comp>tol. FINAL original
force1e-8/gap1e-9/comp1e-11 and undamped curvature remain unchanged. Both caller
precision modes now have independent original KKT regression checks.

The isolated `fp_environment_probe.dll` is qualification-only, never linked to
the app, and restores caller control exactly. Its compiler/source/artifact
manifest and replay/fixture hashes are part of source-bound native qualification.
The optional `build_fem_contact_trace.py` late-line observer is a separate DLL;
the product has no trace I/O. Do not lower engine precision to obtain convergence.

Separate pre-existing release prerequisite: long-double outward Bound arithmetic
assumes64bit significand precision. Under callerPC53, computing1+2^-54 then
expanding by one80bit ULP can exclude the exact result. Current actual GodotPC64
qualification does not prove caller-independent interval safety. A scoped64bit/
round-nearest numerical boundary with exact restoration, or precision-aware
enclosures, is still required before a whole release. See the fixture notes and
coupled implementation plan; this condition is not hidden by passing solver KKT.

The fresh actual11stage `--grasp --contact --coupled --curved` probe now passes
all three curved cases, including the original two-hand/two-body failure.
Independent original force<=1.799e-11, comp<=4.311e-12, physical penetration
<=7.406e-13; every body has a positive active contact through nonidentity B.
See fem-curved-contact-engine-validation-2026-11-04.json and the28test core
report. Diagnostic wall times441/181/2994ms are NOT real-time qualification.
The confirmed numerical boundary issue above and inactive contact/merit cost
must be addressed before actual operator/GPU/Windows completion.

## Scoped numerical boundary qualification — 2026-11-04

The previously documented callerPC53 interval defect is addressed by native/fp_environment.h at the numerical API boundaries. It establishes x87 PC64/RN and SSE RN with gradual underflow, restoring caller controls on return, exceptions and nesting. The pinned Windows x86-64 Zig build passed189 native tests, including64 independent caller-control combinations,11 actual Godot stages and32 focused engine regressions. Reports are archived under docs/assets/fp-boundary-*-validation-2026-11-04.json. Local quoted headers are now included transitively in build provenance; the extension cache also includes the boundary header.

This supersedes the earlier outstanding caller-boundary prerequisite for these tested APIs and this pinned toolchain only. Compiler flags include -fno-rounding-math; runtime and assembly checks do not prove arbitrary compiler portability. Real-time performance, jaw acquisition, controller/anatomy coupling, partial-tip cuts and complete input/GPU/Windows surgery remain unqualified.
