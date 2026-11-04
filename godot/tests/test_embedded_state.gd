extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok:failures+=1;push_error(message)
func total(values:PackedFloat64Array)->float:
	var result:=0.
	for value in values:result+=value
	return result
func momentum(state:Dictionary,dt:float)->PackedFloat64Array:
	var result:=PackedFloat64Array([0.,0.,0.])
	for node in range(state.support.mass.size()):
		for j in range(3):result[j]+=state.support.mass[node]*(state.xyz[node*3+j]-state.previous[node*3+j])/dt
	return result
class FailLater extends RefCounted:
	var inner=load("res://scripts/membrane_cut.gd").new()
	var calls:=0
	func slice_triangle(points,indices,a,b,c)->Dictionary:
		calls+=1
		if calls==2:return {"valid":false,"changed":false,"reason":"injected_later_failure"}
		return inner.slice_triangle(points,indices,a,b,c)
func _initialize()->void:
	check(ResourceLoader.exists("res://scripts/embedded_membrane.gd"),"embedded mechanical state module exists")
	if failures:quit(1);return
	var model=load("res://scripts/embedded_membrane.gd").new()
	var base:=PackedVector3Array([Vector3(-1,0,-1),Vector3(1,0,-1),Vector3(1,0,1),Vector3(-1,0,1)])
	var ids:=PackedInt32Array([0,2,1,0,3,2]);var anchors:=PackedByteArray([0,0,0,0])
	check(model.initialize(base,ids,anchors,2.).valid,"embedded state starts from its own original material mesh")
	var initial:Dictionary=model.snapshot()
	var exported:Dictionary=model.snapshot();exported.xyz[0]+=.5;exported.support.cells[0].area=999.
	check(model.snapshot()==initial,"editing an exported view cannot mutate the accepted control state or material cells")
	check(not model.initialize(base,PackedInt32Array([0,2,9]),anchors,2.).valid and model.snapshot()==initial,"invalid embedded initialization leaves accepted state intact")
	var xyz:PackedFloat64Array=initial.xyz.duplicate();var previous:=xyz.duplicate();var dt:=1./60.
	for node in range(initial.support.controls.size()):
		xyz[node*3]*=1.03;xyz[node*3+2]*=.98
		for j in range(3):previous[node*3+j]=xyz[node*3+j]-(.001*(j+1)+.002*xyz[node*3])*dt
	check(model.set_motion(xyz,previous).valid,"controlled double state can be assigned without a hidden integration tick")
	var before:Dictionary=model.snapshot();var old_momentum:=momentum(before,dt)
	var energy=load("res://scripts/membrane_energy.gd").new();check(energy.configure(base,ids,before.support),"precut energy configures")
	var old_energy:float=energy.evaluate(before.xyz,2.,3.).energy
	var patch:=PackedVector3Array([Vector3(.25,-.2,-1.2),Vector3(.25,-.2,1.2),Vector3(.25,.4,0)])
	# A single triangular sweep crosses both original cells and shares their
	# finite interior endpoints. No pre-defined circle or tissue deletion.
	var cut:Dictionary=model.incise_patches([patch])
	check(cut.valid and cut.changed,"embedded state accepts a real retained geometric blade patch: "+cut.reason)
	if not cut.valid:
		DirAccess.make_dir_recursive_absolute("res://reports")
		var file:=FileAccess.open("res://reports/embedded-state-cut-failure.bin",FileAccess.WRITE)
		if file:file.store_var({"points":model.positions(),"indices":before.indices,"patch":patch})
		quit(1);return
	var after:Dictionary=model.snapshot();var new_momentum:=momentum(after,dt)
	check(after.events==1 and after.indices.size()>before.indices.size(),"accepted geometric incision changes topology once without integrating time")
	check(absf(total(after.support.mass)-total(before.support.mass))<1e-10,"new virtual-control copies preserve total actual material mass")
	for j in range(3):check(absf(new_momentum[j]-old_momentum[j])<1e-8,"cut-control copies preserve accepted material momentum without a velocity reset")
	check(energy.configure(base,ids,after.support),"postcut retained energy configures")
	check(absf(energy.evaluate(after.xyz,2.,3.).energy-old_energy)<1e-8,"cut-control copies do not inject elastic energy into unchanged material motion")
	var physical:PackedFloat64Array=model.physical_positions()
	check(physical.size()==after.rest.size()*3,"every retained fine point has a double geometric publication")
	var vertex:=4;var force:=PackedFloat64Array([.7,-.3,.2])
	var distributed:Dictionary=model.point_force(vertex,force)
	check(distributed.valid,"fine tool force maps through the transpose of the material embedding")
	var displacement:PackedFloat64Array=after.xyz.duplicate();var work:=0.
	for i in range(displacement.size()):
		var delta:=.0001*sin(i*.7);displacement[i]+=delta;work+=distributed.force[i]*delta
	check(model.set_motion(displacement,after.previous).valid,"virtual-work probe admits bounded control displacement")
	var shifted:PackedFloat64Array=model.physical_positions();var fine_work:=0.
	for j in range(3):fine_work+=force[j]*(shifted[vertex*3+j]-physical[vertex*3+j])
	check(absf(work-fine_work)<1e-12,"coarse force mapping exactly preserves virtual work at the contacted fine point")
	model.set_motion(after.xyz,after.previous)
	var saved:Dictionary=model.snapshot();var trace:=FailLater.new();model._cutter=trace
	var second:=PackedVector3Array([Vector3(-1.2,-.2,.1),Vector3(1.2,-.2,.1),Vector3(0,.4,.1)])
	var rejected:Dictionary=model.incise_patches([second,second])
	check(not rejected.valid and trace.calls==2 and model.snapshot()==saved,"a later finite patch failure cannot publish partial embedded topology or motion")
	var invalid:Dictionary=model.point_force(vertex,PackedFloat64Array([NAN,0.,0.]))
	check(not invalid.valid and model.snapshot()==saved,"invalid operator force leaves accepted material state unchanged")
	model._cutter=load("res://scripts/membrane_cut.gd").new()
	var distant:=patch.duplicate()
	for i in range(distant.size()):distant[i]+=Vector3(3,0,0)
	var outside:Dictionary=model.incise_patches([distant])
	check(outside.valid and not outside.changed and model.snapshot()==saved,"off-tissue blade sweep preserves topology motion and event count")
	var fixed=load("res://scripts/embedded_membrane.gd").new();fixed.initialize(base,ids,PackedByteArray([1,0,0,0]),1.)
	var fixed_state:Dictionary=fixed.snapshot();var moved:PackedFloat64Array=fixed_state.xyz.duplicate()
	moved[0]+=.01
	check(not fixed.set_motion(moved,fixed_state.previous).valid,"a fixed original material control cannot move when its fine topology changes")
	var corner=load("res://scripts/embedded_membrane.gd").new()
	var triangle:=PackedVector3Array([Vector3.ZERO,Vector3.RIGHT,Vector3.BACK])
	corner.initialize(triangle,PackedInt32Array([0,2,1]),PackedByteArray([1,0,0]),1.)
	var a:=Vector3(.6,-.1,-.1);var b:=Vector3(-.1,-.1,.6)
	var separated:Dictionary=corner.incise_patches([PackedVector3Array([a,b,b+Vector3.UP*.2]),PackedVector3Array([a,b+Vector3.UP*.2,a+Vector3.UP*.2])])
	check(separated.valid and separated.changed,"corner-anchor fixture makes a genuinely severed opposite fragment")
	if separated.valid:
		var split:Dictionary=corner.snapshot();var free:Dictionary={};var motion:PackedFloat64Array=split.xyz.duplicate()
		for face in range(split.ancestors.size()):
			var center:Vector3=(split.rest[split.indices[face*3]]+split.rest[split.indices[face*3+1]]+split.rest[split.indices[face*3+2]])/3.
			if center.x+center.z>.5:
				for j in range(3):free[split.support.elements[face*3+j]]=true
		for node in free:motion[node*3+1]+=.1
		check(corner.set_motion(motion,split.previous).valid,"a free fragment cannot inherit a world anchor from an original basis vertex outside its retained material")
	print("Embedded mechanical state: ",failures," failures");quit(1 if failures else 0)
