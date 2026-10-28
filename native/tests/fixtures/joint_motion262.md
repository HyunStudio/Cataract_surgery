# Actual intermediate collision at request262

Frozen full replay `.tools/membrane-validation-hook4w9h` uses the outward-rounded plane certificate and accepts261 complete outer ticks. Request262's first substep passes static force/contact gates, then its continuous guard reports status1, face40/body1, minimum sampled gap-9.0830284e-8 at local time.5. The whole outer request rolls back without material loss or broken edges. This is a detected collision, not a query-budget failure.

Captured files:

- `joint_motion262.json`, SHA256 `a776584e556c29ba719195988ac8d905d21dffe8ebeeaa5c57379d369f40fd491`: actual packed guard request, including [.0,.5] of the original pose path.
- `joint_static262.json`, SHA256 `19220bb4824678b619d67e92cc6ec4e924f9722a92cab089dd0424974519b1a2`: actual corresponding static solver request. The accepted candidate has energy1.73313e-9, force7.964e-11, endpoint penetration6.791e-11 and complementarity0.
- Ignored rejected outer-state binary SHA256 `626f6cf30de0e26d51cd5a2433accd24e029f9afc1d9eaa9a8ac0d17c99b8f52`.

Diagnostic `replay_motion262_capture.gd` exported these packed requests directly. Independent SciPy pose interpolation at10001 times finds minimum gap-9.0830338e-8 around local time.5004. At time.5 the nearest point has barycentric weights [.0753713141,.6982203730,.2264083129] on source vertices[222,742,1], at body-axis parameter0 (the jaw endpoint). Vertex742 is prescribed, but its own capsule gap is+.0169255855; the penetrating face witness lies in the triangle interior. Thus this is not explained by a prescribed grasp point already inside solid jaw geometry.

Keep the guard's rejection regression. The next physical solve must account for intermediate-time contact constraints as well as endpoint constraints, and still pass complete-interval checking. Do not make this captured candidate pass by removing bodies, increasing gap tolerance, projecting it after force convergence or accepting sampled endpoints alone. These are numerical scene-unit diagnostics, not surgical measurements or clinical validation.
