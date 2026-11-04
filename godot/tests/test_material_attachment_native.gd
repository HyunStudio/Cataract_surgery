extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok:failures+=1;push_error(message)
func model():
	var tissue=load("res://scripts/embedded_membrane.gd").new()
	tissue.initialize(PackedVector3Array([Vector3.ZERO,Vector3.RIGHT,Vector3.BACK]),PackedInt32Array([0,1,2]),PackedByteArray([0,0,0]),1.)
	return tissue
func _initialize()->void:
	check(ClassDB.class_exists("MembraneFEMKernel"),"material point motion needs the actual native constrained FEM")
	if failures:quit(1);return
	var backend=ClassDB.instantiate("MembraneFEMKernel");var maximum:=0.
	for hands in [1,2]:
		var tissue=model();var material:Array=[PackedFloat64Array([.6,.2,.2]),PackedFloat64Array([.2,.6,.2])]
		for hand in range(hands):check(tissue.grasp_material(hand,0,material[hand]).valid,"actual one/two-hand interior grasp registers")
		var targets:Dictionary={};var start:Dictionary=tissue.snapshot();var force:=PackedFloat64Array();force.resize(start.xyz.size())
		for hand in range(hands):
			var target:PackedFloat64Array=start.grasps[hand].target.duplicate();target[1]=.001 if hand==0 else -.001;targets[hand]=target
		var moved:Dictionary=tissue.advance(1./60.,force,backend,2.,3.,1.,250,targets)
		check(moved.valid,"actual material constraints satisfy original native and independent engine force: "+moved.reason)
		if not moved.valid:quit(1);return
		var after:Dictionary=tissue.snapshot();maximum=maxf(maximum,moved.force_inf)
		check(after.steps==start.steps+1 and after.previous==start.xyz and after.time==start.time+1./60.,"material point motion publishes one physical clock/history step")
		for hand in range(hands):
			var held:Dictionary=after.grasps[hand];var point:=PackedFloat64Array([0.,0.,0.])
			for j in range(3):
				for axis in range(3):point[axis]+=after.xyz[held.nodes[j]*3+axis]*held.weights[j]
			for axis in range(3):check(absf(point[axis]-targets[hand][axis])<=1e-9,"actual accepted material point meets requested exact hand target")
			check(held.reaction.size()==3 and held.target==targets[hand],"reaction and target belong to the same accepted material attachment")
		var saved:Dictionary=tissue.snapshot();targets[0][1]+=.01
		var failed:Dictionary=tissue.advance(1./60.,force,backend,2.,3.,1.,0,targets)
		check(not failed.valid and tissue.snapshot()==saved,"exhausted native candidate cannot publish new targets, reactions, controls or histories")
	check(maximum<=1e-8,"independent original material force tolerance remains unchanged")
	print("Native material attachment: ",failures," failures; force=",maximum);quit(1 if failures else 0)
