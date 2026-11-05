# Legacy complete-case CI topology diagnosis

Observed remote failure d665ac5 Godot run41953551012, job127002915038.
Windows reproduction exits1 with identical target, statusblade_nonmanifold_vertex.
Transparent capture records previous successful cutter result plus next rejected
input. No changed target, tolerance, body, cutter source check or test assertion.

Owned fixture legacy-physics-nonmanifold-state.bin:295vertices, previous478faces,
current468faces. Independent edge/link graph confirms previous stars allvalid;
10faces removed,0added; vertices73,260,259,222each boundarydegree4/twofans.
The cutter correctly rejects the subsequent nonmanifold input atomically.
Legacy capsule_solver.step_tools marks strain-torn edges inactive and rebuilds
triangles, so this is a source-topology/material-loss issue after cutting,
not an error to silence in the cutter's input contract.

Audit tool freezes inputs/engine, replays exact rejected cut and verifies graph.
It intentionally reports qualified:false/reproduced:true, not a green fullcase.
Do not skip this CI test, widen cutter acceptance or disable physical protections
as a fix. Product default must use qualified material-preserving mechanics;
finite jaw acquisition, full case, runtime/GPU and native Windows delivery remain.
The separately frozen native full blade route session21538 remains live and
unchanged; source-based native CI41953551140has now completed successfully.
