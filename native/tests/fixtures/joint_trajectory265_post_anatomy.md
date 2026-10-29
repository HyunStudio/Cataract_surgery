# Actual265 second-substep trajectory failure after anatomical refinement

Captured from terminal whole-step replay `.tools/joint-current-replay-8y23t5vb`
using extension SHA256 `8fd3acc87548dd3835ffb331056cca63309c55907099a069646590e9a6c64746`. The replay proof binds current
native sources and explicitly overlaid canonical Godot scripts. No new full
extraction prefix was run. Original checkpoint remains immutable.

The first substep's final anatomy solve44 passes independent force7.1330433e-9,
gap6.0715e-17 and complementarity4.48784e-13. All final tool/anatomy guards clear.
In the second substep, endpoint solve58 passes; guard59 proves a tool collision
of2.38342e-9 at time.03125. Adding that physical time produces request60, preserved
byte-for-byte here. Its SHA256 is `a288ccc5827e310af2d76fa04e54cb8701571c9a2c737fd73a5a8d0d8a28bad6`.

Actual engine request60 returns status1 after100outer iterations/8581evaluations/
2978models/16908factors. Final force residual.0021222492831460375, no penetration
or complementarity violation; the force gate fails. Position publication is
unchanged. Whole tick rolls back to accepted264, with no material loss/fracture
or accepted uncertainty. This is a known failure fixture, not a passing test.

The context JSON preserves the immediately preceding endpoint reactions and rho,
with prior_times=[1]. Initial positions exactly equal that accepted output.
The current API restarts reactions at zero and baseline rho on every refinement.
The context is for a generic, independently reviewed warm-start experiment; it
has NOT been integrated or shown to resolve this failure. Do not special-case
this fixture, increase work bounds or weaken physical acceptance to pass it.

Diagnostic timing of the identical standalone request: budget0 .084882seconds;
budget1 6.733436seconds, status1/atomic rejection. No real-time claim.
