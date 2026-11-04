extends RefCounted
const Precision=preload("res://scripts/membrane_precision.gd")
## Transactional material-state transfer for a verified geometric incision.
## Lumped areal mass and rest/history bindings are engineering approximations.
static func invalid(reason:String)->Dictionary:
	return {"valid":false,"reason":reason}
static func blend(values:PackedVector3Array,binding:Dictionary)->Vector3:
	var ids:Vector3i=binding.ids;var w:=Precision.binding_weights(binding)
	var total:float=w[0]+w[1]+w[2]
	if not is_finite(total) or total<=0.:return Vector3(INF,INF,INF)
	var result:=Vector3.ZERO
	for axis in range(3):
		var base:float=values[ids.x][axis]
		result[axis]=base+((float(values[ids.y][axis])-base)*w[1]+(float(values[ids.z][axis])-base)*w[2])/total
	return result
static func flag(values:PackedByteArray,binding:Dictionary)->int:
	var weights:=Precision.binding_weights(binding)
	for j in range(3):
		if weights[j]>0. and values[binding.ids[j]]==0: return 0
	return 1
## Geometry/material preparation has no mechanical support policy. Both the
## existing fine-node backend and an embedded backend can consume identical
## retained rest areas and histories without bypassing their own mass guards.
static func prepare(state:Dictionary,cut:Dictionary)->Dictionary:
	if not cut.get("valid",false):return invalid("transfer_input")
	var size:int=cut.points.size(); var faces:int=cut.indices.size()/3
	var rest:=PackedVector3Array(); var previous:=PackedVector3Array()
	var anchored:=PackedByteArray(); var removed:=PackedByteArray(); var outside:=PackedByteArray()
	for binding in cut.bindings:
		var r:=blend(state.rest,binding); var p:=blend(state.previous,binding)
		if not r.is_finite() or not p.is_finite() or r.length_squared()>256. or p.length_squared()>256.: return invalid("transfer_state")
		rest.append(r); previous.append(p)
		anchored.append(flag(state.anchored,binding)); removed.append(flag(state.removed,binding)); outside.append(flag(state.outside,binding))
	if rest.size()!=size: return invalid("binding_count")
	var raw:=PackedFloat64Array(); var totals:=PackedFloat64Array(); totals.resize(state.face_areas.size())
	var material:PackedFloat64Array=cut.get("fractions",PackedFloat64Array())
	if not material.is_empty() and material.size()!=faces:return invalid("material_fraction_count")
	for i in range(faces):
		var a:int=cut.indices[i*3]; var b:int=cut.indices[i*3+1]; var c:int=cut.indices[i*3+2]; var parent:int=cut.sources[i]
		var normal:=(rest[b]-rest[a]).cross(rest[c]-rest[a]); var area:=normal.length()*.5
		var u:int=state.indices[parent*3]; var v:int=state.indices[parent*3+1]; var w:int=state.indices[parent*3+2]
		var original:Vector3=(state.rest[v]-state.rest[u]).cross(state.rest[w]-state.rest[u])
		if not is_finite(area) or area<=1e-16 or normal.dot(original)<=0.: return invalid("rest_subdivision")
		for edge in [[a,b],[b,c],[c,a]]:
			if rest[edge[0]].distance_to(rest[edge[1]])<=1e-8: return invalid("rest_edge_resolution")
		var portion:float=area if material.is_empty() else material[i]
		if not is_finite(portion) or portion<=0.:return invalid("material_fraction")
		raw.append(portion); totals[parent]+=portion
	if not material.is_empty():
		for portion in totals:
			if absf(portion-1.)>1e-10:return invalid("material_partition")
	var areas:=PackedFloat64Array(); var lumped:=PackedFloat64Array(); lumped.resize(size)
	for i in range(faces):
		var parent:int=cut.sources[i]
		if totals[parent]<=0.: return invalid("material_area")
		# Geometry fractions distribute the existing material area, rather
		# than assigning new material or accumulating remeshing area drift.
		var area:float=state.face_areas[parent]*(raw[i]/totals[parent]); areas.append(area)
		for j in range(3): lumped[cut.indices[i*3+j]]+=area/3.
	return {"valid":true,"reason":"","rest":rest,"previous":previous,"anchored":anchored,"removed":removed,"outside":outside,"face_areas":areas,"lumped":lumped}

static func transfer(state:Dictionary,cut:Dictionary,density:float)->Dictionary:
	if not is_finite(density) or density<.01 or density>100.:return invalid("transfer_input")
	var prepared:=prepare(state,cut)
	if not prepared.valid:return prepared
	var size:int=cut.points.size();var faces:int=cut.indices.size()/3
	var lumped:PackedFloat64Array=prepared.lumped
	var anchored:PackedByteArray=prepared.anchored;var removed:PackedByteArray=prepared.removed
	var inverse:=PackedFloat64Array(); inverse.resize(size)
	for i in range(size):
		if lumped[i]<=0.: continue
		var value:float=1./(density*lumped[i])
		if not is_finite(value) or value>1e12: return invalid("mass_resolution")
		if anchored[i]==0 and removed[i]==0: inverse[i]=value
	var grasps:={}; var grasp_faces:={}
	for hand in state.grasps:
		if not state.grasp_faces.has(hand): continue
		var original:int=state.grasps[hand]; var parent:int=state.grasp_faces[hand]; var candidates:={}
		for i in range(faces):
			if cut.sources[i]!=parent: continue
			for j in range(3):
				var v:int=cut.indices[i*3+j]; var binding:Dictionary=cut.bindings[v]
				if binding.ids==Vector3i(original,original,original): candidates[v]=i
		# Cutting through the attachment face can create two equally valid
		# banks. Release that severed attachment instead of picking a bank.
		if candidates.size()!=1: continue
		var v:int=candidates.keys()[0]
		grasps[hand]=v; grasp_faces[hand]=candidates[v]; inverse[v]=0.
	prepared["inverse"]=inverse;prepared["grasps"]=grasps;prepared["grasp_faces"]=grasp_faces
	return prepared
