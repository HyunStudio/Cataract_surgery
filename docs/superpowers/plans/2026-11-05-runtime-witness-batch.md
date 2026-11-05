# Runtime witness batch implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Reduce interpreted all-face witness overhead toward real-time surgery without omitting physical inspections or changing accepted results.
**Architecture:** Ephemeral per-layer geometry preparation and the existing bounded all-pair native API; keep scalar fallback/reference, independent per-pair validation and all final force/CCD gates. No cross-call cache, culling or physical-zero shortcut.
**Tech stack:** Godot4.7.2, existing optional GDExtension and binary64 material state.

Measured owned180 baseline:127391ms; solver11calls7.913s(6.21%), scalar witness1,791,924calls20.940s(16.44%), full guard9calls.023s, other engine98.515s(77.33%). Result dictionary and accepted controls exactly match qualified baseline; source/artifact/script/fixture hashes checked. This was concurrent with a route and is not a controlled throughput comparison. Evidence: docs/assets/temporal-cost-profile-2026-11-05/.

- [x] RED independent engine batch protocol tests: require API, typed ordered result, scalar parity, bad final status/value/bary/reconstruction/minimum, unavailable API, ownership, capacity. Test full packet atomicity; malformed bulk must never quietly scalar-fallback.
- [x] Refactor material_surface_query.gd into exact-order per-face preparation and per-witness validation shared by scalar/batch. Batch owns per-call geometry, validates every ordered pair, publishes packed values only after all validation. Preserve scalar result/error semantics and caller ownership.
- [x] Connect MaterialNormals._inspect to batch only when supported. Iterate face/body in identical order and acquire same barycentric rows. Existing scalar backends unchanged; full per-layer inspections and complete final motion guard stay mandatory. No new tolerance/budget/capacity relaxation.
- [x] Forward bulk API in capture and actual-test proxies. Add actual typed scalar/batch bit parity and old/malformed last-pair coverage. Test exact150 and180 accepted control/result parity, total work/history and rollback. Update source-bound focused/engine validators with new tests.
- [x] Requalify relevant focused suites/actual engine on frozen input. Profile same owned180 with transparent counters including bulk call count; compare controlled paired runs only after exact parity. Adopt only demonstrated gain. Native numerical source remains unchanged, so validate existing279report input/build hashes rather than repeating unrelated math tests.
- [x] Record current route/CI result and measured limits; commit. Full simulator goal stays active: no full-case/real-time/GPU/native Windows-release claim from component checks.

Independent native physical-zero proposal is deferred: even eliminating all measured solver time cannot address most observed cost. The rounded-radius² proof issue must be solved before that separate optimization.


Implementation progress: RED missingbatch; GREEN packet tests. RED temporal
integration previously calledscalar/ignoredmalformedbatch; GREEN new runtime
branch. Shared validator preserves original arithmetic exactly after offset/status
normalization. Original scalar test passes. Native actual bridge and whole-state
150/180 parity are running frozen (.tools/fem-extension-2b686da9),35stages;
focused60suites frozen .tools/embedded-regressions-e65o77qt. Do not mutate frozen
inputs or current source during source-bound validation. No speedup claim yet.

Continuous route on prior962e061 is TERMINAL failure, not a live wait: source
snapshot .tools/fem-extension-e83q8l5s,152acceptedsteps/209STAGEDcut events,
2354finepoints/2581faces/346controls. New fixture
operative-motion153-temporal-state.bin SHAf27759220fa994a9dc09babb031575509d0bfff6dd3944c7c3d178f92827102d.
Raw owned153 request history archived; totals16+17+21+17+8+81+11+79=250.
At t[.375,.5,1] one warmcandidate needs81Newton; final t[.3125,.375,.5,1]
exhausts79 with force5.81677. Bulk work must preserve this physical failure,
not hide it. Solve after exact adapter parity/performance evidence; no whole
route/central material detachment was qualified. Remote962e061 native/PythonCI
success; defaultGodotCIstillfailure andrender skipped.


First actual35stages and60focused suites PASS. Entire state/result byte parity
150 and180 PASS; every original pair still queried:150753008pairs76bulk calls,
scalar104288ms→batch46187ms;1801791924pairs93bulk calls,151288ms→55294ms.
These are one controlled paired comparison per owned step, not full case/FPS.
Initial independent batch180 gate52078ms (same177Newton/result); improvements
remain far from real-time. Native source unchanged.

Self-review found an important error-path gap AFTER this first full run: invalid
bulk returned generic material_normal_geometry, so Embedded could try ordinary
fallback. Added two whole-advance RED assertions (primary/fallback) then fixed
explicit material_normal_batch_geometry as a fatal protocol result in both
selection paths. Prior spent work remains preserved. GREEN priority, batch and
temporal protocol tests. Full35+60qualification is being rerun on final source;
earlier proof is archived explicitly as before-protocol-fix evidence.


Failed153 parity on the pre-protocol-fix frozen snapshot2b686da9 PASS: both
scalar/bulk still reject material_normal_budget, same250Nativework and exact
failure result plus unchanged full source-state bytes.237452pairs match,23bulk
calls. Logs/script/metrics archived docs/assets/witness-batch-failed153-2026-11-05/.
The final protocol fix changes only rejection of invalid geometry packets;
this owned153 failure involved valid proposals and an unresolved physical solve.
Do not mistake this parity qualification for successful153physics.


FINAL current source:35actualengine stages PASS (.tools/fem-extension-09_u69hm),
60focused suites PASS (.tools/embedded-regressions-nhi7l3sk), current/frozen input
hashes match. Existing279native report/build inputs remain unchanged and valid.
Second paired15086383→46555ms;180143876→47370ms. Both full accepted states/
results byteexact; original753008/1791924pairs,155/177work unchanged. These
repeat the first comparison's improvement but are not full-case/FPS qualification.
Current separateowned180gate55560ms is still far from real-time.
Archived final reports under docs/assets/witness-batch-final-*.
No Native numerical code changed, no pair culling or tolerance/budget relaxation.

Narrow read-only review approved final fatal error propagation/work accounting.
Next: retain failed153 as unresolved, investigate its numerical conditioning with
exact requests, and qualify piecewise time dynamics independently (see
2026-11-05-piecewise-dynamics-assessment.md). Do not rerun a long prefix merely
to rediscover the same owned failure; do not claim a full surgery/GPU/release.
