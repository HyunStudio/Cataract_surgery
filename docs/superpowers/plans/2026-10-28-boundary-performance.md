# Detached membrane boundary performance

Execute inline; full realism goal remains active. Previous turn made authoritative progress (e430723, 37 suites, GPU normal/adverse, packaged Windows build).

Evidence: 600 deterministic active steps took 23.340s with instrumentation; boundary resolve 12.072s, height queries 10.564s / 133,200 calls. Fresh rendered workload was 22.92fps. Geometry/contact semantics must remain unchanged.

- [x] Save baseline deterministic full state and original boundary reference; add independent actual-triangle height equivalence, source isolation and reconfiguration tests.
- [x] Cache exact XZ height results per immutable configured field with a bounded 512-entry cache. Never quantize queries or skip contact, outside history or extraction checks. Configure replaces cache with the field atomically. Conservatively reject contact queries outside padded actual-vertex Y bounds; hoist packed array references from the triangle loop. No height interpolation arithmetic or collision thresholds change.
- [x] Compare deterministic final capsule/lens state and full contact query outputs with baseline. Measure boundary/profile and actual rendered workload.
- [x] Independent review, affected/full suites, GPU normal/adverse, export/native/archive and documentation. No completion claim for remaining adaptive cuts, full-tool contact or clinical accuracy.

Verified: independent review clear; 38 headless suites passed; actual NVIDIA normal and injury routes passed; editor import/export/native120frames exited0; nine-file ZIP CRC passed. Isolated rendered workload22.92→40.21fps with retained-flap/contact semantics preserved. Full600-step numerical state and1000 reference contact queries matched exactly.

New evidence changes the next action: simulator.gd currently caps physics catch-up at one step/frame, so the faster rendered workload still advances only about19.63 active simulated seconds over30 wall-clock seconds. Real-time timestep/throughput verification must precede claiming60Hz surgery dynamics. Full objective remains active; no other completion criterion is waived.
