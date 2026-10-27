# Real-time fixed-step surgery throughput

Previous goal turn made authoritative progress:8f92f34, exact boundary optimization,38 suites and updated Windows artifact. Full realism objective remains active.

Cause: simulator._ready sets Engine.max_physics_steps_per_frame=1, which drops catch-up below60fps. Godot Engine documentation confirms this behavior (https://docs.godotengine.org/en/stable/classes/class_engine.html#class-engine-property-max-physics-steps-per-frame). Do not stretch or skip tissue steps to make the clock look real-time.

Measured600 fixed steps: lens5.520s, capsule5.171s(including boundary2.829s), motion1.067s, injury0.614s, geometry0.993s; total14.060s instrumented. Fixed60Hz requires reducing cost, then restoring catch-up. Reference geometry, masses, force/tear/flow laws and substeps remain unchanged.

- [x] Cache immutable cortical identity per particle/bond at lens reset and avoid zero peel-weight calls when neither cortical endpoint is released. Prove reference numeric equivalence and preserve reset/legacy/hydro/peeling behavior.
- [x] Reduce remaining height-query cost if measured necessary; actual mathematical results and contact history must match reference.
- [x] Coalesce live geometry/UI/record presentation once per rendered frame while retaining every fixed physics step; explicit offline/manual steps publish immediately. Review must discard pending live publication; captures must use latest-state timestamps. RED/GREEN presentation tests.
- [x] Restore bounded engine catch-up (8) and measure actual simulated seconds/wall seconds separately from rendered FPS. Test forced low render rate and normal/adverse/pause/resume with fixed timestep.
- [x] Full regression/GPU/reference comparisons, independent review, export/native/archive and docs. Sustained performance and complete realism acceptance remain open if not proven.

Evidence:1200 legacy/dimensioned lens states and metrics matched original after each step; integrated600-step capsule coordinates/metrics matched baseline;1000 original boundary contact dictionaries matched. Forced30fps clock and deferred-publication regressions observed RED→GREEN. Independent review clear;40 suites and actual-GPU normal/adverse passed. Source active workload32.17fps, overall sim/wall0.978565 and post-warmup0.999901. Release export/120-frame launch passed; external-script native active probe yielded no report and was stopped, so no native active metric is asserted.

This is progress toward the full goal, not completion. Native full-case/pointer acceptance, startup/endurance/60fps performance, precise cut geometry, full tool contact and other documented fidelity gaps remain.

Archive verification passed CRC and byte-for-byte comparison of all9 packaged files against the current build/document files. Milestone complete; the full simulation goal stays active.
