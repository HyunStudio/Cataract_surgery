extends RefCounted
## Static fine-face contact bridge checks. No integration, reaction solve or CCD.
const CHECK:=1e-11
static func invalid(reason:String)->Dictionary:
	return {"valid":false,"changed":false,"reason":reason}
static func face(state:Dictionary,index:int,segment:PackedFloat64Array,radius:float,backend)->Dictionary:
	if state.is_empty() or index<0 or index>=state.indices.size()/3:return invalid("contact_face")
	if segment.size()!=6 or not is_finite(radius) or radius<=0. or radius>.3:return invalid("contact_input")
	for value in segment:
		if not is_finite(value) or absf(value)>16.:return invalid("contact_coordinate")
	if backend==null or not backend.has_method("contact_fem"):return invalid("native_contact_unavailable")
	var nodes:PackedInt32Array=state.support.elements.slice(index*3,index*3+3)
	var shape:PackedFloat64Array=state.support.weights.slice(index*9,index*9+9)
	var controls:=PackedFloat64Array()
	for node in nodes:controls.append_array(state.xyz.slice(node*3,node*3+3))
	var answer=backend.contact_fem({"controls":controls,"weights":shape,"segment":segment,"radius":radius})
	if not answer is Dictionary or not answer.get("status") is int:return invalid("native_contact_shape")
	if answer.status!=0:return {"valid":false,"changed":false,"reason":"native_contact_query","status":answer.status}
	for key in ["values","gradient","hessian"]:
		if not answer.get(key) is PackedFloat64Array:return invalid("native_contact_shape")
		for value in answer[key]:
			if not is_finite(value):return invalid("native_contact_nonfinite")
	var values:PackedFloat64Array=answer.values;var gradient:PackedFloat64Array=answer.gradient;var hessian:PackedFloat64Array=answer.hessian
	if values.size()!=22 or gradient.size()!=9 or hessian.size()!=81:return invalid("native_contact_shape")
	if values[0]<=0. or values[20]<0. or values[20]>1. or values[21]<0. or values[21]>4. or floor(values[21])!=values[21]:return invalid("native_contact_witness")
	var fine:=PackedFloat64Array();fine.resize(9)
	for corner in range(3):
		var total:float=shape[corner*3]+shape[corner*3+1]+shape[corner*3+2]
		shape[corner*3+1]/=total;shape[corner*3+2]/=total;shape[corner*3]=1.-shape[corner*3+1]-shape[corner*3+2]
		for axis in range(3):fine[corner*3+axis]=controls[axis]+shape[corner*3+1]*(controls[3+axis]-controls[axis])+shape[corner*3+2]*(controls[6+axis]-controls[axis])
	var sum:=0.
	for corner in range(3):
		if values[8+corner]<0. or values[8+corner]>1.:return invalid("native_contact_barycentric")
		sum+=values[8+corner]
	if absf(sum-1.)>CHECK:return invalid("native_contact_barycentric")
	var material:=PackedFloat64Array([0.,0.,0.]);var delta:=PackedFloat64Array([0.,0.,0.]);var squared:=0.
	for axis in range(3):
		var axis_point:float=segment[axis]+values[20]*(segment[3+axis]-segment[axis])
		var surface:=0.
		for corner in range(3):surface+=values[8+corner]*fine[corner*3+axis]
		if absf(axis_point-values[2+axis])>CHECK or absf(surface-values[5+axis])>CHECK:return invalid("native_contact_witness")
		delta[axis]=surface-axis_point;squared+=delta[axis]*delta[axis]
	if absf(squared-values[0])>CHECK*maxf(1.,squared) or absf(sqrt(squared)-radius-values[1])>CHECK:return invalid("native_contact_gap")
	# Convex closest-point KKT inequalities independently check the static
	# witness. This numerical diagnostic is not a continuous-clearance proof.
	for corner in range(3):
		var derivative:=0.
		for axis in range(3):derivative+=delta[axis]*(fine[corner*3+axis]-values[5+axis])
		if derivative < -CHECK:return invalid("native_contact_minimum")
	for endpoint in range(2):
		var derivative:=0.
		for axis in range(3):derivative+=delta[axis]*(values[2+axis]-segment[endpoint*3+axis])
		if derivative < -CHECK:return invalid("native_contact_minimum")
	for node in range(3):
		for corner in range(3):material[node]+=values[8+corner]*shape[corner*3+node]
		for axis in range(3):
			if absf(gradient[node*3+axis]-2.*material[node]*delta[axis])>CHECK:return invalid("native_contact_gradient")
	for i in range(9):
		for j in range(9):
			if absf(hessian[i*9+j]-hessian[j*9+i])>CHECK*maxf(1.,absf(hessian[i*9+j])):return invalid("native_contact_hessian")
	return {"valid":true,"changed":false,"reason":"","face":index,"events":state.events,"steps":state.steps,"nodes":nodes,"material_weights":material,"values":values,"gradient":gradient,"hessian":hessian}
