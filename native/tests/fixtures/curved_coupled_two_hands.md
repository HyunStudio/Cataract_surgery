# Actual retained curved two-hand contact regression

`curved_coupled_two_hands.json` contains the exact native request saved by
`godot/tests/test_embedded_coupled_curved_native.gd` in frozen probe
`fem-extension-d76d95gk`. Synthetic capsule only, no patient data.217controls,
396original material energy cells,404retained fine collision faces,2held points
and2pressure spheres. The test uses real nonidentity material B maps after an
actual finite incision; it is not an actual jaw/controller/full-surgery case.

Original real engine result: budget250, force5.8737726238e-8, physical penetration
5.9576936314e-12, comp4.1978498291e-11, original state fully rolled back. One-hand
cases at bothmu2and10000pass. The exact same saved request passes in a Python
process with x87 control0x27f, but reproduces the engine failure bitwise after
setting x87 precision64(control0x37f). FTZ/DAZ toggles make no difference. The
isolated probe always restores caller control and is never linked into product.

The policy switched to exact inner minimization at comp<=10*tol, although final
comp still failedtol. That forced convergence of an intermediate AL model
instead of updating its outer dual/rho; damping grew70.37 and tiny line steps
spent the250budget. The saved final observer has slope-1.30372e-21 and accepted
fraction.5, not evidence that precision should be lowered. Change inexact inner
activation to ANY remaining constraint violation(comp>tol), keeping the original
final force1e-8/gap1e-9/comp1e-11 and undamped curvature. Tests now independently
check original NumPy KKT/finite contact under both caller precision modes.

Microsoft documents the Windows x64 x87 control defaults and nonvolatile
control-state convention in its [x64 calling convention reference](https://learn.microsoft.com/en-us/cpp/build/x64-calling-convention?view=msvc-170).
The observed different callers motivated this explicit regression; a whole
boundary audit of long-double interval assumptions remains separate from this
intermediate-model policy fix.
