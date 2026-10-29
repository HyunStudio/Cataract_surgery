# Experimental membrane numerical kernel

Update on c70f532: the saved failed264outer timestep now passes with the new
optional coupled core. Replay km0ox2ou completes52calls, adds two actual iris
constraints, passes final tool/anatomy continuous guards and preserves all rest
material with0broken edges/accepted uncertainty. Independently recomputed final
force4.77614e-9, gap1.12017e-12 and complementarity3.83425e-13meet the original
gates. Canonical140tests, explicit264capture, fresh bridge and actual capsule
checks pass. A new full extraction uvp7et92 is running; neither it nor the full
application is qualified by the saved timestep. The older full-prefix failure
below remains historical evidence.

Optional actual-capsule integration exists, but is not the default backend. Latest full extraction `ttc652cp` on3a1c95b accepts263ticks and rejects264 atomically when the first combined iris/tool solve returns2. Initial iris checks clear; all retained area remains with zero broken edges or accepted uncertainty. The exact failed request is preserved in tests/fixtures/joint_anatomy264.json with sibling provenance. `python tools/check_anatomy_capture.py` is an explicit heavy convergence gate; atomic rejection is not qualification. Earlier `faad2gqn`/265 boundary evidence remains historical. See MERIT_DIFFERENCE.md and TRAJECTORY_CONTACT.md.

The optional Godot `anatomical_contact.gd` adapter freezes finite anatomical triangles and queries the existing native guard against double-precision moving tissue points. It chunks every selected point/face pair within the existing limits, maps collision face/vertex/time, and never projects tissue. Supported margin is `(1e-9,.3]`, strictly above the fixed guard gap. It does not classify closed-shell interiors, wounds or exterior state. The optional actual capsule path now generates iris constraints through `solve_anatomy`, rejects penetrating initial history and requires both tool/anatomical interval checks within one eight-solve loop. See ANATOMICAL_CONTACT.md. Native110 component regressions and focused/frozen actual integration checks pass; the separate new full extraction fails as described above. The captured legacy265 request with two added endpoint constraints also rejects atomically and is not anatomical extraction success.

The continuous guard now computes each body's swept bounds/margin once and each
face's old/new bounds once, reusing the same values in the original pair order.
Arithmetic, comparisons, counters and work limits remain unchanged. An isolated
baseline/cache comparison produced identical status/eight statistics for88calls;
the adopted source passes110native regressions and fresh Godot bridge/actual
capsule integration. Isolated iris-query timing improvements are not whole-app
realtime qualification. The bounded local step model is now installed in the optional coupled core
after140frozen regressions and independent264KKT verification. Whole outer
timestep and extraction qualification remain separate, pending engine replay.

The standalone kernel minimizes

`E(x) = sum_free |x_i - predicted_i|²/(2 inverse_mass_i) + sum_edges (|x_a-x_b|-rest)²/(2 alpha)`.

Pins (`inverse_mass=0`) remain exactly at input positions. The edge energy is the existing compliant-distance engineering model; this does not add a clinically calibrated capsule constitutive law, bending, or fracture mechanics.

## ABI contract

`membrane_solve(n, xyz, inverse_mass, edge_count, a, b, rest, alpha, budget, gradient_tolerance, stats)`

- Input XYZ and inverse mass are double precision; endpoint arrays contain C ints. Arrays have their declared lengths; the C caller owns allocation. Output XYZ replaces accepted finite iterates.
- Return `0` for gradient convergence with positive finite pivots in the full undamped free-coordinate Hessian, `1` for outer budget exhaustion, `2` for numerical/line-search failure, `3` for a negative curvature pivot, `4` for singular/inconclusive stationary curvature, `-1` for invalid inputs. Invalid input leaves XYZ untouched. Numerical failure must never be treated as convergence. Full coupled curvature is screened numerically in double precision; status0is neither an exact-arithmetic proof nor a clinical/unique-minimum certificate. Deterministic saddle escape remains unsupported: unstable stationary input reports failure instead of injecting physical motion.
- Stats contain8doubles: energy, free-coordinate gradient infinity norm, completed outer iterations, objective evaluations, factorization attempts, last relative linear residual, minimum accepted line step, final direction damping. Before a valid objective evaluation, energy/gradient are infinity, not misleading zeros. Unavailable/overflowed linear residual is infinity. No hidden runtime claim follows from these counters.
- Initial scope requires strictly positive finite compliance alpha, positive finite rest lengths, inverse masses in `[0, 1e12]`, finite coordinates, at most4096vertices/16384edges and at most1000outer iterations. Exactly collapsed active edges reject explicitly pending a well-defined direction model.
- Building/testing does not integrate the solver into Godot, solve contact coupling, or approve a release.

The sparse direction uses the exact distance Hessian, including transverse geometric stiffness. A positive GN diagonal provides a direction-only Levenberg metric. Pinned coordinates are eliminated. Eigen LDLT reuses symbolic ordering within a solve; each numerical factorization must have positive finite pivots and an acceptable linear residual before its direction is used. Damping retries are bounded at12/outer iteration, backtracking at32evaluations/outer and outer iterations at1000. Failure exhausts explicitly; no unconverged fallback is passed off as success. These are work-count bounds, not hard wall-time or sparse-fill memory guarantees.

## Local build and checks

Install/extract the official Zig0.17.0 Windows compiler into `.tools/zig-x86_64-windows-0.17.0` only after verifying the manifest SHA256 `b5663f69581dcf391293fbf16c06cb80d81d806545ce618b4d0bab7f0eb8c428`.

```
python tools/setup_native_dependencies.py
python tools/build_membrane_kernel.py
python tools/build_contact_distance.py
python tools/build_contact_guard.py
python tools/build_contact_merit_probe.py
python tools/build_contact_step_probe.py
python tools/build_coupled_contact.py
python -m unittest discover -s native/tests -v
```

Eigen5.0.1 is pinned at `bc3b39870ecb690a623a3f49149a358b95c5781d`; see THIRD_PARTY.md and licenses/. The previous matrix-free implementation is preserved in commit739fa46. Its captured scene cost was about.21s. Current sparse solve measured.046–.053s across6standalone calls, with E3.819273056e-8, gradient_inf2.697e-9,24outer iterations and30factorization attempts. This is still slower than a60Hz substep budget and is not an app performance result.

`contact_step_model.h` is the bounded local PHR direction model used by the
optional coupled core, with a separate test-only probe. It
shares12factor attempts across working-set changes and damping retries. Internal
0indicates a checked stationary model;6is a complete-modeled descent direction;
7is a supported-part direction with unavailable inactive rows omitted;8retains
the first checked initial-set negative-slope Newton seed on proposal-budget
exhaustion, with change_upper=+infinity and no model-decrease certificate. None
of these proposal statuses means physical acceptance. Callers must recheck the actual
gradient slope, full nonlinear merit, physical KKT, final curvature and continuous
guards using one original nonlinear line search. Unavailable active gradients
reject and cannot be rescued by a saved seed. Frozen264passes independent KKT,
and the raw-seed integration passes all140frozen native regressions including
saved265. Fresh canonical builds pass140native tests, the independent264gate,
and fresh Godot bridge/actual capsule checks. Saved whole-timestep replay passes;
the new full extraction is running. The default application backend remains unchanged. Local tests are independent
small analytical/oracle/bounds/domain checks, not full-operation qualification.

## Isolated Godot bridge

`python tools/build_membrane_extension.py` builds `.tools/native-godot` with the pinned godot-cpp4.5bindings. It does not modify the product project's resources or install a native dependency into the released app. Its packed XYZ and inverse/rest arrays retain float64precision across the engine boundary; input arrays are not mutated, and mismatched dimensions reject before pointer access. Godot-facing tests are in `native/tests/test_godot_bridge.gd`. Dynamic tissue/contact/fracture integration remains separate.

`python tools/validate_native_extension.py` freezes the built DLL and canonical tracked test/config/fixture inputs, verifies their identities, then checks first import and the headless contract. Editor import uses `--quit-after 35 --frame-delay 1000` to mitigate the upstream deferred documentation shutdown race ([Godot#111048](https://github.com/godotengine/godot/issues/111048), [#123658](https://github.com/godotengine/godot/pull/123658)). The earlier25ms delay remained timing-dependent and failed on aplabvxc; an independent fresh copy with identical inputs and1000ms delay exited0. Every observed import progress stage must complete. This qualifies only the recorded workaround path; it is not an engine fix or a guarantee against all shutdown races. `--raw-import` reproduces the original failing path. Runtime tests are undelayed; no simulation step or product frame rate is changed.

Build manifests bind each DLL to source hashes, clean pinned dependency revisions, compiler identity and flags. Cached extension objects include compiler identity. `python tools/benchmark_membrane_kernel.py` verifies its exact DLL/build manifest and parsed fixture identities before and after measurements. Reports are written under ignored `godot/reports/`.

## Captured reference fixture

`tests/fixtures/refined_flap.json` is the first stretch solve in outer integration tick2 after a64segment circle(radius.4) is cut through the actual anterior capsule, yielding745points/1668edges. Grip acquisition is at interior positive-X flap vertex plus.025Y (radius.065, contact radius.018), then the forceps moves.005Y per outer tick. Substep attachment interpolation places the held point at.0025Y before this capture. Alpha=.072. The real flap boundary includes cornea, iris and the actual portal/wound. It is captured before any stretch projection or fracture in that substep, so it isolates the solver input rather than assuming the fractured result is correct. The capturing source is the substep pose implementation committed as ee05602; all1668lambda entries are zero. JSON float values preserve the actual Godot float-vector state.

Independent diagnostic objective values: SciPy L-BFGS-B3.819356697e-8 (relative-energy stopping, gradient_inf1.343e-6), SciPy sparse trust-region3.819275721e-8 (optimality1.583e-8, work exhaustion). Neither is asserted to be an exact unique minimizer. Tests compare energy and strain with a stated allowance and independently recompute the output objective; solver status must additionally indicate convergence to its requested gradient tolerance.

## Standalone contact geometry

`python tools/build_contact_distance.py` builds a separate ignored `contact_distance.dll` with the same pinned compiler/provenance checks and warnings-as-errors. It has no Eigen/IPC dependency and does not modify the membrane or Godot DLL. The standard-library implementation is independent; IPC1.6.1 is only an optional reference oracle.

`membrane_contact_distance(segment6, triangle9, radius, output22)` consumes two finite axis endpoints and three triangle vertices. Every coordinate must have absolute value at most16; radius must be finite and in `(0,.3]`. The caller allocates each array at its declared length. Invalid arguments return-1without writing output.

Output layout: squared axis/triangle distance[0], distance-minus-radius[1], axis witness[2:5], triangle witness[5:8], triangle barycentric weights[8:11], squared-distance gradient with respect to the9triangle coordinates[11:20], axis parameter[20], internal feature tag[21]. Radius only affects the gap; the gradient is of squared axis distance, not the gap. Features may change; tags are diagnostic rather than persistent contact IDs.

Statuses are0regular selected-feature derivative,1axis/face intersection,2degenerate or numerically inconclusive geometry,3numerically tied witnesses with distinct gradients. For2the numerical values are diagnostic and must not certify clearance or drive accepted mechanics. For3the selected gradient is not a unique ordinary derivative. For1zero squared-distance gradient is not a zero physical reaction or a resolved penetration. Exact predicates/CCD/side preservation, contact response and Hessians are outside this component's scope.

The query enumerates at most12candidates without heap allocation. It includes finite axis/face intersection and coplanar clipping, rather than checking only endpoint/edge distances. Internal long-double arithmetic reduces cancellation; it is still finite arithmetic. A conservative oriented-volume cancellation screen returns2when plane/intersection witnesses are unreliable. Numerically indistinguishable candidate distances with different internal gradients return3without an absolute gradient-size floor.

Optional independent comparison: `python tools/compare_contact_distance.py --ipctk-path .tools/ipc-probe-python`. Use the isolated pinned IPC1.6.1diagnostic installation described in the coupled-contact plan; the product does not depend on it. The comparison binds the actual DLL, compiled oracle, fixture and script hashes before/after, checks analytical status cases and minimum gradient coverage, and starts reports unqualified. After canonical endpoint interpolation, the scoped run covers292cases,238regular gradients,30axis intersections,22ambiguous and2explicitly inconclusive cases. Native tests now include17geometry,12coupled and12original kernel cases. This is not application/CCD/performance or clinical qualification.

## Isolated coupled static energy/contact solve

The isolated extension now registers a separate `MembraneContactKernel.solve_contact(Dictionary)` with strict typed packed64 predictor/initial/material/body arrays and packed32 topology. Output positions remain packed64; caller inputs are COW protected. Shape/count/budget checks precede pointer access. The 64-TU extension build caches against all native contact headers. Fresh frozen bridge and existing capsule integration validators pass with DLL SHA256 `2d6689cb8e38d780463e0993226345ff5ca5c9755bc84db5714b4cdfe381492d` (probes `t2_k1hh_`, `vxb6ds4o`). The capsule validator still exercises the older stretch adapter; the coupled kernel is not yet the actual timestep backend.

`python tools/build_coupled_contact.py` builds a separate `membrane_contact.dll` against pinned Eigen. Existing membrane/Godot DLLs are unchanged. `membrane_solve_contact(n,predicted,xyz,inverse,edges,a,b,rest,alpha,faces,triangles,bodies,capsules,budget,force_tol,gap_tol,comp_tol,dual,stats)` has19arguments. Each capsule is7doubles (axis endpoints6+radius); each face is3C ints. Dual output has `faces*bodies` doubles, ordered face-major. Predictor and initial/warm-start XYZ are separate; pins must match exactly. Duals start internally at0and are output-only. XYZ/duals publish only on status0; every nonzero status preserves them.

The objective is the same fixed-predictor mass/compliant-spring energy. Inequality `g=axis_distance_squared/radius_squared-1>=0` is solved with an augmented Lagrangian and nonnegative reactions. Penalty/direction regularization affects numerical solving, not material stiffness or tear strength. Success requires supplied force, scene-unit penetration and energy-unit complementarity tolerances. A numerical sufficient tangent curvature screen checks positive finite pivots in `H_L+rho*J'J`; active contact Hessians are central differences of gradients. This finite-difference/factorization screen is not an exact-arithmetic or global-minimum certificate.

Statuses:0accepted static result;1work exhaustion;2numerical/line-search failure;3prescribed-point penetration;4unresolved contact/derivative geometry;5curvature screen inconclusive/nonpositive;-1invalid arguments. Actual axis/triangle intersections and active ambiguous derivatives reject4instead of inventing a separating reaction. Inactive ambiguous gradients need no reaction and may be ignored. No CCD, original-side retention, anatomical boundary or fracture/extraction advancement is included in this ABI.

Stats12: energy, stationarity infinity, scene-unit penetration, complementarity maximum, completed outer iterations, objective evaluations, current numerical penalty, inner iterations, factorization attempts, last relative linear residual, contact-curvature search models, geometry-inconclusive search-model fallbacks. Unavailable leading residuals and linear residual initialize to infinity. Finite RHS/residual/slope checks prevent overflow from masquerading as a zero linear residual. Bounds:4096vertices,16384edges/faces,64capsules,65536face/body pairs,1000outer iterations maximum; each outer has at most32inner steps,12damping attempts and32line trials. Curvature uses at most8normal-penalty trials.

`python tools/benchmark_coupled_contact.py` verifies the canonical reduced fixture. Optional `--full-export --input PATH` parses a saved actual full-substep diagnostic explicitly. Reports bind parsed input bytes, both DLLs/build sources and the script, reassemble energy/material/contact forces independently in Python through the separately IPC-checked geometry ABI, and verify identities afterward. Latest local reference: energy1.25121888e-8, force residual2.54e-9, median1.92ms. Saved745vertex/708free-point static body problem: energy3.29866367e-9, force1.06e-9, no penetration, median432.66ms across3calls. These are CPU static queries, not app frame times or complete extraction.

Float32 publication is a separate unresolved integration issue: quantizing that full native candidate moves coordinates by up to5.55e-8and changes force residual to4.62e-6. Actual frozen Godot cornea/iris and existing swept body projection make no further position correction on the quantized candidate, but this does not restore native force accuracy. Integration must retain authoritative float64positions/history and separately validate accepted rendering/publication. Whole application promotion/release remains blocked by unfinished implementation, not by a successful static diagnostic.

The optional actual capsule path now retains model-owned packed64 positions/history/rest, transfers them through geometric incision, and solves the fixed predictor jointly through `set_contact_backend`. `python tools/validate_native_extension.py --coupled-capsule` checks actual curved incision,3forceps traction ticks, double predictor/history/pins and transactional failures. `--coupled-extraction` replays the existing full extraction route with the same bodies/anatomy. The latter currently remains unqualified: its first replay accepts263ticks and rejects264on numerical status2. Existing stretch integration still passes separately. The new path requires actual body geometry for grasping and geometric incision instead of coarse blade edge deletion. Body/CCD/anatomy are still float32 rejection guards, not jointly solved double anatomical constraints or native-tolerance continuous clearance certification. No default-backend promotion or new release follows.

Joint endpoint force constraints use `Path.interval.physical_radius`, the original tool profile thickness. Its `radius` continues to include explicit `sweep_padding` for conservative angular/chord guards; caller-supplied no-path enclosures retain their padding. Conflating these radii had created artificial overlap between closed jaws during rotation. Generated path/request regressions and legacy consumers now pass with this separation. This does not by itself resolve the remaining nonlinear second-substep failure or certify a complete operation.

Tick264's exact packed request is a canonical regression. Numerical penalty escalation now requires penetration to exceed the requested gap tolerance as well as insufficient relative reduction, preventing already feasible contact roundoff from driving unnecessary penalty growth. All original physical acceptance gates and100outer/32inner work bounds remain. The captured standalone regression changes from status2toaccepted with independently checked KKT/pins, and all42native tests pass. Rebuilt bridge and actual small-traction validators also pass; this fixes the isolated numerical failure, not yet the complete operation.

The physical-radius second-substep request is also canonical. Inner accepted iterates that already meet the original caller's three physical gates now return to the unchanged outer reevaluation/curvature screen before additional auxiliary oversolving or a dual update. Both native and Godot regressions were observed failing, then pass without changing predictor/material/tolerances/budgets. All43native tests pass; the engine static request reports force1.33494e-9, penetration8.5258e-10and complementarity8.9e-13. Actual small traction and rollback also pass; a complete extraction remains a separate gate.
