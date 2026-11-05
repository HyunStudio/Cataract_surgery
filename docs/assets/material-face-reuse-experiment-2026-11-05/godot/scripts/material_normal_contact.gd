extends RefCounted
## Distributed unilateral normal candidates; never a full-geometry/CCD substitute.
const Surface=preload("res://scripts/material_surface_query.gd")
const GAP:=1e-9
const COMP:=1e-11
static func invalid(reason:String,work:int=0)->Dictionary:
	return {"valid":false,"changed":false,"reason":reason,"work_iterations":work}
static func _weights(state:Dictionary,face:int,bary:PackedFloat64Array)->PackedFloat64Array:
	var b:PackedFloat64Array=state.support.weights.slice(face*9,face*9+9)
	var weights:=PackedFloat64Array([0.,0.,0.]);var total:=bary[0]+bary[1]+bary[2]
	for j in range(3):
		var sum:float=b[j*3]+b[j*3+1]+b[j*3+2]
		for k in range(3):weights[k]+=(bary[j]/total)*(b[j*3+k]/sum)
	var sum:=weights[0]+weights[1]+weights[2]
	for j in range(3):weights[j]/=sum
	return weights
static func _add(state:Dictionary,face:int,bary:PackedFloat64Array,rows:Array,keys:Dictionary)->void:
	var nodes:PackedInt32Array=state.support.elements.slice(face*3,face*3+3)
	var weights:=_weights(state,face,bary)
	var mapping:Dictionary={}
	for j in range(3):
		if weights[j]>0.:mapping[nodes[j]]=weights[j]
	var ordered:Array=mapping.keys();ordered.sort();var canonical:Array=[]
	for node in ordered:canonical.append([node,mapping[node]])
	var key:=var_to_bytes(canonical)
	if keys.has(key):return
	keys[key]=true;rows.append({"face":face,"barycentric":bary.duplicate(),"nodes":nodes,"weights":weights})
static func _inspect(state:Dictionary,xyz:PackedFloat64Array,context:Dictionary,backend,rows:Array,keys:Dictionary,seed:bool)->Dictionary:
	var view:=state.duplicate(false);view.xyz=xyz;var violations:Array=[]
	if context.bodies==0:return {"valid":true,"violations":violations}
	if context.capsules.size()!=context.bodies*7:return invalid("material_normal_geometry")
	for face in range(state.indices.size()/3):
		var batch:=Surface.face_bodies(view,face,context.capsules,backend)
		if not batch.valid:return invalid("material_normal_geometry")
		for witness in batch.witnesses:
			if seed and witness.values[1]<.02:
				for j in range(3):
					var corner:=PackedFloat64Array([0.,0.,0.]);corner[j]=1.;_add(state,face,corner,rows,keys)
				_add(state,face,witness.barycentric,rows,keys)
			if witness.values[1] < -GAP:violations.append({"face":face,"barycentric":witness.barycentric})
	return {"valid":true,"violations":violations}
static func solve(state:Dictionary,request:Dictionary,context:Dictionary,backend)->Dictionary:
	if not backend.has_method("solve_material_points_fem") or not backend.has_method("material_witness_fem"):return invalid("material_normal_unavailable")
	var rows:Array=[];var keys:Dictionary={};var work:=0
	var initial:=_inspect(state,request.xyz,context,backend,rows,keys,true)
	if not initial.valid:return initial
	for exchange in range(16):
		if work>=request.budget:return invalid("material_normal_budget",work)
		if rows.size()>8192 or rows.size()*context.bodies>65536:return invalid("material_normal_pair_budget",work)
		var value:=request.duplicate(true);value.budget=request.budget-work
		var nodes:=PackedInt32Array();var weights:=PackedFloat64Array()
		for row in rows:
			nodes.append_array(row.nodes)
			for j in range(3):weights.append_array(row.weights)
		value.face_nodes=nodes;value.face_weights=weights
		var result=backend.solve_material_points_fem(value)
		if not result is Dictionary or not result.get("status") is int or not result.get("stats") is PackedFloat64Array or result.stats.size()!=16:return invalid("material_normal_shape",work)
		if result.has("normal_rows"):return invalid("material_normal_model",work)
		var spent:float=result.stats[2]
		if not is_finite(spent) or spent<0. or spent>value.budget or floor(spent)!=spent:return invalid("material_normal_work",work)
		work+=int(spent)
		if result.status!=0:return invalid("material_normal_solve",work)
		if not result.get("xyz") is PackedFloat64Array or result.xyz.size()!=request.xyz.size():return invalid("material_normal_shape",work)
		var checked:=_inspect(state,result.xyz,context,backend,rows,keys,false)
		if not checked.valid:return invalid(checked.reason,work)
		if checked.violations.is_empty():
			result.stats[2]=work
			return {"valid":true,"result":result,"rows":rows.duplicate(true),"work_iterations":work}
		var old_size:=rows.size()
		for violation in checked.violations:_add(state,violation.face,violation.barycentric,rows,keys)
		if rows.size()==old_size:return invalid("material_normal_stalled",work)
	return invalid("material_normal_exchange_budget",work)
static func force(state:Dictionary,xyz:PackedFloat64Array,dual:PackedFloat64Array,rows:Array,context:Dictionary)->Dictionary:
	if xyz.size()!=state.xyz.size():return invalid("material_normal_coordinate_shape")
	if dual.size()!=rows.size()*context.bodies:return invalid("material_normal_dual_shape")
	var distributed:=PackedFloat64Array();distributed.resize(xyz.size());var complementarity:=0.
	for i in range(rows.size()):
		if not rows[i] is Dictionary:return invalid("material_normal_row_shape")
		var row:Dictionary=rows[i]
		if not row.get("face") is int or row.face<0 or row.face>=state.indices.size()/3:return invalid("material_normal_provenance")
		if not row.get("barycentric") is PackedFloat64Array or row.barycentric.size()!=3:return invalid("material_normal_provenance")
		var total:=0.
		for value in row.barycentric:
			if not is_finite(value) or value<0. or value>1.:return invalid("material_normal_provenance")
			total+=value
		if absf(total-1.)>1e-11:return invalid("material_normal_provenance")
		if not row.get("nodes") is PackedInt32Array or row.nodes!=state.support.elements.slice(row.face*3,row.face*3+3):return invalid("material_normal_provenance")
		if not row.get("weights") is PackedFloat64Array or row.weights!=_weights(state,row.face,row.barycentric):return invalid("material_normal_provenance")
		var weights:PackedFloat64Array=row.weights;var nodes:PackedInt32Array=row.nodes
		var sum:=weights[0]+weights[1]+weights[2];var point:=PackedFloat64Array([0.,0.,0.])
		for j in range(3):
			for axis in range(3):point[axis]+=(weights[j]/sum)*xyz[nodes[j]*3+axis]
		for body in range(context.bodies):
			var u:float=dual[i*context.bodies+body]
			if not is_finite(u) or u<0.:return invalid("material_normal_dual")
			var off:=body*7;var radius:float=context.capsules[off+6];var direction:=PackedFloat64Array();var length:=0.;var projection:=0.
			for axis in range(3):
				direction.append(context.capsules[off+3+axis]-context.capsules[off+axis]);length+=direction[axis]*direction[axis]
				projection+=(point[axis]-context.capsules[off+axis])*direction[axis]
			var t:=clampf(projection/length,0.,1.) if length>0. else 0.;var delta:=PackedFloat64Array();var squared:=0.
			for axis in range(3):
				delta.append(point[axis]-context.capsules[off+axis]-t*direction[axis]);squared+=delta[axis]*delta[axis]
			if not is_finite(squared) or sqrt(squared)-radius < -GAP:return invalid("material_normal_gap")
			complementarity=maxf(complementarity,absf(u*(squared/(radius*radius)-1.)))
			if complementarity>COMP:return invalid("material_normal_complementarity")
			for j in range(3):
				for axis in range(3):distributed[nodes[j]*3+axis]-=u*2.*(weights[j]/sum)*delta[axis]/(radius*radius)
	return {"valid":true,"force":distributed,"complementarity":complementarity}
