# Next owned180 failure: temporal distributed material normals

Full frozen blade session21538 is TERMINAL exit0 capture/route_passedfalse
(actual engine return1). Do not poll/restart it. Source snapshotd665ac5:
.tools/fem-extension-fdy5l63n. Previous cut299 capacity failure is passed,
but no complete frame beyond179 is qualified.

Captured operative-motion180-state.bin owns staged state:179steps,301cut
events,4486fine vertices,4817faces,346controls,limit8192. Events301 belong to
intermediate cut processing before the rejected physics frame, not accepted
whole-frame publication. Whole simulator transaction correctly rolls back.

Native request0 material_points budget250 succeeds22Newton, force3.2243e-11;
request1 material_points budget228 succeeds24Newton, force1.6662e-10.
Full geometry guard then finds a middle-path collision at t=.5, face22/body0,
gap-4.18177e-5. Cold original-fine-face trajectory gets remaining204Newton and
fails withforce.37807666. Total work250 is preserved; do not raise it or relax
force1e-8/gap1e-9/COMP1e-11. Central flap remains attached.

Raw little-endian exporter/decode retains exact request and response doubles,
including the entire guard history. Use owned requests instead of replaying
another long successful prefix. Endpoint success is not motion clearance.

Next implementation after bulk-query foundation:
- Native private FineContacts already supports material_points with layer-major
  time(), local interpolated controls, force t, Hessian t² and point merit
  change(previous,before,after,shape,time). Verify these paths with RED tests;
  add a separate recorded-trajectory material-point API, preserve all old calls.
- Godot point generator must inspect actual original geometry at every sampled
  body pose/time and add penetrating material-point rows across layers.
- Independent point reactions must validate provenance, dual shape, t-scaled
  force and original stress/inertia. Never reuse point duals as fine-face
  temporal multipliers; separate candidate model/seed contracts remain.
- Full physical motion guard remains mandatory and can insert another witness
  time within existing16layer/shared250work limits. Publish only after all
  independent force/gap/COMP/whole-motion gates; otherwise roll back everything.
- Test analytic moving/rotating interior contact, time scaling, endpoint-only
  parity, invalid model/negative work/ownership, callerFP and owned180 exact
  whole-step acceptance before another full route. Bulk witnesses may reduce
  repeated query cost but are not a contact-model or real-time qualification.

Native optional bulk ABI5tests and actual bridge6stages pass. It is not yet used
by runtime; full native270test qualification is still running before commit.
