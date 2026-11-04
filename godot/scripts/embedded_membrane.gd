extends RefCounted
## Experimental retained-cut state in an original-material mechanical basis.
## Starts from its own rest state; never projects an accepted legacy simulation.
## Time integration/contact and partial-crack enrichment are separate work.
const Support=preload("res://scripts/membrane_support.gd")
const Refinement=preload("res://scripts/membrane_refinement.gd")
const Precision=preload("res://scripts/membrane_precision.gd")
const Cutter=preload("res://scripts/membrane_cut.gd")
var _cutter=Cutter.new()
var _state:Dictionary={}
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
	_state={"original":original.duplicate(),"original_indices":indices.duplicate(),"original_anchors":anchors.duplicate(),"rest":original.duplicate(),"indices":indices.duplicate(),"ancestors":ancestors,"areas":areas,"anchored":anchors.duplicate(),"fixed":_fixed_controls(support,anchors),"removed":flags,"outside":flags.duplicate(),"fallback":original.duplicate(),"support":support,"density":density,"xyz":xyz,"previous":xyz.duplicate(),"events":0}
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
	if changed:_state=staged._state
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
	_state=next
	return {"valid":true,"changed":true,"reason":"","work":cut.get("work",0),"publication_error":error}
