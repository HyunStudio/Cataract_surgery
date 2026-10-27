# Area-preserving membrane incision

> **For agentic workers:** Execute inline with superpowers:executing-plans. The user has authorized continued implementation without design confirmation.

**Goal:** Replace coarse face deletion with a local incision that retains tissue area, creates two real crack banks and transfers existing numerical state.

**Architecture:** First implement a bounded pure geometric cutter. A finite swept curtain intersects actual triangles; inserted points share source-edge identity, local subdivision retains winding, and vertex face fans split only across incision edges. Barycentric source bindings carry material/rest/history data into the later XPBD integration. Integration must then rebuild constraints and masses without healing existing seams or dropping retained flap area.

**Tech stack:** Godot4.7.2/GDScript; current feature checkout. No new dependency. This is a geometric engineering approximation, not calibrated fracture mechanics or a claim of precise clinical CCC.

**Spec:** `docs/REALISM_COMPLETION_KO.md`, active full-simulator goal. Product release `be14d7f` remains unchanged until integration and full qualification succeed.

## Invariants and review focus

- Finite stroke and blade depth only: no infinite-plane cut, masking, or broad off-path damage.
- Preserve every source face's current/rest area within stated numerical tolerance; no face deletion as a fallback.
- Shared old edges reuse intersection points; disconnected coincident surfaces must never weld.
- Interior crack tips stay connected; crack banks can separate. Existing cracks remain separated through original vertex identity.
- Invalid geometry, ambiguous coplanarity, nonmanifold topology and work/geometry exhaustion reject atomically.
- New point bindings are convex barycentric combinations of original triangle vertices; original points retain identity.

## Tasks

1. Create `godot/scripts/membrane_cut.gd` and `godot/tests/test_membrane_cut.gd`. RED→GREEN cases: boundary-to-boundary and interior slits, multiple shared faces, finite depth/stroke, repeated cuts/old seams, winding/area/bindings, unsupported geometry and budgets. Review the geometry before integrating.
2. Integrate incision state into `capsule_solver.gd`: source bindings for rest/previous/anchors, positive areal mass, constraints/components/pressure/contact updates, grasp identity, removed/extracted area accounting. Only actual knife sweeps cut. Replace tensile face deletion with explicit fracture topology separately; never silently retain legacy face loss while claiming completion.
3. Update realistic CCC driver and verify cut/flap topology, true held flap extraction and dynamic contact. Run standard regression, human input cases, real GPU and compiled release qualification. Existing outcome gates remain unchanged.

## Ledger

- Previous goal turn was progress: release `be14d7f` verified/packaged, validator fixes reviewed, full Godot52 and Python541 passed. Current HEAD `7453606`, clean checkout, no live validation jobs.
- Engineering choice: retain material area through subdivision and crack-bank splitting rather than reducing tool radius or raising mesh density while continuing to delete incident faces. Fine fracture direction/material calibration remains a later physical requirement.
- Geometric component now passes boundary/interior slits, shared-edge endpoint insertion, crossing/repeated seams, disconnected coincident surfaces, narrow triangles, finite oblique depth, convex current/rest transfer and atomic budgets/bad input. Runtime rejects nonmanifold vertex links and nonpositive child winding, and each planned source face must have a complete seam chain.
- RED→GREEN on actual curved capsule: rounded edge insertion originally generated overlapping microscopic fans; explicit topological edge insertion fixed this. Fractional endpoint tolerance left short uncut bridges; physical scene-distance endpoint tolerance fixed this. The64-stroke closed circle now retains total area and separates exactly2components,745vertices/924triangles from original217/396, about1.9s for the entire batch on this machine. This is a geometry test, not live frame-rate or surgical-device calibration.
- Independent review's bow-tie source and mixed near-boundary face cases were reproduced RED and fixed. No default `capsule_solver`/knife path connection yet; no new source full53/GPU/native result is claimed at this point. The verified Windows release remains `be14d7f`.
- Geometry committed `1e1763e`; scoped review found no new substantive topology/locality/binding issue. Standard runner now includes53suites. A frozen tracked copy of that commit is being tested under `.tools/cut-regression-1e1763ea`, allowing subsequent integration work without changing a live suite's source.
- Frozen import initially exited1 because the Godot console executable is only a launcher and its sibling GUI engine was not copied. This was a confirmed missing-runtime failure, not an observation timeout; copying the matching sibling corrected the setup. Frozen identity records both launcher SHA256 `c8f0a6bc45a19b33541501e57f6f7cd972ab18453743266339d495cbbe846643` and actual editor core SHA256 `ab1824f85bfd8e0e4128182c000c4003a3e042245b2967848d089b2a04b22424`. Export validator's earlier `editor_sha256` labels the launcher; later provenance should also identify the core. Release engine/product PCK identity checks remain independent and valid.

## Material/XPBD connection — current work in progress

- Frozen pre-integration53-suite run completed exit0 (`cut-frozen53.log`, exec46459 closed). It proves `1e1763e`, not the later state-transfer changes.
- Added transactional `capsule_solver.incise` using `membrane_refinement.transfer`. Convex bindings transfer rest/previous positions and conservative anchor/exterior/removed flags. Parent material face areas are distributed by child rest-area fractions; retained/extracted area accounting uses these authoritative areas, preserving mass without remeshing drift. Constraints use material rest lengths, not deformed positions. Existing captures remain immutable; reset restores original specimen.
- Grasp identities follow their original material face and original vertex binding. If that attachment face splits into two indistinguishable banks, the severed attachment releases rather than selecting one arbitrarily. Grasp acquisition now preserves the point's local tool-frame offset instead of snapping it to the tool center. This fixed a RED no-impulse capture regression.
- Scoped review reproduced a numerical-domain mismatch: newly accepted support could fall below old pressure/edge thresholds. Tests were RED; positive areal support now receives force/mass at every accepted size, nonzero short edge distances are constrained, and exactly collapsed distances use the material rest direction. No artificial mass or raised tear threshold was introduced.
- **Known RED:** `test_capsule_incision` currently fails the small refined-free-flap traction assertion. Its transfer/mass/area/history/grasp/reset/domain assertions pass. This suite is now first in the standard54-suite runner, so canonical validation cannot silently omit the failure. There is no new all54-pass claim or release.
- Actual extraction probe `incision-extraction-probe.log` uses64actual geometry incisions, real flap boundary and .005/tick forceps motion. Initial capture is now0strain/0loss. Second tick still fractures short1.152e-4rest edges (pre-solve max strain18.7101; cut loss.0000129944). Snapshot `incision-first-tear.bin` contains before/after geometry. Earlier probe attempt had a typed-array harness error despite exit0 and was discarded; no pass was inferred from that exit.
- A diagnostic relocation of rupture to after6GS iterations reduced the transient but still failed(max8.53), and was reverted as ineffective. Simply raising iterations/tear strength, deleting pieces, or relaxing completion is not a solution. Next: coupled constraint residual/convergence or conservative mesh-quality improvement for these very short edges, then area-preserving tensile fracture and actual knife sweep integration. The default app still uses its old blade-edge deletion; this new API is not yet wired to input.
- Current focused8-suite batch passed after local contact offsets and domain fixes: capsule solver, old capsule extraction, body app, control context, anterior geometry, simulator, visual snapshot and recording. This is not a full current-source pass. The canonical54runner was actually run and stopped at the retained new traction regression (`incision-current54-red.log`).
- Final scoped review also found later density changes could exceed1e12inverse mass. A RED per-step transactional-domain assertion reproduced it; step preflight now checks all positive material support before any numerical mutation. The new suite returns to exactly1known traction failure. Substep attachment targets still use the full outer-tick pose while tool bodies interpolate; testing per-substep kinematic attachment poses is another concrete next diagnostic.
