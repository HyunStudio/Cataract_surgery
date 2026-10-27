# Integrated specialist simulator validation — 2026-10-28

This report applies to the new default `simulator.tscn`, not the earlier procedural `main.tscn`.

## Latest verified milestone — production `be14d7f`

This section supersedes the historical working-state reports below. Fresh standard Godot runner: **52 suites, exit0** (`admitted-flow-full52.log`). Fresh Python regression: **541 passed**; this includes19 export-validator checks, including an actual local Godot PCK collision regression. Production source was unchanged during export qualification; later changes only isolate controlled fixtures and add validation tooling/documentation.

Current full normal encounter passes with0failures in three separate runs: headless source (`actual-admitted-flow-encounter.log`), NVIDIA GPU source (`admitted-flow-controlled-gpu.log`) and the identical Windows release engine mounting the compiled production PCK (`admitted-native-full.log`). Actual bounded target motion, bilateral entry/withdrawal/exchange, actual flap extraction, current admitted-flow material transport, nucleus/cortex removal, IOL delivery/alignment, wound checks, immutable review and reset assertions remain enabled. Final removed mass1.0, retained detached area0, extracted flaps1, no corneal/posterior breach. Retained/cut-loss/extracted rest areas3.253985/1.813249/.252092 and252broken edges expose the remaining coarse-cut limitation. Fresh GPU extraction/result images were inspected.

GPU adverse source (`admitted-flow-adverse-gpu.log`) exits0 and verifies actual posterior damage/outflow, action stop, completion refusal and reset; fresh image inspected. Original exported `OphthoSim-Surgical.exe --quit-after 120` also exits0 on RTX3070Laptop/NVIDIA566.14 (`admitted-native-startup.log`); stderr is empty. This startup gate is separate from the mounted-pack fixture gate.

Exported executable SHA256: `d34d36f3be1a6c49c56525ae86469b92e4f417ddf0b43cf00dd80c385c4b0562`.
Production PCK SHA256: `a795b81dff7a7d65cad2ba3a18b1aaf40c941e215e7fe66580ff86af4da5775e`.

`tools/validate_export.py` freezes both candidate files, builds a separate tokenized QA pack, and runs a byte-identical release executable. The bootstrap verifies the production PCK hash and mounts it with `replace_files=false`, preserving the trusted fixture namespace. A real collision regression demonstrates that an overlapping product path cannot replace assertions. Early nonzero fixture exits, colored engine errors, missing completion markers and changed artifacts fail qualification. Reports retain source state, raw/adapted fixture, adapter/editor/QA-pack hashes, logs and PID. No validation files are included in the user release.

```powershell
python tools/validate_export.py godot/build/candidate-be14d7f/OphthoSim-Surgical.exe --scenario control
python tools/validate_export.py godot/build/candidate-be14d7f/OphthoSim-Surgical.exe --scenario adverse
python tools/validate_export.py godot/build/candidate-be14d7f/OphthoSim-Surgical.exe --scenario normal
```

The compiled-resource test does not test the original main scene. Neither source nor native target-driven automation establishes human mouse/keyboard choreography, clinical validity, sustained real-time performance, fine CCC mechanics or actual corneal tunnel integration. Earlier47/50-suite claims and `b1f60f9` package references below are historical, not the current source result.

## Current working source: actual-part continuous motion

Rigid motion now advances using the distance of the actual nominal part, following the normalized signed portal axis and the shared world-up render frame. Endpoint speed bounds include frame rotation and jaw articulation; numerical portal-distance allowances reduce the denominator bound. Existing chord/radial bounds only select candidate faces. They cannot independently create physical contacts or injury. A previous thin-triangle sleeve near miss is now certified clear rather than blocked. Near-pivot numerical padding cannot invent distant powered contact; a failing reproduction drove nominal-radius-only contact queries. Zero-insertion orientation changes remain unresolved unless all-axis halfspace pruning establishes clearance. Query and iteration exhaustion reject atomically with reasons.

Contact-time metadata and endpoint-speed retreat support stationary articulation. An atomically rejected future jaw pose is marked conservative before injury dispatch, so a pose that was never committed cannot damage current tissue. Actual initial contact retains part-relative load. This closes a new failing regression found while adding continuous nominal motion.

Fresh six-suite batch passes: pivot, rigid app, injury parts, anterior body app, tool exchange, and the rewritten continuous default adverse case. The adverse route now uses normal target controls from actual entry to wrong-depth posterior contact, rather than injecting an inside pose across the signed portal. It preserves speed bounds and verifies actual posterior aperture, outflow, alert/action stop, completion refusal and reset. Actual NVIDIA rigid app and continuous adverse source runs both exit0; editor import exits0. A separate bilateral entry/actual exterior tool-exchange test passes and is included in the51-suite runner; no fresh all51-pass result is claimed.

The old1800-step opposite-cortex diagnostic completed with global adhesion release1.0 using admitted flow, even while the older conservative bent-tip envelope held the tip. The new canonical normal case now chooses an opposite cortical site and requires admitted surface-flow propagation to>.95release; the live current run reports.951006with no alert and no corneal/posterior damage after actual flap extraction. Its downstream phaco/IA/IOL/full completion is still under verification. The old near-entry path is not forced through iris, tissue thresholds and removal/retained-piece completion gates remain unchanged.

No new active GPU performance measurement, native release or ZIP is qualified by this working continuation. The previousb1f60f9Windows archive remains the delivered verified package. Corneal body/tunnel integration, anterior uncertainty/performance, precise cut mechanics, full human input usability and clinical calibration remain incomplete.

## Previous pivot-constrained iris/posterior integration evidence

The current source adds rigid generic shaft/sleeve/working-part envelopes against actual iris/posterior meshes. Tip interpolation and normalized signed portal axes remain constrained; no off-pivot overlap translation is applied. A second-order normalization bound encloses centerline curves; radial envelopes enclose off-axis parts. Initial overlap/uncertainty blocks rather than inventing clearance. Corneal body/tunnel integration remains pending.

Immutable packed-array geometry snapshots and face AABB candidate filtering retain original face IDs/revisions. Same-revision edits invalidate the cache; an indexed/exhaustive actual-anatomy comparison matches exactly. Explicit geometry/query/kernel budgets fail closed; missing-witness exhaustion cannot publish triangle-1 as injury evidence. Only an exact nominal part query can promote an envelope candidate to proved contact. Physical part witness movement, including articulation, supplies the relative load.

Injury dispatch preserves per-part cutting/energy eligibility and suppresses unproved conservative candidates. Stationary actual tip power is neither suppressed nor diluted by a same-face body candidate. Accepted binary articulation is tested after accepted pose motion and consistently used by rendering, ToolPath geometry and history. Capsule grasp intent additionally requires active user intent, preventing re-grasp after release. Tool replacement clears articulation. This sequential rigid acceptance does not prove a unique simultaneous elastic pose/articulation path; capsule ToolPath still interpolates endpoint states.

Focused default rigid-body, part dispatch and pivot geometry tests pass, including actual-iris shaft-only contact, speed/pivot/reset, blocked jaw opening with clear closed-jaw withdrawal, eventual opening, source mutation, false envelope witnesses, prior jaw state and budget exhaustion. Actual NVIDIA default rigid-body GPU test exits0, screenshot inspected. No new sustained GPU measurement or native/archive export is claimed. The standard runner now includes50suites but no fresh all50-pass result is claimed.

Current full-route investigation: entry, opening and actual flap extraction pass, but the old hydro driver aims at near-entry cortex around(1.0278,-.1542,0); the actual cannula stops around(.4825,.0337,0)at shaft/iris contact. A120-step diagnostic confirmed the repeated blocked target. The4500-step run was intentionally stopped after this geometric cause was confirmed, not because an observation wait expired. An opposite-hemisphere admitted-flow propagation probe is in progress. Existing direct-teleport adverse fixture also fails its posterior-puncture assertions under the new body constraint and needs a physically admissible adverse route. These are unresolved integration issues; the ZIP below remains the previousb1f60f9verified milestone.

## Continuous pointer control investigation — current continuation

The first unintended noncut tear in the previous driver was traced to a2.055645-unit cannula teleport in.05seconds. The canonical default encounter now uses normal target controls and bounded continuous movement, persistent hydro targets, actual aspiration transport and unchanged outcome gates. A real signed-pivot entry stall was reproduced and fixed by retracting to the pivot before crossing between inside/outside poses. Rig and integrated default-app approach regressions pass; independent scoped review found no substantive issue.

The first continuous run removed100% material with no retained detached flap, but its final wider-injector route contacted the inner tunnel edge, exceeded a per-tick displacement assertion and failed wound completion. A centered collision-free path was isolated and added. The fresh standard47-suite runner exits0, including the complete continuous default encounter, adverse injury, extraction, exchange and clock/presentation cases. This is not evidence that collision recovery or actual tunnel publication is complete. Full anterior contact uncertainty, coarse extra edge failure and runtime cost remain open.

Fresh editor import and Windows release export exit0; the newly exported default native app launches for120frames and exits0 with the actual RTX3070Laptop/NVIDIA566.14 OpenGL context. Source-run GPU adverse case reports0failures. The final source-run GPU normal encounter also reports0failures:100%mass removed, one extracted flap, zero retained detached area, IOL/wound checks passed and zero corneal/posterior injury. The fresh result image was inspected. Final retained area3.210435, cut-loss1.849384, extracted area.259507and255broken edges show the remaining coarse-edge failure. These source-script runs do not establish native full active-case acceptance. No new performance or Python rerun is claimed.

## Previous source result before continuous-control correction

The working source now connects dimensioned full-tool paths to anterior face response, with angular bounds, solver-owned local jaw attachments, atomic interval validation and correction-bounded broadphase. The prior rigid anterior-tip blocker is disabled only where this elastic path takes responsibility. Cornea/iris/posterior full-body and actual entry-mesh integration remain pending.

The new instrument-path, membrane and default-app press tests pass; an actual NVIDIA GPU press run exits0 (44projections/37uncertain moving queries over25manual ticks). The fresh47-suite runner **stops at the volumetric encounter**:100% material removed, implant/wound checks passed, cornea/posterior intact, but final completion is correctly refused with2retained detached pieces, area.03565669. Coarse additional tearing, moving-query budget exhaustion and performance remain open. The original-side constraints are retained through all XPBD iterations; invalid metadata and interval/compliance overflow reject before mutation. Independent review verified the scoped fixes.

No new release/archive or full active GPU success is claimed for this work-in-progress source. The Windows ZIP still corresponds to the prior instrument-profile milestone below. See [current integration evidence and next actions](superpowers/plans/2026-10-28-instrument-body-contact.md).

## Instrument profile and contact foundations — 2026-10-28

Default dimensioned instruments now share generic rod dimensions and orientation with the prospective contact profiles. Both forceps jaws are tracked by unique names and update their complete endpoint geometry, including angle and length, during closure/reopening. Applied and reviewed frames restore the same shape. This is the app-visible change in this milestone.

Four new standalone suites cover capsule/triangle geometry, instrument profiles/live jaws, rigid-body motion envelopes and closed-shell entry tunnels. The rigid adapter and tunnel builder are **not enabled in default app physics/rendering yet**. The current app still uses its previous swept spherical tip contacts and logical wound predicate. Integration requires portal-compatible pose resolution, elastic anterior face contact, injury face identity handling and bounded cached tunnel publication.

- Actual healthy default cornea plus the101-point entry trace produces1483vertices/2962triangles, with oriented closed walls, original source-face mapping and full capsule clearance through the hole. Inscribed16-gon footprint and1e-6 welding tolerance are engineering approximations. Latest parent build712ms; independent observation781ms. Open injured source shells and ambiguous/budget-exhausted results reject atomically. This cost is unsuitable for per-tick reconstruction.
- Independent review exposed masked static-query false clearance, skinny-face Gram cancellation, shallow edge-pair cancellation and two tunnel budget gaps. Each has a failing reproduction followed by a passing fix. Static arbitrary masks with uncertified clearance fail closed. Profile tests also reject overflowing frame magnitudes. Final review reported no remaining substantive issue in the standalone scope.
- Standard runner **44 suites passed** with exit0. Final profile and tunnel changes were also rerun individually after their review fixes. Source-run full default normal encounter and volumetric injury route both reported zero failures on the actual RTX3070Laptop/NVIDIA566.14 OpenGL context. The extraction image was visually inspected. These prove existing app behavior and rendering, not integrated body contact.
- Fresh editor import, Windows release export and native120-frame default launch exited0, with a fresh180-byte native log showing the actual NVIDIA context. Native full active-case acceptance remains pending; source-script GPU routes do not establish that result.

No new active-performance measurement is claimed. The32.17fps timing milestone below remains historical evidence. Python code is unchanged; no remote CI result or clinical/device calibration is claimed. The [overall completion goal](REALISM_COMPLETION_KO.md) remains active.

## Fixed-step timing and presentation milestone — 2026-10-28

The default app now permits up to eight fixed physics ticks per rendered frame instead of one, with geometry/UI publication coalesced once per rendered frame. Tissue tick size, internal substeps, force/fracture/flow coefficients and clock integration are unchanged. [Godot documents](https://docs.godotengine.org/en/stable/classes/class_engine.html#class-engine-property-max-physics-steps-per-frame) why a one-step catch-up cap slows simulation below the physics tick rate. This section supersedes the prior cap-related limitation below, while startup and sustained performance remain open.

- A forced 30 fps runtime regression reproduced only 1.53 simulated seconds over 3.02 real seconds with the old cap. After the change it advanced 3.13 over 3.04 seconds, with finite tissue and pause/resume checks. The short-test tolerance accounts for startup fixed ticks and scheduler jitter; it is not a precision-clock guarantee.
- Live geometry is published after the fixed steps for that rendered frame. Explicit offline/manual steps still publish immediately. Tests prove that publication itself never integrates tissue, latest resolved poses and capture timestamps match, and pending live geometry cannot overwrite review. Normal review remains immutable sampled state, not deterministic input replay.
- Lens reset caches immutable cortical identity for particles/bonds. Peel-weight evaluation is skipped only when neither cortical endpoint can contribute. Actual triangle fields cache double-precision barycentric constants while preserving the original operation order. A 1200-step legacy/dimensioned shadow comparison matched **every** lens visual-state field and metric after every step, including hydro exposure, damage and removal. A 600-step integrated diagnostic retained identical capsule coordinates and lens/capsule metrics;1000 contact/outside query results matched the original boundary implementation.
- Instrumented 600-step diagnostic: lens 5.520→2.583 seconds; total 14.060→10.427 seconds. Those timings include wrappers and explicit per-step display, so they are diagnostic CPU evidence rather than the final live-render measurement.
- Final source-run active workload:1920×1080,30 seconds, RTX 3070 Laptop, moving powered phaco with a retained flap; **32.17 fps /31.083 ms mean /54.496 ms P95**, finite state, tissue access true, no alert,10.811% actual mass removed. Wall time 30.0099 s versus simulated 29.3667 s gives overall ratio 0.978565. After the same 2-second warmup used for frame timing, ratio was **0.999901**. The earlier 40.21 fps result used one physics tick/frame and advanced only about 19.63 simulated seconds; it was less physical work and is not a higher-performance real-time baseline.

Fresh standard runner: **40 suites passed**, including runtime clock/pause/resume and coalesced presentation/review regressions. Actual NVIDIA full normal encounter and posterior-injury route passed. Editor import and Windows release export exited 0. Python implementation is unchanged; no remote CI result is claimed.

The exported Windows executable also passed a fresh 120-frame normal-launch OpenGL smoke (exit 0, actual NVIDIA context, no script/shader errors). An attempted external `--script` active harness produced no report and was stopped; **no native active-workload timing is claimed**. Those speed measurements above are source-engine runs; native full-case operation remains a separate acceptance item.

The measured steady window follows real time on this machine, but the startup gap,32 fps display and lack of endurance/cross-hardware testing remain material limits. This is not stable 60 fps acceptance or calibrated surgical timing. Independent code review found no substantive issue and reran presentation, boundary and layered-material regressions successfully. Full realism, adaptive cuts, whole-tool contact, dynamic bag/rupture behavior and complete pointer workflow remain active work.

## Detached-boundary performance milestone — 2026-10-28

The retained-flap workload now measures **40.21 fps / 24.872 ms mean, 28.957 ms P95** at 1920×1080, 30 seconds with 2 seconds warmup discarded, RTX 3070 Laptop. The same retained-flap workload before this change measured 22.92 fps / 43.634 ms mean / 49.221 ms P95. No other test/export process ran during the accepted rendered measurements. Actual removed mass was 9.009%, tissue access true, finite state and no alert. Timing-sensitive GPU workloads perform more physics steps when frame throughput improves; removed-mass differences are not a deterministic physics equivalence test. This remains below stable 60 fps and is not endurance acceptance. The app currently caps physics catch-up at one step per rendered frame (`Engine.max_physics_steps_per_frame=1`), so simulation time slows under this load. With energy fixed at 1.0, recorded active energy integrals correspond to about 11.15 simulated seconds before and 19.63 after, over 30 wall-clock seconds. This is not verified real-time 60Hz tissue operation; timestep/throughput work remains necessary.

- A 600-step deterministic diagnostic identified boundary resolve as 12.072 s of 23.340 s instrumented physics time; most was repeated actual-triangle height interpolation. Final instrumented run was 13.925 s physics / 2.844 s boundary. This is a local diagnostic with timing wrappers, not a portable CPU guarantee.
- The configured field now owns a bounded 512-entry exact-XZ height cache. Coordinates are not quantized, Y remains irrelevant to triangle height, and source geometry is copied. Successful reconfiguration atomically replaces geometry and its cache; rejected configuration retains both. Packed geometry references are bound once per query instead of repeatedly looked up inside the face loop.
- An actual-vertex Y envelope rejects impossible surface-contact queries before interpolation. Padding includes accepted barycentric edge extrapolation and float-vector rounding. This is conservative broadphase only; no movement, contact sample, boundary resolution, exterior history or extraction check is skipped.
- All capsule vertex coordinates and lens/capsule metrics after the same 600 deterministic active steps exactly matched the prior implementation. A separate 1000-query old/new comparison returned identical contact/outside/result dictionaries. Independent full-mesh interpolation tests cover 1400 random field queries, repeat/Y independence, caller edits, geometry replacement/rejection, bounded memory, closely spaced coordinates and barycentric-edge contact. Independent review found no substantive issue and reran boundary/cache suites successfully.

Fresh local runner: **38 suites passed**, including the new independent query-equivalence suite. Default full encounter and posterior-injury routes also passed with the actual NVIDIA GPU. Editor import and Windows release export exited 0; the exported OpenGL application ran 120 frames and exited 0 without script/shader errors. Python implementation is unchanged; no new Python or remote CI result is claimed.

The full realism objective remains active. This change reduces existing boundary work without adding missing adaptive cut topology, full-tool contact, dynamic lens/bag mechanics, surgical assets or complete human pointer verification.

## Supported capsule extraction milestone — 2026-10-28

Fresh local `tools/run-godot.ps1 -Test`: **37 suites passed** (37 engine invocations, zero errors, runner exit 0), including four new extraction/boundary/director/exchange suites. Existing Python implementation/tests are unchanged. Remote GitHub CI has not been run.

The default encounter now retains the disconnected anterior membrane until actual forceps traction carries the complete supported component through the opened entry. Retirement requires an unanchored component, positive retained face area, a current grasp and exterior history for **every** vertex. Released/intraocular/partly exterior pieces cannot satisfy the completion gate. Constraints with no surviving face support are removed, and orphaned point grasps are released.

- Root shares the actual cornea/iris geometry and opened trace with the membrane boundary adapter. The modern entry footprint includes its external portal mouth, and moving tools and membrane points use the same opening. Boundary contact is bounded projected-triangle **vertex** contact with tangent sliding, not membrane-face collision or FEM. A guard derived from actual corneal rim radius/inner height provides reduced lateral containment below the tunnel; it is not a full scleral wall. This guard prevents unpassed vertices from escaping below the rim and never creates extraction evidence itself.
- Free flaps no longer receive bag transmural compartment pressure: both sides are wetted by the same modeled compartment. Supported bag faces still receive the original pressure load. Local fluid drag and free-flap hydrodynamics remain unmodeled.
- Signed insertion places a real working tip outside the portal while retaining the inward shaft direction. Default tool exchange requires a collision-resolved exterior pose. The withdrawal button schedules motion through normal contact resolution; it cannot instantly unlock exchange. Independent review found both the old positive withdrawal endpoint and a near-pivot aiming dead zone. Regressions reproduce both failures and pass with the fixes.
- Actual full default encounter passed headless and on the RTX 3070 Laptop GPU: preparation, blade trace, supported flap grasp/folding/extraction, withdrawal/tool exchange/re-entry, accepted-flow hydro separation, nuclear phaco, cortical IA, IOL delivery, final inspection and normal ending. No tissue arrays or completion flags are edited by the driver. Continuous extraction route poses are individually checked for reachability. This remains constrained-pose integration, not a complete human pointer route or clinical evaluation.
- Actual default extraction: initial membrane rest area **5.319326**, retained **3.253985**, extracted **0.266921**, cut loss **1.798420** model units²; residual detached area zero, finite state. The large cut loss is a known coarse 217-node edge-cut limitation. It does **not** demonstrate accurate continuous curvilinear capsulorhexis or a clinically suitable opening. Adaptive cut topology and calibrated tear propagation remain required.
- Captured pre-extraction face indices remain immutable; recorded geometry restores the retained flap, then live display restores extracted topology. Debrief reports extracted count/area, retained detached area and a named event, with default area converted to mm². GPU extraction and normal result captures were visually inspected. GPU adverse case also passed, retaining posterior injury and failure behavior.

Fresh isolated 30-second 1080p moving powered workload (2-second warmup), with a retained ungrasped flap: **643 frames, 22.92fps / 43.634ms mean, 49.221ms P95**, 5.405% actual mass removed, finite state, tissue access true, no alert. This workload now includes free-flap boundary contact and real exterior tool exchange; the previous 46.95fps scene did not. It exposes a substantial active-performance cost and is **not** sustained-performance acceptance or a 60fps result. Optimize/profiling of detached-boundary work remains required.

Fresh editor import and Windows release export exited 0. The exported executable ran 120 frames with its actual NVIDIA OpenGL context and exited 0 without script/shader errors.

Overall completion remains **active**: adaptive cut fidelity, whole shaft/jaw/blade contact, dynamic lens/bag and rupture aftermath, detailed assets/optics, complete pointer workflow and sustained performance remain open. Earlier milestones below describe historical states; this section supersedes their extraction/tool-exchange limitations.

## Dimensioned volumetric anatomy milestone — 2026-10-28

- The **default playable app** now initializes a shared representative anterior segment at 0.24 model units/mm: 9.2mm diameter / 4.2mm thick lens, enclosing bag, 3.0mm central chamber clearance and a closed inner/outer corneal shell. The lens is still 111 numerical particles, now sampled in a volumetric rest shape; this is not display-only scaling. Representative lens dimensions refer to [Xue et al.](https://onlinelibrary.wiley.com/doi/10.1155/2019/8319027); the remaining surface fits and coefficients are engineering choices, not a measured patient or calibrated biomechanics.
- Anterior and posterior bag rings share their equator. Equal meridional-angle sampling preserves real triangle enclosure with the existing 217 membrane nodes. Independent review found outer particles protruding through coarse linear-ring facets despite passing an analytic-profile test. A new test independently interpolates actual indexed face heights and proves enclosure of every rest particle.
- Shared geometry also sets iris/pupil cases, entry portals, working depths, IOL target/rest scale, tool-specific tip radii and collision/render surfaces. Generic instrument handles are now outside the operative field; working tips and shafts are separately modeled. Full shaft/jaw/blade collision remains open.
- Accepted inflow drives a bounded cortical surface exposure field with symmetric neighbor exchange and relaxation. Tests verify no source/no release, local onset, propagation beyond the direct tip radius, bounds, nuclear identity and reset. This is a reduced exposure model, **not CFD, measured pressure or extra compartment volume**.
- Corneal surface damage and through-wall loss are separate. Only removed outer-face samples with a clear path through both shell boundaries contribute to estimated through-wall area/conductance. Sample measurement is bounded to 512 outer leaves; further subdivision is limited if the budget is reached. This is an area estimate, not a calibrated hydraulic aperture. Independent review reproduced the previous superficial-damage false leak; the regression now verifies one-wall no-leak and two-wall actual passage.
- Revision-zero anatomy now tracks presence as well as revision, so undamaged legacy rich replay restores its own cornea/posterior rather than leaving dimensioned geometry visible. Same-count lens topology caches reset between cases/replay. New instrument references follow model rebuilds.
- Fresh local standard runner: **33 suites passed**, including five new default-mode suites (geometry, cortical surface flow, corneal shell injury, volumetric full encounter, volumetric adverse case). Old fixed-coordinate app fixtures explicitly opt into the legacy specimen; they do not stand in for the new default tests. Python implementation/tests unchanged in this milestone.
- Default full encounter passed headless and on the RTX 3070 Laptop GPU: actual continuous blade entry, anterior connectivity cut, accepted-flow adhesion release, all nuclear/cortical mass removal at the inlet, IOL deployment/alignment, collision-resolved withdrawal through the wound, measured final inspections, completed ending and immutable review. This test drives normal tool/action methods with constrained poses, not a full human pointer route or clinical evaluation. New default adverse case proves posterior puncture, posterior outflow, persistent failure after assessment and healthy reset into a smaller-pupil case.
- GPU intact/oblique geometry, normal ending and adverse captures were visually inspected: `volumetric-anatomy.png`, `volumetric-depth.png`, `volumetric-results.png`, `volumetric-injury.png` under `godot/reports`. The oblique view is a diagnostic test capture, not a newly exposed camera mode.

### New geometry: moving powered GPU workload

The benchmark follows the new chamber route and anterior opening, then scans lateral position **and depth** for 30 seconds at 1920×1080. Energy, aspiration and inflow are each 1.0 normalized controls. First two seconds discarded; no other test/export process ran during the accepted measurement.

| Metric | Observed |
|---|---|
| Sampled frames | 1,316 |
| Mean FPS / frame time | 46.95 fps / 21.297ms |
| P95 frame time | 27.428ms |
| Actual removed mass | 8.108% of initial mass |
| Finite / tissue access / case alert | true / true / none |

This remains below a stable 60fps target. The earlier 56.01fps result below used the flatter specimen, smaller tip and a different depth/power path; it is historical and not a same-workload comparison. The benchmark requires actual removal and a clear case alert before accepting a run, so a powered but ineffective hover cannot be reported as active-operation validation.

Editor import and Windows release export exited 0. The native OpenGL executable ran 120 frames and exited 0 without script/shader errors. Refreshed nine-file Windows ZIP passed CRC verification. Overall goal remains active: separated anterior flap extraction, actual dynamic particle/bag boundaries and rupture aftermath, tool exchange withdrawal/reinsertion, full-tool contact, detailed environment/assets, full pointer workflow and sustained performance are still required.

## Packed visual snapshot milestone — 2026-10-27

- Fresh standard runner: **28 Godot suites passed**, including packed visual state preservation/isolation. Independent review reran packed snapshot and surgical display tests; no substantive findings.
- Display updates now freeze copied packed numerical lens/membrane arrays. Rich particle/bond/edge dictionaries are reconstructed only on explicit capture for the existing recording/review format. No solver integration, geometry or injury logic changed; dictionary replay fixtures retain their original compatibility path.
- Regression checks cover all current public fields (position, velocity, mass, active flags, material identity, adhesion, bond damage/rest/endpoints, membrane edge values/topology), live state changes after apply, cut topology, caller mutation isolation, and old rich replay fixtures.
- 500-copy headless microbenchmark: lens rich rows **1.928ms** versus packed **0.058ms**; capsule edge rich rows **1.174ms** versus full packed capsule snapshot **0.122ms**. Reconstructed rich values exactly matched mirrors. These timings measure the copy operation, not total frame rate.
- Fresh 30-second moving powered workload at 1920×1080, 2-second warmup, RTX 3070 Laptop: **1,570 frames; 56.01fps / 17.855ms mean; 22.786ms P95; removed mass 48.65%; finite state**. All other test/export processes had finished before measurement. Previous injury build measured 42.75fps / 23.392ms in the same workload; this is a shared-desktop observation, not a guaranteed 31% gain on every machine or a stable 60fps result.
- GPU full encounter passed with complete removal, IOL delivery/alignment, final inspections and immutable review. Editor import and native export passed; exported OpenGL application ran 120 frames and exited 0 without script/shader errors. Refreshed nine-file Windows ZIP passed CRC verification.
- Overall realism goal remains active. Anatomy proportions and tool shaft clearance require a coupled geometry/kinematics improvement; this performance milestone does not resolve them.

## Local structural injury milestone — 2026-10-27

- Fresh standard runner: **27 Godot suites passed**. Added local injury, posterior boundary flow, persistent injury case state and actual-application suites. Python implementation/tests unchanged in this milestone.
- Actual local corneal/posterior contact exposure now refines nearby triangles and removes a bounded aperture. Collision and display use the resulting shared topology, with measured missing area and persistent case evidence. Distant geometry remains, topology is capped at 8,192 vertices/faces per surface, stale revisions are ignored and malformed batches reject atomically.
- Posterior and corneal missing area drive separately reported boundary conductance. Every macrostep's averaged actual flows obey compartment volume balance, including lower/upper bounds; posterior outflow does not delete lens mass. This remains a single compartment with an unmodeled downstream reservoir, not vitreous or dropped-nucleus dynamics.
- Actual application tests verify blade puncture, powered stationary contact, energy after switching tools at a resting contact, alert/release, completion rejection after acknowledgment, reset and immutable pre/post injury review. Independent review reproduced stationary power falsely contacting an existing incision; moving and stationary contact now share the same full-radius wound exclusion. A second structural injury raises a new event after acknowledgment.
- Independent reviewer reran injury application/case, geometry contact and injury component suites with zero failures. Additional tests cover tiny refined face contact, excluded-nearer-face handling, non-energy-tool exposure rejection and area/flag consistency.
- Healthy full layered encounter and adverse application tests passed on NVIDIA RTX 3070 Laptop GPU. Captures: `godot/reports/injury-contact.png`, `injury-debrief.png`, `professional-results.png`. The healthy fixture releases the blade and follows the open chamber route before anterior cutting; an active blade swept through intact cornea causes real injury instead of being exempted.
- Fresh 30-second moving powered workload, 1920×1080, 2-second warmup: **1,198 frames; mean 42.75 fps / 23.392 ms; P95 32.419 ms; removed mass 48.65%; finite true**. No concurrent GPU test during this measured run. This fails the stable 60fps target; performance optimization remains open.
- All injury thresholds, loads, aperture radius and conductance coefficients are synthetic engineering choices. They are not tissue failure force or clinically validated limits. Anatomical barrier reference: [AAO posterior capsule rupture signs](https://eyewiki.aao.org/Intraoperative_Signs_of_Posterior_Capsular_Rupture).
- Editor import and Windows release export exited 0; the exported native OpenGL executable ran 120 frames and exited 0 without script/shader errors. The refreshed nine-file ZIP passed CRC verification. Overall goal remains active for shaft/jaw contact, vitreous/dropped material/implant support, complication handling, richer anatomy/room assets, full pointer workflow and sustained performance.

## Continuous anatomical tip contact milestone — 2026-10-27

- Fresh standard runner: **23 Godot suites passed**, including surface-contact, anatomical-coordinator and anatomical-application suites. Existing Python source/tests were unchanged in this milestone.
- The swept sphere kernel checks triangle faces, edge cylinders and vertex spheres, with two-sided contact and bounded sliding. Tests cover fast crossings, actual missing triangles, tangent withdrawal, internal coplanar seams, malformed topology and nonfinite/overflowing coordinates.
- Shared generated corneal dome, conical finite-thickness iris and posterior bowl now drive rendering and collision. The previous displayed iris height and old numeric depth guard disagreed; both were replaced. The anatomical dimensions and app tip radius `.01` are synthetic engineering choices, not calibrated anatomical/tool data.
- In the actual app, intact capsule blocks a phaco tip and interposed membrane prevents its energy from acting on lens material. Fluid aspiration in the anterior compartment remains possible. A blade-created opening permits subsequent local phaco entry. Grasp reach and physical contact radius are separate.
- Full layered encounter passed both headless and on the NVIDIA GPU with the new contacts: entry → membrane opening → cannula local flow release → nuclear phaco → separate cortical IA → IOL → final inspections → completed. Captured GPU report: `godot/reports/full-encounter-gpu.json`.
- GPU traction/local aspiration suite passed after its old teleporting fixtures were replaced with actual chamber routing and a blade-created local access opening. Intact/traction/rupture/local-removal images were visually inspected.
- Independent review reproduced a corneal aperture that accepted a sphere whose center fit but whose footprint overlapped intact surface. Fixed by testing projected surface distance plus the full tip radius. Reviewer independently reran edge/center crossings at radii `.01` and `.018` and the large-coordinate rejection; all passed. All three new suites are in the local runner and CI workflow (remote CI not claimed).
- Interior contact query averaged **1.737 ms before broad bounds rejection, 0.770 ms after** in the 120-query microbenchmark. Rendering/solver performance is separately measured below.

### Actual moving, powered workload

`benchmark_active.gd` prepared a real membrane opening, then continuously moved a powered phaco tip in the chamber for 30 seconds at 1920×1080. First 2 seconds discarded. This is the first new-mode measurement with local fracture/aspiration and continuous contact active rather than an idle field.

| Metric | Observed |
|---|---|
| Sampled frames | 1,295 |
| Mean FPS / frame time | 46.12 fps / 21.683 ms |
| P95 frame time | 29.294 ms |
| Removed mass at end | 48.65% of initial total mass |
| Finite model state | true |

This does **not** satisfy a stable 60fps active-operation target; profiling/optimization and longer duration acceptance remain required. It is not comparable to the earlier idle measurements as if they were the same workload.

Tip collision is a sphere approximation, not complete shaft/jaw/blade contact. Contact-limited movement is recorded per hand and summed; those metrics are not tissue force or damage. This older milestone preceded the structural injury implementation above. Full hardware/tool shapes and complete pointer-driven workflow verification remain open in [overall completion criteria](REALISM_COMPLETION_KO.md). Overall goal remains active.

## Layered material milestone — 2026-10-27

The default app now enables nuclear/cortical material identity, localized capsule-cortex adhesion and cortical aspiration peeling. Homogeneous kernel fixtures remain available as the explicit legacy solver mode.

- Fresh run of `tools/run-godot.ps1 -Test`: **20 Godot suites passed**, including new lens-material and layered-lens tests.
- Extended complete encounter passed: blade entry/membrane opening → cannula local adhesion release using actually admitted compartment inflow → nuclear phaco (169 steps, approximately 51.35% of initial total mass) → separate IA cortical removal → IOL → final checks → completed. Final nuclear and cortical mass both zero, total removed mass 1.0, 52 visual frames, 102.15 seconds of simulated time. No tissue state is edited by the test driver.
- A separate cortical IA test removed all cortical mass (48.65% of initial total mass) without ultrasound while retaining all initial nuclear mass (51.35%). Closed/full compartment with zero actual admitted inflow cannot release adhesion despite a nonzero commanded pump.
- Independent review found endpoint-order dependence in cortex-cortex peeling. The fix evaluates both eligible endpoints and uses the strongest local contribution; swap-symmetry regression passes.
- GPU local traction/rupture/aspiration test passed with the material shader, and the microscope image was visually inspected. Material colors are cached by fixed source topology; tissue movement still updates geometry.
- New measured 30-second 1080p live-physics sample, after editor/export activity had finished: **1,498 frames, mean 53.47 fps / 18.701 ms, P95 23.920 ms** on the same RTX 3070 Laptop GPU. Earlier concurrent runs ranged 48.97–51.41fps. The previous 58.13fps integration measurement below is historical, before this material milestone. Active surgery and endurance acceptance remain pending.
- Fresh native Windows release/export smoke: exit 0 with the real NVIDIA OpenGL context. Python source was unchanged; the earlier 522-pass result remains regression evidence, not a new rerun.

This is still a reduced radial-shell/point-spring model. It is not continuum hydraulic layer separation or validated clinical biomechanics. [Overall completion criteria](REALISM_COMPLETION_KO.md) remain active, especially actual anatomical surface contact, posterior/corneal injury, geometry/visual fidelity and full pointer-driven operating verification.

## Earlier integration verification

- Windows, Python 3.12.10, Godot 4.7.2 stable official `ed1daf0bf`, Compatibility OpenGL 3.3, NVIDIA driver 566.14, RTX 3070 Laptop GPU.
- Python regressions: **522 passed in 30.57 seconds**.
- All **18 Godot headless suites** passed through `tools/run-godot.ps1 -Test`: session, world, input, integration, playthrough, capsule solver, lens/fluid solver, instrument rig, simulator, case director, case recording, incision, IOL, lens surface, operating app, simulation UI, surgical display, full encounter.
- Full new-mode encounter: three preparation checks; continuous blade entry; membrane cutting changes connectivity; adaptive local phaco/aspiration removes 100% material in 321 solver steps; user-held IOL delivery and independent elastic unfolding; tool withdrawal; three measured inspections; completed ending; immutable visual review. Test drives constrained instrument poses and user action methods, with no tissue/mass/completion mutation. It is an automated integration route, not a human usability or clinical evaluation.
- The same full encounter passed with a real NVIDIA GPU context. `test_simulator_render.gd` passed actual contact, traction rupture and local aspiration (5.4% removed, remaining >50%) and captured four states.
- Additional operating tests cover a seeded patient-motion event, release/fresh-press pedal rearming, paused observation until assessment, persistent two-hand grasp, source-injector binding during partial IOL delivery, depth reset, help-modal release/freeze, review keyboard isolation and sound callback.
- Minimum-width UI layout tested at 1152×800; 1600×1000 microscope and result captures visually inspected. New-mode GPU images: `godot/reports/professional-microscope.png`, `professional-results.png`, `physics_01_intact.png`–`physics_04_local_aspiration.png`.
- Independent code review found partial IOL delivery following the selected hand and stale aiming depth after new case. Both were fixed and regression tested. Additional inspection fixed path-length accounting for direct pitch/insertion changes and review keyboard shortcuts.
- Windows release export and a 120-frame native OpenGL launch completed with exit 0 and no script/shader errors. Source/editor import completed without errors. No remote GitHub CI success is claimed.

## New-mode GPU measurement

`godot/tests/benchmark_simulator.gd` runs the integrated microscope, live capsule/lens physics, persistent dual instruments and monitor/UI for 30 seconds at 1920×1080. First 2 seconds are discarded. It does not benchmark powered tissue removal or all scenarios.

| Metric | Observed |
|---|---|
| Frames after warmup | 1,628 |
| Mean frame time / FPS | 17.202 ms / 58.13 fps |
| P95 frame time | 21.149 ms |
| GPU | NVIDIA GeForce RTX 3070 Laptop GPU |

This is a short shared-desktop observation, not a 60fps guarantee, endurance test or cross-hardware acceptance. The earlier game's 300-second 59.97fps result does not apply to this mode.

## Model scope and remaining fidelity work

The playable integrated path is verified. It is an initial specialist simulation game, not the completion of the entire historical 32-work-package roadmap. The models are uncalibrated: 217-node XPBD membrane, 111-particle connected lens, single fluid compartment, elastic point implant and traced incision gap. Mesh surface interpolation follows physical positions/connectivity. Mechanical tip contact and local energy/aspiration are implemented; full shaft/jaw/blade contact, continuum layer hydraulics, vitreous/dropped-material dynamics, physiological feedback, real device calibration, photorealistic assets and clinical/haptic validation are not. Later milestones above add shared corneal/posterior tip contact, separate cortical material and local structural injury.

Record review uses sampled immutable visual states (2-second interval, 900 frames, 32MB export limit); it is not deterministic physical input replay. The director checks simulation evidence and provides no clinical skill grade. See [Korean controls and scope](SPECIALIST_SIMULATOR_KO.md).

## Reproduce

```powershell
powershell -ExecutionPolicy Bypass -File tools/run-godot.ps1 -Test
python -m pytest -q
.tools/godot/Godot_v4.7.2-stable_win64_console.exe --path godot --resolution 1600x1000 --script res://tests/test_simulator_render.gd
.tools/godot/Godot_v4.7.2-stable_win64_console.exe --path godot --resolution 1600x1000 --script res://tests/test_full_encounter.gd
.tools/godot/Godot_v4.7.2-stable_win64_console.exe --path godot --script res://tests/benchmark_simulator.gd
```

### Current control and full-case diagnosis

Real projected mouse/key event regressions reproduce and fix stale pending motion after context changes, negative insertion mirroring during fixed-length aiming and paused G-key latch activation. Pending targets are cleared on release_controls and hand switch. Explicit withdrawal disarms then schedules fresh targets; blocked tool exchange preserves those withdrawal targets. The regression went from7failures to0 and also exits0 on NVIDIA OpenGL. Seven surrounding control/app suites pass; independent scoped control review found no substantive regression.

The normal encounter subsequently failed its first near-entry nucleus target(.366354,-.016539,.640237), with tip(.180381,-.018742,.692422) and iris contact. Only.045045mass was removed; nucleus removal and full completion are NOT passed. The run was deliberately stopped after this diagnosis. Subsequent exchanges were cascaded test failures, not verified impossible withdrawals. A new diagnostic rerun saves actual pose/mesh/particle data on the first block and stops after the failed phase. Alternative-portal reachability and near-contact query convergence remain under investigation. The standard runner now has52suites; no all52run or new native package is claimed.

Exact failure capture confirms the right shaft/iris witness (original face1030); centerward recovery clears. A normal diagnostic rerun terminates exit1 at that first block. A physically constrained bimanual full-case driver now traces a real left entry, withdraws/switches/exchanges/reenters and selects the portal with nominal whole-tool clearance. Independent scoped review found no teleport or outcome shortcut. Its current live run has passed bilateral entry, flap extraction and hydro>.95; downstream removal and completion remain pending. Static target-center screening of the prior saved material also identifies centers inaccessible from both portals; this does not establish removal impossibility because local fragmentation/peeling and attraction permit offset operation. Further actual trajectory/material investigation remains necessary. The driver uses targets/pedal APIs; human end-to-end choreography is still separate. Further5focused suites pass, and current controls pass on NVIDIA; no all52or native export claim.

Bimanual first run terminal result is exit1: actual total removed mass.306306 (prior single-portal.045045), nucleus remaining.207207, no alert. The next rejected material center requires whole-tool iris intersection from both portals. A static offset+.10Y is clear through left and inside existing local phaco influence. A further full run now tests bounded nearby operation and physical inlet removal, with no solver-strength/outcome changes. It is pending. These results supersede the preceding live-run wording; full normal completion and current-source export are not qualified.

### Queued wheel and pitch control

Wheel and Q/E previously mutated accepted rigs before collision validation. Bursts failed5new assertions. They now queue proposed poses for the same fixed-tick speed/contact controller as mouse motion. Independent review caught discarded zero-insertion orientation; two further RED assertions drove retained axis intent and angular-limited, separately certified zero-to-zero pivot rotation. Nearby uncertified rotation retains the accepted axis. Context resets clear proposed axes. Current8focused suites and final NVIDIA control event run exit0; independent scoped review found no substantive issue.

The first offset full run ended exit1 at total removal.306306. Its viable+.20lift was excluded because Vector3 distance measured.200000002980232; a static probe proves the lesser+.15intersects iris and+.20is clear. Search rounding tolerance1e−6remains below actual unchanged.22energy/.16peel influence. The rounded offset full run is live after entry/flap extraction; no full completion/export claim.

Rounded offset run6148 terminated exit1 at total removal.360360, nucleus remaining.153153 and no alert. Current driver chooses among reachable local targets instead of treating the first inaccessible particle center as total failure. Bound-particle local ranges are unchanged; only degree0free particles may use a .40tool-target offset inside unchanged .44suction influence. Every particle must still fracture/peel and physically enter the inlet. No material state is injected. Tip tolerance is.005; inaccessible exhaustion saves actual bonds/degrees/particles. Independent fixture review found no invalid shortcut. New full run actual-local-material-encounter.log is pending.

## Current admitted-flow material continuation

The last completed default anatomical case removed54of57nuclear particles at the actual inlet (removed mass.486486, nucleus.027027, cortex.486486, noalert), then retained three connected nodes. Saved bonds prove the issue: free-only aspiration forces gave connected material no followability. Current source adds weak local connected advection proportional to admitted aspiration flow. This is a reduced dimensionless engineering model, not vacuum holdability, CFD or clinical calibration. It does not alter bond thresholds, energy/peel ranges, mass or completion gates. It is motivated by flow/fragment behavior, not parameterized from a clinical study: [Gupta etal2015 laboratory study](https://pubmed.ncbi.nlm.nih.gov/25747166/).

A regression went RED for missing connected movement, then GREEN while preserving intact bonds/mass. Independent review exposed stale cached admission after depletion; two further RED cases cover that history and dry free-particle inlet capture. The fixed obstruction prepass now admits current-substep boundary flow before forces, excludes leakage/rupture from aspiration and gates both free/connected transport and capture. No current admitted aspiration means no aspiration capture. Existing degree0and actual .05inlet guards remain. Lens-fluid and fresh6focused suites (layered, material, hydro, injury-flow, legacy full encounter, control) pass; independent re-probe confirms the stale-admission case now produces0speed/0flow.

Current anatomical full run actual-admitted-flow-encounter.log is live after real bilateral entry and flap extraction. The older cached-flow diagnostic was deliberately stopped because its source was superseded. A flow-only target is attempted only after exhausting reachable local fracture/peel targets; actual drag must move retained tissue before actual fragmentation/inlet removal. No current all52pass, GPU full-route, performance or release claim.

An instrumented25manual-tick press costs1.565seconds:1.283capsule, .084lens, .098motion, .069presentation;44contacts/37uncertain. This is CPU diagnosis rather than FPS validation. First saved uncertain candidate has no hits in4097dense samples, but sampling is not a clearance certificate. The moving-face algorithm is still unchanged and unresolved.
