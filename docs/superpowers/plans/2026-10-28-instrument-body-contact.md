# Instrument body contact and actual entry tunnel geometry

Execute toward full realism goal; previous turn6d6bda6 is verified progress. User authorized implementation without design-question pauses.

Design: generic dimensioned instrument segments share renderer/contact profiles. Geometry kernel gives exact unmasked capsule/triangle distance and conservative swept segment contact. Rigid cornea/iris/posterior constrain the inserted body; elastic anterior membrane requires distributed pressure/contact, not arbitrary disappearance or rigid-only blocking. Working parts alone receive cutting/energy effects.

Important discovered dependency: a generic ignored-face callback cannot certify continuous shaft clearance through a spatial wound; the nearest ignored witness can hide a later intact contact. The kernel must fail closed in that case. Actual entry tunnel surface geometry is needed, rather than weakening the sweep or ignoring entire intersected triangles.

- [x] Parallel kernel/profile components, independent files/tests. Kernel supports exact unmasked query and conservative motion, explicitly refusing uncertified ignore intervals.
- [x] Unify renderer frame and full jaw closure with contact geometry. Both named jaws change endpoints, angle and length; applied/reviewed frames restore the same geometry.
- [x] Pure closed-shell tunnel builder: bounded convex stroke subtraction, conforming triangles, walls, original source-face IDs (-1 for walls), source validation and work budgets. Actual healthy default cornea and 101-point trace pass. Open injured shells explicitly reject; integration/caching and injury identity handling remain in the next task.
- [ ] Apply rigid inserted body contact against actual tunnel/iris/posterior, with reachability-aware pose correction, and elastic capsule body response. Guard part-specific cutting/energy; preserve source face identities.
- [ ] Default complete encounter, adverse/body-only tests, review/capture/reset, GPU workload, independent review, Windows export/archive and docs. Do not declare shaft physics complete before application integration and complete encounter proof.

Limits: capsule envelopes approximate generic parts (knife prism is conservatively enclosed), not manufacturer-specific full mesh collision. Existing point/triangle cloth mechanics need explicit disclosure until complete. Full goal remains active.

## Integration handoff

`instrument_body_contact.resolve(from_tip,from_axis,to_tip,to_axis,tool,radius,grip,surfaces)` is a verified standalone rigid adapter. Accepts actual `positions/triangles/revision` meshes for cornea/iris/posterior; returns tip/axis/fraction/contacts/recovered/reason. Consume recovered pose even at fraction zero. It has no portal constraint or elastic anterior handling and is deliberately not enabled in the default app yet. Translation plus quaternion interpolation must be reconciled with the actual portal rig, never applied off-pivot silently. Avoid repeated full kernel queries for validation in the eventual hot path.

`tunnel_surface.build(points,indices,paths,width,portals,max_triangles)` is also a standalone foundation; the default app still uses the existing logical wound predicate and traced-line rendering. Its healthy default output is1483 vertices/2962 triangles; approximately0.7–1.0s build in local observations. It cannot be rebuilt each physics tick. Cache on actual geometry/trace and handle asynchronous publication or cut completion without admitting an uncertified pose. Do not substitute a closed healthy tunnel over an injured open cornea or pass generated triangle IDs into the raw injury tracker.

Elastic anterior contact should use intact-face barycentric witnesses and inverse-mass distributed unilateral constraints, interleaved with edge XPBD, with previous-pose contact side and swept motion candidates. Existing vertex-only `_project_contact` misses face interiors and can be undone by edge constraints. Keep grasp radius separate. Include retained held/free flap faces (do not exclude entire held component as rigid tip avoidance does); exempt only the local grasp attachment. Pinned/anchored vertices have zero inverse mass; report unsatisfied contact instead of deleting tissue. Contact deformation may cause strain tearing, while shaft/sleeve cannot directly cut or transmit phaco energy. Alternate flap boundary/contact and retire extraction only after constraints converge. Remove duplicate rigid anterior-tip blocking only when this response takes responsibility.

Verification added RED→GREEN reproductions for masked static-query false clearance, skinny-face Gram cancellation, shallow edge crossing, consistent contact tolerance, jaw tracking/closure and overflowing render-axis magnitude. Kernel masks fail closed when no clearance certificate exists. Whole goal remains active; these component tests do not certify complete body physics.
