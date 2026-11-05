# Investigate certified inactive material-point cost

Latest measurement after a7f85a6 recovery: source-bound owned153 instrumented
whole step97.8s,Native solve/contact82.6%,bulk1.77%,guard0.06%,other engine15.6%.
All result/control/request/response/guard bytes match the captured baseline.
Separate timer-only Native replay14requests94.45s;regularity0.351s(0.37%),
all saved response bytes identical. Ruling: DO NOT implement regularity omission
on this evidence; it cannot materially address the current latency. No production
Native optimization added. Earlier inactive-certificate proposal remains unimplemented.
Full unchanged route now reaches244acceptedsteps but fails central-detachment;
terminal connectivity diagnosis takes priority (2026-11-05-terminal-connectivity.md).

Historical planning notes follow; old durations/process IDs are not current state.

No production change during active final temporal-source validation18776. Earlier81677 failed150 and is terminal.
Owned180 is functionally passing but153946ms; actual144 now175600ms.
Full simulator real-time goal remains unmet. Need measured cost decomposition,
not another small unqualified allocation rewrite.

Code observation: FineContacts.evaluate with physical_dual builds regular[face]
using fem_trajectory_merit::regular on all shape rows. Material points repeat
one row three times, so that triangle regularity is always false. Consequently
physical dual0 cannot take the existing certified-inactive PHR shortcut even
when its original-control hull certifies strict separation. Every scalar point
geometry query still happens before this branch.

Hypothesis: point geometry does not need triangle-area regularity. A valid
fixed material point, mandatory successful point geometry proposal, physical
multiplier0 and outward original-field hull separation can certify zero PHR
without the irrelevant triangle-area test. A stronger optional point-field hull
may certify more inactive rows than the existing three-control hull. Do not
change dense fine-face behavior, skip mandatory queries, infer safety from a
heuristic epsilon, or loosen force/gap/COMP/work gates.

Before adoption:
- Independently review exact sufficient conditions, rounded/unrounded distinction,
  contract validation and malformed point-row/far cases.
- Add isolated helper-count RED/GREEN tests for point-only physical-zero paths,
  valid/failing/all caller FP controls, zero-vs-positive dual and proof failures.
- Require old/new values/gradients/blocks/merit intervals and owned179/180 whole
  accepted states/results to remain bitwise identical; no claimed-regular point
  triangle. Compare the point constraint model only.
- Profile actual owned180 costs (native solves, scalar/bulk proposals, full guard,
  engine validation/allocation), then controlled measured improvement and full
  relevant regressions. No current optimization or speedup claim.

Bulk witness proposal API remains separate and unused at runtime. It can later
reduce interpreted marshalling while preserving every independent witness check.


Read-only review constraint: current inactive_hulls uses Bound(radius*radius)
with an already rounded binary64 product. If rounded downward, distance² greater
than that value does NOT prove separation from the exact binary64 radius².
A tiny inward offset can therefore retain positive penetration. A point-only
certificate must enclose the unrounded radius product outward, establish both
normalized inactivity and original-field separation, require successful mandatory
query plus validated repeated point rows and actual physical dual exactly0
(including signed zero). Uncertain bounds fall back; tiny positive dual never
uses the shortcut. Add downward-rounded-radius², tiny-offset, equality/uncertain,
malformed-point, positive-dual, temporal and signed-zero tests before any adoption.
No such optimization currently exists.

Profile before picking native interval work versus interpreted query costs.
An optional all-pair runtime batch may instead construct owned per-layer control/
shape arrays once, call existing bounded material_witnesses_fem for every pair,
and independently validate/reconstruct every returned witness. Reuse fine face
geometry only within that immutable call; no cache keyed by sizes/topology alone.
No far-pair culling is planned without a separate proof. Require scalar/bulk
packet and acceptance bit parity, malformed final pair atomicity, all layers,
capacity/ownership coverage and actual measured cost decomposition. The earlier
face-reuse prototype showed no stable gain and must not be silently reinstated.


Additional exact-threshold requirement for a future point-specific certificate:
current normalized field uses rounded binary64 r2=radius*radius. Require BOTH
separation from exact binary64radius² and normalized inactivity relative to
roundedr2*(1+dual/rho). Using only exactradius²*(1+dual/rho) is insufficient when
roundedr2 rounds UP. A conservative maximum of separately outward-enclosed
thresholds can establish both. This is a proposal only; no helper implemented.
Current180profile was6%solver, but failed153native line-search81/79 had hundreds
of evaluations and dominated cost. Reprofile AFTER numerical recovery before
choosing engine versus native interval work; one saved step is not all workloads.
