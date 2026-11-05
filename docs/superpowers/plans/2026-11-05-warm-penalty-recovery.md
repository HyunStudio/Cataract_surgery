# Warm temporal point penalty recovery implementation plan

Latest outer-route result after a7f85a6: all244physics ticks accepted but the
existing final central-detachment assertion FAILED (470incisions,6636vertices,
7129faces,retainedarea conserved). The former153solver blockade is passed;
this does not establish correct capsular opening. Evidence archived as
assets/warm-recovery-full-route-2026-11-05.json and matching log. Terminal
topology observation/independent connectivity diagnosis is now in
2026-11-05-terminal-connectivity.md. Full simulator goal remains active.
Remote a7f85a6 Python andNative CI bothsuccess, Actions41980892757/41980892718.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans task-by-task.

**Goal:** Recover numerical stagnation in the SAME physical temporal-contact problem, preserving loads, dt, predictor, constraints, acceptance and work limits.
**Architecture:** Only seeded multi-layer material-point solves may restart an AL subproblem after a backtracked accepted Newton step, reducing numerical rho by10. Preserve accepted PRIVATE iterate and physical multiplier guess; re-evaluate under the new rho in the next bounded outer iteration. Cold/static/ordinary APIs retain their path. No publication until all original gates pass.
**Stack:** Existing private native FEM/contact solver, pinned Zig/Eigen, independent Python/Godot force and complete-motion checks.

Evidence before implementation: exact153request5 needs81iterations/453evaluations,
request7exhausts79/560. Same inputs with rho1 pass16/14; cold pass24/25. Original
line observer shows accepted fractions .125,.0625,.00390625,... startingiteration3.
Independent small3node rotating-contact family with small nonuniform guesses and
rho1e6 exhausts32iterations (fractions3e-5 orsmaller); same physical problems with
rho1pass5iterations. Thus mechanism is reproducible beyond the owned packet.
This does not prove full153motion passes, nor fidelity of the affine path model.

- [x] RED small-family recovery tests, atomic budget exhaustion, all64FP contexts and exact owned153subproblem acceptance using independent original stress/inertia/contact checks.
- [x] After unchanged-source observer finishes, modify only membrane_fem_contact.inc: after accepted Newton step (count it), use existing fraction<.5 damping criterion to restart seeded temporal POINT AL subproblem with rho=max(1,rho/10). Retain x and dual; fresh evaluate at next outer start; no dual update/physical acceptance on restart. Respect existing100outer/250work caps and final force/gap/COMP/SPD gates.
- [x] Rebuild standalone and every affected probe artifact from current hashed inputs. Run new tests and original283numerical tests/29patterns; reject if old ordinary/static contracts regress. Inspect restart behavior/old good seeds; no case-number or specific-time threshold.
- [x] Rebuild actual extension. Parameterize owned test for153 while retaining180default contract; full36actualengine stages include original150/180and153, whole-state scalar/bulk parity and rollback. Current60focused engine inputs are unchanged unless later GD edits require a rerun.
- [ ] Only after exact153whole-step passes and regressions qualify, resume the frozen actual outer blade route; preserve any next failure. Record speed limits and keep full surgery/clinical/GPU/release goals unproven.

Risk: lowering ALrho changes numerical objective between subproblems; a fresh
full evaluation is mandatory and no stale gradient/updated dual may survive.
Every restart follows an already counted accepted Newton step and is also within
existing outer cap. Recovery is not a new physical time step or permission to
waive endpoint/original/full-motion gates. The separate piecewise-dynamics
investigation remains necessary for faithful time evolution.


Implementation/source-bound diagnosis:
- Original observer completed; request5status0/all16stats andrequest7status1/all16
  stats matched saved captures exactly. Accepted fractions below.5 begin at
  iterations3/6 and repeatedly shrink below1e-4. Trace hashes/summaries archived.
- Three independent small-family subcases RED on old solver. New4test module
  GREEN: unchanged original stress/inertia/contact, input ownership,1workatomicity,
  all64actualcallerFPcontexts, andexact owned153subproblems.
- Production recovery is the planned bounded ALrestart after a counted accepted
  step; original dual guess retained, no stale updateddual promoted. Read-only
  review found no substantive defect. Future coverage: warm held/pinned and stiff
  multi-contact/repeatedrestart cases, in addition to existing equality tests.
- Exact153request5 now20vs81Newton,request7success25vsfailure79. Other6captured
  requests retain saved stats bit-for-bit. These are subproblems only.
- Actual whole owned153 nowPASS208/250Newton, independentforce8.43997e-9,
  full-motion certificate0 andatomicrollback;120716ms remainsNOTreal-time.
  Actual180PASS138/250,force2.75213e-9,45630ms. New numerical schedule can change
  prior accepted last bits; physical model, dt/loads/gates remain the same.
- Full283tests/29patterns and36actualengine stages stillrunning frozen before
  commit/fullroute. Current60focused GDinputs unchanged; do not repeat needlessly.


FINAL component qualification:283Native tests/29patterns PASS,36actualengine
stages PASS; current source/build/frozen hashes checked. Existing60focusedGD
source hashes remain unchanged. Original144/146/150/156/167and180pass;150and180
whole-state scalar/bulk byteparity stillpasses within this NEW numerical version.
Whole153passes208/250, originalindependentforce8.43997e-9, fullCCD0 andclock/
rollbackchecks,120716ms. This is not real-time or an actual outer-route pass.

Supplementary small two-contact pinned/held checks atmu2and10000 pass independent
stress/inertia/reaction residuals<=2.77e-9. Their scope is numerical constraints,
not finite-jaw acquisition or complete motion. Raw supplementary metrics archived;
mandatory283tests/36stages remain the primary source-bound regression evidence.

Remote prior8c3c2d9 native/PythonCI success; defaultGodotCI failed. New sourceCI
pending push. Nextresume unchanged frozen fullroute andpreserve anynextfailure;
keep piecewise-fidelity investigation separate and the full goal active.
