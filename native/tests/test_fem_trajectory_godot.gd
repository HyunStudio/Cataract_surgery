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
	check(ClassDB.class_exists("MembraneFEMKernel"),"actual extension registers original-material kernel")
	if failures:quit(1);return
	var kernel=ClassDB.instantiate("MembraneFEMKernel")
	check(kernel.has_method("solve_trajectory_fem"),"real extension exposes original-material trajectory candidate")
	if failures:quit(1);return
	var packet:=PackedFloat64Array();packet.resize(41)
	for off in [0,3]:packet[off]=.3;packet[off+1]=.2;packet[off+2]=.3
	for off in [6,9]:packet[off]=.3;packet[off+1]=.05;packet[off+2]=.3
	packet[12]=.1
	var request:={"xyz":PackedFloat64Array([0.,0.,0.,1.,0.,0.,0.,0.,1.]),"inverse":PackedFloat64Array([1.,1.,1.]),"nodes":PackedInt32Array([0,1,2]),"gradients":PackedFloat64Array([-1.,1.,0.,-1.,0.,1.]),"areas":PackedFloat64Array([.5]),"mu":2.,"lambda":3.,"dt":.1,"budget":250,"force_tolerance":1e-8,"gap_tolerance":1e-9,"complementarity_tolerance":1e-11,"grip_nodes":PackedInt32Array(),"grip_weights":PackedFloat64Array(),"targets":PackedFloat64Array(),"face_nodes":PackedInt32Array([0,1,2]),"face_weights":PackedFloat64Array([1.,0.,0.,0.,1.,0.,0.,0.,1.]),"capsules":packet.slice(6,13),"kinds":PackedInt32Array([0]),"packets":packet,"times":PackedFloat64Array([.5,1.])}
	request.previous=request.xyz.duplicate();var saved:=request.duplicate(true)
	var result:Dictionary=kernel.solve_trajectory_fem(request)
	check(result.status==0 and result.xyz.size()==9 and result.dual.size()==2 and result.stats.size()==16,"typed layered candidate returns original controls and both multipliers")
	if result.status!=0:print(result);quit(1);return
	var g:=elastic(result.xyz)
	for k in range(9):g[k]+=(result.xyz[k]-request.xyz[k])/(request.dt*request.dt)
	for layer in range(2):
		var t:float=request.times[layer];var posed:PackedFloat64Array=request.xyz.duplicate()
		for k in range(9):posed[k]+=t*(result.xyz[k]-request.xyz[k])
		var segment:=PackedFloat64Array()
		for k in range(6):segment.append(packet[k]+t*(packet[k+6]-packet[k]))
		var q:Dictionary=kernel.contact_fem({"controls":posed,"weights":request.face_weights,"segment":segment,"radius":.1})
		check(q.status==0 and q.values[1]>=-1e-9 and result.dual[layer]>=0.,"independent sampled gap and nonnegative multiplier")
		if q.status!=0:quit(1);return
		check(absf(result.dual[layer]*(q.values[0]/(.1*.1)-1.))<=1e-11,"independent sampled complementarity")
		for k in range(9):g[k]-=result.dual[layer]*t*q.gradient[k]/(.1*.1)
	var maximum:=0.
	for value in g:maximum=maxf(maximum,absf(value))
	check(maximum<=1e-8 and request==saved,"independent original force includes time pullback and preserves request")
	var endpoint:Dictionary=kernel.solve_trajectory_fem(request.merged({"times":PackedFloat64Array([1.])},true))
	var static_result:Dictionary=kernel.solve_contact_fem(request)
	check(endpoint==static_result,"endpoint-only typed candidate preserves static result bitwise")
	for malformed in [{},request.merged({"previous":PackedFloat64Array([0.])},true),request.merged({"times":[.5,1.]},true),request.merged({"times":PackedFloat64Array([0.,1.])},true),request.merged({"kinds":PackedFloat64Array([0.])},true),request.merged({"packets":PackedFloat64Array([0.])},true),request.merged({"budget":1.5},true)]:
		var bad:Dictionary=kernel.solve_trajectory_fem(malformed)
		check(bad.status==-1 and bad.reaction.is_empty() and bad.dual.is_empty(),"malformed trajectory request publishes no reactions")
	var failed:Dictionary=kernel.solve_trajectory_fem(request.merged({"budget":0},true))
	check(failed.status!=0 and failed.xyz==request.xyz and failed.reaction.is_empty() and failed.dual.is_empty(),"failed typed trajectory candidate is atomic")
	print("Native trajectory FEM Godot bridge: ",failures," failures; force=",maximum);quit(1 if failures else 0)
