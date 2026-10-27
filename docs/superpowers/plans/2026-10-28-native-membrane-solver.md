# Native membrane solver implementation plan

> Execute inline with superpowers:executing-plans. Continued implementation is authorized by the user.

**Goal:** Resolve refined-flap numerical stretch without hiding physical damage, and measure the cost before replacing runtime integration.

**Architecture:** A pure C++ double-precision implicit spring-energy solver, initially tested through a small C ABI. Minimize mass-weighted displacement plus existing compliant edge energy with a matrix-free Gauss–Newton direction, preconditioned conjugate gradient and energy backtracking. Report convergence and bounded-work exhaustion explicitly. A Godot GDExtension bridge is a subsequent gate, not an assumed working integration.

**Updated after measured RED:** Undamped GN still exhausted100outer iterations at E9.063e-7. Adaptive direction-only damping improved it to E4.0406e-8 but gradient1.877e-5 still failed. CG diagnostics showed only37iterations/outer on average, so the512CG cap was not the main cause. The exact distance Hessian's transverse geometric stiffness was then included, with bounded negative-curvature damping retries. The same objective,100outer limit and1e-8gradient test now pass at23outer/5118totalCG/28objective evaluations: E3.819273071e-8, gradient_inf5.6323e-9, maxstrain.00260886. Measured standalone cost.209–.224s remains unsuitable for realtime. No runtime connection/release yet.

**Tech stack:** Godot4.7.2 remains the product engine. Portable Zig0.17.0 C++ compiler (SHA256 b5663f69581dcf391293fbf16c06cb80d81d806545ce618b4d0bab7f0eb8c428); godot-cpp godot-4.5-stable commit e83fd0904c13356ed1d4c3d09f8bb9132bdc6b77 for later forward-compatible extension evaluation. No new runtime Python dependency.

**Spec:** REALISM_COMPLETION_KO.md and conservative-membrane-cut plan. Preserve material masses, actual crack topology, tool attachments and the retained failing traction gate. No clinical calibration claim.

## Review focus

- Invalid/nonfinite input rejects atomically, pinned positions stay exact, exhausted budgets cannot be reported as converged.
- Very small accepted rest lengths and masses must not gain artificial floors that change mechanics.
- Independent analytical and captured-scene objective/gradient checks, not only implementation-mirroring tests.
- Positive compliance only initially; incompressible/zero-compliance input must reject explicitly until supported.
- Standalone kernel success does not qualify dynamic contact, fracture, GPU, release packaging or real-time performance.

## Tasks

- [x] Write tests in native/tests/test_membrane_kernel.py: analytic two-point spring with unequal masses, pinned endpoint, invalid transaction, budget exhaustion, refined scene objective and gradient; run RED before implementing native/membrane_kernel.cpp.
- [x] Implement C ABI, bounded solve and native build helper; run correctness tests and record actual timing without a real-time claim.
- [x] Review kernel and convergence failure cases, then add isolated GDExtension binding tests.
- [x] Connect an optional backend to actual capsule substeps after revisiting repeated contact projection/velocity/fracture semantics. Keep the real refined-traction regression and extraction gate; default promotion remains pending.
- [ ] Run refined traction/extraction and unchanged regression gates, GPU and compiled-release validation before shipping anything.

## Sparse direct solve and stability gate

The current captured solve spends5118CG iterations and about.2s. Next replace repeated Krylov work with Eigen5.0.1 sparse LDLT over free coordinates, preserving the exact same objective, gradient tolerance and work bound. Retain a fixed sparsity pattern and reuse symbolic ordering within a solve; rebuild values/factorization for each trial damping. Positive finite LDLT pivots are required before using a Newton direction. At gradient convergence, an undamped Hessian factorization must additionally check full coupled curvature; zero gradient plus an unstable coupled mode must return3, without injecting arbitrary physical motion.

- [x] Add a compressed two-free-point collective mode with positive coordinate diagonals but negative coupled curvature; reproduce RED with the current coordinate-only screen.
- [x] Pin Eigen5.0.1 from official gitlab.com/libeigen/eigen at bc3b39870ecb690a623a3f49149a358b95c5781d, preserve license notice and reproducible setup/build. This is a header-only build dependency, not a runtime service.
- [x] Implement sparse assembly/free-coordinate elimination, LDLT directions and full stationary curvature test. Keep numerical failures distinct, finite pivots/residual checks, and analytical/scene tests unchanged.
- [x] Compare fresh standalone benchmark and independent objective/gradient; do not infer GPU/frame-rate from it. Scoped review before proceeding to the Godot bridge.

## Sparse kernel and engine-boundary results

## Runtime integration ruling

Ruling: first inject an optional native stretch backend into the actual capsule model; keep existing tool-body and tissue-boundary operators. Each global XPBD proximal update uses effective edge rest `r_eff = r - alpha*lambda_old`; its implicit energy gives `delta_lambda = -(length-r_eff)/alpha`, hence `lambda_new = -(length-r)/alpha`. Repeating without external contact is then a no-op, rather than minimizing a new original-rest energy6times. Cache only exact published positions/duals plus all mass/topology/alpha inputs. This is an engineering global XPBD update, not a proof that the entire nonlinear contact problem has reached a unique minimizer.

Ruling: optional-backend mode evaluates tensile rupture after projection/boundary acceptance, not at the predicted pre-solve state. Legacy blade failure remains separate and remains incomplete area-preserving fracture work. Failure/exhaustion/invalid backend output or invalid body/boundary resolution rolls back the whole outer step (history, grasps, topology, extracted area and time), with a separate explicit failure diagnostic. Default legacy mode stays unchanged until native integration is qualified. Tests must retain real anatomical refinement, forceps traction and body/boundary calls; no contact bypass or threshold relaxation.

- Previous goal turn was progress: native matrix-free kernel committed739fa46. Revalidated10tests before this stage. Full coupled buckling with individually positive coordinate diagonals reproduced a new RED; free-coordinate sparse exact-Hessian LDLT now detects it. Directions require positive finite pivots and a finite acceptable relative linear residual. At stationarity an undamped full factorization screens curvature; status3negative/status4singular are distinct from convergence. No artificial mass, tear strength or objective change.
- Current native12/12tests pass. Reviewer reproduced a possible overflowing RHS norm reporting residual0; an extreme finite-input test was RED, then fixed with explicit finite RHS/residual norm checks. Compiler warnings remain errors for the standalone kernel. Scoped reviewer found no serious sparse assembly/sign/pin/curvature issue.
- Standalone10measured calls after warmup: median46.891ms(range44.422–55.801), E3.819273056e-8, gradient_inf2.697e-9, strain.00260873,24outer/30factorizations. DLL SHA256 bbe88975ed23f2fe4b1ca2b8559ffeb038857282f1f1d381a3346fe48309bf5f; fixture SHA256 0d5a27d589e351bf6dbd25a41d8caf69df6ab54502eedd8c16b231069ccbfe62. This remains slower than a60Hz substep and is not an app/GPU result.
- Added packed-float64 Godot bridge with shape checks before pointer access and COW output (caller input remains unchanged). Tests cover analytical solve, malformed shape/edge arrays, exhaustion, diagnostics and actual captured scene. Its class-absence RED was observed before implementation; direct Godot runtime test passed0failures, about47ms for the captured input. Product project/resources remain untouched.
- Binding generation initially omitted OS needed by upstream print_string.cpp; diagnosed missing generated header and explicitly included OS in the reduced profile. Build now uses63translation units, pinned godot-cpp4.5stable, with compiler-aware object caching. Compiler/dependency/source identities are verified and stored with exact DLL hashes; benchmark hashes the actual bytes parsed. Native and dependency license notices are retained.
- **Editor boundary:** fresh `--headless --editor --import` with the extension crashed0xc0000005; no-extension control succeeded. Omitting PDB reproduced the crash, excluding the unrelated short-PDB-name warning as the cause. Warm import and direct game test succeeded. Behavior matches upstream [#111048](https://github.com/godotengine/godot/issues/111048), [#111645](https://github.com/godotengine/godot/issues/111645), and open [#123658](https://github.com/godotengine/godot/pull/123658) about deferred editor documentation callbacks after cleanup. Exact internal crash stack was not symbolized here; this is a supported diagnosis, not a local engine patch.
- Three fresh probes passed import plus bridge with `--frame-delay1000` applied **only to editor import**. This is a documented timing workaround, not an engine fix or a simulation timing change. Raw failure proof remains `native-extension-validation-no-delay.json`; default validator records its arguments, hashes and scoped qualification. Frozen DLL/test/config identities were strengthened after review; one final run verifies canonical tracked inputs rather than generated mirrors.
- Current app's `test_capsule_incision` remains the known RED until the native solver is actually integrated. Next: preserve per-substep predicted state, contact constraints, held material offsets, history and conservative fracture decisions while applying native output; verify that failure/exhaustion never silently advances an invalid physical state. Do not repeatedly minimize a new energy against already-corrected positions inside the old6projection loop, and do not discard body/tissue contact to make traction pass.
- Final strengthened frozen-input validator completed exit0 (`native-extension-validation.json`, probe membrane-validation-8ek4jbp4), both fresh import with the explicit editor delay and bridge test passed. Extension SHA2566a783d58ea46fca3f2468a3259e37ab167883316364622f4ba3368baf3d81809. Reviewer confirmed frozen-DLL and canonical test/config provenance fixes, no new substantive issue. Final native12tests passed again; app `incision-before-native-integration.log` returned exactly the known1traction failure. No all54/GPU/product-integration/release qualification is claimed. All build/validation job handles are terminal.

## Evidence before native work

## Optional actual-capsule integration evidence

- The backend-absence test was RED before implementation. Native global XPBD effective-rest/dual updates now run in the actual capsule class with unchanged anatomical and tool-body contact operators. Full outer-step state rolls back on backend failure, accepted-looking nonfinite output, body-contact failure or anatomical-boundary failure. Default null-backend legacy behavior is unchanged.
- Ruling: an ordinary1e-8gradient stop can expose a negative soft-mode pivot near the float32 rest configuration. Retain failure status and retry once at1e-12only for status3with nonzero gradient below the ordinary tolerance. The captured near-rest case failed at1e-8and1e-10, passed at1e-12; universally requiring1e-12instead exhausted the100outer budget during traction. Exact stationary saddles are not retried or accepted, and no failed final status advances the world. This is a bounded numerical policy, not a material/strength adjustment.
- Frozen actual integration passes64curved cuts,30rest ticks, acquisition and.005traction:32accepted outer ticks,745vertices,924triangles, initial/retained area5.3193263467, free flap.506774729, cut loss0, broken0, peak strain.0071046464. Actual moving forceps-body test:21contacts,0uncertain, peak strain.0202432383, residual2.100118e-8, no material loss. Deliberate numerical/body/boundary failures leave positions/history/grasps/time/extraction unchanged.
- Existing8focused legacy suites all pass (capsule_solver, capsule_extraction, body_app, instrument_path, control_context, simulator, visual_snapshot, full_encounter). The full standard suite, GPU, full refined extraction, native app default and release are not qualified.
- Scoped read-only review found no substantive integration blocker, confirmed XPBD algebra/cache/rollback; identified frozen probe accounting and scope wording gaps. Both were fixed: the post-run hash set now includes every intended copied resource plus DLL, and capsule evidence has its own scope. Final strengthened `--capsule` validator passes import/runtime exit0 in membrane-validation-27z0l5cn; report native-capsule-validation.json binds engine, sources, frozen inputs and unchanged extension6a783d58ea46fca3f2468a3259e37ab167883316364622f4ba3368baf3d81809.
- Precision/performance limitation: native energy/gradient are evaluated in float64 before published PackedVector3Array quantization; existing rest norms/history are float32. No persistent float64 world state or integrated realtime claim. Full extraction and actual knife routing remain next gates.

The same captured first refined-flap substep has initial max strain .004570974. Existing sequential constraint updates later produce spurious large stretch. Independent L-BFGS-B gave energy3.819356697e-8, max strain.002539, gradient infinity norm1.343e-6 (relative-energy stop; not strict gradient convergence). Sparse trust-region least squares gave energy3.819275721e-8, strain.002636, optimality1.583e-8, but exceeded1000evaluations and reported failure after280.266s. Global XPBD Newton updates overshot severely. This motivates a stabilized coupled solve, not claiming a unique or clinically calibrated solution.

Sources: [XPBD paper](https://mmacklin.com/xpbd.pdf), [official GDExtension guide](https://docs.godotengine.org/en/stable/tutorials/scripting/cpp/gdextension_cpp_example.html), [Zig manifest](https://ziglang.org/download/index.json).

## Review hardening

Scoped read-only review confirmed the exact Hessian/free-coordinate mathematics and identified a symmetric compressed saddle accepted by gradient alone, unavailable early-failure stats and possible overflow in geometric stiffness. New tests reproduced these RED. Early failure stats now explicitly expose infinite unavailable energy/gradient; nonfinite C/length rejects. Negative coordinate Hessian diagonal returns status3for an unstable stationary point. This screen does not certify positive definiteness of the full coupled Hessian; do not call status0a proof of a physical minimum. Complete second-order certification/escape and improved linear solve performance remain prerequisites for runtime qualification. Tests now10/10pass.

Final build also rejects overflow of stiffness times geometric-curvature coefficients, not only overflow of C/length. C++ compiles under `-Wall -Wextra -Wpedantic -Werror`; native10/10tests pass in.210s for the suite. Scoped reviewer found no new substantive issue in the fixes; the full Hessian stability and runtime contact limitations remain explicit. Compiler setup and all native build/test jobs have completed; no live child process is intentionally left by this task.
