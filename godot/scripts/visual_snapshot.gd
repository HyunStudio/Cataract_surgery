extends RefCounted
## Rich dictionaries are materialized only for a caller requesting capture/review.
static func expand_lens(state:Dictionary)->Dictionary:
	if not state.has("positions"): return state.duplicate(true)
	var particles:Array[Dictionary]=[]
	var bonds:Array[Dictionary]=[]
	for i in range(state.positions.size()):
		particles.append({"position":state.positions[i],"velocity":state.velocities[i],"mass":state.masses[i],"active":state.active[i]!=0,"cortex":state.cortex[i]!=0,"adhesion":state.adhesion[i]})
	for i in range(state.bond_a.size()):
		bonds.append({"a":state.bond_a[i],"b":state.bond_b[i],"rest":state.bond_rest[i],"active":state.bond_active[i]!=0,"damage":state.bond_damage[i]})
	return {"particles":particles,"bonds":bonds}

static func expand_capsule(state:Dictionary)->Dictionary:
	if not state.has("edge_a"): return state.duplicate(true)
	var edges:Array[Dictionary]=[]
	for i in range(state.edge_a.size()):
		edges.append({"a":state.edge_a[i],"b":state.edge_b[i],"rest":state.edge_rest[i],"active":state.edge_active[i]!=0,"lambda":state.edge_lambda[i]})
	return {"positions":state.positions.duplicate(),"triangles":state.triangles.duplicate(),"edges":edges}
