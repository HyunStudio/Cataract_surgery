# Experimental membrane numerical kernel

Not connected to the product yet. Godot's current refined-traction test still fails.

The standalone kernel minimizes

`E(x) = sum_free |x_i - predicted_i|²/(2 inverse_mass_i) + sum_edges (|x_a-x_b|-rest)²/(2 alpha)`.

Pins (`inverse_mass=0`) remain exactly at input positions. The edge energy is the existing compliant-distance engineering model; this does not add a clinically calibrated capsule constitutive law, bending, or fracture mechanics.

## ABI contract

`membrane_solve(n, xyz, inverse_mass, edge_count, a, b, rest, alpha, budget, gradient_tolerance, stats)`

- Input XYZ and inverse mass are double precision; endpoint arrays contain C ints. Arrays have their declared lengths; the C caller owns allocation. Output XYZ replaces accepted finite iterates.
- Return `0` for gradient convergence with no detected negative coordinate curvature, `1` for outer budget exhaustion, `2` for numerical/line-search failure, `3` for a certified unstable stationary point, `-1` for invalid inputs. Invalid input leaves XYZ untouched. Numerical failure must never be treated as convergence. The coordinate curvature screen catches a compressed symmetric saddle but is **not a full Hessian stability certificate**; status0does not prove a minimum. Coupled buckling and deterministic saddle escape remain unqualified before runtime integration.
- Stats contain8doubles: energy, free-coordinate gradient infinity norm, completed outer iterations, objective evaluations, total CG iterations, final relative CG residual, minimum accepted line step, final direction damping. Before a valid objective evaluation, energy/gradient are infinity, not misleading zeros. No hidden runtime claim follows from these counters.
- Initial scope requires strictly positive finite compliance alpha, positive finite rest lengths, inverse masses in `[0, 1e12]`, finite coordinates, at most4096vertices/16384edges and at most1000outer iterations. Exactly collapsed active edges reject explicitly pending a well-defined direction model.
- Building/testing does not integrate the solver into Godot, solve contact coupling, or approve a release.

The matrix-free direction uses the exact distance Hessian, including transverse geometric stiffness. A positive GN diagonal provides a direction-only Levenberg metric. Negative-curvature CG attempts increase that damping, with at most12attempts/outer iteration,512CG steps/attempt,32backtracking evaluations/outer and1000outer iterations. Exhausting curvature retries can leave a truncated descent direction; energy backtracking still applies. The residual diagnostic belongs to the last attempted CG solve, so it can exceed the target on truncated attempts. This is not a numerical-convergence flag; callers must use the returned status and objective gradient.

## Local build and checks

Install/extract the official Zig0.17.0 Windows compiler into `.tools/zig-x86_64-windows-0.17.0` only after verifying the manifest SHA256 `b5663f69581dcf391293fbf16c06cb80d81d806545ce618b4d0bab7f0eb8c428`.

```
python tools/build_membrane_kernel.py
python -m unittest discover -s native/tests -v
```

## Captured reference fixture

`tests/fixtures/refined_flap.json` is the first stretch solve in outer integration tick2 after a64segment circle(radius.4) is cut through the actual anterior capsule, yielding745points/1668edges. Grip acquisition is at interior positive-X flap vertex plus.025Y (radius.065, contact radius.018), then the forceps moves.005Y per outer tick. Substep attachment interpolation places the held point at.0025Y before this capture. Alpha=.072. The real flap boundary includes cornea, iris and the actual portal/wound. It is captured before any stretch projection or fracture in that substep, so it isolates the solver input rather than assuming the fractured result is correct. The capturing source is the substep pose implementation committed as ee05602; all1668lambda entries are zero. JSON float values preserve the actual Godot float-vector state.

Independent diagnostic objective values: SciPy L-BFGS-B3.819356697e-8 (relative-energy stopping, gradient_inf1.343e-6), SciPy sparse trust-region3.819275721e-8 (optimality1.583e-8, work exhaustion). Neither is asserted to be an exact unique minimizer. Tests compare energy and strain with a stated allowance and independently recompute the output objective; solver status must additionally indicate convergence to its requested gradient tolerance.
