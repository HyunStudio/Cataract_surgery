extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok:failures+=1;push_error(message)
func elastic(x:PackedFloat64Array)->PackedFloat64Array:
	var f:=PackedFloat64Array();f.resize(6)
	for a in range(3):f[a*2]=x[3+a]-x[a];f[a*2+1]=x[6+a]-x[a]
	var c00:=0.;var c01:=0.;var c11:=0.
	for a in range(3):c00+=f[a*2]*f[a*2];c01+=f[a*2]*f[a*2+1];c11+=f[a*2+1]*f[a*2+1]
	var determinant:=c00*c11-c01*c01;var h:=1.5*log(determinant)-2.
	var g:=PackedFloat64Array();g.resize(9)
	for a in range(3):
		var first:float=(2.*f[a*2]+h*(f[a*2]*c11-f[a*2+1]*c01)/determinant)*.5
		var second:float=(2.*f[a*2+1]+h*(f[a*2+1]*c00-f[a*2]*c01)/determinant)*.5
		g[a]=-first-second;g[3+a]=first;g[6+a]=second
	return g
func _initialize()->void:
	check(ClassDB.class_exists("MembraneFEMKernel"),"real coupled bridge registers kernel")
	if failures:quit(1);return
	var kernel=ClassDB.instantiate("MembraneFEMKernel")
	check(kernel.has_method("solve_precise_contact_fem") and kernel.has_method("solve_contact_fem"),"actual extension exposes coupled implicit candidate")
	if failures:quit(1);return
	var request:={"xyz":PackedFloat64Array([0.,0.,0.,1.,0.,0.,0.,0.,1.]),"inverse":PackedFloat64Array([1.,1.,1.]),"nodes":PackedInt32Array([0,1,2]),"gradients":PackedFloat64Array([-1.,1.,0.,-1.,0.,1.]),"areas":PackedFloat64Array([.5]),"mu":2.,"lambda":3.,"dt":1./60.,"budget":250,"force_tolerance":1e-8,"gap_tolerance":1e-9,"complementarity_tolerance":1e-11,"grip_nodes":PackedInt32Array([0,0,0]),"grip_weights":PackedFloat64Array([1.,0.,0.]),"targets":PackedFloat64Array([0.,0.,0.]),"face_nodes":PackedInt32Array([0,1,2]),"face_weights":PackedFloat64Array([1.,0.,0.,0.,1.,0.,0.,0.,1.]),"capsules":PackedFloat64Array([.3,.05,.3,.3,.05,.3,.1])}
	var saved:=request.duplicate(true);var maximum:=0.
	for mode in ["solve_contact_fem","solve_precise_contact_fem"]:
		for hands in [1,2]:
			var input:=request.duplicate(true)
			if hands==2:input.grip_nodes.append_array(PackedInt32Array([1,1,1]));input.grip_weights.append_array(PackedFloat64Array([1.,0.,0.]));input.targets.append_array(PackedFloat64Array([1.,0.,0.]))
			var result:Dictionary=kernel.call(mode,input)
			check(result.status==0 and result.xyz.size()==9 and result.reaction.size()==hands*3 and result.dual.size()==1 and result.stats.size()==16,"actual coupled packed candidate returns both reactions")
			if result.status!=0:print(result);quit(1);return
			var contact:Dictionary=kernel.contact_fem({"controls":result.xyz,"weights":request.face_weights,"segment":request.capsules.slice(0,6),"radius":.1})
			check(contact.status==0 and result.dual[0]>=0. and contact.values[1]>=-1e-9 and absf(result.dual[0]*(contact.values[0]/.01-1.))<=1e-11,"actual bridge independently meets primal/nonnegative/complementarity gates")
			var g:=elastic(result.xyz)
			for k in range(9):g[k]+=(result.xyz[k]-input.xyz[k])/(input.dt*input.dt)-result.dual[0]*contact.gradient[k]/.01
			for hand in range(hands):
				for axis in range(3):
					g[hand*3+axis]+=result.reaction[hand*3+axis]
					check(absf(result.xyz[hand*3+axis]-input.targets[hand*3+axis])<=1e-9,"held point matches accepted requested target")
			for value in g:maximum=maxf(maximum,absf(value))
	check(maximum<=1e-8 and request==saved,"independent GDScript original force includes both reactions and caller data remains untouched")
	for malformed in [{},request.merged({"face_nodes":[]},true),request.merged({"face_nodes":PackedInt32Array([0,1])},true),request.merged({"face_weights":PackedFloat64Array([1.])},true),request.merged({"capsules":PackedFloat64Array([0.])},true),request.merged({"complementarity_tolerance":"1e-11"},true),request.merged({"budget":1.5},true),request.merged({"grip_weights":PackedInt32Array([1,0,0])},true)]:
		for mode in ["solve_contact_fem","solve_precise_contact_fem"]:
			var bad:Dictionary=kernel.call(mode,malformed)
			check(bad.status==-1 and bad.reaction.is_empty() and bad.dual.is_empty(),"typed coupled bridge rejects malformed data without reaction publication")
	var exhausted:Dictionary=kernel.solve_contact_fem(request.merged({"budget":0},true))
	check(exhausted.status!=0 and exhausted.xyz==request.xyz and exhausted.reaction.is_empty() and exhausted.dual.is_empty(),"failed candidate preserves input positions and publishes neither reaction")
	print("Native coupled FEM Godot bridge: ",failures," failures; force=",maximum);quit(1 if failures else 0)
