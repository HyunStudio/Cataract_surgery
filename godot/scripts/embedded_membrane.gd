extends RefCounted
## Experimental retained-cut state in an original-material mechanical basis.
## Starts from its own rest state; never projects an accepted legacy simulation.
## Optional implicit dynamics; contact and partial-crack enrichment remain separate.
const Support=preload("res://scripts/membrane_support.gd")
const Refinement=preload("res://scripts/membrane_refinement.gd")
const Precision=preload("res://scripts/membrane_precision.gd")
const Cutter=preload("res://scripts/membrane_cut.gd")
const Energy=preload("res://scripts/membrane_energy.gd")
const FORCE_TOLERANCE:=1e-8
const GAP_TOLERANCE:=1e-9
var _cutter=Cutter.new()
var _state:Dictionary={}
var _energy:RefCounted
var _native_geometry:Dictionary={}
static func invalid(reason:String)->Dictionary:
	return {"valid":false,"changed":false,"reason":reason}
func snapshot()->Dictionary:
	return _state.duplicate(true)
static func _fixed_controls(support:Dictionary,anchors:PackedByteArray)->PackedByteArray:
	var fixed:=PackedByteArray();fixed.resize(support.controls.size())
	# A virtual basis label can refer to a vertex outside its retained fragment.
	# Only retained anchored material may impose the fixed boundary condition.
	for point in range(anchors.size()):
		if anchors[point]==0:continue
		for node in support.point_nodes[point]:fixed[node]=1
	return fixed
func initialize(original:PackedVector3Array,indices:PackedInt32Array,anchors:PackedByteArray,density:float)->Dictionary:
	if original.size()<3 or original.size()>4096 or indices.is_empty() or indices.size()%3!=0 or indices.size()>24576 or anchors.size()!=original.size():return invalid("initial_shape")
	for flag in anchors:
		if flag not in [0,1]:return invalid("anchor")
	for index in indices:
		if index<0 or index>=original.size():return invalid("initial_index")
	var areas:=PackedFloat64Array();var ancestors:=PackedInt32Array()
	for off in range(0,indices.size(),3):
		areas.append((original[indices[off+1]]-original[indices[off]]).cross(original[indices[off+2]]-original[indices[off]]).length()*.5)
		ancestors.append(off/3)
	var support:=Support.build(original,indices,original,indices,ancestors,areas,density)
	if not support.valid:return invalid(support.reason)
	for mass in support.mass:
		if 1./mass>1e12:return invalid("embedded_mass_resolution")
	var xyz:=PackedFloat64Array()
	for index in support.controls:
		for j in range(3):xyz.append(original[index][j])
	var flags:=PackedByteArray();flags.resize(original.size())
	_state={"original":original.duplicate(),"original_indices":indices.duplicate(),"original_anchors":anchors.duplicate(),"rest":original.duplicate(),"indices":indices.duplicate(),"ancestors":ancestors,"areas":areas,"anchored":anchors.duplicate(),"fixed":_fixed_controls(support,anchors),"removed":flags,"outside":flags.duplicate(),"fallback":original.duplicate(),"support":support,"density":density,"xyz":xyz,"previous":xyz.duplicate(),"events":0,"steps":0,"time":0.,"grasps":{}}
	_energy=null;_native_geometry={}
	return {"valid":true,"changed":true,"reason":""}
func set_motion(xyz:PackedFloat64Array,previous:PackedFloat64Array)->Dictionary:
	if _state.is_empty() or xyz.size()!=_state.xyz.size() or previous.size()!=xyz.size():return invalid("motion_size")
	for values in [xyz,previous]:
		for value in values:
			if not is_finite(value) or absf(value)>16.:return invalid("motion_coordinate")
	for node in range(_state.support.controls.size()):
		var original:int=_state.support.controls[node]
		if _state.fixed[node]==0:continue
		for j in range(3):
			if xyz[node*3+j]!=_state.original[original][j] or previous[node*3+j]!=_state.original[original][j]:return invalid("fixed_control")
	_state.xyz=xyz.duplicate();_state.previous=previous.duplicate()
	return {"valid":true,"changed":true,"reason":""}
func _prepare_energy()->bool:
	if _energy!=null:return true
	var prepared=Energy.new()
	if not prepared.configure(_state.original,_state.original_indices,_state.support):return false
	var nodes:=PackedInt32Array();var gradients:=PackedFloat64Array();var areas:=PackedFloat64Array()
	for cell in prepared._cells:
		for j in range(3):nodes.append(cell.nodes[j])
		gradients.append_array(cell.gx);gradients.append_array(cell.gy);areas.append(cell.area)
	_native_geometry={"nodes":nodes,"gradients":gradients,"areas":areas};_energy=prepared
	return true
func grasp(hand:int,vertex:int)->Dictionary:
	if _state.is_empty() or hand<0 or hand>1 or vertex<0 or vertex>=_state.rest.size():return invalid("grasp_input")
	if _state.grasps.has(hand):return {"valid":_state.grasps[hand].vertex==vertex,"changed":false,"reason":"grasp_occupied"}
	for held in _state.grasps.values():
		if held.vertex==vertex:return invalid("grasp_occupied")
	if _state.anchored[vertex]!=0 or _state.removed[vertex]!=0 or _state.support.point_nodes[vertex].is_empty():return invalid("grasp_unsupported")
	var face:=-1
	for i in range(_state.indices.size()/3):
		if vertex in [_state.indices[i*3],_state.indices[i*3+1],_state.indices[i*3+2]]:face=i;break
	if face<0:return invalid("grasp_unsupported")
	var xyz:=physical_positions();var target:=PackedFloat64Array([xyz[vertex*3],xyz[vertex*3+1],xyz[vertex*3+2]])
	_state.grasps[hand]={"vertex":vertex,"face":face,"target":target,"reaction":PackedFloat64Array([0.,0.,0.])}
	return {"valid":true,"changed":true,"reason":""}
func release_hand(hand:int)->void:
	if not _state.is_empty():_state.grasps.erase(hand)
func _attachments(targets:Dictionary)->Dictionary:
	for hand in targets:
		if not hand is int or not _state.grasps.has(hand):return invalid("grasp_targets")
	var hands:Array=_state.grasps.keys();hands.sort()
	var nodes:=PackedInt32Array();var weights:=PackedFloat64Array();var positions:=PackedFloat64Array()
	var next:Dictionary=_state.grasps.duplicate(true)
	for hand in hands:
		var held:Dictionary=_state.grasps[hand];var target=targets.get(hand,held.target)
		if not target is PackedFloat64Array or target.size()!=3:return invalid("grasp_target_shape")
		for value in target:
			if not is_finite(value) or absf(value)>16.:return invalid("grasp_target_coordinate")
		var local_nodes:PackedInt32Array=_state.support.point_nodes[held.vertex];var local_weights:PackedFloat64Array=_state.support.point_weights[held.vertex]
		if local_nodes.is_empty() or local_nodes.size()>3:return invalid("grasp_support")
		for j in range(3):
			nodes.append(local_nodes[j] if j<local_nodes.size() else local_nodes[0]);weights.append(local_weights[j] if j<local_weights.size() else 0.)
		positions.append_array(target);next[hand].target=target.duplicate()
	return {"valid":true,"reason":"","hands":hands,"nodes":nodes,"weights":weights,"targets":positions,"next":next}
func advance(dt:float,force:PackedFloat64Array,backend,mu:float,lambda:float,damping:float=1.,budget:int=100,targets:Dictionary={})->Dictionary:
	if _state.is_empty():return invalid("uninitialized")
	if not is_finite(dt) or dt<1e-6 or dt>.1 or not is_finite(damping) or damping<0. or damping>1. or budget<0 or budget>1000:return invalid("step_input")
	if not is_finite(mu) or mu<=0. or not is_finite(lambda) or lambda<0.:return invalid("step_material")
	if force.size()!=_state.xyz.size() or _state.support.controls.size()>4096:return invalid("step_shape")
	for value in force:
		if not is_finite(value):return invalid("step_force")
	var attachments:=_attachments(targets)
	if not attachments.valid:return attachments
	var gripping:bool=not attachments.hands.is_empty()
	if backend==null or not backend.has_method("solve_grasp_fem" if gripping else "solve_fem"):return invalid("native_fem_unavailable")
	if not _prepare_energy():return invalid("step_geometry")
	var current:PackedFloat64Array=_state.xyz
	var predicted:=current.duplicate();var inverse:=PackedFloat64Array();inverse.resize(_state.support.mass.size())
	for node in range(inverse.size()):
		var mass:float=_state.support.mass[node]
		if not is_finite(mass) or mass<=0. or 1./mass>1e12:return invalid("embedded_mass_resolution")
		if _state.fixed[node]!=0:continue
		inverse[node]=1./mass
		for axis in range(3):
			var k:=node*3+axis
			predicted[k]+=(current[k]-_state.previous[k])*damping+dt*dt*force[k]/mass
			if not is_finite(predicted[k]) or absf(predicted[k])>16.:return invalid("prediction_coordinate")
	var request:=_native_geometry.merged({"xyz":predicted,"inverse":inverse,"mu":mu,"lambda":lambda,"dt":dt,"budget":budget,"force_tolerance":FORCE_TOLERANCE},true)
	if gripping:request.merge({"grip_nodes":attachments.nodes,"grip_weights":attachments.weights,"targets":attachments.targets,"gap_tolerance":GAP_TOLERANCE},true)
	var result=backend.solve_grasp_fem(request) if gripping else backend.solve_fem(request)
	if not result is Dictionary or not result.get("status") is int or not result.get("xyz") is PackedFloat64Array or not result.get("stats") is PackedFloat64Array:return invalid("native_fem_shape")
	if result.status!=0:return {"valid":false,"changed":false,"reason":"native_fem_solve","status":result.status,"stats":result.stats}
	if result.xyz.size()!=current.size() or result.stats.size()!=(12 if gripping else 8):return invalid("native_fem_shape")
	if gripping and (not result.get("reaction") is PackedFloat64Array or result.reaction.size()!=attachments.targets.size()):return invalid("native_grasp_shape")
	for value in result.stats:
		if not is_finite(value):return invalid("native_fem_stats")
	if result.stats[1]<0. or result.stats[1]>FORCE_TOLERANCE:return invalid("native_fem_force")
	if gripping:
		if result.stats[8]<0. or result.stats[8]>GAP_TOLERANCE:return invalid("native_grasp_gap")
		for value in result.reaction:
			if not is_finite(value):return invalid("native_grasp_reaction")
	for node in range(inverse.size()):
		for axis in range(3):
			var k:=node*3+axis
			if not is_finite(result.xyz[k]) or absf(result.xyz[k])>16.:return invalid("native_fem_coordinate")
			if _state.fixed[node]!=0 and result.xyz[k]!=current[k]:return invalid("native_fem_fixed")
	# Check the original equation independently in GDScript before publication;
	# a success flag and a fabricated residual cannot advance accepted histories.
	var evaluated:Dictionary=_energy.evaluate(result.xyz,mu,lambda)
	if not evaluated.valid:return invalid("independent_fem_energy")
	var grip_force:=PackedFloat64Array();grip_force.resize(current.size());var gap:=0.
	if gripping:
		for grip in range(attachments.hands.size()):
			for axis in range(3):
				var point:=0.
				for j in range(3):
					var node:int=attachments.nodes[grip*3+j];var weight:float=attachments.weights[grip*3+j]
					point+=weight*result.xyz[node*3+axis];grip_force[node*3+axis]+=weight*result.reaction[grip*3+axis]
				gap=maxf(gap,absf(point-attachments.targets[grip*3+axis]))
		if gap>GAP_TOLERANCE:return {"valid":false,"changed":false,"reason":"independent_grasp_gap","gap":gap}
	var residual:=0.
	for node in range(inverse.size()):
		if inverse[node]==0.:continue
		for axis in range(3):
			var k:=node*3+axis
			var value:float=evaluated.gradient[k]+(result.xyz[k]-predicted[k])/(inverse[node]*dt*dt)+grip_force[k]
			if not is_finite(value):return invalid("independent_fem_force")
			residual=maxf(residual,absf(value))
	if residual>FORCE_TOLERANCE:return {"valid":false,"changed":false,"reason":"independent_fem_force","force_inf":residual}
	var accepted:=set_motion(result.xyz,current)
	if not accepted.valid:return accepted
	if gripping:
		for grip in range(attachments.hands.size()):attachments.next[attachments.hands[grip]].reaction=result.reaction.slice(grip*3,grip*3+3)
	_state.grasps=attachments.next
	_state.steps+=1;_state.time+=dt
	return {"valid":true,"changed":true,"reason":"","force_inf":residual,"gap":gap,"stats":result.stats}
static func _publish(state:Dictionary,xyz:PackedFloat64Array)->PackedFloat64Array:
	var result:=PackedFloat64Array();result.resize(state.rest.size()*3)
	for point in range(state.rest.size()):
		var nodes:PackedInt32Array=state.support.point_nodes[point];var weights:PackedFloat64Array=state.support.point_weights[point]
		for axis in range(3):
			if nodes.is_empty():result[point*3+axis]=state.fallback[point][axis]
			else:
				for j in range(nodes.size()):result[point*3+axis]+=weights[j]*xyz[nodes[j]*3+axis]
	return result
func physical_positions()->PackedFloat64Array:
	return PackedFloat64Array() if _state.is_empty() else _publish(_state,_state.xyz)
func positions()->PackedVector3Array:
	return Precision.publish(physical_positions())
func point_force(vertex:int,force:PackedFloat64Array)->Dictionary:
	if _state.is_empty() or vertex<0 or vertex>=_state.rest.size() or force.size()!=3:return invalid("point_force_shape")
	for value in force:
		if not is_finite(value):return invalid("point_force_value")
	var nodes:PackedInt32Array=_state.support.point_nodes[vertex];var weights:PackedFloat64Array=_state.support.point_weights[vertex]
	if nodes.is_empty():return invalid("unsupported_point")
	var distributed:=PackedFloat64Array();distributed.resize(_state.xyz.size())
	for j in range(nodes.size()):
		for axis in range(3):distributed[nodes[j]*3+axis]+=weights[j]*force[axis]
	return {"valid":true,"reason":"","force":distributed}
func incise_patches(patches:Array)->Dictionary:
	if _state.is_empty():return invalid("uninitialized")
	if patches.size()>256:return invalid("patch_budget")
	for patch in patches:
		if not patch is PackedVector3Array or patch.size()!=3:return invalid("patch_shape")
		for point in patch:
			if not point.is_finite() or point.length_squared()>256.:return invalid("patch_coordinate")
	var staged=get_script().new();staged._state=snapshot();staged._cutter=_cutter
	var changed:=false;var work:=0
	for patch in patches:
		var result:Dictionary=staged._incise_one(patch)
		work+=int(result.get("work",0))
		if work>Cutter.MAX_WORK:return invalid("patch_work_budget")
		if not result.valid:return invalid(result.reason)
		changed=changed or result.changed
	if changed:_state=staged._state;_energy=null;_native_geometry={}
	return {"valid":true,"changed":changed,"reason":"","work":work}
func _incise_one(patch:PackedVector3Array)->Dictionary:
	var fine:=positions()
	var cut:Dictionary=_cutter.slice_triangle(fine,_state.indices,patch[0],patch[1],patch[2])
	if not cut.valid or not cut.changed:return cut
	var prepared:=Refinement.prepare({"rest":_state.rest,"previous":Precision.publish(_publish(_state,_state.previous)),"anchored":_state.anchored,"removed":_state.removed,"outside":_state.outside,"indices":_state.indices,"face_areas":_state.areas},cut)
	if not prepared.valid:return invalid(prepared.reason)
	var ancestors:=PackedInt32Array()
	for source in cut.sources:ancestors.append(_state.ancestors[source])
	var support:=Support.build(_state.original,_state.original_indices,prepared.rest,cut.indices,ancestors,prepared.face_areas,_state.density)
	if not support.valid:return invalid(support.reason)
	for mass in support.mass:
		if 1./mass>1e12:return invalid("embedded_mass_resolution")
	var sources:=PackedInt32Array();sources.resize(support.controls.size());sources.fill(-1)
	for face in range(cut.sources.size()):
		for j in range(3):
			var node:int=support.elements[face*3+j];var old:int=_state.support.elements[cut.sources[face]*3+j]
			if support.controls[node]!=_state.support.controls[old] or (sources[node]>=0 and sources[node]!=old):return invalid("support_welding")
			sources[node]=old
	var xyz:=PackedFloat64Array();xyz.resize(support.controls.size()*3);var previous:=xyz.duplicate()
	for node in range(sources.size()):
		if sources[node]<0:return invalid("missing_control_source")
		for j in range(3):xyz[node*3+j]=_state.xyz[sources[node]*3+j];previous[node*3+j]=_state.previous[sources[node]*3+j]
	var next:=_state.duplicate(true)
	next.rest=prepared.rest;next.indices=cut.indices;next.ancestors=ancestors;next.areas=prepared.face_areas
	next.anchored=prepared.anchored;next.removed=prepared.removed;next.outside=prepared.outside
	next.fixed=_fixed_controls(support,prepared.anchored)
	next.fallback=cut.points;next.support=support;next.xyz=xyz;next.previous=previous;next.events+=1
	var published:=_publish(next,xyz);var error:=0.
	for point in range(cut.points.size()):
		for j in range(3):error=maxf(error,absf(published[point*3+j]-cut.points[point][j]))
	if error>Support.EMBEDDING_DISTANCE*4.:return invalid("embedding_publication")
	var grasps:Dictionary={}
	for hand in _state.grasps:
		var held:Dictionary=_state.grasps[hand];var candidates:Dictionary={}
		for face in range(cut.sources.size()):
			if cut.sources[face]!=held.face:continue
			for j in range(3):
				var vertex:int=cut.indices[face*3+j]
				if cut.bindings[vertex].ids==Vector3i(held.vertex,held.vertex,held.vertex) and not candidates.has(vertex):candidates[vertex]=face
		if candidates.size()!=1:continue
		var vertex:int=candidates.keys()[0];var remapped:Dictionary=held.duplicate(true)
		for axis in range(3):
			if absf(published[vertex*3+axis]-held.target[axis])>GAP_TOLERANCE:return invalid("grasp_remap_gap")
		remapped.vertex=vertex;remapped.face=candidates[vertex];grasps[hand]=remapped
	next.grasps=grasps
	_state=next
	return {"valid":true,"changed":true,"reason":"","work":cut.get("work",0),"publication_error":error}
