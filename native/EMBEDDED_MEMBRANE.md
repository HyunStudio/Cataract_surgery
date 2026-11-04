# Experimental embedded membrane core

This standalone DLL evaluates retained original-material cells and computes
implicit position candidates. It does not replace the product backend yet.
There is no contact/CCD, bending, crack propagation/enrichment, operator case or
clinical material calibration in this core. Test stiffnesses are numerical
parameters, not measured capsule tissue properties.

Build and qualify with the pinned Zig0.17.0 / Eigen5.0.1 dependencies:

```powershell
python tools/build_membrane_fem.py
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
