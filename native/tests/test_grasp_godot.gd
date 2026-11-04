extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok:failures+=1;push_error(message)
func _initialize()->void:
	check(ClassDB.class_exists("MembraneFEMKernel"),"exact grasp bridge requires the real native FEM class")
	if failures:quit(1);return
	var kernel=ClassDB.instantiate("MembraneFEMKernel")
	check(kernel.has_method("solve_grasp_fem"),"native Godot bridge exposes exact embedded grasp constraints")
	if failures:quit(1);return
	var request:={"xyz":PackedFloat64Array([0,0,0,1,0,0,0,0,1]),"inverse":PackedFloat64Array([0.,4.,7.]),"nodes":PackedInt32Array([0,1,2]),"gradients":PackedFloat64Array([-1.,1.,0.,-1.,0.,1.]),"areas":PackedFloat64Array([.5]),"mu":2.,"lambda":3.,"dt":1./60.,"budget":100,"force_tolerance":1e-8,"gap_tolerance":1e-9,"grip_nodes":PackedInt32Array([0,1,2]),"grip_weights":PackedFloat64Array([.2,.3,.5]),"targets":PackedFloat64Array([.3,.005,.5])}
	var saved:Dictionary=request.duplicate(true)
	var result:Dictionary=kernel.solve_grasp_fem(request)
	check(result.status==0 and result.stats.size()==12 and result.reaction.size()==3,"real exact-grasp bridge returns an accepted reaction-bearing candidate")
	check(result.stats[1]<=1e-8 and result.stats[8]<=1e-9 and request==saved,"exact-grasp bridge retains force/gap gates and caller immutability")
	var evaluated:Dictionary=kernel.evaluate_fem(request.merged({"xyz":result.xyz},true));var maximum:=0.
	for axis in range(3):
		var point:=0.
		for node in range(3):
			var weight:float=request.grip_weights[node];point+=weight*result.xyz[node*3+axis]
			if request.inverse[node]==0.:continue
			var value:float=evaluated.gradient[node*3+axis]+(result.xyz[node*3+axis]-request.xyz[node*3+axis])/(request.inverse[node]*request.dt*request.dt)+weight*result.reaction[axis]
			maximum=maxf(maximum,absf(value))
		check(absf(point-request.targets[axis])<=1e-9,"actual embedded grasp point reaches its target")
	check(maximum<=1e-8,"actual attachment reaction independently balances the original physical force")
	for malformed in [{},request.merged({"grip_nodes":PackedFloat64Array([0,1,2])},true),request.merged({"grip_weights":[]},true),request.merged({"targets":PackedFloat64Array([0.,0.])},true),request.merged({"gap_tolerance":"small"},true)]:
		check(kernel.solve_grasp_fem(malformed).status==-1,"grasp bridge rejects malformed schemas before native pointer access")
	var failed:Dictionary=kernel.solve_grasp_fem(request.merged({"budget":0},true))
	check(failed.status==1 and failed.xyz==request.xyz,"grasp work exhaustion cannot publish a partial material motion")
	print("Native grasp Godot bridge: ",failures," failures");quit(1 if failures else 0)
