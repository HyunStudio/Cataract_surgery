extends RefCounted
## Static rounded-geometry proposal, including intersection/tie information.
## These numerical checks do not certify a unique grasp, an unrounded material
## contact, force equilibrium or continuous motion clearance.
const CHECK:=1e-11
static func invalid(reason:String)->Dictionary:
	return {"valid":false,"changed":false,"reason":reason}
static func _input(segment:PackedFloat64Array,radius:float,backend)->Dictionary:
	if segment.size()!=6 or not is_finite(radius) or radius<=0. or radius>.3:return invalid("material_witness_input")
	for value in segment:
		if not is_finite(value) or absf(value)>16.:return invalid("material_witness_coordinate")
	if backend==null or not backend.has_method("material_witness_fem"):return invalid("material_witness_unavailable")
	return {"valid":true}
static func _prepare(state:Dictionary,index:int)->Dictionary:
	if state.is_empty() or index<0 or index>=state.indices.size()/3:return invalid("material_witness_face")
	var nodes:PackedInt32Array=state.support.elements.slice(index*3,index*3+3)
	var shape:PackedFloat64Array=state.support.weights.slice(index*9,index*9+9);var controls:=PackedFloat64Array()
	for node in nodes:controls.append_array(state.xyz.slice(node*3,node*3+3))
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
	return {"valid":true,"face":index,"events":state.events,"steps":state.steps,"nodes":nodes,"shape":shape,"controls":controls,"fine":fine}
static func _query(prepared:Dictionary,segment:PackedFloat64Array,radius:float,backend)->Dictionary:
	var nodes:PackedInt32Array=prepared.nodes;var shape:PackedFloat64Array=prepared.shape
	var controls:PackedFloat64Array=prepared.controls;var fine:PackedFloat64Array=prepared.fine
	var answer=backend.material_witness_fem({"controls":controls.duplicate(),"weights":shape.duplicate(),"segment":segment.duplicate(),"radius":radius})
	if not answer is Dictionary or not answer.get("status") is int:return invalid("native_material_witness_shape")
	if answer.status not in [0,1,3]:return {"valid":false,"changed":false,"reason":"native_material_witness","status":answer.status}
	if not answer.get("values") is PackedFloat64Array or answer.values.size()!=13:return invalid("native_material_witness_shape")
	var values:PackedFloat64Array=answer.values
	for value in values:
		if not is_finite(value):return invalid("native_material_witness_nonfinite")
	if values[0]<0. or (answer.status==1 and values[0]!=0.) or (answer.status!=1 and values[0]<=0.) or values[11]<0. or values[11]>1. or values[12]<0. or values[12]>5. or floor(values[12])!=values[12]:return invalid("native_material_witness_range")
	var sum:=0.
	for j in range(3):
		if values[8+j]<0. or values[8+j]>1.:return invalid("native_material_witness_barycentric")
		sum+=values[8+j]
	if absf(sum-1.)>CHECK:return invalid("native_material_witness_barycentric")
	var delta:=PackedFloat64Array([0.,0.,0.]);var squared:=0.
	for axis in range(3):
		var axis_point:float=segment[axis]+values[11]*(segment[3+axis]-segment[axis]);var surface:=0.
		for j in range(3):surface+=values[8+j]*fine[j*3+axis]
		if absf(axis_point-values[2+axis])>CHECK or absf(surface-values[5+axis])>CHECK:return invalid("native_material_witness_reconstruction")
		delta[axis]=surface-axis_point;squared+=delta[axis]*delta[axis]
	if absf(squared-values[0])>CHECK*maxf(1.,squared) or absf(sqrt(squared)-radius-values[1])>CHECK:return invalid("native_material_witness_gap")
	for j in range(3):
		var derivative:=0.
		for axis in range(3):derivative+=delta[axis]*(fine[j*3+axis]-values[5+axis])
		if derivative < -CHECK:return invalid("native_material_witness_minimum")
	for endpoint in range(2):
		var derivative:=0.
		for axis in range(3):derivative+=delta[axis]*(values[2+axis]-segment[endpoint*3+axis])
		if derivative < -CHECK:return invalid("native_material_witness_minimum")
	# A finite intersecting axis can overlap a whole in-plane interval. Until
	# a caller establishes uniqueness, conservatively flag every finite-axis
	# intersection; only a zero-length point probe avoids that ambiguity.
	var finite_axis:=segment[0]!=segment[3] or segment[1]!=segment[4] or segment[2]!=segment[5]
	var ambiguous:bool=answer.status==3 or (answer.status==1 and finite_axis)
	return {"valid":true,"changed":false,"reason":"","face":prepared.face,"events":prepared.events,"steps":prepared.steps,"distance_status":answer.status,"ambiguous":ambiguous,"values":values.duplicate(),"barycentric":values.slice(8,11),"point":values.slice(5,8),"nodes":nodes.duplicate(),"controls":controls.duplicate(),"weights":shape.duplicate()}
static func face(state:Dictionary,index:int,segment:PackedFloat64Array,radius:float,backend)->Dictionary:
	if state.is_empty() or index<0 or index>=state.indices.size()/3:return invalid("material_witness_face")
	var input:=_input(segment,radius,backend)
	if not input.valid:return input
	var prepared:=_prepare(state,index)
	if not prepared.valid:return prepared
	return _query(prepared,segment,radius,backend)
static func face_bodies(state:Dictionary,index:int,capsules:PackedFloat64Array,backend)->Dictionary:
	if capsules.is_empty() or capsules.size()%7!=0 or capsules.size()/7>64:return invalid("material_witness_input")
	for off in range(0,capsules.size(),7):
		var input:=_input(capsules.slice(off,off+6),capsules[off+6],backend)
		if not input.valid:return input
	var prepared:=_prepare(state,index)
	if not prepared.valid:return prepared
	var witnesses:Array=[]
	for off in range(0,capsules.size(),7):
		var answer:=_query(prepared,capsules.slice(off,off+6),capsules[off+6],backend)
		if not answer.valid:return answer
		witnesses.append(answer)
	return {"valid":true,"witnesses":witnesses}
