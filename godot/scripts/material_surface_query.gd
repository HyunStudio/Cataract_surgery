extends RefCounted
## Static rounded-geometry proposal, including intersection/tie information.
## These numerical checks do not certify a unique grasp, an unrounded material
## contact, force equilibrium or continuous motion clearance.
const CHECK:=1e-11
static func invalid(reason:String)->Dictionary:
	return {"valid":false,"changed":false,"reason":reason}
static func _prepare_face(state:Dictionary,index:int)->Dictionary:
	if state.is_empty() or index<0 or index>=state.indices.size()/3:return invalid("material_witness_face")
	if not state.get("xyz") is PackedFloat64Array or not state.get("support") is Dictionary:return invalid("material_witness_material")
	if not state.support.get("elements") is PackedInt32Array or not state.support.get("weights") is PackedFloat64Array:return invalid("material_witness_material")
	if state.support.elements.size()<(index+1)*3 or state.support.weights.size()<(index+1)*9:return invalid("material_witness_material")
	var nodes:PackedInt32Array=state.support.elements.slice(index*3,index*3+3)
	var shape:PackedFloat64Array=state.support.weights.slice(index*9,index*9+9);var controls:=PackedFloat64Array()
	for node in nodes:
		if node<0 or node*3+3>state.xyz.size():return invalid("material_witness_material")
		controls.append_array(state.xyz.slice(node*3,node*3+3))
	for value in controls:
		if not is_finite(value) or absf(value)>16.:return invalid("material_witness_coordinate")
	for value in shape:
		if not is_finite(value) or value<0. or value>1.:return invalid("material_witness_material")
	var fine:=PackedFloat64Array();fine.resize(9)
	for j in range(3):
		var total:float=shape[j*3]+shape[j*3+1]+shape[j*3+2]
		if not is_finite(total) or absf(total-1.)>64.*2.220446049250313e-16:return invalid("material_witness_material")
		for axis in range(3):
			fine[j*3+axis]=controls[axis]+((controls[3+axis]-controls[axis])*shape[j*3+1]+(controls[6+axis]-controls[axis])*shape[j*3+2])/total
			if not is_finite(fine[j*3+axis]):return invalid("material_witness_coordinate")
	var e:=PackedFloat64Array();var f:=PackedFloat64Array()
	for axis in range(3):e.append(fine[3+axis]-fine[axis]);f.append(fine[6+axis]-fine[axis])
	var normal:=PackedFloat64Array([e[1]*f[2]-e[2]*f[1],e[2]*f[0]-e[0]*f[2],e[0]*f[1]-e[1]*f[0]]);var area_squared:=0.
	for value in normal:area_squared+=value*value
	if not is_finite(area_squared) or area_squared<=0.:return invalid("material_witness_resolution")
	return {"valid":true,"nodes":nodes,"controls":controls,"weights":shape,"fine":fine}
static func _validate(values:PackedFloat64Array,offset:int,status:int,fine:PackedFloat64Array,segment:PackedFloat64Array,radius:float)->String:
	for k in range(13):
		if not is_finite(values[offset+k]):return "native_material_witness_nonfinite"
	if values[offset+0]<0. or (status==1 and values[offset+0]!=0.) or (status!=1 and values[offset+0]<=0.) or values[offset+11]<0. or values[offset+11]>1. or values[offset+12]<0. or values[offset+12]>5. or floor(values[offset+12])!=values[offset+12]:return "native_material_witness_range"
	var sum:=0.
	for j in range(3):
		if values[offset+8+j]<0. or values[offset+8+j]>1.:return "native_material_witness_barycentric"
		sum+=values[offset+8+j]
	if absf(sum-1.)>CHECK:return "native_material_witness_barycentric"
	var delta:=PackedFloat64Array([0.,0.,0.]);var squared:=0.
	for axis in range(3):
		var axis_point:float=segment[axis]+values[offset+11]*(segment[3+axis]-segment[axis]);var surface:=0.
		for j in range(3):surface+=values[offset+8+j]*fine[j*3+axis]
		if absf(axis_point-values[offset+2+axis])>CHECK or absf(surface-values[offset+5+axis])>CHECK:return "native_material_witness_reconstruction"
		delta[axis]=surface-axis_point;squared+=delta[axis]*delta[axis]
	if absf(squared-values[offset+0])>CHECK*maxf(1.,squared) or absf(sqrt(squared)-radius-values[offset+1])>CHECK:return "native_material_witness_gap"
	for j in range(3):
		var derivative:=0.
		for axis in range(3):derivative+=delta[axis]*(fine[j*3+axis]-values[offset+5+axis])
		if derivative < -CHECK:return "native_material_witness_minimum"
	for endpoint in range(2):
		var derivative:=0.
		for axis in range(3):derivative+=delta[axis]*(values[offset+2+axis]-segment[endpoint*3+axis])
		if derivative < -CHECK:return "native_material_witness_minimum"
	return ""
static func face(state:Dictionary,index:int,segment:PackedFloat64Array,radius:float,backend)->Dictionary:
	if state.is_empty() or index<0 or index>=state.indices.size()/3:return invalid("material_witness_face")
	if segment.size()!=6 or not is_finite(radius) or radius<=0. or radius>.3:return invalid("material_witness_input")
	for value in segment:
		if not is_finite(value) or absf(value)>16.:return invalid("material_witness_coordinate")
	if backend==null or not backend.has_method("material_witness_fem"):return invalid("material_witness_unavailable")
	var geometry:=_prepare_face(state,index)
	if not geometry.valid:return geometry
	var nodes:PackedInt32Array=geometry.nodes;var controls:PackedFloat64Array=geometry.controls;var shape:PackedFloat64Array=geometry.weights
	var answer=backend.material_witness_fem({"controls":controls,"weights":shape,"segment":segment.duplicate(),"radius":radius})
	if not answer is Dictionary or not answer.get("status") is int:return invalid("native_material_witness_shape")
	if answer.status not in [0,1,3]:return {"valid":false,"changed":false,"reason":"native_material_witness","status":answer.status}
	if not answer.get("values") is PackedFloat64Array or answer.values.size()!=13:return invalid("native_material_witness_shape")
	var values:PackedFloat64Array=answer.values
	var reason:=_validate(values,0,answer.status,geometry.fine,segment,radius)
	if not reason.is_empty():return invalid(reason)
	var finite_axis:=segment[0]!=segment[3] or segment[1]!=segment[4] or segment[2]!=segment[5]
	var ambiguous:bool=answer.status==3 or (answer.status==1 and finite_axis)
	return {"valid":true,"changed":false,"reason":"","face":index,"events":state.events,"steps":state.steps,"distance_status":answer.status,"ambiguous":ambiguous,"values":values.duplicate(),"barycentric":values.slice(8,11),"point":values.slice(5,8),"nodes":nodes,"controls":controls,"weights":shape}
static func batch(state:Dictionary,capsules:PackedFloat64Array,backend)->Dictionary:
	if not state.get("indices") is PackedInt32Array or state.indices.size()%3!=0 or capsules.size()%7!=0:return invalid("material_witness_batch_shape")
	var faces:int=state.indices.size()/3;var bodies:int=capsules.size()/7
	if faces>8192 or bodies>64 or faces*bodies>65536:return invalid("material_witness_batch_budget")
	if faces==0 or bodies==0:return {"valid":true,"changed":false,"reason":"","values":PackedFloat64Array(),"statuses":PackedInt32Array()}
	if backend==null or not backend.has_method("material_witnesses_fem"):return invalid("material_witness_batch_unavailable")
	var segments:Array=[];var radii:=PackedFloat64Array()
	for body in range(bodies):
		var segment:=capsules.slice(body*7,body*7+6);var radius:float=capsules[body*7+6]
		if not is_finite(radius) or radius<=0. or radius>.3:return invalid("material_witness_input")
		for value in segment:
			if not is_finite(value) or absf(value)>16.:return invalid("material_witness_coordinate")
		segments.append(segment);radii.append(radius)
	var geometry:Array=[];var controls:=PackedFloat64Array();var weights:=PackedFloat64Array()
	for face_index in range(faces):
		var prepared:=_prepare_face(state,face_index)
		if not prepared.valid:return prepared
		geometry.append(prepared);controls.append_array(prepared.controls);weights.append_array(prepared.weights)
	# Independent fine geometry above is separate from these owned backend buffers.
	var answer=backend.material_witnesses_fem({"controls":controls,"weights":weights,"capsules":capsules.duplicate()})
	if not answer is Dictionary or not answer.get("status") is int:return invalid("native_material_witness_batch_shape")
	if answer.status!=0:return {"valid":false,"changed":false,"reason":"native_material_witness_batch","status":answer.status}
	if not answer.get("values") is PackedFloat64Array or not answer.get("statuses") is PackedInt32Array or answer.values.size()!=faces*bodies*13 or answer.statuses.size()!=faces*bodies:return invalid("native_material_witness_batch_shape")
	var values:PackedFloat64Array=answer.values;var statuses:PackedInt32Array=answer.statuses
	for face_index in range(faces):
		for body in range(bodies):
			var pair:int=face_index*bodies+body;var status:int=statuses[pair]
			if status not in [0,1,3]:return {"valid":false,"changed":false,"reason":"native_material_witness","status":status}
			var reason:=_validate(values,pair*13,status,geometry[face_index].fine,segments[body],radii[body])
			if not reason.is_empty():return invalid(reason)
	return {"valid":true,"changed":false,"reason":"","values":values.duplicate(),"statuses":statuses.duplicate()}
