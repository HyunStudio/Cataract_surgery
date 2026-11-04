# Motion156 diagnosis and immutable temporal hull caching

Continue the full simulator objective frombc47700; binary64 blade route accepts155
physical ticks, then endpoint candidate fails. Offline temporal witness retries
reach a four-layer native failure at force3.10494e-8 after75/250 steps. No full
operation, real-time, GPU or Windows release qualification exists.

1. Freeze an isolated diagnostic source copy. Reproduce the last valid native
   candidates from original predictor/q0/motion, save the exact numerical seed for
   the failing four-layer solve, and trace stop/polish/line decisions. stats[14]
   is AL outer-loop index, not a failure reason. Do not infer the internal branch.
2. RED cached versus original literal outward-hull inactive certificates on
   random, near-threshold, translated and changing time/body/dual/rho inputs.
   Preserve caller FP restoration and numerical bitwise behavior.
3. Cache each original-control/time/candidate hull in its ContactState. Rebuild
   on every evaluate, swap with its candidate, reuse across bodies and merit
   comparison only. Never reuse across coordinates or infer inactive contact from
   rounded geometry. Keep every full geometry query and all physical gates.
4. Verify original/cached certificate equivalence, original numerical regressions,
   actual144/150/156 original KKT and complete guard, and same numerical output
   against the frozen baseline. Measure throughput on identical problems.
5. Only after diagnosis, fix the demonstrated minimization cause with a failing
   regression and unchanged original force/gap/COMP/SPD/budget gates. Qualify exact
   engine state and repeat full route; preserve next failure instead of declaring
   whole surgery complete from a component pass.


## Frozen diagnosis

The original source copy reproduces the four-layer motion156 result bitwise,
including all16 stats. Its copied baseline DLL and native source closure were
independently checked against the prior source-bound build manifest. The first
trace tool did not perform that preflight itself; it was verified afterward.
Future invocations now verify manifests and the Eigen pin before freezing.

The terminal branch is failed Armijo line search at iteration19/AL outer5.
All32 comparisons are valid. Nominal slope is-1.829296774920474e-25; fraction1
has represented movement infinity norm4.6407322429331543e-14 and merit upper
change8.13314710542786e-25. Thus no trial can be accepted by the original rule.
Polish was last attempted at iteration10, where its proposed original force
was3.019822561456387e-8. Nine later accepted Newton coordinate changes do not
reset polish_tried. At the represented terminal point an independent NumPy/
SciPy nonnegative contact-cone check finds the same single contact with original
force residual1.0164150771041491e-11. That is a hypothesis, not a native accepted
candidate or a complete interval proof. It motivates a failing regression on
fresh physical multiplier refinement after each changed coordinate iterate.

- [Source-bound original trace](../../assets/operative-motion156-stop-trace-2026-11-05.json)
- [Original comparison/line summary](../../assets/operative-motion156-line-summary-2026-11-05.json)
- [Independent contact-cone hypothesis](../../assets/operative-motion156-cone-hypothesis-2026-11-05.json)

## Immutable hull cache

Each ContactState owns one outward original-control hull per face/time. evaluate
rebuilds it for that exact x, and state/next swaps or physical-polish moves carry
it with the corresponding coordinates. It excludes body/dual/rho: their current
pair-specific thresholds are still evaluated separately. Every full distance
query, bounded gap, derivative, merit, force, COMP, exact hold, linear residual,
SPD and whole-interval guard contract remains. With active bodies the existing
65536-pair budget also bounds cache storage (~6MiB per state on this ABI).

New test-only ABI was absent (RED), then cached and unchanged literal original
certificates agree over500 randomized/transformed cases, near-threshold cases,
changing body/time/dual/penalty and all64 caller FP contexts. Four new tests pass.
[228 tests across19 native suites](../../assets/temporal-hull-cache-numerical-2026-11-05.json)
are terminal success. Read-only review found no substantive defect in indexing,
state ownership/invalidation, outward arithmetic or memory bounds. This is
component qualification; no convergence, engine, full-route or real-time claim.
An old/cached serialized bitwise/timing replay is running on frozen DLL copies.
