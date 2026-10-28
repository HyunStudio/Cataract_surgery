# Experimental membrane numerical kernel

Optional actual-capsule integration exists, but is not the default backend. Full refined extraction still rejects the263rd requested tick for unresolved elastic/contact coupling. The new standalone contact geometry component below is not yet connected to Godot or the joint solver.

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
python -m unittest discover -s native/tests -v
```

Eigen5.0.1 is pinned at `bc3b39870ecb690a623a3f49149a358b95c5781d`; see THIRD_PARTY.md and licenses/. The previous matrix-free implementation is preserved in commit739fa46. Its captured scene cost was about.21s. Current sparse solve measured.046–.053s across6standalone calls, with E3.819273056e-8, gradient_inf2.697e-9,24outer iterations and30factorization attempts. This is still slower than a60Hz substep budget and is not an app performance result.

## Isolated Godot bridge

`python tools/build_membrane_extension.py` builds `.tools/native-godot` with the pinned godot-cpp4.5bindings. It does not modify the product project's resources or install a native dependency into the released app. Its packed XYZ and inverse/rest arrays retain float64precision across the engine boundary; input arrays are not mutated, and mismatched dimensions reject before pointer access. Godot-facing tests are in `native/tests/test_godot_bridge.gd`. Dynamic tissue/contact/fracture integration remains separate.

`python tools/validate_native_extension.py` freezes the built DLL and canonical tracked test/config/fixture inputs, verifies their identities, then checks first import and the headless contract. It applies an editor-only1000msframe delay to mitigate the upstream deferred documentation shutdown race ([Godot#111048](https://github.com/godotengine/godot/issues/111048), [#123658](https://github.com/godotengine/godot/pull/123658)). This qualifies only the recorded workaround path; it is not an engine fix. `--raw-import` reproduces the original failing path. No simulation step or product frame rate is changed.

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

Optional independent comparison: `python tools/compare_contact_distance.py --ipctk-path .tools/ipc-probe-python`. Use the isolated pinned IPC1.6.1diagnostic installation described in the coupled-contact plan; the product does not depend on it. The comparison binds the actual DLL, compiled oracle, fixture and script hashes before/after, checks analytical status cases and minimum gradient coverage, and starts reports unqualified. The latest scoped run covers292cases,232regular gradients,30axis intersections,28ambiguous and2explicitly inconclusive cases. Native tests cover16contact queries/contracts plus12existing kernel tests. This is not a complete coupled solver, application performance or clinical qualification.
