# Binary64 retained incision geometry

Continue the full simulator objective after6303680. Exact next incision after154
accepted ticks rejects face1810: positive physical/material area~5.7564e-11,
but binary32 display proxy is collinear. Do not remove it or relax geometry gates.

1. RED a direct binary64 incision API on that physical face and the owned whole
   incision checkpoint. Include simple actual transverse cuts, source fractions,
   invalid input atomicity and independent reconstructed positive orientation.
2. Share topology, budgets and material provenance in the existing cutter. Add
   scalar binary64 vector operations only for the new physical entry point;
   preserve the legacy Vector3 entry point's arithmetic and output contract.
   Keep positive-area, manifold, complete-seam and material-area gates.
3. Feed physical_positions directly from embedded mechanics, preserve binary64
   interpolation weights and compare publication against physical cut points.
   Do not refit material coordinates from a rounded rest/display proxy.
4. Verify exact checkpoint and meaningful regression suites. Qualify real bridge
   and native original equations if state integration changes. Inspect next
   full route failure. No whole-surgery, clinical, GPU or release claim from this.
5. Strengthen central-flap route assertion by original material membership so a
   tiny detached chip alone cannot qualify the intended central tissue flap.


## Implementation and first checks

The new physical API `slice_triangle64` accepts flattened PackedFloat64Array
coordinates. It uses scalar binary64 vectors for patch basis, intersections,
clipping, barycentric coordinates, canonical edge interpolation, midpoint
composition, winding and area. The same topology/manifold/seam/partition/budget
logic serves both physical and legacy entry points. Legacy geometry helpers
still dispatch to the original Vector3/Vector2 operations. Final display copies
remain Vector3, while physical outputs and bindings retain points64/weights64.

Embedded incisions now consume physical_positions directly, and validate
publication against physical cut output rather than a display proxy. Test and
capture cutter adapters delegate the physical API instead of accidentally
falling back to rounded coordinates.

The initial regression failed because the new API did not exist. After adding
it, direct unchanged-sliver, transverse-bank, area/source-binding and invalid
input tests passed; the saved whole incision still failed until the embedded
entry point was connected. The exact saved patch is valid UNCHANGED in the true
geometry; it does not justify manufacturing a new incision. The test checks
unchanged clock/material and increments events only for actual changed cuts.
The prior degenerate-face rejection is eliminated. Local legacy membrane-cut
and finite-patch suites also pass.

The full route's detached-component assertion now requires membership of the
original vertex closest to the central axis. A peripheral chip alone cannot
satisfy that condition. This remains an engineering knife path, not clinical CCC.

Read-only review found no substantive new defect. It explicitly noted that the
existing changed-cut rest/history transfer uses binary32 validation. Thus the
unchanged positive-sliver case does not qualify arbitrary changed slivers through
full refinement; this remains fail-closed and must be addressed if reproduced.
Frozen44-suite regression and22-stage full native/operative repeats are in flight.
No default promotion, actual input/full surgery, throughput, GPU or release claim.

The frozen44 focused suites plus fresh import are terminal and all pass.
[Source-bound engine regression report](../../assets/binary64-incision-regressions-2026-11-05.json).
The full native/operative22-stage run remains live; do not infer its result.

An isolated old/new legacy comparison is also terminal: six finite patches
(three offsets in each geometric/material mode) and two finite curtains produce
identical complete output dictionaries after stripping only the new empty
points64 field. This is compatibility evidence on those8 inputs, not all cuts.
[Inputs and result](../../assets/binary64-incision-legacy-compare-2026-11-05.json),
[comparison script](../../assets/binary64-incision-legacy-compare-2026-11-05.gd).


## Terminal native/operative result

The full frozen run is terminal:21 of22 stages pass. The final operative route
rejects a native equilibrium candidate with status2, force1.18893201e-6 after22
Newton iterations (63 evaluations). Sampled penetration is approximately2.7e-12,
complementarity4.61e-12; these do not waive the force1e-8 gate. The central material
membership assertion correctly also fails: the19 peripheral components do not
constitute the intended central flap. No whole-route success is claimed.

[Full22-stage source-bound report](../../assets/binary64-incision-full-route-2026-11-05.json)
and [terminal log](../../assets/binary64-incision-full-route-2026-11-05.txt).
The old155 incision checkpoint itself is now valid unchanged. The new fresh path
uses more precise geometry and differs from the old rounded path; its exact next
native failure is being captured transparently on the SAME frozen input files.
Do not assume it reached the old154 tick until that capture proves the count.
Do not raise force tolerances or the work/pair budgets to hide this failure.


## Exact next native barrier: motion156

The transparent capture is terminal and reproduces the same native failure.
The new path accepts155 physical ticks (216 staged cut events), then motion156
fails its static endpoint solve. It has346 controls,2665 fine faces and4 bodies.
The typed checkpoint round-trips exactly, and its original control B publication
matches accepted fine positions bitwise. Thus the old155 incision rejection is
also passed in the real route, not only in the isolated unchanged-patch test.

[Capture provenance](../../assets/binary64-incision-next-capture-2026-11-05.json),
[original native request/q0/motion](../../assets/operative-motion156-native-case-2026-11-05.json),
and `godot/tests/fixtures/operative-motion156-state.bin` preserve it.

The endpoint failure has force1.1889320067348663e-6, gap2.7008866165442996e-12,
COMP4.609513794792367e-12 after22 Newton steps, AL outer-loop index6 (stats[14], not a failure-reason code).
The controller's old1e-6 force cap for RETRY ELIGIBILITY prevents its accurate
cold temporal recovery. That cap is not the final1e-8 acceptance gate.

An offline cold [.5,1] solve, from the identical original predictor and remaining
228 steps, passes independent original KKT with force1.0196650453670384e-11 in24
steps. But the complete guard still reports a real intermediate collision at
witness.46875, gap-2.2197969624382363e-6. It is NOT qualified or published.
[First candidate and failed guard](../../assets/operative-motion156-first-temporal-2026-11-05.json).
A bounded witness/seed continuation is being tested separately. Only after full
native/independent/path checks pass should retry selection be generalized and
qualified on this actual engine state. Final tolerances must remain unchanged.


The bounded native continuation is now terminal and NOT qualified. [.5,1] then
[.46875,.5,1] pass independent KKT but fail the complete guard. Adding the next
witness.4697265625 produces native status2, AL outer-loop index5, force3.104943595673991e-8,
gap5.285004453031021e-18 and COMP2.7708076623601036e-17. Only75/250 Newton steps
were spent; this is not exhaustion. The third solve takes107.4s; total138.8s.
[Unqualified exact continuation](../../assets/operative-motion156-temporal-resolve-2026-11-05.json).
Do not change controller retry eligibility yet on the strength of the first
candidate: that alone cannot clear the original path. The precise internal stop branch has not been instrumented yet. Next inspect
this four-layer numerical failure with the last valid seed and original physical
problem, or qualify a genuinely better candidate method. Preserve all gates.

Owned typed motion156 checkpoint SHA256: `97284f912238fd163436c98713fa17e4732b2ec7b38c5e1ba9b7ce093983e647`.
All local capture/replay processes are terminal. Product change253a9fd is pushed;
new remote Python CI41904676104 passed, Godot CI41904676083 failed, native
CI41904675963 was still in progress at last observation. Native41901760065
for the prior seeded candidate change is terminal success. No result is inferred
for a running job, and none was restarted because of an observation timeout.
