# Actual continuous blade subdivision rejection

`blade-continuous-nonmanifold.bin` is an8940-byte Godot4.7.2 Variant dictionary
containing synthetic `points`, `indices`, triangular `patch` and `reason`.
Captured from the actual prepared model in `test_blade_closed.gd`, using normal
bounded target commands, after the normalized affine/source-edge fixes following
8ab9629. No patient data or object handles.

The default GS path accepts its initial100-tick incision prefix, then rejects
`blade_nonmanifold_subdivision` before a closed flap exists. The cutter reports
`nonmanifold_subdivision`. Whole-tick rollback/pause remain active. The isolated
embedded direct-curtain circle passes but is not this actual blade trajectory,
contact or physical integration. Do not use that narrow pass to dismiss this
operator failure or claim the simulator complete.

Next: replay this local geometric input and inspect the resulting edge incidence
and insertion/source bindings before another whole encounter. Keep invalid
subdivisions atomic; do not skip or delete tissue to force the encounter through.
