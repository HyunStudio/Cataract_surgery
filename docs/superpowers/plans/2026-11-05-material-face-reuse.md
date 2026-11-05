# Reuse per-face geometry within one material normal inspection

Execute inline in existing worktree, while d665ac5 full route runs frozen.
Scope is actual interaction throughput; do not change full simulator goal.
Profile owned179 already attributes4.456s to engine validation/allocation,
with52920 scalar witnesses. The same face controls, weights and reconstructed
fine geometry repeat for each body, although xyz is fixed during one inspect.

Use local-only face_bodies(state,index,capsules,backend): prepare one face once,
validate each body and each returned witness with unchanged scalar checks,
return ordered full witnesses. No persistent cache across xyz/topology/steps,
no omitted faces/bodies, no relaxed tolerance, same native scalar queries.
Legacy face API retains its input precedence and results. Normal._inspect uses
the local batch only when bodies>0; zero-body behavior is unchanged.

- [ ] RED missing API; ordered bitwise parity with scalar calls, invalid last
  body, bad native later reply, ownership and fresh xyz/topology coverage.
- [ ] Factor scalar preparation/query without math/reassociation changes.
- [ ] Exact owned179 pre/post state/result bits plus wall-time observation.
  Keep only with meaningful measured improvement, not assumed speedup.
- [ ] Focused/actual engine regressions and read-only review before commit.
Full frozen blade route is independent and must never be restarted for this.

Outcome: NOT ADOPTED. RED missingAPI, GREEN batch/scalar and actual native
witness parity. A sibling Packed array alias was caught by an added test;
request and return copies fixed it. All6 final owned179 result/state hashes
matched8390b6254ea22d6d663e4d419410c07a02b4083f39754446fb4efe4e7951c53e.
With required ownership protection, final alternating wall-time medians were
3.496s baseline and3.717s candidate (shared host, overlapping ranges). The
initial unprotected~12% gain is not valid evidence for adoption. Production
scripts/validators were restored to d665ac5; no unsupported API/test remains.
Prototype sources, tests and exact comparison are archived under
../../assets/material-face-reuse-experiment-2026-11-05/ for further investigation.
Next runtime work needs a larger reduction in scalar native calls and
interpreted allocation, with all independent validation gates preserved.
Full frozen blade session21538 continues unchanged; no duplicate route started.
