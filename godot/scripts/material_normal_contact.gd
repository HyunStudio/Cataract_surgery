extends RefCounted
## Distributed unilateral normal candidates; never a full-geometry/CCD substitute.
const Pose=preload("res://scripts/recorded_body_pose.gd")
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
	var batched:bool=backend!=null and backend.has_method("material_witnesses_fem")
	var packet:Dictionary={}
	if batched:
		packet=Surface.batch(view,context.capsules,backend)
		if not packet.valid:return invalid("material_normal_batch_geometry")
	for face in range(state.indices.size()/3):
		for body in range(context.bodies):
			var gap:float;var bary:=PackedFloat64Array()
			if batched:
				var offset:int=(face*context.bodies+body)*13
				gap=packet.values[offset+1]
				if (seed and gap<.02) or gap < -GAP:bary=packet.values.slice(offset+8,offset+11)
			else:
				var off:=body*7;var witness:=Surface.face(view,face,context.capsules.slice(off,off+6),context.capsules[off+6],backend)
				if not witness.valid:return invalid("material_normal_geometry")
				gap=witness.values[1];bary=witness.barycentric
			if seed and gap<.02:
				for j in range(3):
					var corner:=PackedFloat64Array([0.,0.,0.]);corner[j]=1.;_add(state,face,corner,rows,keys)
				_add(state,face,bary,rows,keys)
			if gap < -GAP:violations.append({"face":face,"barycentric":bary})
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

static func _temporal_layers(state:Dictionary,xyz:PackedFloat64Array,context:Dictionary)->Dictionary:
	if xyz.size()!=state.xyz.size() or not context.get("previous") is PackedFloat64Array or context.previous.size()!=xyz.size():return invalid("material_normal_history")
	for value in xyz:
		if not is_finite(value) or absf(value)>16.:return invalid("material_normal_coordinate")
	for value in context.previous:
		if not is_finite(value) or absf(value)>16.:return invalid("material_normal_history")
	if not context.get("times") is PackedFloat64Array or context.times.is_empty() or context.times.size()>16:return invalid("material_normal_times")
	if not context.get("bodies") is int or context.bodies<0 or context.bodies>64 or not context.get("kinds") is PackedInt32Array or not context.get("packets") is PackedFloat64Array or context.kinds.size()!=context.bodies:return invalid("material_normal_pose")
	var last:=0.;var layers:Array=[]
	for time in context.times:
		if not is_finite(time) or time<=last or time>1.:return invalid("material_normal_times")
		last=time
		var pose:=Pose.sample(context.kinds,context.packets,time)
		if not pose.valid:return invalid("material_normal_pose")
		layers.append({"t":time,"bodies":context.bodies,"capsules":pose.capsules})
	if last!=1.:return invalid("material_normal_times")
	return {"valid":true,"layers":layers}
static func _temporal_positions(previous:PackedFloat64Array,xyz:PackedFloat64Array,time:float)->PackedFloat64Array:
	if time==1.:return xyz.duplicate()
	var posed:=xyz.duplicate()
	for k in range(posed.size()):posed[k]=previous[k]+time*(xyz[k]-previous[k])
	return posed
static func _inspect_trajectory(state:Dictionary,xyz:PackedFloat64Array,context:Dictionary,layers:Array,backend,rows:Array,keys:Dictionary,seed:bool)->Dictionary:
	if xyz.size()!=state.xyz.size():return invalid("material_normal_coordinate")
	for value in xyz:
		if not is_finite(value) or absf(value)>16.:return invalid("material_normal_coordinate")
	var violations:Array=[]
	for layer in layers:
		var posed:=_temporal_positions(context.previous,xyz,layer.t)
		var checked:=_inspect(state,posed,layer,backend,rows,keys,seed)
		if not checked.valid:return checked
		violations.append_array(checked.violations)
	return {"valid":true,"violations":violations}
static func solve_trajectory(state:Dictionary,request:Dictionary,context:Dictionary,backend,seed:Dictionary={})->Dictionary:
	if backend==null or not backend.has_method("solve_trajectory_material_points_fem") or not backend.has_method("material_witness_fem"):return invalid("material_normal_unavailable")
	var prepared:=_temporal_layers(state,request.xyz,context)
	if not prepared.valid:return prepared
	for key in ["times","previous","kinds","packets"]:
		if request.get(key)!=context.get(key):return invalid("material_normal_context")
	var rows:Array=[];var keys:Dictionary={};var work:=0;var guess:PackedFloat64Array=request.xyz.duplicate();var point_seed:Dictionary=seed.duplicate(true)
	if not point_seed.is_empty():
		if not backend.has_method("solve_seeded_trajectory_material_points_fem") or not point_seed.get("rows") is Array:return invalid("material_normal_seed")
		var checked_seed:=warm_start(state,point_seed,point_seed.rows,context)
		if not checked_seed.valid:return checked_seed
		guess=checked_seed.initial
		for row in point_seed.rows:_add(state,row.face,row.barycentric,rows,keys)
	var initial:=_inspect_trajectory(state,guess,context,prepared.layers,backend,rows,keys,false)
	if not initial.valid:return initial
	# Inspect the complete original surface at every layer. Acquire actual
	# violating witnesses; feasible near faces need no speculative constraints.
	for violation in initial.violations:_add(state,violation.face,violation.barycentric,rows,keys)
	for exchange in range(16):
		if work>=request.budget:return invalid("material_normal_budget",work)
		if rows.size()>8192 or rows.size()*context.bodies*prepared.layers.size()>65536:return invalid("material_normal_pair_budget",work)
		var value:=request.duplicate(true);value.budget=request.budget-work
		var nodes:=PackedInt32Array();var weights:=PackedFloat64Array()
		for row in rows:
			nodes.append_array(row.nodes)
			for j in range(3):weights.append_array(row.weights)
		value.face_nodes=nodes;value.face_weights=weights
		var solved_rows:Array=rows.duplicate(true)
		var result
		if not point_seed.is_empty():
			var warm:=warm_start(state,point_seed,rows,context)
			if not warm.valid:return invalid(warm.reason,work)
			for key in ["initial","multiplier_seed","penalty_seed"]:value[key]=warm[key]
			result=backend.solve_seeded_trajectory_material_points_fem(value)
		else:result=backend.solve_trajectory_material_points_fem(value)
		if not result is Dictionary or not result.get("status") is int or not result.get("stats") is PackedFloat64Array or result.stats.size()!=16:return invalid("material_normal_shape",work)
		if result.has("normal_rows"):return invalid("material_normal_model",work)
		var spent:float=result.stats[2]
		if not is_finite(spent) or spent<0. or spent>value.budget or floor(spent)!=spent:return invalid("material_normal_work",work)
		work+=int(spent)
		if result.status!=0:return invalid("material_normal_solve",work)
		if not result.get("xyz") is PackedFloat64Array or result.xyz.size()!=request.xyz.size() or not result.get("dual") is PackedFloat64Array or result.dual.size()!=rows.size()*context.bodies*prepared.layers.size():return invalid("material_normal_shape",work)
		var checked:=_inspect_trajectory(state,result.xyz,context,prepared.layers,backend,rows,keys,false)
		if not checked.valid:return invalid(checked.reason,work)
		if checked.violations.is_empty():
			result.stats[2]=work
			return {"valid":true,"result":result,"rows":rows.duplicate(true),"work_iterations":work}
		# A zero-row solve has no contact penalty (native stats[15]==0).
		# Acquire its new rows cold instead of inventing a contact warm seed.
		if backend.has_method("solve_seeded_trajectory_material_points_fem") and not solved_rows.is_empty():point_seed=candidate_seed(state,context,solved_rows,result)
		else:point_seed={}
		var old_size:=rows.size()
		for violation in checked.violations:_add(state,violation.face,violation.barycentric,rows,keys)
		if rows.size()==old_size:return invalid("material_normal_stalled",work)
	return invalid("material_normal_exchange_budget",work)
static func force_trajectory(state:Dictionary,xyz:PackedFloat64Array,dual:PackedFloat64Array,rows:Array,context:Dictionary)->Dictionary:
	var prepared:=_temporal_layers(state,xyz,context)
	if not prepared.valid:return prepared
	if dual.size()!=rows.size()*context.bodies*prepared.layers.size():return invalid("material_normal_dual_shape")
	if prepared.layers.size()==1:return force(state,xyz,dual,rows,prepared.layers[0])
	var distributed:=PackedFloat64Array();distributed.resize(xyz.size());var complementarity:=0.
	var width:int=rows.size()*context.bodies
	for layer in range(prepared.layers.size()):
		var posed:=_temporal_positions(context.previous,xyz,prepared.layers[layer].t)
		var checked:=force(state,posed,dual.slice(layer*width,(layer+1)*width),rows,prepared.layers[layer])
		if not checked.valid:return checked
		for k in range(distributed.size()):distributed[k]+=prepared.layers[layer].t*checked.force[k]
		complementarity=maxf(complementarity,checked.complementarity)
	return {"valid":true,"force":distributed,"complementarity":complementarity}

static func _point_key(row:Dictionary)->PackedByteArray:
	var mapping:Dictionary={}
	for j in range(3):
		if row.weights[j]>0.:mapping[row.nodes[j]]=row.weights[j]
	var ordered:Array=mapping.keys();ordered.sort();var canonical:Array=[]
	for node in ordered:canonical.append([node,mapping[node]])
	return var_to_bytes(canonical)
static func candidate_seed(state:Dictionary,context:Dictionary,rows:Array,result:Dictionary)->Dictionary:
	return {"model":"material_points","source_steps":state.steps,"source_events":state.events,"source_xyz":state.xyz.duplicate(),"kinds":context.kinds.duplicate(),"packets":context.packets.duplicate(),"rows":rows.duplicate(true),"xyz":result.xyz.duplicate(),"times":context.times.duplicate(),"dual":result.dual.duplicate(),"penalty":result.stats[15]}
static func warm_start(state:Dictionary,seed:Dictionary,rows:Array,context:Dictionary)->Dictionary:
	if seed.get("model")!="material_points" or not seed.get("source_steps") is int or not seed.get("source_events") is int:return invalid("material_normal_seed")
	if seed.source_steps!=state.get("steps") or seed.source_events!=state.get("events") or not seed.get("source_xyz") is PackedFloat64Array or seed.source_xyz!=state.xyz:return invalid("material_normal_seed")
	if seed.get("kinds")!=context.get("kinds") or seed.get("packets")!=context.get("packets") or context.get("previous")!=state.xyz:return invalid("material_normal_seed")
	if not seed.get("xyz") is PackedFloat64Array or not seed.get("times") is PackedFloat64Array or not seed.get("dual") is PackedFloat64Array or not seed.get("rows") is Array:return invalid("material_normal_seed")
	var prepared:=_temporal_layers(state,seed.xyz,context)
	if not prepared.valid:return invalid("material_normal_seed")
	var original_context:=context.duplicate(true);original_context.times=seed.times
	if not _temporal_layers(state,seed.xyz,original_context).valid:return invalid("material_normal_seed")
	var penalty=seed.get("penalty")
	if not (penalty is float or penalty is int) or not is_finite(penalty) or penalty<1. or penalty>1e12:return invalid("material_normal_seed")
	if rows.size()>8192 or seed.rows.size()>8192 or rows.size()*context.bodies*context.times.size()>65536 or seed.rows.size()*context.bodies*seed.times.size()>65536:return invalid("material_normal_seed")
	if seed.dual.size()!=seed.rows.size()*context.bodies*seed.times.size():return invalid("material_normal_seed")
	for value in seed.dual:
		if not is_finite(value) or value<0.:return invalid("material_normal_seed")
	var source_only:={"bodies":0,"capsules":PackedFloat64Array()}
	if not force(state,state.xyz,PackedFloat64Array(),rows,source_only).valid or not force(state,state.xyz,PackedFloat64Array(),seed.rows,source_only).valid:return invalid("material_normal_seed")
	var destination:Dictionary={};var source:Dictionary={}
	for i in range(rows.size()):
		var key:=_point_key(rows[i])
		if destination.has(key):return invalid("material_normal_seed")
		destination[key]=i
	for i in range(seed.rows.size()):
		var key:=_point_key(seed.rows[i])
		if source.has(key) or not destination.has(key):return invalid("material_normal_seed")
		source[key]=i
	var multipliers:=PackedFloat64Array();multipliers.resize(rows.size()*context.bodies*context.times.size())
	for old_layer in range(seed.times.size()):
		var next_layer:int=context.times.find(seed.times[old_layer])
		if next_layer<0:return invalid("material_normal_seed")
		for key in source:
			for body in range(context.bodies):
				var old_pair:int=(old_layer*seed.rows.size()+source[key])*context.bodies+body
				var next_pair:int=(next_layer*rows.size()+destination[key])*context.bodies+body
				multipliers[next_pair]=seed.dual[old_pair]
	# Start numerical conditioning when first entering the time-dependent
	# model. Subsequent temporal continuation keeps its converged penalty;
	# mapped reactions/positions never replace the final physical gates.
	var entering_trajectory:bool=seed.times.size()==1 and context.times.size()>1
	return {"valid":true,"initial":seed.xyz.duplicate(),"multiplier_seed":multipliers,"penalty_seed":1. if entering_trajectory else float(penalty)}
