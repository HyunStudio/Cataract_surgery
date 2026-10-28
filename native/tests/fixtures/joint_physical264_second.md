# Physical-radius second-substep regression

`joint_physical264_second.json` SHA256 `a89973d2dac52d695a628b608471070e8fce76813b711d2f87b7f2d4cf569f01`.

This is an actual optional capsule joint request with745vertices/708free points,1668material edges,924triangles,3tool capsules and alpha.07200000000000001. It uses the original forceps/shaft physical radii (.010,.010,.020), not angular enclosure padding. All free points, predictor, masses, rest lengths and pins are retained.

Diagnostic `.tools/replay_physical264.gd` restored the rejected outer264state from frozen `3ea284w6`, reconstructed the actual anatomy/wound, and executed the current timestep through frozen `mc9e3twd`. First substep accepted (energy5.93891e-9, force6.58474e-9); the second request was captured before solving, using full-precision JSON. The implementation is recorded in f494933; the later no-path enclosure review fix does not change this generated pose path. This is a diagnostic replay from an earlier accepted state, not a complete latest-source extraction qualification.

The original solver reports numerical status2: standalone last recorded force3.66715e-8, penetration3.3510e-10, complementarity8.91294e-13; the engine build also rejects2with slightly different iteration counts. The regression retains the original caller gates (force1e-8, penetration1e-9, complementarity1e-11). Native tests independently reassemble the accepted forces/contact reactions, geometry, complementarity and exact pins. Godot tests exercise the same packed request without a float32round trip. No clinical, whole-operation, anatomical/CCD or realtime claim follows.
