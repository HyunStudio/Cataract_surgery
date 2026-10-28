# Coupled membrane contact implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the failing optional native elastic/body alternation with a joint constrained physical substep, then prove actual refined flap extraction. The complete surgical-simulator goal remains unchanged.

**Architecture:** Freeze the inertial predictor once per physical substep. Minimize its mass-weighted compliant-distance energy together with unilateral capsule/triangle constraints. Recompute geometric witnesses and require explicit force/contact feasibility, bounded CCD and transactional rollback before rupture or extraction.

**Tech Stack:** Godot4.7.2, Zig0.17.0, Eigen5.0.1 and optional GDExtension. Python3.12/NumPy/SciPy/IPC Toolkit1.6.1 currently supply independent diagnostics only.

**Spec:** `docs/REALISM_COMPLETION_KO.md` and `docs/superpowers/plans/2026-10-28-native-membrane-solver.md`.

## Global constraints

- Preserve the full user goal: actual input, complete case, anatomy/device/fluids, 3D assets, sustained performance, GPU and Windows delivery.
- Preserve masses, rest area, grasp material coordinates, prescribed points, velocity history, original tear strength and anatomical/body interactions.
- Keep native rollback on failed solving, unresolved CCD, incompatible prescribed points or unsettled contact. A rejected tick never advances physical time.
- Whole-cycle cancellation cannot justify acceptance. A joint solver needs its own force/complementarity/feasibility checks; do not simply remove individual-operator gates.
- Keep all work bounds explicit; preserve failed probes and source/artifact provenance.
- The reduced fixture is an engineering diagnostic, not full-world feasibility, clinical accuracy or realtime qualification.

## Evidence and architectural decision

Commit4063280 resolves the strict262clearance fixture. Actual extraction accepts262ticks with0uncertain/0loss/0broken, then rejects263: operator3.0290155e-4, constitutive7.805708e-5, retained-plane1.927087e-5. Raising budgets/thresholds, changing the route or removing bodies is not the next action.

The last pass alternates on triangles40/627sharing vertex1. A reduced independent constrained solve varies source vertices1/222/741and freezes all selected neighbors at the captured last elastic iterate. The reduced problem contains11vertices,14incident springs,10affected triangles and3capsules. It has a nearby feasible local configuration; this does not establish feasibility of the complete745vertex world.

Canonical input: `native/tests/fixtures/local_jaw_contact.json`, SHA256a3a42402f9de39742a60371668e9f9449d52bae2bd31ab3b1d24b6120b8fc561. It records initial/predicted state, source IDs, masses, rest lengths, alpha and bodies. Intentional neighbor freezing must never be copied into actual integration.

Independent diagnostic uses IPC squared point/triangle and edge/edge distances/derivatives plus an explicit segment/triangle intersection test. SLSQP on coordinates scaled by.001scene units solves15iterations: maximum movement4.1658976e-5, final minimum gap over all affected face/body pairs about-9e-16. Contact Jacobian central-difference discrepancy1.0072e-7; active NNLS reactions are positive and physical stationarity infinity is about3.8e-11after undoing coordinate/objective scaling. The initial unscaled attempt failed line search. This is local numerical evidence, not a global minimum/uniqueness certificate or actual extraction.

Official references: [Toolkit scope/license](https://github.com/ipc-sim/ipc-toolkit), [Python setup](https://ipctk.xyz/build/python.html), [C++ dependencies](https://ipctk.xyz/about/dependencies.html), [IPC paper](https://ipc-sim.github.io/file/IPC-paper-fullRes.pdf). The toolkit supplies collision/contact functions, not a complete physics solver. Diagnostic ipctk1.6.1cp312win_amd64wheel SHA25603f141b0527728a7fb435e429d9e12aed6e2fdeaf230782c6d448b38cc3c11f8was checked against published PyPI metadata, then installed under ignored `.tools/ipc-probe-python`; product/global Python dependencies were unchanged.

## Review focus

- Unsigned distance on the wrong side and missed axis/triangle intersection cannot certify safety.
- Near-parallel/skinny geometry requires correct feature classification and conservative degeneracy handling.
- Duplicate/opposing constraints or prescribed-point infeasibility must solve or fail explicitly.
- Residuals must refer to the fixed predictor and final represented state.
- Topology/removal changes must invalidate relevant contact/factorization caches.

### Task1: Native distance and derivatives

Files: create `native/contact_distance.h`, `native/tests/test_contact_distance.py`; extend the existing native build only as needed. Inspect the minimal official IPC source/dependency graph before selecting a pinned native subset or independently verified implementation.

- [x] Write and observe RED analytical tests: sphere/face, finite endpoint/edge, axis/triangle intersection, crossing side, near-parallel and skinny/degenerate geometry.
- [x] Add derivative checks away from feature changes and explicit conservative behavior at degeneracy.
- [x] Implement the bounded native component with finite/index/shape validation and dependency/license provenance.
- [x] Compare actual local fixture features/derivatives against independent IPC diagnostics; verify, review and commit.

### Task1 evidence

Previous turn made authoritative progress4063280/d490dd4; this continuation began with a clean worktree. Ruling: use an independent standard-library distance/witness/envelope-gradient implementation rather than pulling the entire IPC native dependency graph into this first component. Official1.6.1point/triangle and edge/edge sources were inspected; IPC remains an isolated independent oracle. Cost: finite arithmetic and explicit inconclusive/ambiguous states rather than an exact geometry guarantee. Full solver/CCD integration remains pending.

The test first failed because the new component did not exist. The completed C ABI has bounded coordinate/radius validation, at most12candidates, axis/face intersection including coplanarity, and gradient9with explicit invalid/intersecting/degenerate/ambiguous statuses. Read-only numerical review found two substantive holes: an absolute gradient threshold hid nonunique minimizers at tiny scales; plane cancellation could report definite intersection for a point with exact distance2^-134/3. Both were added as canonical tests, observed RED, then fixed. Internal candidate gradients now compare conservatively without an absolute floor; unreliable oriented-volume/witness calculations report status2. Status2values cannot certify geometry, and status3does not supply a unique derivative.

Final warnings-as-errors build and28native tests pass (16contact+12existing kernel). Strengthened IPC comparison passes292cases:232regular gradient checks,30intersections,28ambiguous,2analytic inconclusive; maximum squared-distance discrepancy6.66134e-16and gradient1.90603e-15. Six analytic expected-status gates and minimum175gradient checks prevent universal uncertainty from falsely passing. Reports initialize unqualified before oracle import, bind parsed fixture bytes and actual artifact/oracle/source hashes, and verify inputs after execution.

Separate contact DLL SHA256dbdd0a03e7044b0e534e10fb05add430631ba0026e6e01a38ec5491a999541e0. Existing membrane/Godot DLLs and application code were not changed. No new full extraction, GPU, performance or release qualification. All build/test/review/comparison jobs in this stage are terminal. Next: Task2joint constrained energy on the actual reduced fixture before complete-substep integration.

### Task2: Joint constrained energy

Files: create `native/membrane_contact_solver.h`, `native/tests/test_coupled_contact.py`; expose a separate C ABI from `native/membrane_kernel.cpp`, retaining the existing unconstrained ABI.

- [x] Write RED tests for analytic contact reaction, separating inactive contact, duplicate/opposing constraints, prescribed-point infeasibility, exhaustion/numerical failure and the local fixture.
- [x] Use the original fixed predictor/masses/rest/alpha; expose primal, stationarity, complementarity, geometry residuals and duals/status.
- [x] Implement bounded joint solving with consistent derivatives and safeguarded steps. Initial penetration requires an explicit feasibility strategy, never silently successful barrier evaluation.
- [x] Verify final geometry/force balance and constrained tangent curvature as appropriate. Legitimate contact reactions do not require unconstrained zero force. Review/provenance/commit.

### Task2 evidence and rulings

Previous turn was progressb23677f; this continuation began clean. Ruling: expose the new C ABI from separate `native/membrane_contact_solver.cpp` and build a separate DLL, rather than modifying the already qualified unconstrained/Godot DLL before coupled verification. The header/API is documented in native/README.md. Cost: an extra experimental build target until bridge integration. This preserves the old product path, not the final simulator scope.

Ruling: use a bounded augmented-Lagrangian solve of the actual normalized capsule-distance inequalities, fixed inertial predictor and original material energy. Sparse safeguarded directions use the material Hessian plus active Jacobian terms. Acceptance separately checks physical force, contact penetration, complementarity and a sufficient numerical tangent curvature screen. Initial positive-distance penetration can recover; axis intersections/active ambiguous geometry remain explicit failures. The screen includes finite-difference contact Lagrangian Hessians, not an exact second-order proof. No tear/strength/budget relaxation or canonical route change.

The new component was initially RED because it did not exist. First implementation passed the real local fixture but the analytic vertex reaction failed during curvature evaluation: two incident features reconstructed the same clamped endpoint with slightly different arithmetic. Added a geometry regression RED, then canonicalized exact endpoint interpolation; actual nonunique minimizers remain status3. All41native tests pass (17geometry+12coupled+12original). Updated independent geometry comparison292cases passes238regular gradient checks,30intersections,22ambiguous and2explicitly inconclusive cases.

Read-only coupled review found no confirmed KKT sign, acceptance, atomicity or work-bound defect. It identified an overflowing linear RHS norm hardening opportunity; a regression was observed RED for reporting a misleading zero residual, then fixed with finite norm/numerator/slope checks and explicit unavailable residual. No second review substitutes for the observed RED-to-GREEN tests.

Frozen-input local diagnostic matches the independent constrained reference: E1.2512188804e-8, reassembled force2.5416764e-9, penetration4.2532e-12, complementarity1.1203e-14,3successful calls, median1.9219ms. The actual full static export (raw SHA5bb5ae7e043a960e42776a451132a23fb10e66648cf0f9842ef4f6c9c50fe5ab) now also solves745vertices/708free points: E3.2986636693e-9, reassembled force1.05695855e-9, no penetration, complementarity2.337e-15,3successful calls, median432.6646ms. This is no anatomical/CCD/full-operation/realtime qualification; all reports explicitly retain that scope and artifact/input bindings.

Coupled DLL SHA77f75c1961c4519ba1d7792fbddebacb7f1d8172d0fbb32ccd625f04a1e6adb3; revised geometry DLL SHA80e47164e35b5a7cfd66c9c1fcb3d95e0e2ee9b478800873e9e3a6f2eb72fa13. Existing membrane and Godot extension bytes were not changed. Current build/test/review/benchmark/diagnostic handles are terminal.

### Task3 precision gate discovered before integration

The actual full candidate, published as Godot float32vectors, incurs maximum coordinate rounding5.54756e-8and force residual4.61851e-6despite penetration only2.3173e-10. A frozen Godot check of actual cornea/iris and existing swept body projection yields boundary/body correction0, contacts0, uncertainty0. Thus geometric proxy compatibility alone is insufficient for the native force claim. Ruling: retain authoritative float64positions and velocity history for the new complete-substep path; rendering float32is publication, not the physical state. Extend rollback to these arrays and transfer them on incision/topology updates. Do not quietly count quantized force error as the native1e-8gate or remove gates to pass.

### Task3: Actual complete-substep integration

Bridge checkpoint: separate `MembraneContactKernel` accepts strictly typed packed64 inputs, preserves caller ownership, validates shape/budget before pointers, and publishes packed64 output atomically through the existing C ABI. Missing-class RED preceded implementation. The 64-TU build includes the coupled source and all local headers in cache identities. Frozen bridge `t2_k1hh_` and existing capsule `vxb6ds4o` validators pass, extension SHA256 `2d6689cb8e38d780463e0993226345ff5ca5c9755bc84db5714b4cdfe381492d`. Read-only review found no actionable ownership, argument-order, cache/provenance or guard defect. This completes only the bridge checkpoint; persistent float64 model state and actual complete-substep integration remain pending.

Files: confirm and extend the existing native bridge, `godot/scripts/native_membrane_backend.gd`, `godot/scripts/capsule_solver.gd`, body/anatomical adapters, native tests and validator.

- [ ] Write RED transactional, pinned, shape and uncertainty tests for the complete-substep interface; retain failure injection coverage.
- [ ] Freeze the actual predictor once and include every original free point/current topology. Jointly generate/update body and anatomical constraints; do not freeze free neighbors as in the diagnostic.
- [ ] Preserve authoritative float64positions/history across substeps, cuts and failures. Test float32publication separately, without using it to overwrite the physical state each frame.
- [ ] Preserve actual grasp coordinates, history, boundary side, incision/material/extraction accounting and rollback. Check CCD from the physical previous state to the accepted candidate.
- [ ] Replay actual263, then canonical full refined extraction and acceptance guards. A later honest failure is another unfinished gate, not a reason to weaken criteria.
- [ ] Qualify default regressions, sustained performance, actual GPU and packaging before backend promotion. Keep the complete goal unproven until every user requirement is verified.
