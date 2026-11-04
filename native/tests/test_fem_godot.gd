extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok:failures+=1;push_error(message)
func _initialize()->void:
	check(ClassDB.class_exists("MembraneFEMKernel"),"embedded FEM kernel registers through the real Godot extension")
	if failures:quit(1);return
	var kernel=ClassDB.instantiate("MembraneFEMKernel")
	var request:={"xyz":PackedFloat64Array([0,0,0,1.06,.03,0,0,0,1]),"inverse":PackedFloat64Array([0.,4.,7.]),"nodes":PackedInt32Array([0,1,2]),"gradients":PackedFloat64Array([-1.,1.,0.,-1.,0.,1.]),"areas":PackedFloat64Array([.5]),"mu":2.,"lambda":3.,"dt":1./60.,"budget":100,"force_tolerance":1e-8}
	var before:Dictionary=request.duplicate(true)
	var solved:Dictionary=kernel.solve_fem(request)
	check(solved.status==0 and solved.stats[1]<=1e-8,"real packed-array FEM solve meets the original force gate")
	check(solved.xyz.slice(0,3)==request.xyz.slice(0,3) and request==before,"native bridge preserves exact fixed controls and caller arrays")
	var evaluated:Dictionary=kernel.evaluate_fem(request.merged({"xyz":solved.xyz},true))
	check(evaluated.status==0 and evaluated.gradient.size()==request.xyz.size(),"native bridge exposes independent elastic evaluation")
	var maximum:=0.
	for node in [1,2]:
		for j in range(3):maximum=maxf(maximum,absf(evaluated.gradient[node*3+j]+(solved.xyz[node*3+j]-request.xyz[node*3+j])/(request.inverse[node]*request.dt*request.dt)))
	check(maximum<=1e-8,"bridge output independently satisfies its implicit force equation")
	for malformed in [{},request.merged({"nodes":PackedFloat64Array([0,1,2])},true),request.merged({"gradients":PackedFloat64Array([0.])},true),request.merged({"areas":[]},true),request.merged({"mu":"2"},true),request.merged({"budget":1.5},true),request.merged({"inverse":PackedFloat64Array([0.,4.])},true)]:
		check(kernel.solve_fem(malformed).status==-1,"FEM bridge rejects malformed type/shape before native pointer access")
	var exhausted:Dictionary=kernel.solve_fem(request.merged({"budget":0},true))
	check(exhausted.status==1 and exhausted.xyz==request.xyz,"native bridge cannot publish a budget-exhausted candidate")
	print("Native FEM Godot bridge: ",failures," failures");quit(1 if failures else 0)
