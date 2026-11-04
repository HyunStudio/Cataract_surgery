# Coupled retained FEM contact implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Solve original implicit membrane energy with simultaneous exact grasp and nonnegative retained-face body reactions; subsequently connect continuous guards and operator input.

**Architecture:** Reuse existing original energy, sparse cell factors and equality Schur projection. Add actual fine Bq capsule constraints with exact smooth-feature Hessians and bounded PHR outer iteration. Stable original energy difference plus conservative contact merit differences and fixed-equality-dual work provide line acceptance. Final original force/gap/complementarity and undamped tangent curvature remain authoritative. No postprojection substitutes for force balance.

**Tech Stack:** Pinned Zig C++17/Eigen, scalar-double GDScript state, Python NumPy independent KKT oracle.

**Spec:** docs/superpowers/plans/2026-11-04-embedded-contact.md Task3 and full active simulator objective.

## Global constraints

- Force1e-8, physical gap1e-9, complementarity1e-11 remain unchanged.
- Retained fine faces only, actual tool geometry, original mass and fixed controls.
- Non-success leaves output positions and both kinds of reactions untouched.
- Static solve alone cannot advance app state until whole-interval guard passes.

## Review focus

- Opposing/redundant rows must not fabricate forces or hide impossible targets.
- Fine collider excludes absent parent material after incision.
- Inactive contact and zero bodies preserve old unconstrained/grasp contract.
- Nonregular witnesses and invalid arrays fail atomically.
- Final curvature is of original Lagrangian on constraint tangent, not a damped objective.

## Task1: coupled native candidate

- [x] RED ABI tests: one/two hands and bodies, independent original KKT, inactive/zero nonregression, impossible target, invalid/budget atomicity.
- [x] Implement shared-internal native solve and provenance inputs; retain bounded loops and stable merit differences.
- [x] Run new and old native qualifications; review, record limits and commit.

## Task2: actual engine time step

- [x] Typed coupled bridge and independent state acceptance of both force contributions.
- [x] Supplied full body-interval guard before committing coupled tissue histories/time/reactions.
- [ ] Connect actual controller/anatomy and cut-remap motion to the complete interval transaction.
- [ ] Actual jaw face acquisition, tool roll and partial-tip mechanics, then actual mouse/keyboard full surgery and active GPU/Windows release qualification.

## Ledger

Previous goal turn was progress: d98a62a added actual bridge/export and real curved static contact,8engine stages and31focused suites. Whole goal active and unfinished, no external blocker. No default backend switch or release.

New ABI testf5b15f RED missing membrane_fem_solve_contact. Implemented retained-face PHR+exact grasp solve in private include membrane_fem_contact.inc sharing existing Problem/SparseCells unchanged. First build13448 terminal0; test32182e had3failures: early two-body inner line stop atforce1.017e-8, and contact floors atforce5.6e-9/gap3.5e-13 butcomp1.86e-10. No candidate published.

Ruling: infeasible AL inner models may minimize to1e-6, but acceptance remains original force1e-8, physicalgap1e-9, comp1e-11 and undamped curvature. Rho progress must include both gap and comp, because a small dimensional gap can still fail the independent multiplier-gap product. This changes intermediate optimization policy, not final physics or acceptance. Build71166 terminal0, first6testsGREEN8bc8d7. Zero-body stats12/13 now0 rather than uninitialized infinite penetration/comp. Added actual impossible held target (not just invalid3hands).

Expanded tests use independent NumPy active-simplex/finite-axis closest-point enumeration, not native distance/gradient, then recompute original elastic/inertial force + held and nonnegative contact reactions.10testsGREEN1d6665, including duplicate contact rows, finite endpoints, void parent, exact zero-body old grasp result/reaction/stats, invalid/budget/impossible atomicity and undamped inactive-contact negative tangent rejection. Source-bound full native qualificationfbce9b terminal0:25tests (8energy+7grasp+10coupled). Engine extension rebuild95365 terminal0 includes .inc source manifest/cache keys. Actual8stage existing-engine nonregression is running; no coupled engine method/step exists yet.

Diagnostic4case read-onlya59aa3 independently verifies: free/one/twohands/twobodies use26/29/30/31Newtonsteps and13/14/16/15outer indices, finalforce2.76e-10/8.52e-11/1.23e-10/3.06e-10, penetration<=4.17e-17, comp<=1.05e-13, rho1e5. Synthetic three-control tests only; not real tissue calibration, actual-case throughput or full contact qualification. Read-only numerical review pending.

Read-only numerical reviewer found no actionable correctness issue and independently ran10contacttests. Recommended nonnodal held-point/fixed-control coverage: added nodes[0,1,2],weights[.7,.2,.1],inverse[0,1,2] and independent held point/reaction pullback/fixed coordinates/KKT checks.11contacttests1ed343 pass; latest source-bound qualificationfa8575 terminal0:26tests(8+7+11). Report docs/assets/fem-coupled-core-validation-2026-11-04.json.

Freshly rebuilt extension's actual existing8stage3330 terminal0 in fem-extension-ru68yfbm. No errors/leaks/source changes. Report docs/assets/fem-coupled-build-engine-regression-2026-11-04.json. These stages prove old energy/grasp/static-query engine nonregression with the new linked core; they DO NOT exercise a coupled Godot step. All started jobs terminal. No Godot source changed this turn, so the prior31suite source-bound focused engine report still applies to those unchanged scripts; full default -Test remains RED on the separately preserved GS cases.

Next: expose typed solve_contact_fem bridge and independently verify both reaction contributions in accepted original physical force. Add true whole-interval fine geometry guard before any history/time commit, including held motion and actual anatomy. Then continuous jaw face acquisition/tool roll/partial-tip support, actual closed incision and traction, full surgical mouse case, GPU throughput and Windows delivery. Current private .inc shares original sparse/energy machinery; it is not an alternate spring law or postprojection fallback. Whole goal remains active and unfinished.

Task2 bridge RED18679 terminal1 missing solve_contact_fem. Added exact packed type/shape/count checks before C ABI pointers; failure returns original xyz and empty both reaction arrays. New standalone/extension builds77972/29291 terminal0.26native source-bound checks246b17 terminal0. State API REDa9295a missing advance_contact, then fake contractGREEN10da85. Optional coupled path stages both reactions, derives current capsules solely from guard's41value physical packets, recomputes active contact B-transpose forces via independently checked witness, adds actual inertial/elastic/grasp force, then calls existing full double fine-motion guard before ANY accepted position/history/target/reaction/clock mutation. Inactive duals need no ordinary derivative; full interval guard covers all actual fine faces. Only guard stat4 permits documented +INF unsampled nearest gap, no other nonfinite diagnostics. Existing noncontact API/default app path preserved.

First real10stage14586 terminal1 at4test assertions, not a force/guard failure: test wrongly required positive contact dual on every later inertial tick. Saved metrics show force<=5.79e-9 and comp0 on separating ticks, and true linear crossing correctly rejected with full rollback. Independent Python/NumPy6tick replay2f4a82 confirms first dual3.3785/6.8503 then0 with positive physical gaps.01756..03524, all original KKT gates. Ruling: fix the test's adhesive-contact assumption; do not change physical inertia, geometry, forces or success gates. Require positive first pressure and zero dual + independently positive clearance on later separation. Added quaternion-arc interior crossing and malformed guard -INF/+INF/NaN field cases. Prior32focused regression50924 terminal0; new actual10stage2555 and fresh32suite41948 reruns are live after targeted test changes.

Read-only step reviewer found no confirmed ABI/math/sign/transaction defect. Coverage suggestions: nonidentity active B, multi-face/body scatter, zero-dual nonsmooth, curvedkind1 and nonfinite diagnostics. Current added tests cover guarded inactive separation, kind1 arc and extra diagnostics; real nonidentity/multi-face/body coupled dynamics remain next qualification work. Whole-interval/body task split above only records verified partial delivery; anatomy/controller/remap scope is still explicitly open and not waived.

Final actual10stage2555 terminal0 in fem-extension-6trlnfwv, source/hash/leak/error checks all pass.6coupled ticks: independentforce<=5.785541e-9, comp<=1.673187e-14, first dual3.3785/6.8503 then0withclearance.01756..03524. Actual linear and kind1quaternion interior crossings reject at guard with full accepted-state rollback, despite statically clear endpoints. Report docs/assets/fem-guarded-step-engine-validation-2026-11-04.json; current26test core report fem-guarded-step-core-validation-2026-11-04.json. Focused source-frozen32suite41948 terminal0, no errors/leaks/source changes; fem-guarded-step-regression-2026-11-04.json. All jobs terminal. No default app/GS changes, main integration, push or release. Both previous and current goal turns are progress; complete simulator objective remains active.

Next actual task: exercise refined curved B and multi-face/body indexing under real coupled dynamics, record any causal numerical/geometry failure. Extend actual material jaw-point acquisition, surrounding-anatomy/controller authority and cut-remap guard, then qualify actual blade-to-forceps route and full preparation-to-review operator case. Tiny triangle timings are diagnostic only, not throughput or whole-surgery evidence.
