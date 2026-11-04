# Blade midpoint edge-snap regression

`blade-midpoint-edge-snap.bin` is a Godot4.7.2 Variant dictionary with `points`,
`indices`, `patch` and the original `reason`. It contains no patient information
or object references. It was captured from the prepared synthetic anterior
capsule and normal bounded target motion in `test_blade_closed.gd`.

The pre-fix cutter rejects `subdivision_winding`: the midpoint of a short
transverse incision in face(256,255,237) incorrectly snaps onto a nearby source
edge. The replay is checked for area, provenance, nondegenerate winding and a
real incision in `test_membrane_cut_patch.gd`. This resolves that geometric
failure only. The full route subsequently rejects a separate material
`mass_resolution` condition; it is not a full procedure acceptance fixture.
