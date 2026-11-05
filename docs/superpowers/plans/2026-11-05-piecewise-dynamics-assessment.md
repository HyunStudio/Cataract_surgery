# Assess piecewise physical time integration

This is an architectural investigation toward actual moving-tool simulation,
not permission to change an owned packet dt/force/budget and call the old
monolithic candidate fixed. Existing250-work candidate/regressions stay intact.

Read-only review: the present family q(t)=q0+t(q1-q0) restricts every intermediate
tissue coordinate to one straight path. Actual tissue may deflect then return or
change direction during a rotating contact. Early collocation reactions enter
one endpoint equation with t scaling; passing it qualifies that numerical
candidate family, not independently a faithful time evolution. This limitation
does NOT prove why owned153 failed; numerical convergence remains unresolved.

First evidence: exact geometric counterexample with identical endpoints and
recorded linearly moving obstacle. q0=q1=(0,0), obstacle center=(1-2t,0),radius1/10.
The only affine path is0 and intersects at t1/2. A two-piece tissue path
q=(0,t/2) for t<=1/2 and (0,(1-t)/2) afterward has squared separation >=1/17>1/100
(completing the quadratic square on each half). Demonstrate with rational proof
and existing complete motion guards. This proves path representation restriction
only; it is not an equilibrium/dynamic or owned153 feasibility proof.

Before adopting any new integrator:
- Store physical velocity and timestamps; derive q_k+h*v_k and force/inertia
  scaling for actual h. Reusing a previous-position displacement at a different
  duration changes inherited velocity and is forbidden as a shortcut.
- Damping must be a per-time law (e.g. exp(-gamma*h)), not a frame factor repeated
  once per substep. Define calibration/units instead of inventing clinical values.
- Preserve the SAME recorded tool trajectory at actual global substep times,
  including rotation and endpoint correction. Endpoint chords must not substitute
  for rotating paths. A range-aware guard may be needed; prove this contract.
- Independently check force, holds, anatomy and full CCD for every substep. CCD
  rejection may ask refinement but cannot authorize an unresolved transition.
- Stage positions, velocities, topology, attachments, contacts and clocks; publish
  only the whole accepted frame, otherwise roll back EVERYTHING. Interleave any
  cutting operators at their actual substep time with material/momentum transfer.
- Bound total work and substeps explicitly. A new result is a new integrator's
  qualification, not success of the original250-work monolithic packet.
- Compare trajectories, momentum, energy, contact work and reactions with an
  independently time-refined reference under identical loads and recorded tools;
  include deflect-return, rotating finite-axis, direction reversal and owned cases.

Separate evidence tracks: independently solving the same affine problem proves
numerical failure; proving affine infeasibility but a valid piecewise path proves
representation failure; comparison to converged physical references evaluates
fidelity. A piecewise owned-case success alone does not prove affine infeasibility.

Proceed after current all-pair adapter parity/performance qualification. Avoid
unbounded fixture-specific penalty tuning; retain tuning only with reproducible
mechanism and general regression. Full surgery/model/input/GPU/release goal is
unchanged and unproven.


Owned153 exact-request diagnosis now proves NUMERICAL failure of two particular
subproblems, not affine infeasibility: request5(originalwarmrho1e5,81iterations)
passes16 with only penalty reset1 and passes24 cold; request7(originalwarmrho1e6,
79remainingiterations exhausted) passes14 with only penalty reset1 and25cold.
Same physical predictor/dt/loads/constraints/budget. These native subproblems do
NOT prove the full remaining motion or a whole153step can pass. Evidence archived
in docs/assets/owned153-initialization-comparison-2026-11-05.json. Avoid claiming
representation failure from this budget failure. Future numerical safeguards
must be general/mechanistic (e.g. conditioning/curvature), not case-number or
per-time thresholds. The representational/fidelity investigation remains
separately necessary for actual surgical time evolution.


Geometric counterexample VERIFIED with source-bound tools/prove_piecewise_motion.py:
- Native complete guard on same-endpoint affine patch returns1(collision).
- Both actual piecewise patch/body motion intervals return0(certified clear),
  with the same global kind0 recorded body path, radius,128guard work and1e-9gap.
- Exact Fraction proof uses the actual binary64 patch width/radius and separates
  the finite triangle, not just its center. All artifact/input hashes verified.
- Report explicitly qualified:false, geometric_proof_verified:true; no force,
  velocity, energy or physical time-integration claim. Archived proof JSON and
  CI diagnostic step preserve this distinction. Next investigation must meet
  the independent dynamic/reference requirements above before product use.
