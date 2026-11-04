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


The serialized old/cached replay is terminal: return code, coordinates, reactions,
duals and every stats value match bitwise on the exact four-layer failure.
Baseline106.5084s versus cached74.8672s (~1.42x,29.7% elapsed reduction) on this
single input. The failure remains status2 as required for a pure optimization.
[Artifact-bound comparison](../../assets/temporal-hull-cache-comparison-2026-11-05.json).
This is still nowhere near real-time. It does not qualify the engine or full case.


## Fresh physical reactions after changed coordinates

The new owned sparse seed reproduces the four-layer156 failure (REDstatus2,
force3.10494e-8,73.830s with the pure cache). Resetting polish_tried only after
an accepted coordinate update allows the existing physical-dual refinement to
revisit that new x. The same test is GREEN (19.083s) and independently verifies
the original material/inertial/contact KKT, exact holds and original total budget.
No physical parameter, energy, tolerance, SPD or publication gate changed.
Read-only review found no correctness/boundedness/atomicity defect.

[229 tests across20 native suites](../../assets/fresh-physical-reactions-numerical-2026-11-05.json)
are terminal success. [Complete captured156 native resolution](../../assets/fresh-physical-reactions-motion156-2026-11-05.json)
also passes: finalforce1.309019559414537e-11,67/250 total Newton steps and full
interval guard clear. The4-layer solve itself now needs11 steps/20 evaluations,
versus19/113 at the old rejected point. Native/controller exact predictors,
accepted q0, dt, material law, work and pair limits remain unchanged.

The controller was still preventing this cold accurate retry only because the
failed endpoint force1.1889e-6 exceeded its1e-6 RETRY-selection heuristic. A mock
transaction regression is REDbefore removing that upper selection cap and
GREENafter. A companion malformed temporal-force candidate still rejects and
rolls back. Successful candidates retain the final1e-8 native and independent
force gates plus complete path clearance. The one cold retry shares the original
budget and physical predictor; a failed iterate is never used as a seed.
Read-only review found no selection loophole. Real144/146/150/156 engine-core,
44-suite focused regressions and the full22-stage operative run are in progress.
No outer-anatomy/full-case/real-time/GPU/Windows release conclusion follows yet.


## Engine checkpoint verification

The focused44 suites plus fresh import are terminal success.
[Current engine regressions](../../assets/fresh-physical-reactions-regressions-2026-11-05.json).
The actual native core checkpoint stage passes144,146,150 AND156. For156 its
independent engine force is1.298e-11 and exactly one physical/history step is
published after complete recorded-path clearance. Observed time37.906s remains
far from real-time. [Core metrics](../../assets/fresh-physical-reactions-core-metrics-2026-11-05.json)
and [frozen source/build/stage checkpoint](../../assets/fresh-physical-reactions-engine-checkpoint-2026-11-05.json)
retain provenance. The latter is deliberately qualified:false because only21
stages have completed and the22nd full operative route is live. It must not be
presented as a full-route success. Fresh route/anatomy qualification is pending.


## Live full-route progress (not terminal)

The fresh operative route has now accepted160 physical ticks,226 staged incision
events,2811 fine faces and346 controls. Retained material area remains
5.3193263467401275 and independent force1.1967024593495523e-11. Thus it passes
the former155/156 barrier in the actual application path, not just saved cores.
The route is STILL RUNNING; do not call it a completed case or end it on an
observation timeout. Resume exact exec session87686, probe
`.tools/fem-extension-3yegdgdp`, final stageoperative_blade. Last confirmed actual
Godot child PID140144 was consuming CPU; console parent48088 is only the launcher.
[Live progress evidence](../../assets/fresh-physical-reactions-route-progress-2026-11-05.json)
and [log snapshot](../../assets/fresh-physical-reactions-route-progress-2026-11-05.txt).
Product changes are committed/pushed as2888ccb(cache) and8406250(fresh reactions
and bounded accurate retry selection). Main/release/default backend unchanged.

Further throughput inspection finds461 exact ordered control triples shared by
2665 fine faces in the156 fixture. A next optimization can share hulls and zero-
dual certificates across those identical triples while keeping all per-pair
geometry checks. Physical-dual evaluation currently also refines far zero-
reaction gaps; any future certificate reuse there must test physical dual==0,
not its unrelated PHR update, and preserve all geometry/penetration/COMP checks.
These are next candidates, not implemented or qualified changes.
Do not edit validator/build source inputs while the current full run is live:
its terminal source-hash verification must remain valid. Future full runs should
use the transparent capture subclass from the outset to avoid repeating long
prefixes solely to obtain exact failure inputs.
