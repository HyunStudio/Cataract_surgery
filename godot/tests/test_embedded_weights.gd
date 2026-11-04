extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok:failures+=1;push_error(message)
class Capture extends RefCounted:
	var inner=load("res://scripts/membrane_cut.gd").new()
	var last:Dictionary={}
	func slice_triangle(points,indices,a,b,c)->Dictionary:
		last=inner.slice_triangle(points,indices,a,b,c)
		return last
func transferred(values:PackedFloat64Array,binding:Dictionary,axis:int)->float:
	var ids:Vector3i=binding.ids;var w:Vector3=binding.weights
	var sum:=float(w.x)+w.y+w.z
	var base:float=values[ids.x*3+axis]
	return base+((values[ids.y*3+axis]-base)*w.y+(values[ids.z*3+axis]-base)*w.z)/sum
func _initialize()->void:
	var support=load("res://scripts/membrane_support.gd")
	var triangle:=PackedVector3Array([Vector3.ZERO,Vector3.RIGHT,Vector3.BACK])
	var tri_ids:=PackedInt32Array([0,1,2])
	var exact:=PackedFloat64Array([.8,.123456789123,.076543210877,.3,.6,.1,.3,.1,.6])
	var fine:=PackedVector3Array()
	for corner in range(3):fine.append(Vector3(exact[corner*3+1],0.,exact[corner*3+2]))
	var material_area:=PackedFloat64Array([(fine[1]-fine[0]).cross(fine[2]-fine[0]).length()*.5])
	var precise:Dictionary=support.build(triangle,tri_ids,fine,tri_ids,PackedInt32Array([0]),material_area,1.,exact)
	check(precise.valid and precise.weights==exact,"supplied double material weights are retained without a float rest-geometry refit")
	var bad:=exact.duplicate();bad[0]=NAN
	var negative:=exact.duplicate();negative[0]=-.1
	var unnormalized:=exact.duplicate();unnormalized[0]=.9
	var off_material:=exact.duplicate();off_material[0]=.5;off_material[1]=.2;off_material[2]=.3
	for malformed in [PackedFloat64Array([1.]),bad,negative,unnormalized,off_material]:
		check(not support.build(triangle,tri_ids,fine,tri_ids,PackedInt32Array([0]),material_area,1.,malformed).valid,"malformed or geometrically inconsistent precise maps reject")
	var model=load("res://scripts/embedded_membrane.gd").new()
	var base:=PackedVector3Array([Vector3(-1,0,-1),Vector3(1,0,-1),Vector3(1,0,1),Vector3(-1,0,1)])
	check(model.initialize(base,PackedInt32Array([0,2,1,0,3,2]),PackedByteArray([0,0,0,0]),2.).valid,"precise transfer fixture initializes")
	var initial:Dictionary=model.snapshot();var xyz:PackedFloat64Array=initial.xyz.duplicate();var previous:=xyz.duplicate()
	for node in range(initial.support.controls.size()):
		xyz[node*3]*=1.03123456789;xyz[node*3+2]*=.98765432109
		xyz[node*3+1]=.013*sin(node*1.2)
		for axis in range(3):previous[node*3+axis]=xyz[node*3+axis]-.000123456789*(axis+1)
	check(model.set_motion(xyz,previous).valid,"nonfloat accepted controls and histories assigned")
	var capture:=Capture.new();model._cutter=capture
	var patches:=[PackedVector3Array([Vector3(.231,-.2,-1.2),Vector3(.231,-.2,1.2),Vector3(.231,.4,0)]),PackedVector3Array([Vector3(-1.2,-.2,.117),Vector3(1.2,-.2,.117),Vector3(0,.4,.117)])]
	for patch in patches:
		var before:Dictionary=model.snapshot();var old:PackedFloat64Array=model.physical_positions()
		var old_previous:PackedFloat64Array=model._publish(before,before.previous)
		var result:Dictionary=model.incise_patches([patch])
		check(result.valid and result.changed,"precise material transfer accepts actual finite cut: "+result.reason)
		if not result.valid:quit(1);return
		var after:Dictionary=model.snapshot();var current:PackedFloat64Array=model.physical_positions()
		var new_previous:PackedFloat64Array=model._publish(after,after.previous)
		var maximum:=0.;var history_error:=0.
		for point in range(capture.last.points.size()):
			for axis in range(3):
				maximum=maxf(maximum,absf(current[point*3+axis]-transferred(old,capture.last.bindings[point],axis)))
				history_error=maxf(history_error,absf(new_previous[point*3+axis]-transferred(old_previous,capture.last.bindings[point],axis)))
		print("Precise cut transfer: ",maximum," history: ",history_error)
		check(maximum<2e-14 and history_error<2e-14,"cut maps preserve accepted double material interpolation and history, without a float-coordinate refit")
	print("Embedded precise weights: ",failures," failures");quit(1 if failures else 0)
