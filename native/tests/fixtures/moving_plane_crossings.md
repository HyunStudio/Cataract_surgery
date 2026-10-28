# Moving-plane crossing counterexamples

`moving_plane_crossings.json` contains8 deterministic affine triangle / linearly moving sphere counterexamples generated using NumPy seed2612026 and SciPy rotations. Generation considered344 candidate pairs and retained examples with clear triangle-interior endpoint/midpoint projections (plane distance>.12 for radius.1) but an intermediate interior projection with plane distance<.06. Rotation is used only to generate triangle endpoints; the tested triangle trajectory is affine.

Each case records its witness time and distance. The regression independently recomputes the cross-product plane normal, signed point-plane distance and barycentric coordinates using Python scalar arithmetic. The projection lies inside the triangle, so this witness proves actual penetration rather than merely overlap of a plane extension. A three-query budget must never certify clearance, and the original128-query budget must detect penetration. These cases protect the continuous certificate against accepting clear endpoints/midpoints while missing an intermediate crossing.

Generation helper is preserved under ignored `.tools/find_motion_adversaries.py`; the checked-in JSON, rather than a random search at test time, is the reproducible test input. These are numerical engineering counterexamples, not surgical measurements.
