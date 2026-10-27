extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok: failures+=1; push_error(message)
func _initialize()->void:
	var solver=load("res://scripts/membrane_contact.gd").new()
	var original:=PackedVector3Array([Vector3(-1,0,-1),Vector3(1,0,-1),Vector3(0,0,1)])
	var tilted:=PackedVector3Array()
	var rotation:=Basis(Vector3.BACK,PI/4.)
	for p in original: tilted.append(rotation*p)
	var body:Array=[{"a":Vector3(0,.05,0),"b":Vector3(0,.05,0),"previous_a":Vector3(0,.05,0),"previous_b":Vector3(0,.05,0),"radius":.08}]
	var out:Dictionary=solver.project(tilted,PackedInt32Array([0,1,2]),PackedFloat64Array([1,1,1]),body,original,.2)
	check(out.valid and out.contacts>0,"tilted current face contacts the actual spherical tip")
	# The analytical current plane normal, oriented onto the original tissue side.
	var separating:=rotation*Vector3.DOWN
	for i in range(3):
		var correction:Vector3=out.positions[i]-tilted[i]
		check(correction.length()>.001 and correction.normalized().dot(separating)>.9999,"deformed face follows its current separating normal while retaining the original side")
	body[0].a=Vector3(0,-.02,0); body[0].b=body[0].a
	out=solver.project(original,PackedInt32Array([0,1,2]),PackedFloat64Array([1,1,1]),body,original,.2)
	check(out.valid and out.contacts>0,"crossing tool still overlaps the membrane at the current pose")
	for i in range(3): check(out.positions[i].y<-.01,"current nearest normal cannot flip a crossing tool onto the opposite material side")
	var endpoint_face:=PackedVector3Array([Vector3(-.01,0,0),Vector3(-.1,0,-.1),Vector3(-.1,0,.1)])
	body=[{"a":Vector3(0,-.02,0),"b":Vector3(1,-.02,0),"previous_a":Vector3(-.01,.05,0),"previous_b":Vector3(1,.05,0),"radius":.08}]
	out=solver.project(endpoint_face,PackedInt32Array([0,1,2]),PackedFloat64Array([1,1,1]),body,endpoint_face,.2)
	var nearest:=Geometry3D.get_closest_point_to_segment(out.positions[0],body[0].a,body[0].b)
	check(out.valid and out.positions[0].distance_to(nearest)>=.08-1e-7,"crossing an endpoint cannot push the selected witness into the finite shaft while reporting zero residual")
	check(solver.has_method("begin_substep"),"native coupling can hold a consistent contact linearization within a physical substep")
	if not solver.has_method("begin_substep"): print("Membrane normal: ",failures," failures"); quit(1); return
	body=[{"a":Vector3(0,.05,0),"b":Vector3(0,.05,0),"previous_a":Vector3(0,.05,0),"previous_b":Vector3(0,.05,0),"radius":.08}]
	solver.begin_substep(true)
	solver.project(tilted,PackedInt32Array([0,1,2]),PackedFloat64Array([1,1,1]),body,original,.2)
	var second:=PackedVector3Array(); var second_rotation:=Basis(Vector3.BACK,PI/6.)
	for p in original: second.append(second_rotation*p)
	out=solver.project(second,PackedInt32Array([0,1,2]),PackedFloat64Array([1,1,1]),body,original,.2)
	for i in range(3): check((out.positions[i]-second[i]).normalized().dot(Vector3.DOWN)>.9999,"native coupling retains its previous-configuration contact linearization within a substep")
	solver.begin_substep(false)
	out=solver.project(second,PackedInt32Array([0,1,2]),PackedFloat64Array([1,1,1]),body,original,.2)
	for i in range(3): check((out.positions[i]-second[i]).normalized().dot(second_rotation*Vector3.DOWN)>.9999,"a new substep rebuilds contact directions from its actual current geometry")
	solver.begin_substep(true)
	out=solver.project(second,PackedInt32Array([0,1,2]),PackedFloat64Array([1,1,1]),body,second,.2)
	for i in range(3): check((out.positions[i]-second[i]).normalized().dot(second_rotation*Vector3.DOWN)>.9999,"native contact linearization advances with the next physical substep's material geometry")
	print("Membrane normal: ",failures," failures"); quit(1 if failures else 0)
