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
