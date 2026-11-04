extends RefCounted
## Original-material mechanics behind the existing operative capsule interface.
## Optional until complete input/anatomy/extraction/throughput qualification.
const Embedded=preload("res://scripts/embedded_membrane.gd")
const Precision=preload("res://scripts/membrane_precision.gd")
const Path=preload("res://scripts/instrument_path.gd")
const Anatomy=preload("res://scripts/anatomical_contact.gd")
static func invalid(reason:String)->Dictionary:return {"valid":false,"changed":false,"reason":reason}
static func initialize(model)->Dictionary:
	var tissue=Embedded.new()
	var result:Dictionary=tissue.initialize(model._material_rest,model._material_indices,model.anchored,model.surface_density)
	if not result.valid:return result
	return {"valid":true,"reason":"","state":tissue.snapshot()}
static func configure(model,backend:RefCounted,guard:RefCounted)->bool:
	if backend==null or guard==null or model.stretch_backend or model.contact_backend or model.embedded_backend:return false
	for method in ["solve_fem","solve_contact_fem","contact_fem"]:
		if not backend.has_method(method):return false
	if not guard.has_method("guard_motion") or model._integration_steps!=0 or model._incision_events!=0:return false
	if model.positions!=model.rest_positions or model._previous!=model.rest_positions:return false
	var prepared:=initialize(model)
	if not prepared.valid:return false
	model.embedded_backend=backend;model.embedded_guard=guard;model._embedded_state=prepared.state
	model._embedded_solver=null;model.native_failure={}
	return true
static func solver(model):
	if model._embedded_solver==null:model._embedded_solver=Embedded.new()
	model._embedded_solver._state=model._embedded_state.duplicate(true)
	model._embedded_solver._cutter=model._cutter
	return model._embedded_solver
static func mirror_valid(model)->bool:
	if model._embedded_state.is_empty():return false
	var state:Dictionary=model._embedded_state
	return model.triangles==state.indices and model.positions==Precision.publish(Embedded._publish(state,state.xyz)) and model._previous==Precision.publish(Embedded._publish(state,state.previous))
static func publish(model,topology:bool)->void:
	var state:Dictionary=model._embedded_state
	model._physical_xyz=Embedded._publish(state,state.xyz);model._physical_previous=Embedded._publish(state,state.previous)
	model.positions=Precision.publish(model._physical_xyz);model._previous=Precision.publish(model._physical_previous)
	model._integration_steps=state.steps;model._incision_events=state.events
	if not topology:return
	model.rest_positions=state.rest.duplicate();model.anchored=state.anchored.duplicate()
	model._removed=state.removed.duplicate();model._outside=state.outside.duplicate()
	model._physical_rest=Precision.pack(model.rest_positions)
	model._rest_area=PackedFloat64Array();model._rest_area.resize(state.rest.size())
	model._inverse_mass=PackedFloat64Array();model._inverse_mass.resize(state.rest.size())
	model.edges.clear();model._faces=[];model._face_edges=[];model._edge_map={};model._face_rest_area=PackedFloat64Array()
	model._face_material=PackedInt32Array();model._edge_a=PackedInt32Array();model._edge_b=PackedInt32Array()
	model._edge_rest=PackedFloat64Array();model._edge_active=PackedByteArray();model._lambdas=PackedFloat64Array()
	model._incident=[]
	for i in range(state.rest.size()):model._incident.append([])
	for face in range(state.indices.size()/3):
		model._add_face(state.indices[face*3],state.indices[face*3+1],state.indices[face*3+2],state.areas[face],state.ancestors[face])
		for j in range(3):model._rest_area[state.indices[face*3+j]]+=state.areas[face]/3.
	for i in range(state.rest.size()):
		# These fine values describe geometry only. Native inertia is the
		# original support.mass, never this independent tiny-fragment inverse.
		if model.anchored[i]==0 and model._rest_area[i]>0.:model._inverse_mass[i]=1./(state.density*model._rest_area[i])
	model._pinned=model.anchored.duplicate();model._grasps={};model._grasp_faces={};model._grasp_offsets={}
	model._rebuild_triangles()
static func incise(model,patches:Array)->Dictionary:
	if not mirror_valid(model):return invalid("embedded_mirror")
	var tissue=solver(model)
	var result:Dictionary=tissue.incise_patches(patches)
	if not result.valid or not result.changed:return result
	model._embedded_state=tissue.snapshot();publish(model,true)
	return result
static func pressure(model)->PackedFloat64Array:
	var state:Dictionary=model._embedded_state;var out:=PackedFloat64Array();out.resize(state.xyz.size())
	if model.pressure_load==0.:return out
	model._refresh_components()
	var xyz:=Embedded._publish(state,state.xyz)
	for face in range(state.indices.size()/3):
		var a:int=state.indices[face*3];var b:int=state.indices[face*3+1];var c:int=state.indices[face*3+2]
		if model.geometry and not model._components[model._vertex_component[a]].anchored:continue
		var u:=PackedFloat64Array();var v:=PackedFloat64Array()
		for axis in range(3):u.append(xyz[b*3+axis]-xyz[a*3+axis]);v.append(xyz[c*3+axis]-xyz[a*3+axis])
		var force:=PackedFloat64Array([u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]])
		for vertex in [a,b,c]:
			for j in range(state.support.point_nodes[vertex].size()):
				var node:int=state.support.point_nodes[vertex][j];var weight:float=state.support.point_weights[vertex][j]
				for axis in range(3):out[node*3+axis]+=weight*force[axis]*model.pressure_load/6.
	return out
static func boundaries(model,before:PackedFloat64Array,after:PackedFloat64Array)->Dictionary:
	var selected:=PackedInt32Array()
	for i in range(model.anchored.size()):
		if model.anchored[i]==0 and model._removed[i]==0:selected.append(i)
	for name in model.embedded_surfaces:
		var query=Anatomy.new()
		if not query.configure(model.embedded_surfaces[name]):return invalid("anatomy_shape_"+name)
		var result:Dictionary=query.inspect(model.embedded_guard,before,after,selected)
		if result.get("status",-1)!=0:return result.merged({"valid":false,"changed":false,"reason":"anatomy_"+name},true)
	var outside:PackedByteArray=model._outside.duplicate()
	if model.tissue_boundary:
		var old:=Precision.publish(before);var next:=Precision.publish(after)
		for i in selected:
			var result:Dictionary=model.tissue_boundary.resolve(old[i],next[i],outside[i]!=0)
			if not result.valid or result.position!=next[i]:return invalid("boundary_correction")
			outside[i]=1 if result.outside else 0
	return {"valid":true,"reason":"","outside":outside}
static func step(model,dt:float,tools:Array[Dictionary])->Dictionary:
	if not mirror_valid(model):return invalid("mirror")
	if not is_finite(dt) or dt<1e-6 or dt>.1 or tools.size()>2:return invalid("step_input")
	if not is_finite(model.pressure_load) or absf(model.pressure_load)>5. or not is_finite(model.damping) or model.damping<0. or model.damping>1.:return invalid("step_load")
	if model.surface_density!=model._embedded_state.density:return invalid("density_change")
	var body:Array=[];var hands:Dictionary={}
	for tool in tools:
		if not tool.get("hand") is int or tool.hand not in [0,1] or hands.has(tool.hand):return invalid("tool_hand")
		hands[tool.hand]=true
		if not tool.get("tip") is Vector3 or not tool.tip.is_finite() or not tool.get("grip") is bool or not tool.get("cut") is bool:return invalid("tool_input")
		if tool.grip:return invalid("finite_jaw_acquisition_pending")
		if tool.cut:return invalid("requires_finite_blade")
		if not tool.get("body") is Array or tool.body.is_empty():return invalid("body_missing")
		if not model._face_contact.valid_body(tool.body):return invalid("body_input")
		for part in tool.body:
			if not part is Dictionary or not part.has("path") or not Path.valid(part) or part.has("attachment"):return invalid("body_input")
			body.append(part)
	if body.size()>64:return invalid("body_budget")
	var motion:=Path.motion_request(model._physical_xyz,model._physical_xyz,model.triangles,body)
	motion.guard=model.embedded_guard
	var tissue=solver(model);var before:PackedFloat64Array=tissue.physical_positions()
	var result:Dictionary=tissue.advance_contact(dt,pressure(model),model.embedded_backend,model.embedded_mu,model.embedded_lambda,motion,model.damping,model.embedded_budget)
	if not result.valid:return result
	var checked:=boundaries(model,before,tissue.physical_positions())
	if not checked.valid:return checked
	model._embedded_state=tissue.snapshot();model._embedded_state.outside=checked.outside
	model._outside=checked.outside;model._embedded_energy=result.elastic_energy;model._embedded_force=result.force_inf
	model._peak_strain=maxf(model._peak_strain,result.maximum_strain)
	model.body_contact_count=0;model.body_contact_uncertain=0
	for dual in model._embedded_state.get("contacts",{}).get("dual",PackedFloat64Array()):
		if dual>0.:model.body_contact_count+=1
	model.body_contact_residual=result.stats[12]
	model.joint_stats=result.stats.duplicate();publish(model,false)
	return result
