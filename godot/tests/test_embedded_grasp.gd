extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok:failures+=1;push_error(message)
class Backend extends RefCounted:
	var request:Dictionary
	var mode:="predictor"
	func solve_grasp_fem(value:Dictionary)->Dictionary:
		request=value.duplicate(true)
		var stats:=PackedFloat64Array();stats.resize(12);var reaction:=PackedFloat64Array();reaction.resize(value.targets.size())
		if mode=="false_reaction":reaction[0]=1.
		if mode=="failure":return {"status":1,"xyz":value.xyz,"stats":stats,"reaction":reaction}
		return {"status":0,"xyz":value.xyz,"stats":stats,"reaction":reaction}
func _initialize()->void:
	var model=load("res://scripts/embedded_membrane.gd").new()
	check(model.has_method("grasp") and model.has_method("release_hand"),"embedded material supports a source-face-bound surgical grasp")
	if failures:quit(1);return
	var points:=PackedVector3Array([Vector3.ZERO,Vector3.RIGHT,Vector3.BACK]);var indices:=PackedInt32Array([0,2,1])
	model.initialize(points,indices,PackedByteArray([0,0,0]),1.)
	var before:Dictionary=model.snapshot()
	check(model.grasp(0,0).valid,"acquisition binds the actual material point without moving it")
	var acquired:Dictionary=model.snapshot()
	check(acquired.xyz==before.xyz and acquired.previous==before.previous and acquired.time==0. and acquired.grasps.size()==1,"grasp acquisition introduces no material impulse or hidden time step")
	check(not model.grasp(1,0).valid and not model.grasp(2,1).valid,"the same material point and invalid hand cannot acquire another attachment")
	var force:=PackedFloat64Array();force.resize(9);var backend:=Backend.new()
	check(model.advance(1./60.,force,backend,2.,3.).valid,"already satisfied exact grasp advances a rigid rest state")
	check(backend.request.grip_weights[0]==1. and backend.request.gap_tolerance==1e-9,"adapter passes actual material weights and original equality tolerance")
	var saved:Dictionary=model.snapshot()
	var moved:Dictionary=model.advance(1./60.,force,backend,2.,3.,1.,100,{0:PackedFloat64Array([0.,.005,0.])})
	check(not moved.valid and model.snapshot()==saved,"fabricated success cannot publish a material point that misses the commanded grasp target")
	backend.mode="false_reaction"
	check(not model.advance(1./60.,force,backend,2.,3.).valid and model.snapshot()==saved,"fabricated grip reaction cannot bypass independent physical force balance")
	backend.mode="failure"
	check(not model.advance(1./60.,force,backend,2.,3.,1.,100,{0:PackedFloat64Array([0.,.005,0.])}).valid and model.snapshot()==saved,"failed grip solve retains accepted target binding motion history and clock")
	model.release_hand(0)
	var released:Dictionary=model.snapshot()
	check(released.grasps.is_empty() and released.xyz==saved.xyz and released.previous==saved.previous and released.time==saved.time,"release removes the attachment without resetting accepted velocity or time")
	var center:=PackedVector3Array([Vector3.ZERO,Vector3(-1,0,-1),Vector3(1,0,-1),Vector3(1,0,1),Vector3(-1,0,1)])
	var faces:=PackedInt32Array([0,2,1,0,3,2,0,4,3,0,1,4]);var anchors:=PackedByteArray([0,0,0,0,0])
	model.initialize(center,faces,anchors,1.);model.grasp(0,0)
	var a:=Vector3(0,-.2,-1.2);var b:=Vector3(0,-.2,1.2);var up:=Vector3.UP*.4
	var severed:Dictionary=model.incise_patches([PackedVector3Array([a,b,b+up]),PackedVector3Array([a,b+up,a+up])])
	check(severed.valid and severed.changed and model.snapshot().grasps.is_empty(),"cutting the attachment face into two material banks releases the severed grasp instead of picking a bank")
	model.initialize(center,faces,anchors,1.);model.grasp(0,1)
	var retained:Dictionary=model.incise_patches([PackedVector3Array([a,b,b+up]),PackedVector3Array([a,b+up,a+up])])
	check(retained.valid and model.snapshot().grasps.size()==1,"a unique surviving attachment remaps its source face through refinement")
	print("Embedded grasp contract: ",failures," failures");quit(1 if failures else 0)
