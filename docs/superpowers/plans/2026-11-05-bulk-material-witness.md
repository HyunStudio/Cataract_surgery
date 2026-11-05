# Bulk unchanged material witnesses for interaction throughput

Inline TDD in current worktree. Full simulator goal unchanged. Static culling
is deferred because rounded-geometry/status enclosure is not yet proven.
Instead, send all face/body queries in one bounded call using unchanged
material_witness::query math and order. No skipped pairs, changed tolerances,
new contact model, persistent cache or relaxed independent checks.

- [x] C ABI membrane_material_witness_batch: <=8192faces, <=64bodies,
  <=65536pairs; controls9/face, shapes9/face, capsules7/body. Atomic outputs:
  status0 publishes ordered pair codes0/1/3 and13values; any scalar2/-1
  rejects without publishing. Zero/oversized/null input rejects. FP restored.
- [x] Typed optional Godot bulk method, same strict shape checks and owned arrays.
- [ ] Godot independently prepares/validates each face and verifies each returned
  witness with unchanged reconstruction/KKT/regularity checks. Native bulk only
  when available; legacy fallback unchanged. Handle later bad pair atomically.
- [x] Existing scalar/bulk bitwise parity on randomized rigid poses, all status
  classes, maximum counts, invalid last input and64caller FP contexts.
- [ ] Owned179 exact accepted state/result parity, alternating measured cost;
  focused/actual engine regressions and read-only review before adoption.
Full frozen blade route21538 continues unchanged. Even a large component speedup
will not prove full-operation real-time performance or clinical accuracy.

Native5newtests PASS, all270tests/27patterns PASS; actual optional native bridge
6stages PASS. Read-only review found no substantive defect. Bulk is NOT used
by runtime yet, and no speedup is claimed. Remaining Godot independent batch
verification and owned performance/state parity stay open, then runtime use.

Full blade21538 completed with next owned180 temporal failure. See
2026-11-05-motion180-temporal-points.md. Source code of frozen route is unchanged
and must not be rerun until a qualified change addresses that exact failure.
