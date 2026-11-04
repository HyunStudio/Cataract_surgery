extends RefCounted
## Material identity for a joint point. Acquisition by finite jaws and a
## calibrated pressure/friction law are separate, still-required mechanisms.
const Exact=preload("res://scripts/exact_material.gd")
static func invalid(reason:String)->Dictionary:
	return {"valid":false,"changed":false,"reason":"material_attachment_"+reason}
static func position(state:Dictionary,nodes:PackedInt32Array,weights:PackedFloat64Array)->PackedFloat64Array:
	var total:float=weights[0]+weights[1]+weights[2];var point:=PackedFloat64Array()
	for axis in range(3):
		var base:float=state.xyz[nodes[0]*3+axis]
		point.append(base+((state.xyz[nodes[1]*3+axis]-base)*weights[1]+(state.xyz[nodes[2]*3+axis]-base)*weights[2])/total)
	return point
static func constraint(state:Dictionary,held:Dictionary)->Dictionary:
	if not held.get("nodes") is PackedInt32Array or not held.get("weights") is PackedFloat64Array:return invalid("shape")
	if held.nodes.size()!=3 or held.weights.size()!=3:return invalid("shape")
	var total:=0.
	for j in range(3):
		if held.nodes[j]<0 or held.nodes[j]>=state.xyz.size()/3 or not is_finite(held.weights[j]) or held.weights[j]<0.:return invalid("row")
		total+=held.weights[j]
	if not is_finite(total) or total<=0.:return invalid("row")
	var weights:PackedFloat64Array=held.weights.duplicate()
	for j in range(3):weights[j]/=total
	return {"valid":true,"nodes":held.nodes.duplicate(),"weights":weights}
static func _identity(nodes:PackedInt32Array,weights:PackedFloat64Array)->Dictionary:
	var row:Dictionary={};var total:=0.
	for weight in weights:total+=weight
	for j in range(nodes.size()):
		if weights[j]>0.:row[nodes[j]]=weights[j]/total
	return row
static func same_vertex(state:Dictionary,held:Dictionary,vertex:int)->bool:
	return _identity(held.nodes,held.weights)==_identity(state.support.point_nodes[vertex],state.support.point_weights[vertex])
static func create(state:Dictionary,hand:int,face:int,barycentric:PackedFloat64Array)->Dictionary:
	if hand not in [0,1] or state.is_empty() or face<0 or face>=state.indices.size()/3 or barycentric.size()!=3:return invalid("input")
	var sum:=0.
	for value in barycentric:
		if not is_finite(value) or value<0. or value>1.:return invalid("barycentric")
		sum+=value
	if not is_finite(sum) or absf(sum-1.)>1e-12:return invalid("barycentric")
	for j in range(3):
		if barycentric[j]>0. and state.removed[state.indices[face*3+j]]!=0:return invalid("unsupported")
	var nodes:PackedInt32Array=state.support.elements.slice(face*3,face*3+3)
	var weights:=PackedFloat64Array([0.,0.,0.]);var free:=false
	for j in range(3):
		for corner in range(3):weights[j]+=(barycentric[corner]/sum)*state.support.weights[face*9+corner*3+j]
		if not is_finite(weights[j]) or weights[j]<0.:return invalid("row")
		free=free or (weights[j]>0. and state.fixed[nodes[j]]==0)
	if not free:return invalid("unsupported")
	var total:float=weights[0]+weights[1]+weights[2]
	if not is_finite(total) or total<=0.:return invalid("row")
	var identity:=_identity(nodes,weights)
	for other in state.grasps:
		var held:Dictionary=state.grasps[other];var other_identity:Dictionary
		if held.get("kind","")=="material":other_identity=_identity(held.nodes,held.weights)
		else:other_identity=_identity(state.support.point_nodes[held.vertex],state.support.point_weights[held.vertex])
		if other==hand:
			if held.get("kind","")=="material" and identity==other_identity:return {"valid":true,"changed":false,"reason":"","held":held.duplicate(true)}
			return invalid("occupied")
		if identity==other_identity:return invalid("occupied")
	var target:=position(state,nodes,weights)
	for value in target:
		if not is_finite(value) or absf(value)>16.:return invalid("position")
	return {"valid":true,"changed":true,"reason":"","held":{"kind":"material","face":face,"nodes":nodes,"weights":weights,"target":target,"reaction":PackedFloat64Array([0.,0.,0.])}}
static func _feature(ids:PackedInt32Array,signs:PackedInt32Array,face:int)->Dictionary:
	for j in range(3):
		if signs[j]==0 and signs[(j+2)%3]==0:return {"vertex":ids[j]}
	for j in range(3):
		if signs[j]==0:return {"edge":Vector2i(mini(ids[j],ids[(j+1)%3]),maxi(ids[j],ids[(j+1)%3]))}
	return {"face":face}
static func remap_cut(before:Dictionary,cut:Dictionary,after:Dictionary,held:Dictionary)->Dictionary:
	var checked:=constraint(before,held)
	if not checked.valid:return checked
	var face:int=held.face
	if face<0 or face>=before.indices.size()/3 or held.nodes!=before.support.elements.slice(face*3,face*3+3):return invalid("cut_source")
	if not Exact.eligible(held.weights):return invalid("cut_precision")
	var chosen:Dictionary={};var identity:Dictionary={};var feature:Dictionary={};var ambiguous:=false
	for child in range(cut.sources.size()):
		if cut.sources[child]!=face:continue
		var rows:Array[PackedFloat64Array]=[]
		for j in range(3):rows.append(after.support.weights.slice(child*9+j*3,child*9+j*3+3))
		var orientation:Dictionary=Exact.orientation(rows[0],rows[1],rows[2])
		if not orientation.valid or orientation.sign<=0:return invalid("cut_precision")
		var signs:=PackedInt32Array();var inside:=true
		for j in range(3):
			var edge:Dictionary=Exact.orientation(rows[j],rows[(j+1)%3],held.weights)
			if not edge.valid:return invalid("cut_precision")
			signs.append(edge.sign);inside=inside and edge.sign>=0
		if not inside:continue
		var nodes:PackedInt32Array=after.support.elements.slice(child*3,child*3+3)
		var next_identity:=_identity(nodes,held.weights)
		var next_feature:=_feature(after.indices.slice(child*3,child*3+3),signs,child)
		if not chosen.is_empty():
			# Ordinary child tessellation shares the exact mesh feature.
			# New crack banks must never collapse to one control-row identity.
			ambiguous=ambiguous or identity!=next_identity or feature!=next_feature
			continue
		chosen=held.duplicate(true);chosen.face=child;chosen.nodes=nodes;identity=next_identity;feature=next_feature
	if chosen.is_empty():return invalid("cut_membership")
	if ambiguous:return {"valid":true,"retained":false}
	var point:=position(after,chosen.nodes,chosen.weights)
	for axis in range(3):
		if not is_finite(point[axis]) or absf(point[axis]-held.target[axis])>1e-9:return invalid("cut_gap")
	return {"valid":true,"retained":true,"held":chosen}
